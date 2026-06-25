"""Tier-3 IDENTITY inference (Phase 7c) — the showcase, and pure enhancement.

This is the second LLM layer above the GLiNER/relex floor and, like every layer
above it, it is OPTIONAL (rules #4/#5): with ``llm_enabled=False`` (the default) it
produces nothing, writes nothing, and the Tier-1/Tier-2 floor + the reveal fence
stand fully intact. Nothing here is reachable without the flag — no client is
constructed and no socket is opened.

THE LOAD-BEARING RULE (this whole phase):
    An identity edge's ``revealed_chapter`` = the SMALLEST chapter k at which the
    model can conclude the identity from chapters 1..k ONLY, **backed by a quoted
    confirming clause that actually occurs in chapters 1..k.** Confirmed-only
    semantics — the chapter a careful reader could first FULLY conclude it, never a
    partial-clue guess. The Phase-7b addendum proved a plain prompt blooms an
    identity 1–2 chapters EARLY on a partial clue; the citation margin is therefore
    the PRODUCTION mechanism, not an experiment. The model MUST emit a supporting
    quote per asserted identity; this code verifies that quote occurs (normalized)
    in the fed text of chapters 1..k; an identity with NO valid in-range citation is
    NOT written, and is counted separately so a fail-closed is diagnosable.

How the reveal is computed (the addendum sweep, now production code):
    For a candidate pair of canonical nodes, sweep k = 1..(last chapter), feeding
    ONLY chapters 1..k (never past k). For EACH Tier-3 relation the model confirms
    with a verified in-range citation, record the smallest k it was confirmed at and
    write one edge with ``revealed_chapter = k``. A single pair may carry more than
    one relation at different chapters (e.g. Wren==Caelum is a SECRET_IDENTITY the
    reader concludes at ch2 and a TRANSMIGRATED_INTO the reader concludes at ch4 —
    two layered reveals, the LotM-style showcase).

Anchor, don't invent (same rule as 7a): head/tail re-ground to existing canonical
floor nodes; identity is an EDGE, never a node collapse — the slider must still show
two nodes with a blooming edge between them. Provenance ``method='llm'``, ``tier=3``
(both already in the Phase-0 CHECK constraints — no schema change). Edges flow
through the existing ``edges`` table → ``query/fence.py`` unchanged (Phase 5 already
fences identity edges by the both-endpoints rule).

The five Tier-3 relations are all in the inference VOCABULARY; the sample proves
three (SECRET_IDENTITY, ALIAS, TRANSMIGRATED_INTO). SAME_AS and REINCARNATION are
schema-and-prompt-ready but UNPROVEN until a sample exercises them.

Tests inject a fake model via :class:`IdentityProtocol`; the real model wraps the
wired :class:`~storyweave.nlp.llm.LlmClient`. No heavy import here — stdlib only.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

from storyweave.config import Settings, get_settings
from storyweave.db.models import (
    TIER3_RELATIONS,
    Edge,
    ExtractionMethod,
    Node,
    RelationTier,
)
from storyweave.db.repository import Repository
from storyweave.ingest.work_config import IdentityConfig
from storyweave.nlp.llm import LlmClient, llm_available

# Symmetric Tier-3 relation(s): endpoints stored order-independent.
_SYMMETRIC_IDENTITY: frozenset[str] = frozenset({"SAME_AS"})

# Minimum normalized length for a citation to count — guards against a model
# "quoting" a stop-word fragment that trivially occurs in any text.
_MIN_CITATION_CHARS = 8

SYSTEM_PROMPT = (
    "You are a strict identity-resolution tool for fiction. You are given a passage (the "
    "chapters a reader has read so far) and TWO named entities. MOST pairs of names are "
    "DIFFERENT people — default to NOT the same. Answer YES only if the passage EXPLICITLY "
    "equates the two (states that one IS the other, or is the other's alias / secret "
    "identity / reincarnation / transmigrated soul). Resemblance, suspicion, being in the "
    "same scene, serving the same person, or being allies/family is NOT identity. If you "
    "are not sure, answer NO.\n"
    "If (and only if) YES, choose exactly one relation:\n"
    "- SAME_AS: two plain names for one person, no secrecy or special mechanism.\n"
    "- ALIAS: one name is a known alias, codename, or persona of the other.\n"
    "- SECRET_IDENTITY: one is secretly the other; the true identity is hidden in-world.\n"
    "- REINCARNATION: one is the reborn/reincarnated continuation of the other (a past life).\n"
    "- TRANSMIGRATED_INTO: one's soul or consciousness, from another world or life, now "
    "inhabits the other's body.\n"
    "You MUST quote, as 'clue', an EXACT span that appears VERBATIM in THIS passage. "
    "Which span depends on the relation:\n"
    "- For SAME_AS / ALIAS / SECRET_IDENTITY: quote the clause that states the equivalence, "
    "naming or unmistakably referring to BOTH entities (these are co-named in the text).\n"
    "- For TRANSMIGRATED_INTO / REINCARNATION: the reveal is usually SINGLE-ANCHORED — the "
    "passage establishes that a soul or consciousness from another world or past life now "
    "inhabits ONE named body (often via inherited memories, or waking inside that body), and "
    "it need NOT name both entities in one clause. Quote that transmigration/inheritance "
    "clause exactly as it appears.\n"
    "The clue MUST occur verbatim in the passage; do NOT quote this instruction or invent a "
    "clause. If no such span exists, answer NO. Output ONLY strict JSON, no prose: "
    '{"same": true|false, "relation": "SAME_AS"|"ALIAS"|"SECRET_IDENTITY"|"REINCARNATION"'
    '|"TRANSMIGRATED_INTO"|null, "clue": "<exact span copied from the passage, or empty>"}.'
)


@dataclass
class IdentityVerdict:
    """One model judgement for a pair at a given reading position."""

    same: bool
    relation: str | None  # one of TIER3_RELATIONS (normalized), or None
    clue: str  # the model's quoted supporting clause (verified by the orchestrator)
    malformed_relation: bool = False  # YES whose `relation` field was a non-str blob we
    # could not coerce (the qwen JSON-object bug) — skipped + counted, never raises.


class IdentityProtocol(Protocol):
    """The surface the orchestrator depends on (lets tests inject a fake model)."""

    def infer(self, a: str, b: str, text: str, k: int) -> IdentityVerdict: ...


def normalize_relation(raw: object) -> str | None:
    """Map a model relation value onto the Tier-3 vocabulary (or None).

    Tolerant of a MALFORMED relation field by design: qwen2.5:7b intermittently emits
    `relation` as a JSON object/list instead of a string. The old code did ``raw.strip()``
    and RAISED on a non-str, which the orchestrator's broad except then escalated into
    zeroing the WHOLE identity run. Here we instead coerce an unambiguous string out of a
    1-element list or a single-value / known-key dict, and otherwise return None — the
    same "unrecognized relation -> no edge" path as an unknown string. It NEVER raises.
    """
    if isinstance(raw, str):
        if not raw.strip():
            return None
        key = re.sub(r"[\s\-]+", "_", raw.strip()).upper()
        return key if key in set(TIER3_RELATIONS) else None
    if isinstance(raw, (list, tuple)):
        return normalize_relation(raw[0]) if len(raw) == 1 else None
    if isinstance(raw, dict):
        for wrapper_key in ("relation", "type", "value", "name", "label"):
            if wrapper_key in raw:
                return normalize_relation(raw[wrapper_key])
        values = list(raw.values())
        return normalize_relation(values[0]) if len(values) == 1 else None
    return None  # None, number, bool, or anything else -> unrecognized, never raises


def _relation_is_malformed(raw: object, normalized: str | None) -> bool:
    """True iff a non-null, non-str relation blob failed to coerce to a Tier-3 relation.

    Distinguishes the qwen JSON-object bug (a dict/list/number we could not read) from
    the ordinary "model gave a null or an unknown STRING relation" no-edge path.
    """
    return normalized is None and raw is not None and not isinstance(raw, str)


class LlmIdentityModel:
    """Real model: wraps the wired OpenAI-compatible client with the cite-anchored prompt.

    Constructible only when the flag is ON (``LlmClient`` refuses otherwise), so the
    disabled-path no-socket guarantee (rule #5) holds by construction.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._client = LlmClient(settings)

    def infer(self, a: str, b: str, text: str, k: int) -> IdentityVerdict:
        user = (
            f"PASSAGE (chapters 1..{k}):\n{text}\n\n"
            f"Do '{a}' and '{b}' denote the same identity? If yes, give the relation and "
            f"quote the proving clause from the passage. JSON only."
        )
        obj = self._client.complete_json(SYSTEM_PROMPT, user)
        raw_relation = obj.get("relation") if isinstance(obj, dict) else None
        relation = normalize_relation(raw_relation)
        return IdentityVerdict(
            same=bool(obj.get("same") is True),
            relation=relation,
            clue=str(obj.get("clue", "") if isinstance(obj, dict) else "").strip(),
            malformed_relation=_relation_is_malformed(raw_relation, relation),
        )


# --------------------------------------------------------------------------- #
# Citation verification — the production confidence margin.
# --------------------------------------------------------------------------- #
_CITE_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)
_WS = re.compile(r"\s+")


def _normalize_citation(s: str) -> str:
    """NFKC + casefold + strip punctuation + collapse whitespace.

    Mirrors the ingest cleaner's NFKC coordinate space. Deliberately tolerant of
    formatting (smart quotes, em-dashes, casing, line wraps) so a faithfully-quoted
    clause matches the fed text — but it does NOT tolerate different *words*, so a
    fabricated or paraphrased "quote" is correctly rejected (that is the whole point
    of the citation gate).
    """
    s = unicodedata.normalize("NFKC", s)
    s = _CITE_PUNCT.sub(" ", s.casefold())
    return _WS.sub(" ", s).strip()


def citation_in_range(clue: str, fed_text: str) -> bool:
    """True iff the model's quoted clause actually occurs in the fed ch1..k text.

    The FABRICATION guard, identical for every relation: a paraphrased, invented, or
    instruction-echoed "quote" does not occur verbatim (normalized) in the passage and
    is rejected. ``citation_valid`` layers the relation-family rule on top of this; this
    floor is never relaxed (so the no-citation-no-edge guarantee, test B, is untouched).
    """
    norm_clue = _normalize_citation(clue)
    if len(norm_clue) < _MIN_CITATION_CHARS:
        return False
    return norm_clue in _normalize_citation(fed_text)


# Identity relations whose reveal is structurally SINGLE-ANCHORED: the prose
# establishes a soul/consciousness from another world or past life now inhabiting ONE
# named body (LotM: Zhou Mingrui's memories flood into Klein's body — the text never
# co-states both names in one clause). Demanding a both-naming citation here fails
# CLOSED on the true reveal (measured live on real prose, both models), so for these
# the citation rule is the existence floor PLUS an in-range anchor for at least one of
# the two entities — never a both-names clause.
SINGLE_ANCHOR_IDENTITY: frozenset[str] = frozenset({"TRANSMIGRATED_INTO", "REINCARNATION"})
# Identity relations that co-name both entities in-text by nature; the model is asked to
# quote the co-naming clause. (We do NOT add a hard both-names CODE gate for them: 7c
# measured that the live model often cites a real-but-descriptive clause near the reveal
# that names neither party, so a hard both-names gate would fail-close SECRET_IDENTITY
# too. Strict-family over-merge is the PARKED NLI-relevance concern, re-measured first.)
BOTH_NAMES_IDENTITY: frozenset[str] = frozenset({"SAME_AS", "ALIAS", "SECRET_IDENTITY"})


def _entity_anchored_in_range(name: str, fed_text: str) -> bool:
    """True iff the entity's name occurs (normalized) in the fed ch1..k text."""
    norm_name = _normalize_citation(name)
    return bool(norm_name) and norm_name in _normalize_citation(fed_text)


def citation_valid(
    clue: str, fed_text: str, relation: str | None, name_a: str = "", name_b: str = ""
) -> bool:
    """Relation-family-aware citation validity — the production confidence margin.

    Two modes, chosen by the relation FAMILY (the relation TYPE still comes from the
    model; only the citation-VALIDITY rule varies — enum-driven, never per-novel):

    * **Both-names family** (SAME_AS / ALIAS / SECRET_IDENTITY): existence floor only —
      the clue must occur verbatim in-range (``citation_in_range``). The prompt asks for a
      co-naming clause; we deliberately do not additionally HARD-require both names in code
      (7c: that fail-closes the strict family on the live model's descriptive citations).

    * **Single-anchor family** (TRANSMIGRATED_INTO / REINCARNATION): existence floor AND at
      least one of the two entities is anchored (named) in the fed ch1..k text. The reveal
      is structurally single-anchored — the clue evidences the transmigration/inheritance
      and need NOT name both — so requiring a both-naming clause here is wrong (it fails
      CLOSED on the true reveal). Requiring one in-range anchor keeps a degenerate "soul
      edge between two entities neither of whom is present yet" from being written.

    The ``citation_in_range`` fabrication floor is enforced for EVERY relation, so this is
    auditably NOT a weakening of the no-citation-no-edge guard — it only changes WHICH real,
    in-range quote counts, scoped to the family that structurally cannot co-name both.
    """
    if not citation_in_range(clue, fed_text):
        return False  # fabrication guard — unchanged for ALL relations (test B)
    if relation in SINGLE_ANCHOR_IDENTITY:
        return _entity_anchored_in_range(name_a, fed_text) or _entity_anchored_in_range(
            name_b, fed_text
        )
    return True


# --------------------------------------------------------------------------- #
# Orchestration.
# --------------------------------------------------------------------------- #
@dataclass
class IdentityReport:
    work_id: int
    edges_added: int = 0
    per_relation: dict[str, int] = field(default_factory=dict)
    pairs_tested: int = 0
    citations_rejected: int = 0  # same=YES dropped for a missing/invalid in-range citation
    malformed_relations: int = 0  # same=YES whose relation field was an uncoercible blob
    disabled: bool = False  # llm_enabled=False — produced nothing by design
    degraded: bool = False  # model unavailable/failed mid-run — floor kept intact

    def summary(self) -> str:
        if self.disabled:
            return (
                f"work id={self.work_id}: LLM disabled — no Tier-3 identity edges "
                f"(Tier-1/Tier-2 floor intact)"
            )
        if self.degraded:
            return (
                f"work id={self.work_id}: identity model unavailable — kept the floor "
                f"(0 Tier-3 edges)"
            )
        by_rel = ", ".join(f"{r}:{n}" for r, n in sorted(self.per_relation.items())) or "none"
        return (
            f"work id={self.work_id}: {self.edges_added} Tier-3 identity edges ({by_rel}); "
            f"{self.pairs_tested} pairs tested, {self.citations_rejected} uncited YES rejected, "
            f"{self.malformed_relations} malformed relations skipped"
        )


def _fed_texts(repo: Repository, work_id: int) -> list[tuple[int, str]]:
    """[(k, chapters-1..k concatenated)] ascending — the reveal-respecting windows."""
    chapters = sorted(repo.list_chapters(work_id), key=lambda c: c.ordinal)
    out: list[tuple[int, str]] = []
    acc: list[str] = []
    for ch in chapters:
        acc.append(ch.clean_text.strip())
        out.append((ch.ordinal, "\n\n".join(acc)))
    return out


def _candidate_pairs(
    repo: Repository, work_id: int, config: IdentityConfig
) -> list[tuple[Node, Node]]:
    """Unordered pairs of co-occurring candidate nodes (identity is about persons).

    Co-occurrence = the two nodes are mentioned in at least one common chapter; we only
    ask the LLM about entities that actually appear together. Ordered (source, target)
    by first-seen so direction reads met-first -> revealed. Capped (knobs are data).
    """
    nodes = [
        n
        for n in repo.list_nodes(work_id)
        if n.id is not None and n.type.value in set(config.candidate_types)
    ]
    chapters_of: dict[int, set[int]] = {}
    for m in repo.list_mentions(work_id):
        if m.node_id is not None:
            chapters_of.setdefault(m.node_id, set()).add(m.chapter_ordinal)

    pairs: list[tuple[Node, Node]] = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            assert a.id is not None and b.id is not None
            if chapters_of.get(a.id, set()) & chapters_of.get(b.id, set()):
                src, tgt = sorted((a, b), key=lambda n: (n.first_seen_chapter, n.name))
                pairs.append((src, tgt))
    # Most-important pairs first, then cap (real novels have many co-occurring people).
    pairs.sort(key=lambda p: p[0].importance + p[1].importance, reverse=True)
    return pairs[: config.max_candidate_pairs]


def infer_identities(
    work_id: int,
    repo: Repository,
    config: IdentityConfig | None = None,
    settings: Settings | None = None,
    model: IdentityProtocol | None = None,
) -> IdentityReport:
    """Infer Tier-3 identity edges with reveal-respecting, citation-gated semantics.

    Idempotent + tier-scoped: clears only this work's Tier-3 edges and rebuilds,
    leaving Tier-1/Tier-2 untouched. Pure enhancement (rule #4): with the flag off it
    is disabled (nothing written, no socket); if the model fails it degrades and keeps
    the floor.
    """
    cfg = config or IdentityConfig()
    cfg_settings = settings or get_settings()
    report = IdentityReport(work_id=work_id)

    if model is None:
        if not llm_available(cfg_settings):
            report.disabled = True  # flag off -> produce nothing (no client, no socket)
            return report
        try:
            model = LlmIdentityModel(cfg_settings)
        except Exception:  # pragma: no cover - defensive: never hard-depend on the LLM
            report.degraded = True
            return report

    windows = _fed_texts(repo, work_id)
    pairs = _candidate_pairs(repo, work_id, cfg)
    report.pairs_tested = len(pairs)

    # relation -> (smallest confirming k, verified clue), per pair.
    resolved: list[tuple[Node, Node, dict[str, tuple[int, str]]]] = []
    try:
        for src, tgt in pairs:
            confirmed: dict[str, tuple[int, str]] = {}
            for k, fed in windows:
                verdict = model.infer(src.name, tgt.name, fed, k)
                if not verdict.same:
                    continue
                relation = verdict.relation
                if relation is None:
                    # A malformed (uncoercible non-str) relation degrades THIS pair-k only —
                    # it is counted and skipped, never escalated to a whole-run `degraded`.
                    if verdict.malformed_relation:
                        report.malformed_relations += 1
                    continue
                if not citation_valid(verdict.clue, fed, relation, src.name, tgt.name):
                    report.citations_rejected += 1  # YES without a valid in-range citation
                    continue
                if relation not in confirmed:
                    confirmed[relation] = (k, verdict.clue.strip())
            if confirmed:
                resolved.append((src, tgt, confirmed))
    except Exception:  # pragma: no cover - model failed mid-run -> degrade, keep floor
        report.degraded = True
        return report

    repo.clear_edges_by_tier(work_id, RelationTier.IDENTITY)
    for src, tgt, confirmed in resolved:
        assert src.id is not None and tgt.id is not None
        for relation, (k, clue) in confirmed.items():
            s_id, t_id = src.id, tgt.id
            if relation in _SYMMETRIC_IDENTITY and s_id > t_id:
                s_id, t_id = t_id, s_id
            repo.add_edge(
                Edge(
                    work_id=work_id,
                    source_id=s_id,
                    target_id=t_id,
                    relation=relation,
                    tier=RelationTier.IDENTITY,
                    # The identity exists once both referents are present; the reader
                    # only CONNECTS them at k -> revealed_chapter = k (the reveal shift).
                    first_seen_chapter=min(src.first_seen_chapter, tgt.first_seen_chapter),
                    revealed_chapter=k,
                    extraction_method=ExtractionMethod.LLM,
                    evidence_span=clue,
                )
            )
            report.edges_added += 1
            report.per_relation[relation] = report.per_relation.get(relation, 0) + 1

    return report
