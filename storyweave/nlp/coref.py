"""Conservative coreference merge — fold self-reference PRONOUN nodes into the POV.

The Phase-2 string clusterer (``nlp/cluster.py``) merges surface variants of a NAME
(``Veris`` -> ``Lady Veris``) but cannot touch a pronoun: ``you`` / ``I`` share no
surface tokens with ``Sunny``, so in a single-POV second-person narration the POV
character's edges split across ``Sunny`` / ``you`` / ``I`` — ``Sunny`` looks
under-connected and the pronoun nodes look like phantom characters.

This module fixes that *one* safe case and ONLY that case:

* MERGE first/second-person self-reference pronoun NODES into the single POV character,
  re-pointing their edges (dedup, keep the EARLIEST reveal stamp), then deleting the
  now-edgeless junk node. Gated on a per-work config flag (``coref.merge_self_reference``,
  default OFF) and a resolvable POV — a tie at the top, or an unfound explicit POV name,
  SKIPS the merge. The pronoun surface set + the POV are DATA (``storyweave.toml``), never
  ``if work == "...":``.
* LEAVE ambiguous epithets (``the younger soldier``, ``broad-shouldered man``) UNMERGED —
  more than one real character could match and an over-eager fuse CORRUPTS data. They are
  only OBSERVED (counted as still-deferred coref), never guessed at.

This is Tier-1/2 entity coref, NOT Tier-3 identity inference. ``fence.py`` is untouched: a
merged edge keeps ``min`` of its sources' ``revealed_chapter`` (never earlier than one of
its own sources' reveals), so merging can never bloom an edge before it was already due.
Idempotent: a second run finds no pronoun nodes and is a no-op. Pure Python, light venv.
"""

from __future__ import annotations

from dataclasses import dataclass

from storyweave.db.models import Node, NodeType
from storyweave.db.repository import Repository
from storyweave.ingest.work_config import WorkConfig
from storyweave.nlp.cluster import normalize_surface


@dataclass
class CorefReport:
    work_id: int
    pov_character: str | None = None
    nodes_merged: int = 0  # self-reference pronoun nodes folded into the POV
    edges_repointed: int = 0  # edges moved onto the canonical POV node
    edges_deduped: int = 0  # duplicate edges collapsed (kept the earliest stamps)
    self_loops_removed: int = 0  # edges that became POV->POV after re-pointing
    mentions_repointed: int = 0  # pronoun mentions re-attributed to the POV (evidence kept)
    ambiguous_left: int = 0  # epithet-like lowercase nodes deliberately NOT merged
    skipped_reason: str | None = None  # set iff no merge ran (disabled / no unambiguous POV)

    def summary(self) -> str:
        if self.skipped_reason is not None:
            return f"work id={self.work_id}: coref merge skipped ({self.skipped_reason})"
        return (
            f"work id={self.work_id}: folded {self.nodes_merged} pronoun node(s) into "
            f"'{self.pov_character}' ({self.edges_repointed} edges re-pointed, "
            f"{self.edges_deduped} deduped, {self.self_loops_removed} self-loops removed, "
            f"{self.mentions_repointed} mentions kept); {self.ambiguous_left} ambiguous "
            f"epithet(s) left unmerged"
        )


def _is_epithet_like(node: Node, pronouns: set[str]) -> bool:
    """A descriptive common-noun reference (no proper-name capital), not a pronoun.

    Observational only — these are the still-deferred-coref class we refuse to guess at.
    Proper names carry an uppercase letter; ``the younger soldier`` does not.
    """
    norm = normalize_surface(node.name)
    return (
        node.type is NodeType.CHARACTER
        and norm not in pronouns
        and not any(ch.isupper() for ch in node.name)
    )


def _resolve_pov(nodes: list[Node], cfg_pov: str, pronouns: set[str]) -> Node | None:
    """The single POV character to merge pronouns into, or None when it is ambiguous.

    Explicit ``pov_character`` -> the unique non-pronoun Character matching it (0 or >1
    matches => None). Otherwise auto-detect the single most-important Character; a TIE at
    the top returns None (when unsure, do not merge).
    """
    chars = [
        n
        for n in nodes
        if n.type is NodeType.CHARACTER
        and n.id is not None
        and normalize_surface(n.name) not in pronouns
    ]
    if not chars:
        return None
    if cfg_pov.strip():
        target = normalize_surface(cfg_pov)
        matches = [n for n in chars if normalize_surface(n.name) == target]
        return matches[0] if len(matches) == 1 else None
    ranked = sorted(chars, key=lambda n: n.importance, reverse=True)
    if len(ranked) >= 2 and ranked[0].importance == ranked[1].importance:
        return None  # top is tied -> unsure -> skip
    return ranked[0]


def merge_coref(
    work_id: int, repo: Repository, config: WorkConfig | None = None
) -> CorefReport:
    """Fold self-reference pronoun nodes into the POV character. Idempotent; see module doc."""
    cfg = (config or WorkConfig()).coref
    report = CorefReport(work_id=work_id)
    if not cfg.merge_self_reference:
        report.skipped_reason = "disabled (coref.merge_self_reference = false)"
        return report

    nodes = repo.list_nodes(work_id)
    pronouns = {normalize_surface(s) for s in cfg.self_reference_surfaces if s.strip()}
    report.ambiguous_left = sum(1 for n in nodes if _is_epithet_like(n, pronouns))

    pov = _resolve_pov(nodes, cfg.pov_character, pronouns)
    if pov is None or pov.id is None:
        report.skipped_reason = "no unambiguous POV character"
        return report
    report.pov_character = pov.name
    pov_id = pov.id

    junk = [
        n
        for n in nodes
        if n.type is NodeType.CHARACTER
        and n.id is not None
        and n.id != pov_id
        and normalize_surface(n.name) in pronouns
    ]
    if not junk:
        report.skipped_reason = "no self-reference pronoun nodes (already merged / none)"
        return report
    junk_ids = {n.id for n in junk}

    def canon(node_id: int) -> int:
        return pov_id if node_id in junk_ids else node_id

    # Re-point edges endpoint-by-endpoint. A self-loop (POV->POV) is dropped; a collision
    # with an existing edge of the same (source, target, relation, tier) is deduped, keeping
    # the EARLIEST first_seen/revealed of the pair (the fence invariant). Direction-sensitive
    # dedup never fuses two genuinely different edges.
    kept: dict[tuple[int, int, str, int], tuple[int, int, int]] = {}
    for e in repo.list_edges(work_id):
        assert e.id is not None
        src, tgt = canon(e.source_id), canon(e.target_id)
        if src == tgt:
            repo.delete_edge(e.id)
            report.self_loops_removed += 1
            continue
        key = (src, tgt, e.relation, int(e.tier))
        if key in kept:
            keep_id, fs, rv = kept[key]
            new_fs, new_rv = min(fs, e.first_seen_chapter), min(rv, e.revealed_chapter)
            if (new_fs, new_rv) != (fs, rv):
                repo.update_edge_reveal(keep_id, new_fs, new_rv)
                kept[key] = (keep_id, new_fs, new_rv)
            repo.delete_edge(e.id)
            report.edges_deduped += 1
        else:
            if (src, tgt) != (e.source_id, e.target_id):
                repo.update_edge_endpoints(e.id, src, tgt)
                report.edges_repointed += 1
            kept[key] = (e.id, e.first_seen_chapter, e.revealed_chapter)

    # Now the junk nodes are edgeless: re-attribute their mentions (keep evidence) and drop.
    for n in junk:
        assert n.id is not None
        report.mentions_repointed += repo.repoint_mentions(work_id, n.id, pov_id)
        repo.delete_node(n.id)
        report.nodes_merged += 1

    return report
