"""The Tier-2/Tier-3 curation layer for "The Ninth House" (integration phase, Part B).

Runs entirely in the light venv: it doesn't need the real GLiNER pipeline, only a
work whose nodes already carry the surface-form names `curate_ninth_house` looks
up (a light stand-in for what `extract`+`relate` actually produced — see
docs/INTEGRATION.md Part B.3 for the measured real-pipeline surface forms this
mirrors). What matters here is the curation logic itself: provenance labeling,
idempotency, and loud (not silent) failure on a missing node.
"""

from __future__ import annotations

from storyweave.db.models import ExtractionMethod, Node, NodeType, RelationTier, Work
from storyweave.db.repository import Repository
from storyweave.demo.seed_ninth_house import _IDENTITY_EDGES, _SOCIAL_EDGES, curate_ninth_house

# Every source/target surface form curate_ninth_house's lookup tables reference.
_REQUIRED_NAMES = sorted(
    {n for spec in (_IDENTITY_EDGES, _SOCIAL_EDGES) for src, tgt, *_ in spec for n in (*src, *tgt)}
)


def _seed_stub_work(repo: Repository) -> int:
    wid = repo.create_work(Work(slug="ninth-house-stub", title="Stub"))
    for name in _REQUIRED_NAMES:
        repo.add_node(
            Node(
                work_id=wid,
                type=NodeType.CHARACTER,
                name=name,
                first_seen_chapter=1,
                revealed_chapter=1,
                extraction_method=ExtractionMethod.GLINER,
            )
        )
    return wid


def test_curates_all_seven_identity_and_twelve_social_edges() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = _seed_stub_work(repo)
        report = curate_ninth_house(repo, wid)

        assert report.identity_edges_added == 7
        assert report.social_edges_added == 12
        assert report.missing_nodes == []


def test_curated_edges_are_provenance_tagged_curated_never_llm() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = _seed_stub_work(repo)
        curate_ninth_house(repo, wid)

        edges = repo.list_edges(wid)
        assert len(edges) == 19  # 7 identity + 12 social
        methods = {e.extraction_method for e in edges}
        assert methods == {ExtractionMethod.CURATED}  # never llm
        identity = [e for e in edges if e.tier == RelationTier.IDENTITY]
        social = [e for e in edges if e.tier == RelationTier.SOCIAL]
        assert len(identity) == 7 and len(social) == 12


def test_idempotent_rerun_does_not_duplicate() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = _seed_stub_work(repo)
        curate_ninth_house(repo, wid)
        curate_ninth_house(repo, wid)  # second run must replace, not append

        assert len(repo.list_edges(wid)) == 19


def test_missing_node_is_reported_loudly_not_silently_dropped() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="incomplete", title="Incomplete"))
        # Seed only ONE of the required names — every edge touching a missing name
        # must show up in the report, not vanish quietly.
        repo.add_node(
            Node(work_id=wid, type=NodeType.CHARACTER, name=_REQUIRED_NAMES[0],
                 first_seen_chapter=1, revealed_chapter=1,
                 extraction_method=ExtractionMethod.GLINER)
        )
        report = curate_ninth_house(repo, wid)

        assert report.identity_edges_added + report.social_edges_added < 19
        assert len(report.missing_nodes) > 0


def test_kaelen_reincarnation_and_its_deepening_share_the_same_pair() -> None:
    """The one required DEEPENING (bible §6 row 6): the Sorrel/Aurelia Marrow pair
    gets a SECRET_IDENTITY edge at ch20 and a second, richer REINCARNATION edge at
    ch34 — same two node names, not a different pair standing in for it."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = _seed_stub_work(repo)
        curate_ninth_house(repo, wid)

        nodes = {n.name: n.id for n in repo.list_nodes(wid)}
        sorrel, aurelia = nodes["Sorrel"], nodes["Aurelia Marrow"]
        pair_edges = [
            e for e in repo.list_edges(wid)
            if {e.source_id, e.target_id} == {sorrel, aurelia}
        ]
        assert {e.relation for e in pair_edges} == {"SECRET_IDENTITY", "REINCARNATION"}
        assert {e.revealed_chapter for e in pair_edges} == {20, 34}
