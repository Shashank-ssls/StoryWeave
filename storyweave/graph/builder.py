"""Tier-1 structural relationship extraction — the GLiNER-floor's edges (Phase 3).

This produces a connected, correctly-typed graph with ZERO LLM (rule #3). Edges come
from entity co-occurrence: two canonical entities whose mentions fall within a
configurable character window in the same chapter become a candidate edge. The
relation is chosen by a small, explainable type-pair rule table (+ a lexical cue that
promotes membership to leadership), with ``RelatedTo`` as the never-drop fallback so
no co-occurring pair is lost (Tier-1 list, SPEC §5.3).

Every edge is stamped with provenance (method=rule, an evidence quote) and the
universal reveal stamps. For a rule-derived structural edge the relationship is known
to the reader exactly when both entities have co-occurred, so
``revealed_chapter == first_seen_chapter == the earliest co-occurrence chapter``.
Reveal-shifting (secrets) is Tier-3/LLM work for Phase 7. Idempotent: rebuilds edges.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from storyweave.db.models import Edge, ExtractionMethod, Mention, Node, NodeType, RelationTier
from storyweave.db.repository import Repository
from storyweave.ingest.work_config import RelationConfig, WorkConfig

# Directed type-pair -> Tier-1 relation (source type, target type).
_DIRECTED: dict[tuple[NodeType, NodeType], str] = {
    (NodeType.CHARACTER, NodeType.ORGANIZATION): "MemberOf",
    (NodeType.CHARACTER, NodeType.PLACE): "LocatedIn",
    (NodeType.CHARACTER, NodeType.ABILITY): "HasAbility",
    (NodeType.CHARACTER, NodeType.ITEM): "OwnsItem",
    (NodeType.CHARACTER, NodeType.TITLE): "HasTitle",
    (NodeType.CHARACTER, NodeType.EVENT): "ParticipatedIn",
    (NodeType.ORGANIZATION, NodeType.PLACE): "LocatedIn",
    (NodeType.ORGANIZATION, NodeType.ORGANIZATION): "AffiliatedWith",
    (NodeType.PLACE, NodeType.EVENT): "ParticipatedIn",
}
# Lexical cues that promote a Character–Organization MemberOf to LeaderOf.
_LEADER_CUES = {
    "leader", "led", "leads", "head", "ruler", "ruled", "rules", "reigned",
    "commander", "commands", "chief", "regent", "throne", "king", "queen", "lord",
}


@dataclass
class _PairAccum:
    """Accumulates co-occurrence evidence for one unordered node pair."""

    count: int = 0
    first_chapter: int = 10**9
    evidence: str = ""
    cues: str = ""


@dataclass
class RelationReport:
    work_id: int
    edges_added: int = 0
    per_relation: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        by_rel = ", ".join(f"{r}:{n}" for r, n in sorted(self.per_relation.items()))
        return f"work id={self.work_id}: {self.edges_added} Tier-1 edges ({by_rel})"


def classify_relation(src: Node, tgt: Node, evidence: str) -> tuple[Node, Node, str]:
    """Return (source, target, relation) for a co-occurring pair via the rule table."""
    ev = evidence.lower()
    rel = _DIRECTED.get((src.type, tgt.type))
    if rel is not None:
        source, target = src, tgt
    else:
        rel = _DIRECTED.get((tgt.type, src.type))
        if rel is not None:
            source, target = tgt, src
        else:
            return src, tgt, "RelatedTo"  # fallback: never drop a co-occurring pair
    if rel == "MemberOf" and any(c in ev for c in _LEADER_CUES):
        rel = "LeaderOf"
    return source, target, rel


def _evidence(text: str, a: Mention, b: Mention, pad: int = 30) -> str:
    start = max(0, min(a.char_start, b.char_start) - pad)
    end = min(len(text), max(a.char_end, b.char_end) + pad)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def build_relationships(
    work_id: int, repo: Repository, config: WorkConfig | None = None
) -> RelationReport:
    """Extract + persist Tier-1 edges from entity co-occurrence. Idempotent."""
    cfg: RelationConfig = (config or WorkConfig()).relations
    repo.clear_edges(work_id)
    report = RelationReport(work_id=work_id)

    nodes = {n.id: n for n in repo.list_nodes(work_id) if n.id is not None}
    chapter_text = {c.id: c.clean_text for c in repo.list_chapters(work_id)}

    # Group node-bearing mentions by chapter.
    by_chapter: dict[int, list[Mention]] = {}
    for m in repo.list_mentions(work_id):
        if m.node_id is not None:
            by_chapter.setdefault(m.chapter_ordinal, []).append(m)

    pairs: dict[tuple[int, int], _PairAccum] = {}
    for chapter_ordinal, mentions in by_chapter.items():
        mentions.sort(key=lambda m: m.char_start)
        for i, a in enumerate(mentions):
            for b in mentions[i + 1 :]:
                if b.char_start - a.char_end > cfg.window_chars:
                    break  # sorted: nothing further is in range
                if a.node_id == b.node_id:
                    continue
                assert a.node_id is not None and b.node_id is not None
                key = (min(a.node_id, b.node_id), max(a.node_id, b.node_id))
                acc = pairs.setdefault(key, _PairAccum())
                acc.count += 1
                if chapter_ordinal < acc.first_chapter:
                    acc.first_chapter = chapter_ordinal
                    acc.evidence = _evidence(chapter_text.get(a.chapter_id, ""), a, b)
                    acc.cues = acc.evidence

    for (id_a, id_b), acc in pairs.items():
        if acc.count < cfg.min_cooccurrences:
            continue
        source, target, relation = classify_relation(nodes[id_a], nodes[id_b], acc.cues)
        assert source.id is not None and target.id is not None
        repo.add_edge(
            Edge(
                work_id=work_id,
                source_id=source.id,
                target_id=target.id,
                relation=relation,
                tier=RelationTier.STRUCTURAL,
                first_seen_chapter=acc.first_chapter,
                revealed_chapter=acc.first_chapter,  # rule edge: revealed when first seen
                extraction_method=ExtractionMethod.RULE,
                evidence_span=acc.evidence,
            )
        )
        report.edges_added += 1
        report.per_relation[relation] = report.per_relation.get(relation, 0) + 1

    return report
