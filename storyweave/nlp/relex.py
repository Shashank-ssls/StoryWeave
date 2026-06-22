"""Tier-2 social-relation extraction with GLiNER-RelEx (Phase 7a).

This is the FIRST enhancement layer above the GLiNER floor — and it is still pure
enhancement (rule #4): with the relex model absent the system degrades cleanly to
the Phase 3/5 Tier-1 structural graph. The capability ships *inside* the already
pinned ``gliner`` package (no new framework): ``GLiNER.inference(..., relations=[...],
return_relations=True)`` returns entities + typed relations in one forward pass.
We run the small ``gliner-relex-base-v1.0`` checkpoint on CPU (no VRAM risk).

Design choices (all interview-defensible):

* **No new node type, no phantom nodes.** Relex finds relations between text spans;
  we keep an edge only when BOTH spans anchor (by normalized surface) to canonical
  entities the GLiNER floor already grounded. Relex enriches edges, never invents
  entities — so a hallucinated span simply yields no edge.
* **Provenance ``method='gliner'``** (it is a GLiNER model). The ``tier`` field (2 =
  SOCIAL) is what distinguishes these from the Tier-1 ``method='rule'`` edges, so no
  schema migration is needed.
* **Same reveal stamps as Tier-1.** A *stated* social relation is known to the reader
  exactly when they read it, so ``revealed_chapter == first_seen_chapter == the
  chapter of the chunk it was extracted from``. (Reveal-shifting secrets are Tier-3,
  Phase 7c.) These edges flow through the existing ``edges`` table and therefore
  through ``query/fence.py`` unchanged — no new unfenced path.

The heavy ``gliner``/``torch`` import is LAZY (inside ``_ensure_loaded``) so this
module imports cleanly under the light ``.venv``; the model only loads under
``.venv-ml``. Tests inject a fake extractor via :class:`RelexProtocol`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from storyweave.config import Settings, get_settings
from storyweave.db.models import Edge, ExtractionMethod, RelationTier
from storyweave.db.repository import Repository
from storyweave.ingest.work_config import WorkConfig
from storyweave.nlp.cluster import normalize_surface
from storyweave.nlp.extractor import configure_hf_cache

if TYPE_CHECKING:  # pragma: no cover - typing only
    from gliner import GLiNER

# Natural-language relation prompts -> canonical Tier-2 relation (SPEC §5.3). GLiNER
# is zero-shot, so we prompt it with phrases and map the returned phrase back to one
# of the eighteen Tier-2 relations. Multiple phrases may target the same relation.
RELATION_PROMPTS: dict[str, str] = {
    "ally of": "Ally", "allied with": "Ally", "friend of": "Ally",
    "enemy of": "Enemy",
    "rival of": "Rival",
    "mentor of": "Mentor", "teacher of": "Mentor", "trained": "Mentor",
    "raised": "Mentor",
    "student of": "Student", "apprentice of": "Student",
    "parent of": "Parent", "father of": "Parent", "mother of": "Parent",
    "child of": "Child", "son of": "Child", "daughter of": "Child",
    "sibling of": "Sibling", "brother of": "Sibling", "sister of": "Sibling",
    "uncle of": "Family", "aunt of": "Family", "relative of": "Family",
    "spouse of": "Spouse", "married to": "Spouse",
    "in love with": "Romantic", "lover of": "Romantic",
    "betrayed": "Betrayed",
    "serves": "Serves", "works for": "Serves", "serves under": "Serves",
    "killed": "Killed",
    "protects": "Protects",
    "fears": "Fears",
    "respects": "Respects",
}

# Relations with no inherent direction — their endpoints are stored order-independent
# so A–Ally–B and B–Ally–A collapse to one edge.
SYMMETRIC_RELATIONS: frozenset[str] = frozenset(
    {"Ally", "Enemy", "Rival", "Sibling", "Spouse", "Family", "Romantic"}
)

# Entity labels for the relex NER pass. The anchoring step re-grounds every span to a
# canonical node, so this only needs to be broad enough to surface the right spans.
ENTITY_LABELS: list[str] = [
    "person", "organization", "location", "title", "item", "creature", "concept",
]


@dataclass
class RelationSpan:
    """One directed relation from relex, before anchoring to canonical nodes."""

    source_surface: str
    relation: str  # canonical Tier-2 relation
    target_surface: str
    score: float
    evidence: str = ""


class RelexProtocol(Protocol):
    """The surface the orchestration depends on (lets tests inject a fake)."""

    def extract(self, text: str) -> list[RelationSpan]: ...


class RelexExtractor:
    """Lazy wrapper around a GLiNER-RelEx checkpoint mapping outputs to Tier-2 vocab."""

    def __init__(
        self,
        model_name: str | None = None,
        ner_threshold: float | None = None,
        rel_threshold: float | None = None,
        device: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self.model_name = model_name or self._settings.relex_model
        self.ner_threshold = (
            ner_threshold if ner_threshold is not None else self._settings.relex_ner_threshold
        )
        self.rel_threshold = (
            rel_threshold if rel_threshold is not None else self._settings.relex_rel_threshold
        )
        self.device = device or self._settings.relex_device
        self._model: GLiNER | None = None

    def _ensure_loaded(self) -> GLiNER:
        if self._model is None:
            configure_hf_cache(self._settings)
            from gliner import GLiNER  # lazy: heavy import only under .venv-ml

            model = GLiNER.from_pretrained(self.model_name)
            if self.device and self.device != "cpu":
                model = model.to(self.device)
            self._model = model
        return self._model

    def extract(self, text: str) -> list[RelationSpan]:
        """Extract Tier-2 relations from ``text`` (offsets relative to it)."""
        if not text.strip():
            return []
        model = self._ensure_loaded()
        prompts = list(RELATION_PROMPTS.keys())
        _entities, relations = model.inference(
            texts=[text],
            labels=ENTITY_LABELS,
            relations=prompts,
            threshold=self.ner_threshold,
            relation_threshold=self.rel_threshold,
            return_relations=True,
            flat_ner=False,
        )
        out: list[RelationSpan] = []
        for rel in relations[0]:
            canonical = RELATION_PROMPTS.get(rel["relation"])
            if canonical is None:
                continue  # unknown prompt -> stay within the Tier-2 vocabulary
            head: dict[str, Any] = rel["head"]
            tail: dict[str, Any] = rel["tail"]
            out.append(
                RelationSpan(
                    source_surface=head["text"],
                    relation=canonical,
                    target_surface=tail["text"],
                    score=float(rel["score"]),
                    evidence=_evidence(text, head, tail),
                )
            )
        return out


def _evidence(text: str, head: dict[str, Any], tail: dict[str, Any], pad: int = 30) -> str:
    """A short quote spanning the two related entities (provenance)."""
    starts = [int(head.get("start", 0)), int(tail.get("start", 0))]
    ends = [int(head.get("end", 0)), int(tail.get("end", 0))]
    start = max(0, min(starts) - pad)
    end = min(len(text), max(ends) + pad)
    return re.sub(r"\s+", " ", text[start:end]).strip()


@dataclass
class _EdgeAccum:
    """Best evidence for one (source, target, relation) across the work."""

    score: float = 0.0
    first_chapter: int = 10**9
    evidence: str = ""


@dataclass
class SocialReport:
    work_id: int
    edges_added: int = 0
    per_relation: dict[str, int] = field(default_factory=dict)
    degraded: bool = False  # True when the relex model was unavailable (graceful floor)

    def summary(self) -> str:
        if self.degraded:
            return (
                f"work id={self.work_id}: relex unavailable — kept the Tier-1 floor "
                f"(0 Tier-2 edges added)"
            )
        by_rel = ", ".join(f"{r}:{n}" for r, n in sorted(self.per_relation.items()))
        return f"work id={self.work_id}: {self.edges_added} Tier-2 edges ({by_rel})"


def _node_surface_index(repo: Repository, work_id: int) -> dict[str, int]:
    """Map a normalized surface -> the canonical node it most often belongs to.

    Built from the persisted mentions (which already carry the floor's clustering via
    ``node_id``) plus each node's own name, so relex spans re-ground to real entities.
    """
    votes: dict[str, dict[int, int]] = {}

    def _vote(surface: str, node_id: int) -> None:
        key = normalize_surface(surface)
        if key:
            counts = votes.setdefault(key, {})
            counts[node_id] = counts.get(node_id, 0) + 1

    for node in repo.list_nodes(work_id):
        if node.id is not None:
            _vote(node.name, node.id)
    for mention in repo.list_mentions(work_id):
        if mention.node_id is not None:
            _vote(mention.surface, mention.node_id)

    return {surface: max(counts, key=lambda nid: counts[nid]) for surface, counts in votes.items()}


def extract_social_relations(
    work_id: int,
    repo: Repository,
    config: WorkConfig | None = None,
    settings: Settings | None = None,
    extractor: RelexProtocol | None = None,
) -> SocialReport:
    """Run GLiNER-RelEx over a work and persist Tier-2 edges between canonical nodes.

    Idempotent: clears only this work's Tier-2 edges and rebuilds, leaving Tier-1
    structural edges untouched. Pure enhancement — if the relex model cannot be
    loaded, returns a degraded report and leaves the Tier-1 floor intact (rule #4).
    """
    cfg = config or WorkConfig()
    cfg_settings = settings or get_settings()
    report = SocialReport(work_id=work_id)

    if extractor is None:
        try:
            extractor = RelexExtractor(
                model_name=cfg.relations.relex_model,
                ner_threshold=cfg.relations.relex_ner_threshold,
                rel_threshold=cfg.relations.relex_rel_threshold,
                settings=cfg_settings,
            )
        except Exception:  # pragma: no cover - defensive: never hard-depend on relex
            report.degraded = True
            return report

    surface_to_node = _node_surface_index(repo, work_id)
    chapter_ordinal = {c.id: c.ordinal for c in repo.list_chapters(work_id) if c.id is not None}

    accum: dict[tuple[int, int, str], _EdgeAccum] = {}
    try:
        for chapter in repo.list_chapters(work_id):
            assert chapter.id is not None
            for chunk in repo.list_chunks(chapter.id):
                for span in extractor.extract(chunk.text):
                    src = surface_to_node.get(normalize_surface(span.source_surface))
                    tgt = surface_to_node.get(normalize_surface(span.target_surface))
                    if src is None or tgt is None or src == tgt:
                        continue  # no phantom nodes; both endpoints must be grounded
                    if span.relation in SYMMETRIC_RELATIONS and src > tgt:
                        src, tgt = tgt, src  # order-independent key for symmetric relations
                    key = (src, tgt, span.relation)
                    acc = accum.setdefault(key, _EdgeAccum())
                    ordinal = chapter_ordinal.get(chunk.chapter_id, chapter.ordinal)
                    if span.score > acc.score:
                        acc.score = span.score
                        acc.evidence = span.evidence
                    acc.first_chapter = min(acc.first_chapter, ordinal)
    except Exception:  # pragma: no cover - model failed mid-run -> degrade, keep floor
        report.degraded = True
        return report

    repo.clear_edges_by_tier(work_id, RelationTier.SOCIAL)
    for (src, tgt, relation), acc in accum.items():
        repo.add_edge(
            Edge(
                work_id=work_id,
                source_id=src,
                target_id=tgt,
                relation=relation,
                tier=RelationTier.SOCIAL,
                first_seen_chapter=acc.first_chapter,
                revealed_chapter=acc.first_chapter,  # stated relation: revealed when read
                extraction_method=ExtractionMethod.GLINER,
                evidence_span=acc.evidence,
            )
        )
        report.edges_added += 1
        report.per_relation[relation] = report.per_relation.get(relation, 0) + 1

    return report
