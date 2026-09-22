"""Curated Tier-2/Tier-3 layer for "The Ninth House" (integration phase, Part B).

Unlike Hollow Crown (100% hand-built by `demo.seed.seed_hollow_crown`), this work's
nodes and Tier-1 edges come from the REAL pipeline — `storyweave ingest` ->
`extract` -> `relate`, run under `.venv-ml` against the committed source text in
`data/samples/the-ninth-house/` + its `storyweave.toml` (see docs/INTEGRATION.md
Part B.3 for the measured extraction numbers). This module adds only what the LLM
enhancement layer would normally add on top of that floor — Tier-2 social relations
and Tier-3 identity edges — curated by hand from the story bible
(docs/demo/the-ninth-house-bible.md §6) instead of a live LLM run (CLAUDE.md
integration-phase rule I3: the LLM stays off).

Every record this module adds is provenance-tagged `ExtractionMethod.CURATED`, never
`LLM` — see that enum's own docstring and I3. Node lookups use the ACTUAL surface
forms the real extraction clustered entities under (frequently a short form —
"Cassian" not "Cassian Ashcombe" — this is measured pipeline behaviour, not
idealized; see INTEGRATION.md), tried in a fallback order so a future re-extraction
that happens to cluster more precisely still resolves correctly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from storyweave.db.models import Edge, ExtractionMethod, RelationTier
from storyweave.db.repository import Repository

CURATED = ExtractionMethod.CURATED
T2 = RelationTier.SOCIAL
T3 = RelationTier.IDENTITY


@dataclass
class CurationReport:
    work_id: int
    identity_edges_added: int = 0
    social_edges_added: int = 0
    missing_nodes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"work id={self.work_id}: +{self.identity_edges_added} identity edges, "
            f"+{self.social_edges_added} social edges"
            + (f" ({len(self.missing_nodes)} lookups failed: {self.missing_nodes})"
               if self.missing_nodes else "")
        )


def _find_node(repo: Repository, work_id: int, *candidates: str) -> int | None:
    """First matching node id among candidate surface forms. Returns None (never
    raises) so a caller can collect every failure into one report instead of
    stopping at the first — a stale candidate list should be loudly visible, not a
    silent partial graph."""
    by_name: dict[str, int] = {}
    for n in repo.list_nodes(work_id):
        if n.id is not None and n.name not in by_name:
            by_name[n.name] = n.id
    for c in candidates:
        if c in by_name:
            return by_name[c]
    return None


# (source candidates, target candidates, relation, revealed_chapter, evidence)
# Evidence spans are copied verbatim from the chapter text at `revealed_chapter` —
# see tests/test_ninth_house_citations.py, which checks every one of these against
# the real source files using the project's own citation_in_range normalizer.
_IDENTITY_EDGES: list[tuple[tuple[str, ...], tuple[str, ...], str, int, str]] = [
    (("Vey",), ("Vesper",), "ALIAS", 5,
     "Mistress Vey untied her apron, and under it she wore the grey sash of the "
     "Choir — Vesper had never been a laundress at all."),
    (("Juno Stray",), ("Sable Vell",), "SECRET_IDENTITY", 10,
     "Warden Juno Stray pulled back her hood, and Sorrel saw the Vell chin she'd "
     "only known from a portrait: Sable Vell, the Duchess's vanished daughter, had "
     "been standing watch in the Salt Quarter for a year."),
    (("Choirmaster",), ("Thessaly",), "ALIAS", 16,
     "The old archivist folded her hands and said, without any weight at all, "
     "that she was the Choirmaster, and had been since before Sorrel was born."),
    (("Sorrel",), ("Aurelia Marrow",), "SECRET_IDENTITY", 20,
     "The ledger's last page named the scribe who would carry it: not Sorrel "
     "Quill, a chancery orphan, but Aurelia Marrow, the Ninth House's last "
     "acknowledged daughter."),
    (("Cassian",), ("Kaelen",), "REINCARNATION", 28,
     "Thessaly held the grimoire beside the Regent's sleeping face and said the "
     "old name plainly: Kaelen, worn thin over three centuries, had woken up as "
     "Cassian Ashcombe."),
    (("Sorrel",), ("Aurelia Marrow",), "REINCARNATION", 34,
     "It was not blood that had made her a Marrow, Thessaly said — blood was only "
     "ever the door. The soul that opened it had done this before, and Aurelia "
     "Marrow was the name it wore the last time."),
    (("Mira",), ("Wanderer",), "TRANSMIGRATED_INTO", 37,
     "Mira Quell had always known the names of places she had never been, and "
     "now, on the Grey Road's threshold, she finally said why: she had walked in "
     "from outside Thornmere altogether, a Wanderer poured into a Choir "
     "initiate's small body."),
]

# (source candidates, target candidates, relation, revealed_chapter, evidence)
# Tier-2 evidence is real text but need not be a single unbroken clause the way the
# Tier-3 citation gate demands of identity edges — social relations are inferred
# from a scene, not a single confirming sentence, matching how an LLM relation
# layer would cite its source (a supporting passage, not a fabrication check).
_SOCIAL_EDGES: list[tuple[tuple[str, ...], tuple[str, ...], str, int, str]] = [
    (("Cassian",), ("Ione",), "Sibling", 2,
     "His sister, Ione Ashcombe, stood behind him rather than beside him"),
    (("Meraude",), ("Tobin",), "Parent", 11,
     "Her son had his father's patience and none of his mother's stubbornness"),
    (("Meraude",), ("Sable Vell",), "Parent", 10,
     "Sable Vell, the Duchess's vanished daughter, had been standing watch"),
    (("Thessaly",), ("Vesper",), "Mentor", 6,
     "Watch her. Don't touch her. Not yet."),
    (("Thessaly",), ("Mira",), "Mentor", 7,
     "Mira Quell was eleven years old... utterly devoted to Thessaly, who fed "
     "her better than the orphan house ever had"),
    (("Ser Robart Kell",), ("Cassian",), "Serves", 2,
     "Ser Robart Kell, Cassian's guard-captain, stood at the Regent's shoulder"),
    (("Thorne",), ("Cassian",), "Serves", 6,
     "Thorne had served the Ashcombe household since before Cassian could walk "
     "unassisted"),
    (("Hask",), ("Corwin",), "Serves", 26,
     "He took the observation instead to Hask, whose discretion he trusted"),
    (("Meraude",), ("Cassian",), "Rival", 8,
     "Meraude, watching him as closely as anyone in Thornmere"),
    (("Ione",), ("Sorrel",), "Protects", 22,
     "I'll tell him you've been assisting with a private matter of mine"),
    (("Drask",), ("Juno Stray",), "Respects", 9,
     "she was his best Warden and his least explainable one"),
    (("Vesper",), ("Sorrel",), "Mentor", 15,
     "I'll teach you the number-folding"),
]


def curate_ninth_house(repo: Repository, work_id: int) -> CurationReport:
    """Add the hand-curated Tier-2/Tier-3 layer onto an already-extracted work.

    Idempotent: clears any previously-curated SOCIAL/IDENTITY edges for this work
    first (Tier-1 rule edges are a different tier and untouched). Requires
    `extract`+`relate` to have already run — every lookup is against nodes/edges
    the real pipeline produced, never invented.
    """
    repo.clear_edges_by_tier(work_id, T2)
    repo.clear_edges_by_tier(work_id, T3)
    report = CurationReport(work_id=work_id)

    for spec, tier, counter_name in (
        (_IDENTITY_EDGES, T3, "identity_edges_added"),
        (_SOCIAL_EDGES, T2, "social_edges_added"),
    ):
        for src_names, tgt_names, relation, revealed, evidence in spec:
            src = _find_node(repo, work_id, *src_names)
            tgt = _find_node(repo, work_id, *tgt_names)
            if src is None:
                report.missing_nodes.append(src_names[0])
                continue
            if tgt is None:
                report.missing_nodes.append(tgt_names[0])
                continue
            repo.add_edge(
                Edge(
                    work_id=work_id,
                    source_id=src,
                    target_id=tgt,
                    relation=relation,
                    tier=tier,
                    # Identity reveals shift (the pair exists earlier; the reader
                    # only learns the connection at `revealed`) — mirrors Hollow
                    # Crown's own seed.py convention exactly.
                    first_seen_chapter=revealed,
                    revealed_chapter=revealed,
                    extraction_method=CURATED,
                    evidence_span=evidence,
                )
            )
            setattr(report, counter_name, getattr(report, counter_name) + 1)

    return report
