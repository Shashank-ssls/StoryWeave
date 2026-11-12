"""Retrofit R6: who the graph shows, ranked from chapters <= n only.

The cast dial in v1 was a client-side no-op (defect D3), so "show me the main 20" meant
nothing. This computes a per-chapter importance rank on the server, and the payload query
filters on it as a DISPLAY clause after the fence.

**Edge degree is deliberately NOT a feature.** The R6 phase doc lists "STATED degree <= n"
among them; R1 measured why that is wrong. v1's only ranking signal was fenced payload
degree, and when the co-occurrence edges were switched off the ranking collapsed with
them (P@10 0.4000 -> 0.3000, MAP 0.4414 -> 0.3668). Ranking a cast by how many edges the
extractor happened to find makes the display filter a hostage to extraction recall, which
R4-R5 measured at close to zero. Everything here is therefore a property of the TEXT.

**Rule 7, structurally.** Every feature is computed from mentions in chapters <= n, and a
separate row is stored per chapter, so the rank at chapter 5 cannot be contaminated by a
character who becomes important at chapter 30. A book-wide rank would be a spoiler side
channel even though no name leaks: it tells the reader who matters later.

Features, each min-max normalised **within that chapter's candidate set** and summed with
**equal weight** (weights are per-work data in ``storyweave.toml``, and were fixed before
any scoring run -- see the R6 pre-registration):

* ``lifetime_mentions`` -- how often the text has named them so far;
* ``recent_mentions`` -- mentions in the last 10% of chapters <= n (at least 3), so a
  character active *now* outranks one who was busy in chapter 2 and vanished;
* ``chapter_spread`` -- distinct chapters they appear in, which separates a recurring
  figure from one crowded into a single scene;
* ``has_proper_name`` -- a named character outranks "the girl";
* ``speaks_dialogue`` -- someone the book lets talk is rarely furniture.

A **significance gate** runs before ranking: a Character is eligible only with a proper
name AND (>= 3 chapters OR >= 5 mentions) by chapter n. Non-Characters are not gated,
because the overlays (Places, Items, Organizations) are opt-in already.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from storyweave.db.models import Mention, Node, NodeSalience, NodeType
from storyweave.db.repository import Repository

#: Feature names, in the order they are summed. Stored so the report can list them.
FEATURES: tuple[str, ...] = (
    "lifetime_mentions",
    "recent_mentions",
    "chapter_spread",
    "has_proper_name",
    "speaks_dialogue",
)

#: Dialogue is double quotes or square brackets. Single quotes are EXCLUDED: in this
#: corpus `'` is also the apostrophe in "don't" and marks thought rather than speech
#: (the same decision R2's cleaner made, for the same reason).
_DIALOGUE = re.compile(r"“[^”]*”|\"[^\"]*\"|\[[^\]]*\]", re.DOTALL)

#: A proper name starts with a capital and is not a bare role word. The graph's own
#: generic-word list would be circular here, so this is the narrow test: at least one
#: capitalised token that is not sentence-initial boilerplate.
_PROPER = re.compile(r"\b[A-Z][a-z]+")

_GENERIC = frozenset(
    {
        "the girl", "the boy", "the man", "the woman", "the child", "the stranger",
        "the servant", "the guard", "the scribe", "the captain", "the king",
        "the queen", "the regent", "the envoy", "the trader", "the smuggler",
    }
)


@dataclass
class SalienceReport:
    work_id: int
    chapters: int = 0
    rows_written: int = 0
    eligible_per_chapter: dict[int, int] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"work id={self.work_id}: {self.rows_written} salience rows over "
            f"{self.chapters} chapters"
        )


def has_proper_name(name: str) -> bool:
    """True if ``name`` looks like a proper name rather than a role word."""
    if name.strip().lower() in _GENERIC:
        return False
    return bool(_PROPER.search(name))


def dialogue_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges of spoken text, for the ``speaks_dialogue`` feature."""
    return [(m.start(), m.end()) for m in _DIALOGUE.finditer(text)]


def _in_any(span: tuple[int, int], ranges: Sequence[tuple[int, int]]) -> bool:
    return any(lo <= span[0] < hi for lo, hi in ranges)


def _minmax(values: dict[int, float]) -> dict[int, float]:
    """Min-max normalise within the candidate set; a flat feature contributes 0."""
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    if hi <= lo:
        return dict.fromkeys(values, 0.0)
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def is_eligible(
    node: Node, chapters_seen: int, mention_count: int, min_chapters: int = 3, min_mentions: int = 5
) -> bool:
    """The significance gate. Characters only; overlays are opt-in already."""
    if node.type is not NodeType.CHARACTER:
        return True
    if not has_proper_name(node.name):
        return False
    return chapters_seen >= min_chapters or mention_count >= min_mentions


def compute_salience(
    work_id: int,
    repo: Repository,
    weights: dict[str, float] | None = None,
    recent_fraction: float = 0.10,
    recent_min_chapters: int = 3,
) -> SalienceReport:
    """Compute and persist a salience rank per (node, chapter). Idempotent."""
    w = {f: 1.0 for f in FEATURES}
    if weights:
        w.update({k: v for k, v in weights.items() if k in w})

    chapters = repo.list_chapters(work_id)
    nodes = {n.id: n for n in repo.list_nodes(work_id) if n.id is not None}
    mentions = [m for m in repo.list_mentions(work_id) if m.node_id is not None]

    # Which mentions are inside spoken text, computed once per chapter.
    speech_by_chapter = {
        c.ordinal: dialogue_spans(c.clean_text) for c in chapters
    }
    spoken: set[int] = set()  # mention ids that sit inside dialogue
    for m in mentions:
        ranges = speech_by_chapter.get(m.chapter_ordinal, [])
        if m.id is not None and _in_any((m.char_start, m.char_end), ranges):
            spoken.add(m.id)

    report = SalienceReport(work_id=work_id, chapters=len(chapters))
    repo.clear_node_salience(work_id)

    ordinals = [c.ordinal for c in chapters]
    for n in ordinals:
        # --- rule 7: only chapters <= n are visible to the ranking ---
        upto = [m for m in mentions if m.chapter_ordinal <= n]
        if not upto:
            continue
        revealed = {node.id for node in repo.list_nodes_revealed(work_id, n)}

        by_node: dict[int, list[Mention]] = {}
        for m in upto:
            if m.node_id in revealed:
                by_node.setdefault(m.node_id or 0, []).append(m)

        # "Recent" = the last 10% of chapters read so far, at least 3.
        window = max(recent_min_chapters, int(round(n * recent_fraction)))
        recent_from = max(1, n - window + 1)

        raw: dict[str, dict[int, float]] = {f: {} for f in FEATURES}
        eligible: list[int] = []
        for node_id, ms in by_node.items():
            node = nodes.get(node_id)
            if node is None:
                continue
            seen_chapters = {m.chapter_ordinal for m in ms}
            if not is_eligible(node, len(seen_chapters), len(ms)):
                continue
            eligible.append(node_id)
            raw["lifetime_mentions"][node_id] = float(len(ms))
            raw["recent_mentions"][node_id] = float(
                sum(1 for m in ms if m.chapter_ordinal >= recent_from)
            )
            raw["chapter_spread"][node_id] = float(len(seen_chapters))
            raw["has_proper_name"][node_id] = 1.0 if has_proper_name(node.name) else 0.0
            raw["speaks_dialogue"][node_id] = (
                1.0 if any(m.id in spoken for m in ms) else 0.0
            )

        if not eligible:
            continue
        normed = {f: _minmax(raw[f]) for f in FEATURES}
        scores = {
            node_id: sum(w[f] * normed[f].get(node_id, 0.0) for f in FEATURES)
            for node_id in eligible
        }
        # Deterministic order: score desc, then earliest appearance, then id.
        ranked = sorted(
            eligible,
            key=lambda i: (-scores[i], nodes[i].first_seen_chapter, i),
        )
        report.eligible_per_chapter[n] = len(ranked)
        rows = [
            NodeSalience(node_id=node_id, chapter=n, score=scores[node_id], rank=rank)
            for rank, node_id in enumerate(ranked, start=1)
        ]
        repo.add_node_salience_bulk(rows)
        report.rows_written += len(rows)

    return report
