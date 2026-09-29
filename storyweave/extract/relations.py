"""Retrofit R4: build the closed-relation graph from GLiNER-RelEx + the validator.

This is the producer that replaces the co-occurrence rule R1 switched off. The shape is
deliberately boring:

    relex proposes  ->  the validator disposes  ->  one row per (relation, head, tail)

Three things are worth defending at an interview:

* **The quote is a slice, not a summary.** Every proposal's quote is a literal slice of
  the chapter's ``clean_text``, expanded to sentence boundaries from the two mention
  offsets. That is what lets validator check (a) be an exact ``in`` test rather than a
  fuzzy match, and it is why :class:`RelationSpan` had to grow offsets.
* **Two passes, because the kin guard is not local.** A kin claim with no possessive can
  still be accepted if the same claim recurs in another chapter, so every proposal is
  collected before any is judged.
* **Weight instead of duplicates.** Repeat evidence for the same (relation, head, tail)
  increments ``weight`` and keeps the best quote. Different relations on the same pair
  stay separate rows -- that is defect D2, and the unique index is on the relation too.

Degrades like every other model layer (rule #4): if relex cannot load, the report says
so and the database is left with whatever it already had.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from storyweave.config import Settings, get_settings
from storyweave.db.models import (
    RELATION_RING,
    Edge,
    ExtractionMethod,
    Relation,
    RelationGrade,
    RelationTier,
)
from storyweave.db.repository import Repository
from storyweave.extract.cues import DEFAULT_CUES
from storyweave.extract.validator import (
    RelationProposal,
    ValidationContext,
    ValidationResult,
    validate,
)
from storyweave.ingest.work_config import WorkConfig
from storyweave.nlp.cluster import normalize_surface
from storyweave.nlp.relex import (
    R4_RELATION_PROMPTS,
    RelexExtractor,
    RelexProtocol,
    _node_surface_index,
)

#: Relation -> the storage tier its rows keep using, so R4 needs no schema change to
#: `edges.tier`. Ring 1 minus SAME_AS is social; SAME_AS is identity; ring 2 is
#: structural (it is what the Tier-1 builder used to guess at).
_TIER_FOR_RING = {1: RelationTier.SOCIAL, 2: RelationTier.STRUCTURAL}

#: How far a quote may grow when expanding to sentence boundaries. A citation a reader
#: cannot check at a glance is not really a citation.
MAX_QUOTE_CHARS = 400

_SENT_END = re.compile(r"[.!?][\"'”’)\]]*\s")


@dataclass
class RelationReport:
    """What one R4 relation build did, in numbers the phase report can quote."""

    work_id: int
    proposals: int = 0
    edges_written: int = 0
    edges_reinforced: int = 0
    rejected: int = 0
    per_relation: dict[str, int] = field(default_factory=dict)
    per_grade: dict[str, int] = field(default_factory=dict)
    rejections_by_reason: dict[str, int] = field(default_factory=dict)
    degraded: bool = False

    def summary(self) -> str:
        if self.degraded:
            return f"work id={self.work_id}: relex unavailable - no R4 edges written"
        by_rel = ", ".join(f"{r}:{n}" for r, n in sorted(self.per_relation.items()))
        by_grade = ", ".join(f"{g}:{n}" for g, n in sorted(self.per_grade.items()))
        return (
            f"work id={self.work_id}: {self.proposals} proposals -> "
            f"{self.edges_written} edges (+{self.edges_reinforced} reinforcements), "
            f"{self.rejected} rejected. [{by_rel}] grades [{by_grade}]"
        )


def expand_to_sentence(text: str, start: int, end: int, max_chars: int = MAX_QUOTE_CHARS) -> str:
    """The smallest sentence-ish span of ``text`` containing ``[start, end)``.

    Walks back to the end of the previous sentence and forward to the end of this one,
    then hard-caps the length. The result is always a literal substring of ``text``, so
    validator check (a) is an exact containment test.
    """
    lo = max(0, start - max_chars)
    left = lo
    for match in _SENT_END.finditer(text, lo, start):
        left = match.end()
    right_match = _SENT_END.search(text, end, min(len(text), end + max_chars))
    right = right_match.end() if right_match else min(len(text), end + max_chars)
    return text[left:right].strip()


def _labels_for_nodes(repo: Repository, work_id: int) -> dict[int, list[str]]:
    """Every name an entity has, UNFENCED, for the validator's both-names test.

    Unfenced is correct here and is not a fence bypass: this decides whether the QUOTE
    names the participants, which is a property of the sentence, not of the reader. What
    the reader may see is decided later and only by ``query/fence.py``, on
    ``revealed_chapter``.
    """
    labels: dict[int, list[str]] = {}
    for node in repo.list_nodes(work_id):
        if node.id is None:
            continue
        names = [node.name]
        names.extend(label.label for label in repo.list_entity_labels(node.id))
        # Longest first so "Orin Drask" is preferred over "Orin" when both are present.
        labels[node.id] = sorted({n for n in names if n}, key=len, reverse=True)
    return labels


def build_relations(
    work_id: int,
    repo: Repository,
    config: WorkConfig | None = None,
    settings: Settings | None = None,
    extractor: RelexProtocol | None = None,
    proposal_sink: Callable[[RelationProposal, ValidationResult], None] | None = None,
) -> RelationReport:
    """Run relex over a work and persist the validated closed-relation edges.

    ``proposal_sink``, when given, is handed EVERY proposal with its verdict, accepted
    or not. R4's recall audit needs that: to say which stage lost a gold relation you
    have to know whether the model ever proposed it, and an accepted proposal leaves no
    trace in ``validator_rejections``.
    """
    cfg = config or WorkConfig()
    cfg_settings = settings or get_settings()
    report = RelationReport(work_id=work_id)

    if extractor is None:
        try:
            extractor = RelexExtractor(
                model_name=cfg.relations.relex_model,
                ner_threshold=cfg.relations.relex_ner_threshold,
                rel_threshold=cfg.relations.relex_rel_threshold,
                settings=cfg_settings,
                # R4's own prompt set, and no canonical map: `span.relation` comes back
                # as the prompt phrase, which is what R4_RELATION_PROMPTS is keyed on.
                prompts=list(R4_RELATION_PROMPTS),
            )
        except Exception:  # pragma: no cover - never hard-depend on a model
            report.degraded = True
            return report

    surface_to_node = _node_surface_index(repo, work_id)
    chapters = repo.list_chapters(work_id)
    clean_text = {c.ordinal: c.clean_text for c in chapters}
    node_types = {n.id: n.type for n in repo.list_nodes(work_id) if n.id is not None}
    labels = _labels_for_nodes(repo, work_id)
    cues = {**DEFAULT_CUES, **_configured_cues(cfg)}

    # --- pass 1: propose ------------------------------------------------- #
    proposals: list[RelationProposal] = []
    try:
        for chapter in chapters:
            assert chapter.id is not None
            for chunk in repo.list_chunks(chapter.id):
                for span in extractor.extract(chunk.text):
                    mapped = R4_RELATION_PROMPTS.get(span.relation)
                    if mapped is None:
                        continue  # a prompt outside the closed twelve
                    relation, reverse = mapped
                    src_surface, tgt_surface = span.source_surface, span.target_surface
                    starts = (span.source_start, span.target_start)
                    ends = (span.source_end, span.target_end)
                    if reverse:
                        src_surface, tgt_surface = tgt_surface, src_surface
                    quote = expand_to_sentence(
                        chapter.clean_text,
                        chunk.char_start + min(starts),
                        chunk.char_start + max(ends),
                    )
                    proposals.append(
                        RelationProposal(
                            relation=relation,
                            source_id=surface_to_node.get(normalize_surface(src_surface)),
                            target_id=surface_to_node.get(normalize_surface(tgt_surface)),
                            quote=quote,
                            quote_chapter=chapter.ordinal,
                            source_surface=src_surface,
                            target_surface=tgt_surface,
                            score=span.score,
                            kin_role=span.relation if relation == Relation.KIN_OF else None,
                        )
                    )
    except Exception:  # pragma: no cover - model died mid-run -> degrade
        report.degraded = True
        return report

    report.proposals = len(proposals)

    # The kin guard's second limb: which (pair, kin role) claims recur across chapters.
    kin_claims: dict[tuple[int, int, str], set[int]] = defaultdict(set)
    for proposal in proposals:
        if (
            proposal.relation == Relation.KIN_OF
            and proposal.source_id is not None
            and proposal.target_id is not None
        ):
            key = (
                min(proposal.source_id, proposal.target_id),
                max(proposal.source_id, proposal.target_id),
                proposal.kin_role or "",
            )
            kin_claims[key].add(proposal.quote_chapter)

    context = ValidationContext(
        clean_text=clean_text,
        node_types=node_types,
        labels=labels,
        kin_claim_chapters=kin_claims,
        cues=cues,
    )

    # --- pass 2: dispose ------------------------------------------------- #
    # Only this producer's own rows are cleared: curated and legacy edges survive,
    # exactly as R1's clear_edges_by_method fix requires.
    repo.clear_edges_by_method(work_id, ExtractionMethod.GLINER)
    repo.clear_validator_rejections(work_id)

    for proposal in proposals:
        result = validate(proposal, context)
        if proposal_sink is not None:
            proposal_sink(proposal, result)
        if not result.ok:
            report.rejected += 1
            reason = result.reason.value if result.reason else "UNKNOWN"
            report.rejections_by_reason[reason] = report.rejections_by_reason.get(reason, 0) + 1
            repo.add_validator_rejection(
                work_id,
                proposal.relation,
                reason,
                source_surface=proposal.source_surface,
                target_surface=proposal.target_surface,
                source_id=proposal.source_id,
                target_id=proposal.target_id,
                quote=proposal.quote,
                quote_chapter=proposal.quote_chapter,
                detail=result.detail,
            )
            continue

        assert result.relation is not None
        assert result.source_id is not None and result.target_id is not None
        existing = repo.get_edge_by_relation_pair(
            work_id, result.relation.value, result.source_id, result.target_id
        )
        if existing is not None:
            repo.reinforce_edge(
                existing,
                first_seen_chapter=proposal.quote_chapter,
                revealed_chapter=proposal.quote_chapter,
                grade=result.grade,
                quote=proposal.quote,
                quote_chapter=proposal.quote_chapter,
                surface_term=result.surface_term,
            )
            report.edges_reinforced += 1
            continue

        repo.add_edge(
            Edge(
                work_id=work_id,
                source_id=result.source_id,
                target_id=result.target_id,
                relation=result.relation.value,
                tier=_TIER_FOR_RING[RELATION_RING[result.relation]],
                # R4 task 4: an edge is revealed at the chapter of its earliest
                # qualifying quote. Reinforcement can only lower it.
                first_seen_chapter=proposal.quote_chapter,
                revealed_chapter=proposal.quote_chapter,
                extraction_method=ExtractionMethod.GLINER,
                evidence_span=proposal.quote,
                weight=1,
                grade=result.grade,
                quote=proposal.quote,
                quote_chapter=proposal.quote_chapter,
                kin_role=result.kin_role,
                surface_term=result.surface_term,
            )
        )
        report.edges_written += 1
        name = result.relation.value
        report.per_relation[name] = report.per_relation.get(name, 0) + 1
        grade = result.grade.value if result.grade else "NONE"
        report.per_grade[grade] = report.per_grade.get(grade, 0) + 1

    return report


def _configured_cues(cfg: WorkConfig) -> dict[Relation, list[str]]:
    """Per-work cue overrides from ``storyweave.toml`` (knobs are data, never code)."""
    out: dict[Relation, list[str]] = {}
    for name, words in cfg.relations.cues.items():
        try:
            out[Relation(name)] = list(words)
        except ValueError:
            continue  # a name outside the closed twelve is ignored, not an error
    return out


__all__ = [
    "MAX_QUOTE_CHARS",
    "RelationGrade",
    "RelationReport",
    "build_relations",
    "expand_to_sentence",
]
