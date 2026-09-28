"""Retrofit R3: four drawable types, chapter-gated entity labels, title linking.

The load-bearing tests here are the compatibility ones. R3 narrows what the graph draws
without migrating a single legacy row, so the things that must not break are: the frozen
v1 database still opens AND serves, and the seeded Hollow Crown fixture is byte-identical
(rule I2). Those are asserted directly rather than assumed.
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import stat
from pathlib import Path

import pytest

from storyweave.db.models import (
    GRAPH_NODE_TYPES,
    LEGACY_TYPE_MAP,
    EntityLabel,
    ExtractionMethod,
    GraphNodeType,
    LabelKind,
    LegacyTypeFate,
    Mention,
    Node,
    NodeType,
    Work,
    is_graph_type,
)
from storyweave.db.repository import Repository
from storyweave.graph.serialize import graph_json
from storyweave.nlp.cluster import cluster_mentions_detailed, is_contiguous_subsequence
from storyweave.nlp.labels import LABEL_TO_TYPE
from storyweave.nlp.titles import find_title_links
from storyweave.query import fence

REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_DB = REPO_ROOT / "evidence" / "v1_ninth_house.db"


# --------------------------------------------------------------------------- #
# The two vocabularies and the mapping between them
# --------------------------------------------------------------------------- #


def test_stored_vocabulary_is_unchanged() -> None:
    """The schema still accepts all eight v1 types — nothing was migrated away."""
    assert {t.value for t in NodeType} == {
        "Character", "Place", "Organization", "Item",
        "Ability", "Concept", "Event", "Title",
    }


def test_graph_vocabulary_is_the_four_and_a_subset_of_stored() -> None:
    assert {t.value for t in GraphNodeType} == {
        "Character", "Organization", "Place", "Item"
    }
    assert {t.value for t in GraphNodeType} <= {t.value for t in NodeType}
    assert {t.value for t in GRAPH_NODE_TYPES} == {t.value for t in GraphNodeType}


def test_legacy_type_map_covers_every_stored_type_with_a_documented_fate() -> None:
    assert set(LEGACY_TYPE_MAP) == set(NodeType)
    assert LEGACY_TYPE_MAP[NodeType.ABILITY] is LegacyTypeFate.NOT_A_NODE
    assert LEGACY_TYPE_MAP[NodeType.CONCEPT] is LegacyTypeFate.NOT_A_NODE
    assert LEGACY_TYPE_MAP[NodeType.EVENT] is LegacyTypeFate.NOT_A_NODE
    assert LEGACY_TYPE_MAP[NodeType.TITLE] is LegacyTypeFate.BECOMES_LABEL
    for t in GRAPH_NODE_TYPES:
        assert is_graph_type(t)


def test_gliner_prompts_only_the_four_drawable_types() -> None:
    """Enforcement point (a): nothing outside the four types is ever created."""
    assert set(LABEL_TO_TYPE.values()) <= set(GRAPH_NODE_TYPES)


# --------------------------------------------------------------------------- #
# Enforcement point (b): write-time rejection
# --------------------------------------------------------------------------- #


def _work(repo: Repository) -> int:
    repo.initialize_schema()
    return repo.create_work(Work(slug="t", title="T"))


def _node(work_id: int, node_type: NodeType, name: str = "X") -> Node:
    return Node(
        work_id=work_id,
        type=node_type,
        name=name,
        first_seen_chapter=1,
        revealed_chapter=1,
        extraction_method=ExtractionMethod.GLINER,
    )


@pytest.mark.parametrize(
    "node_type", [NodeType.ABILITY, NodeType.CONCEPT, NodeType.EVENT, NodeType.TITLE]
)
def test_writing_a_non_drawable_type_to_a_new_db_is_rejected(node_type: NodeType) -> None:
    with Repository(":memory:") as repo:
        wid = _work(repo)
        with pytest.raises(ValueError, match="not drawable"):
            repo.add_node(_node(wid, node_type))
        assert repo.list_nodes(wid) == []


@pytest.mark.parametrize("node_type", list(GRAPH_NODE_TYPES))
def test_writing_a_drawable_type_is_allowed(node_type: NodeType) -> None:
    with Repository(":memory:") as repo:
        wid = _work(repo)
        assert repo.add_node(_node(wid, node_type)) > 0


def test_legacy_escape_hatch_is_explicit_and_still_works() -> None:
    """The fixtures that predate R3 can still be seeded, but only on purpose."""
    with Repository(":memory:") as repo:
        wid = _work(repo)
        node_id = repo.add_node(_node(wid, NodeType.TITLE, "Prince"), allow_legacy_type=True)
        assert node_id > 0
        assert repo.list_nodes(wid)[0].type is NodeType.TITLE


# --------------------------------------------------------------------------- #
# Enforcement point (c): the display clause, after the fence clause
# --------------------------------------------------------------------------- #


def test_graph_read_narrows_the_fenced_set_to_drawable_types() -> None:
    with Repository(":memory:") as repo:
        wid = _work(repo)
        for t in (NodeType.CHARACTER, NodeType.PLACE):
            repo.add_node(_node(wid, t, f"{t.value} one"))
        for t in (NodeType.ABILITY, NodeType.CONCEPT, NodeType.EVENT, NodeType.TITLE):
            repo.add_node(_node(wid, t, f"{t.value} one"), allow_legacy_type=True)

        # The fence itself is unchanged: it still returns every revealed node.
        assert len(fence.visible_nodes(repo, wid, 1)) == 6
        # The graph read applies the display filter on top of it.
        drawn = fence.visible_graph_nodes(repo, wid, 1)
        assert {n.type for n in drawn} == {NodeType.CHARACTER, NodeType.PLACE}


def test_display_filter_never_widens_the_fence() -> None:
    """The display clause is a subset of the fence's result at every chapter."""
    with Repository(":memory:") as repo:
        wid = _work(repo)
        for chapter, t in enumerate(
            (NodeType.CHARACTER, NodeType.PLACE, NodeType.ITEM), start=1
        ):
            repo.add_node(
                Node(
                    work_id=wid,
                    type=t,
                    name=f"n{chapter}",
                    first_seen_chapter=chapter,
                    revealed_chapter=chapter,
                    extraction_method=ExtractionMethod.GLINER,
                )
            )
        for n in range(0, 5):
            fenced = {node.id for node in fence.visible_nodes(repo, wid, n)}
            drawn = {node.id for node in fence.visible_graph_nodes(repo, wid, n)}
            assert drawn <= fenced


# --------------------------------------------------------------------------- #
# entity_labels is a FENCE SURFACE
# --------------------------------------------------------------------------- #


def _labelled_work(repo: Repository) -> tuple[int, int]:
    wid = _work(repo)
    node_id = repo.add_node(
        Node(
            work_id=wid,
            type=NodeType.CHARACTER,
            name="Orin Drask",
            first_seen_chapter=1,
            revealed_chapter=1,
            extraction_method=ExtractionMethod.GLINER,
        )
    )
    for label, kind, chapter, primary in (
        ("Warden-Captain Orin Drask", LabelKind.FULL, 1, True),
        ("Drask", LabelKind.SHORT, 3, False),
        ("the Warden", LabelKind.TITLE, 5, False),
        ("the Gray Sparrow", LabelKind.EPITHET, 9, False),
    ):
        repo.add_entity_label(
            EntityLabel(
                entity_id=node_id,
                label=label,
                kind=kind,
                revealed_chapter=chapter,
                is_primary=primary,
                quote="evidence",
            )
        )
    return wid, node_id


def test_a_label_revealed_at_k_is_absent_at_k_minus_1() -> None:
    """The R3 fence requirement, stated as directly as it can be."""
    with Repository(":memory:") as repo:
        wid, _ = _labelled_work(repo)
        for label, k in (("Drask", 3), ("the Warden", 5), ("the Gray Sparrow", 9)):
            before = {x.label for x in fence.visible_entity_labels(repo, wid, k - 1)}
            at = {x.label for x in fence.visible_entity_labels(repo, wid, k)}
            assert label not in before, f"{label!r} leaked at chapter {k - 1}"
            assert label in at, f"{label!r} missing at its own chapter {k}"


def test_a_label_on_an_unrevealed_entity_is_hidden_even_if_the_label_is_revealed() -> None:
    """The both-rule: a name for someone the reader has not met is still a spoiler."""
    with Repository(":memory:") as repo:
        wid = _work(repo)
        late = repo.add_node(
            Node(
                work_id=wid,
                type=NodeType.CHARACTER,
                name="Hidden",
                first_seen_chapter=8,
                revealed_chapter=8,
                extraction_method=ExtractionMethod.GLINER,
            )
        )
        repo.add_entity_label(
            EntityLabel(
                entity_id=late, label="Hidden", kind=LabelKind.FULL, revealed_chapter=1
            )
        )
        assert fence.visible_entity_labels(repo, wid, 7) == []
        assert len(fence.visible_entity_labels(repo, wid, 8)) == 1


def test_label_reveal_is_absent_from_the_graph_payload_not_merely_hidden() -> None:
    with Repository(":memory:") as repo:
        wid, _ = _labelled_work(repo)
        before = graph_json(repo, wid, 4)
        after = graph_json(repo, wid, 5)
        assert "the Warden" not in repr(before["elements"])
        assert "the Warden" in repr(after["elements"])


def test_display_name_tracks_the_most_recent_naming_label() -> None:
    """R3: "the most recent label with revealed_chapter <= n", among naming kinds.

    Note the consequence, which is spec-correct but worth seeing stated: once a
    SHORTENING appears it becomes the display name, because it is the most recently
    learned spelling. At ch1 only the full form is known, so the node reads
    "Warden-Captain Orin Drask"; from ch3, when "Drask" first appears, it reads "Drask".
    Flagged in R3_RESULT.md as a candidate for R7 to revisit on readability grounds.
    """
    with Repository(":memory:") as repo:
        wid, node_id = _labelled_work(repo)
        # ch1: only the full form has been revealed.
        assert fence.visible_display_names(repo, wid, 1)[node_id] == (
            "Warden-Captain Orin Drask"
        )
        # ch3: the shortening is now the most recent naming label.
        assert fence.visible_display_names(repo, wid, 3)[node_id] == "Drask"
        # ch5: the TITLE is revealed but does NOT take over the name - it attaches to
        # the person (R3 task 5), so the display name is still the last NAME learned.
        assert fence.visible_display_names(repo, wid, 5)[node_id] == "Drask"
        assert "the Warden" in {
            x.label for x in fence.visible_entity_labels(repo, wid, 5)
        }
        # ch9: an EPITHET is a name, so it does become the display name.
        assert fence.visible_display_names(repo, wid, 9)[node_id] == "the Gray Sparrow"


# --------------------------------------------------------------------------- #
# Title linking: apposition only, ambiguity refused, fenced at the link chapter
# --------------------------------------------------------------------------- #


def test_title_links_only_on_exact_apposition() -> None:
    links, _ = find_title_links(
        {1: {"Orin Drask", "Drask"}},
        {
            1: "Orin Drask walked the quarter.",  # no apposition -> no link
            4: "He was the Archivist, everyone knew.",  # anaphora -> no link
            6: "Orin Drask, the Warden of the quarter, said nothing.",
            8: "the Scribe, Drask, bent over the ledger.",
        },
    )
    by_title = {link.title: link for link in links}
    assert set(by_title) == {"the Warden", "the Scribe"}
    assert by_title["the Warden"].chapter == 6
    assert by_title["the Scribe"].chapter == 8
    assert "the Archivist" not in by_title
    for link in links:
        assert link.quote  # a quote is mandatory


def test_title_apposed_to_two_people_is_refused_entirely() -> None:
    links, rejected = find_title_links(
        {1: {"Orin Drask"}, 2: {"Mira Quell"}},
        {
            3: "Orin Drask, the Warden, said nothing.",
            9: "Mira Quell, the Warden, took the post.",
        },
    )
    assert links == []
    assert len(rejected) == 1
    assert rejected[0].title == "the Warden"
    assert rejected[0].entity_ids == (1, 2)
    assert "ambiguous" in rejected[0].reason


def test_title_link_takes_the_earliest_chapter_that_states_it() -> None:
    links, _ = find_title_links(
        {1: {"Drask"}},
        {7: "Drask, the Warden, spoke.", 3: "Drask, the Warden, arrived."},
    )
    assert [(link.title, link.chapter) for link in links] == [("the Warden", 3)]


def test_a_linked_title_is_not_linked_in_any_payload_at_k_minus_1() -> None:
    """R3 task 7, end to end: link chapter k, invisible at k-1, visible at k."""
    with Repository(":memory:") as repo:
        wid = _work(repo)
        node_id = repo.add_node(
            Node(
                work_id=wid,
                type=NodeType.CHARACTER,
                name="Orin Drask",
                first_seen_chapter=1,
                revealed_chapter=1,
                extraction_method=ExtractionMethod.GLINER,
            )
        )
        links, _ = find_title_links(
            {node_id: {"Orin Drask"}},
            {1: "Orin Drask arrived.", 6: "Orin Drask, the Warden, said nothing."},
        )
        assert len(links) == 1 and links[0].chapter == 6
        repo.add_entity_label(
            EntityLabel(
                entity_id=node_id,
                label=links[0].title,
                kind=LabelKind.TITLE,
                revealed_chapter=links[0].chapter,
                quote=links[0].quote,
            )
        )
        assert "the Warden" not in repr(graph_json(repo, wid, 5)["elements"])
        assert "the Warden" in repr(graph_json(repo, wid, 6)["elements"])


# --------------------------------------------------------------------------- #
# Abbreviation merge: all five rules, and the refusals that keep over-merges at 0
# --------------------------------------------------------------------------- #


def _mention(surface: str, chapter: int, node_type: NodeType = NodeType.CHARACTER) -> Mention:
    return Mention(
        work_id=1,
        chapter_id=chapter,
        chapter_ordinal=chapter,
        ordinal=0,
        surface=surface,
        type=node_type,
        char_start=0,
        char_end=len(surface),
        score=0.9,
        extraction_method=ExtractionMethod.GLINER,
    )


def test_rule_1_requires_a_contiguous_ordered_run() -> None:
    assert is_contiguous_subsequence(("drask",), ("warden-captain", "orin", "drask"))
    assert is_contiguous_subsequence(("orin", "drask"), ("warden-captain", "orin", "drask"))
    # The failure the old set-subset test allowed: two words of a three-word name that
    # are not adjacent are a DIFFERENT person's name.
    assert not is_contiguous_subsequence(("orin", "quell"), ("orin", "drask", "quell"))
    # Reversed order is not a shortening either.
    assert not is_contiguous_subsequence(("drask", "orin"), ("orin", "drask", "quell"))


def test_rule_1_merges_a_clean_shortening() -> None:
    out = cluster_mentions_detailed(
        [_mention("Warden-Captain Orin Drask", 1), _mention("Drask", 2)]
    )
    assert [c.name for c in out.clusters] == ["Warden-Captain Orin Drask"]
    assert len(out.merges) == 1
    assert out.under_merges == []


def test_rule_1_refuses_a_non_contiguous_match() -> None:
    out = cluster_mentions_detailed(
        [_mention("Orin Drask Quell", 1), _mention("Orin Quell", 2)]
    )
    assert sorted(c.name for c in out.clusters) == ["Orin Drask Quell", "Orin Quell"]


def test_rule_2_refuses_when_the_short_form_appears_first() -> None:
    out = cluster_mentions_detailed(
        [_mention("Drask", 1), _mention("Warden-Captain Orin Drask", 5)]
    )
    assert len(out.clusters) == 2
    assert any("rule 2" in d.reason for d in out.under_merges)


def test_rule_3_refuses_outside_the_configured_chapter_window() -> None:
    from storyweave.ingest.work_config import ClusteringConfig

    mentions = [_mention("Warden-Captain Orin Drask", 1), _mention("Drask", 30)]
    far = cluster_mentions_detailed(mentions)
    assert len(far.clusters) == 2
    assert any("rule 3" in d.reason for d in far.under_merges)

    # The window is per-work DATA: widen it and the same pair merges.
    near = cluster_mentions_detailed(
        mentions, ClusteringConfig(abbreviation_chapter_window=40)
    )
    assert len(near.clusters) == 1


def test_rule_4_refuses_a_stopword_only_shortening() -> None:
    out = cluster_mentions_detailed([_mention("Lady Veris", 1), _mention("lady", 2)])
    assert len(out.clusters) == 2
    assert any("rule 4" in d.reason for d in out.under_merges)


def test_ambiguous_shortening_is_refused_and_nothing_is_over_merged() -> None:
    """Two full names could host "Drask", so neither claims it. THE over-merge guard."""
    out = cluster_mentions_detailed(
        [_mention("Orin Drask", 1), _mention("Mira Drask", 1), _mention("Drask", 2)]
    )
    assert sorted(c.name for c in out.clusters) == ["Drask", "Mira Drask", "Orin Drask"]
    assert out.merges == []
    assert any("ambiguous" in d.reason for d in out.under_merges)


def test_a_shortening_of_a_different_type_is_never_merged() -> None:
    out = cluster_mentions_detailed(
        [_mention("Sorrel Vane", 1), _mention("Vane", 2, NodeType.PLACE)]
    )
    assert len(out.clusters) == 2


def test_merging_can_be_switched_off_entirely() -> None:
    from storyweave.ingest.work_config import ClusteringConfig

    out = cluster_mentions_detailed(
        [_mention("Warden-Captain Orin Drask", 1), _mention("Drask", 2)],
        ClusteringConfig(merge_abbreviations=False),
    )
    assert len(out.clusters) == 2


def test_every_under_merge_carries_a_reason() -> None:
    """The report must be able to list WHY each alias was left unmerged."""
    out = cluster_mentions_detailed(
        [_mention("Orin Drask", 1), _mention("Mira Drask", 1), _mention("Drask", 2)]
    )
    assert out.under_merges
    for decision in out.under_merges:
        assert decision.reason and not decision.merged


# --------------------------------------------------------------------------- #
# Migration, up and down, on a fixture database
# --------------------------------------------------------------------------- #


def _fixture_db(path: Path) -> Path:
    """A small database WITHOUT entity_labels, as a pre-R3 database would be."""
    with Repository(path) as repo:
        wid = _work(repo)
        node_id = repo.add_node(
            Node(
                work_id=wid,
                type=NodeType.CHARACTER,
                name="Orin Drask",
                first_seen_chapter=1,
                revealed_chapter=1,
                extraction_method=ExtractionMethod.GLINER,
            )
        )
        from storyweave.db.models import Chapter

        chapter_id = repo.add_chapter(
            Chapter(
                work_id=wid,
                ordinal=1,
                clean_text="Orin Drask walked. Drask said nothing.",
                content_hash="h",
            )
        )
        for surface, chapter in (("Orin Drask", 1), ("Drask", 4)):
            mention_id = repo.add_mention(
                Mention(
                    work_id=wid,
                    chapter_id=chapter_id,
                    chapter_ordinal=chapter,
                    ordinal=0,
                    surface=surface,
                    type=NodeType.CHARACTER,
                    char_start=0,
                    char_end=len(surface),
                    score=0.9,
                )
            )
            repo.set_mention_node(mention_id, node_id)
        repo.conn.execute("DROP TABLE entity_labels")
        repo.conn.commit()
    return path


def test_migration_up_then_down(tmp_path: Path) -> None:
    from tools.migrate_entity_labels import down, table_exists, up

    db = _fixture_db(tmp_path / "pre_r3.sqlite")
    with sqlite3.connect(db) as conn:
        assert not table_exists(conn, "entity_labels")
        nodes_before = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    # up: creates the table and backfills name + alias surfaces with their own chapters
    assert up(db) == 2
    with Repository(db) as repo:
        work = repo.get_work_by_slug("t")
        assert work is not None and work.id is not None
        labels = {
            (x.label, x.kind.value, x.revealed_chapter)
            for x in repo.list_entity_labels_revealed(work.id, 40)
        }
        assert labels == {("Orin Drask", "full", 1), ("Drask", "short", 4)}
        # The alias is fenced to ITS OWN first appearance, not the entity's reveal.
        assert {x.label for x in repo.list_entity_labels_revealed(work.id, 3)} == {
            "Orin Drask"
        }

    # up is idempotent (the UNIQUE key absorbs a re-run)
    up(db)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM entity_labels").fetchone()[0] == 2

    # down: drops the table and touches nothing else
    down(db)
    with sqlite3.connect(db) as conn:
        assert not table_exists(conn, "entity_labels")
        assert conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] == nodes_before


# --------------------------------------------------------------------------- #
# Compatibility: the frozen v1 DB and the Hollow Crown fixture (rule I2)
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not FROZEN_DB.is_file(), reason="frozen baseline DB not present")
def test_frozen_v1_database_still_opens_and_serves(tmp_path: Path) -> None:
    """It contains Ability/Concept/Event/Title rows; it must load AND serve under R3."""
    copy = tmp_path / "frozen.db"
    shutil.copy2(FROZEN_DB, copy)
    copy.chmod(stat.S_IWRITE | stat.S_IREAD)  # copy2 preserves the read-only bit

    with Repository(copy) as repo:
        work = repo.get_work_by_slug("the-ninth-house")
        assert work is not None and work.id is not None

        # Every legacy row still loads through pydantic validation.
        all_nodes = repo.list_nodes(work.id)
        assert len(all_nodes) == 206
        assert {n.type for n in all_nodes} > set(GRAPH_NODE_TYPES)

        # The fence is unchanged; the graph read narrows it.
        assert len(fence.visible_nodes(repo, work.id, 40)) == 206
        drawn = fence.visible_graph_nodes(repo, work.id, 40)
        assert {n.type for n in drawn} <= set(GRAPH_NODE_TYPES)
        assert len(drawn) < 206  # the legacy types are no longer drawn

        # And it serves: no phantom nodes, every node fully populated.
        payload = graph_json(repo, work.id, 40)
        served = payload["elements"]["nodes"]
        assert len(served) == len(drawn)
        for element in served:
            data = element["data"]
            assert data["type"] in {t.value for t in GRAPH_NODE_TYPES}
            assert data["label"]  # a legacy DB has no labels; falls back to node.name
        # Every served edge has both endpoints among the served nodes.
        ids = {element["data"]["id"] for element in served}
        for element in payload["elements"]["edges"]:
            assert element["data"]["source"] in ids
            assert element["data"]["target"] in ids


def test_hollow_crown_fixture_is_byte_identical(tmp_path: Path) -> None:
    """Rule I2: R3 must not change one byte of the seeded fixture."""
    from storyweave.demo.seed import seed_hollow_crown

    db = tmp_path / "hc.sqlite"
    with Repository(db) as repo:
        repo.initialize_schema()
        seed_hollow_crown(repo)

    digest = hashlib.sha256()
    with sqlite3.connect(db) as conn:
        for table in (
            "works", "nodes", "edges", "node_properties",
            "chapters", "chunks", "mentions", "arcs",
        ):
            for row in conn.execute(f"SELECT * FROM {table} ORDER BY rowid"):
                digest.update(repr(row).encode())

    # Recorded before any R3 code was written; see docs/retrofit/RETROFIT_PROGRESS.md.
    assert digest.hexdigest() == (
        "e73a69c07d36fa7126173fb86ee5f8c3f158228bffc9adbc3bc54a8108ecc482"
    )
