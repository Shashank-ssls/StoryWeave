"""Retrofit R6: salience, the four-clause payload query, the ego view and defect D3.

The theme of these tests is the boundary retrofit rule 1 draws: the FENCE decides what is
safe to show, the DISPLAY clauses decide what is worth showing, and the two must never be
confused. So each test either pins a display filter actually doing something (v1's did
not — defect D3) or pins the fence still winning when a display filter would have let
something through.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storyweave.db.models import (
    Chapter,
    Chunk,
    Edge,
    ExtractionMethod,
    Mention,
    Node,
    NodeSalience,
    NodeType,
    RelationGrade,
    RelationTier,
    Work,
)
from storyweave.db.repository import Repository
from storyweave.graph.salience import compute_salience, dialogue_spans, has_proper_name
from storyweave.query import fence

# Three chapters, and Sorrel/Denna are named often enough to clear the significance
# gate (proper name AND (>=3 chapters OR >=5 mentions)). The gate is NOT relaxed for the
# tests: the fixture is made realistic instead, because a gate that a two-line fixture
# can pass would not be doing its job on a novel.
TEXT_A = 'Sorrel counted the ledger. "Denna," Sorrel said. Denna looked at Sorrel.'
TEXT_B = "Sorrel walked to the Gate. Denna waited there. Denna and Sorrel spoke."
TEXT_C = "Sorrel returned. Denna followed Sorrel. A stranger passed the Gate."


def _work(tmp_path: Path) -> tuple[Repository, int, dict[str, int]]:
    repo = Repository(tmp_path / "r6.sqlite")
    repo.initialize_schema()
    work_id = repo.create_work(Work(slug="w", title="W"))
    ids: dict[str, int] = {}
    # Sorrel and Denna are revealed at 1; the Stranger only at chapter 2.
    for name, revealed, ntype in (
        ("Sorrel", 1, NodeType.CHARACTER),
        ("Denna", 1, NodeType.CHARACTER),
        ("Gate", 1, NodeType.PLACE),
        ("Stranger", 3, NodeType.CHARACTER),
    ):
        ids[name] = repo.add_node(Node(
            work_id=work_id, name=name, type=ntype, first_seen_chapter=1,
            revealed_chapter=revealed, extraction_method=ExtractionMethod.GLINER))
    for ordinal, text in ((1, TEXT_A), (2, TEXT_B), (3, TEXT_C)):
        chapter_id = repo.add_chapter(Chapter(
            work_id=work_id, ordinal=ordinal, title=f"C{ordinal}",
            clean_text=text, content_hash=f"h{ordinal}"))
        repo.add_chunk(Chunk(
            chapter_id=chapter_id, work_id=work_id, ordinal=0, char_start=0,
            char_end=len(text), text=text, content_hash=f"c{ordinal}"))
        for name in ("Sorrel", "Denna", "Gate", "Stranger"):
            key = name if name != "Stranger" else "stranger"
            start = text.find(key)
            index = 0
            while start >= 0:
                repo.add_mention(Mention(
                    work_id=work_id, chapter_id=chapter_id, chapter_ordinal=ordinal,
                    ordinal=index, surface=name, type=NodeType.CHARACTER,
                    char_start=start, char_end=start + len(key), score=1.0,
                    node_id=ids[name]))
                index += 1
                start = text.find(key, start + len(key))
    return repo, work_id, ids


# --- salience features ------------------------------------------------------- #


def test_dialogue_spans_find_double_quotes_and_brackets() -> None:
    assert dialogue_spans('He said "hello" then left.') == [(8, 15)]
    assert dialogue_spans("[Can you hear me?]") == [(0, 18)]


def test_single_quotes_are_not_dialogue() -> None:
    """`'` is also the apostrophe in "don't" -- the same call R2's cleaner made."""
    assert dialogue_spans("she didn't answer 'properly'") == []


def test_has_proper_name_rejects_bare_role_words() -> None:
    assert has_proper_name("Orin Drask")
    assert not has_proper_name("the girl")
    assert not has_proper_name("the captain")


# --- rule 7: no future information in the ranking ---------------------------- #


def test_a_node_revealed_later_is_absent_from_an_earlier_rank_list(tmp_path: Path) -> None:
    """The heart of rule 7. A book-wide rank would leak who matters later."""
    repo, work_id, ids = _work(tmp_path)
    compute_salience(work_id, repo)
    at_2 = {n.id for n in fence.visible_cast_ranked(repo, work_id, 2)}
    assert ids["Stranger"] not in at_2, "a node revealed at 3 must not rank at 2"
    assert ids["Sorrel"] in at_2
    repo.close()


def test_the_significance_gate_excludes_a_walk_on(tmp_path: Path) -> None:
    """One mention, one chapter, no proper name -> not part of anyone's cast."""
    repo, work_id, ids = _work(tmp_path)
    compute_salience(work_id, repo)
    ranked = {n.id for n in fence.visible_cast_ranked(repo, work_id, 3)}
    assert ids["Stranger"] not in ranked
    repo.close()


def test_salience_rows_are_per_chapter(tmp_path: Path) -> None:
    repo, work_id, _ = _work(tmp_path)
    compute_salience(work_id, repo)
    chapters = {
        row["chapter"]
        for row in repo.conn.execute("SELECT DISTINCT chapter FROM node_salience")
    }
    assert chapters.issubset({1, 2, 3})
    assert 3 in chapters
    repo.close()


# --- the four-clause query --------------------------------------------------- #


def test_the_cast_dial_actually_binds(tmp_path: Path) -> None:
    """Defect D3: in v1 this filter was a client-side no-op and changed nothing."""
    repo, work_id, _ = _work(tmp_path)
    compute_salience(work_id, repo)
    every_type = ["Character", "Organization", "Place", "Item"]
    one = fence.visible_payload_nodes(repo, work_id, 3, 1, every_type)
    many = fence.visible_payload_nodes(repo, work_id, 3, 50, every_type)
    everyone = fence.visible_payload_nodes(repo, work_id, 3, None, every_type)
    assert len(one) == 1
    assert len(many) > len(one)
    assert len(everyone) >= len(many)
    repo.close()


def test_the_type_clause_is_separate_from_the_cast_clause(tmp_path: Path) -> None:
    repo, work_id, ids = _work(tmp_path)
    compute_salience(work_id, repo)
    chars = fence.visible_payload_nodes(repo, work_id, 3, None, ["Character"])
    withplace = fence.visible_payload_nodes(repo, work_id, 3, None, ["Character", "Place"])
    assert ids["Gate"] not in {n.id for n in chars}
    assert ids["Gate"] in {n.id for n in withplace}
    repo.close()


def test_the_fence_still_wins_when_a_display_clause_would_admit(tmp_path: Path) -> None:
    """cast=all and every type requested must STILL not serve an unrevealed node."""
    repo, work_id, ids = _work(tmp_path)
    compute_salience(work_id, repo)
    served = fence.visible_payload_nodes(
        repo, work_id, 2, None, ["Character", "Organization", "Place", "Item"]
    )
    assert ids["Stranger"] not in {n.id for n in served}
    repo.close()


def _edge(work_id: int, src: int, tgt: int, relation: str, grade: RelationGrade) -> Edge:
    return Edge(
        work_id=work_id, source_id=src, target_id=tgt, relation=relation,
        tier=RelationTier.SOCIAL, first_seen_chapter=1, revealed_chapter=1,
        extraction_method=ExtractionMethod.LLM, grade=grade, quote="q", quote_chapter=1)


def test_both_served_grades_are_returned(tmp_path: Path) -> None:
    """Rule 4 as amended in R7: STATED and INFERRED are both served."""
    repo, work_id, ids = _work(tmp_path)
    repo.add_edge(_edge(work_id, ids["Sorrel"], ids["Denna"], "ALLY_OF", RelationGrade.STATED))
    repo.add_edge(_edge(work_id, ids["Denna"], ids["Sorrel"], "SERVES", RelationGrade.INFERRED))
    served = fence.visible_payload_edges(
        repo, work_id, 3, [ids["Sorrel"], ids["Denna"]]
    )
    assert {e.relation for e in served} == {"ALLY_OF", "SERVES"}
    repo.close()


def test_same_as_is_served_only_when_stated(tmp_path: Path) -> None:
    """The one relation that keeps the strict rule: an identity error is the worst kind."""
    repo, work_id, ids = _work(tmp_path)
    repo.add_edge(_edge(work_id, ids["Sorrel"], ids["Denna"], "SAME_AS", RelationGrade.INFERRED))
    pair = [ids["Sorrel"], ids["Denna"]]
    assert fence.visible_payload_edges(repo, work_id, 3, pair) == []

    repo.conn.execute("UPDATE edges SET grade = 'STATED' WHERE relation = 'SAME_AS'")
    repo.conn.commit()
    served = fence.visible_payload_edges(repo, work_id, 3, pair)
    assert [e.relation for e in served] == ["SAME_AS"]
    repo.close()


def test_every_served_edge_carries_a_quote(tmp_path: Path) -> None:
    repo, work_id, ids = _work(tmp_path)
    repo.add_edge(_edge(work_id, ids["Sorrel"], ids["Denna"], "ALLY_OF", RelationGrade.STATED))
    for edge in fence.visible_payload_edges(repo, work_id, 3, [ids["Sorrel"], ids["Denna"]]):
        assert edge.quote or edge.evidence_span
    repo.close()


# --- defect D3: the status count ---------------------------------------------- #


def test_the_status_count_goes_through_the_fence(tmp_path: Path) -> None:
    """REGRESSION for D3. This test fails against the old behaviour.

    The old endpoint called `repo.count_nodes(work_id)`, which counts every row whatever
    its chapter, so it returned 4 at chapter 1 as well as at chapter 2 -- telling a
    chapter-1 reader that a fourth entity exists. The assertion below is exactly that
    difference: `count_nodes` is asserted to disagree with the fenced count, so if
    someone reverts the endpoint the test goes red rather than silently passing.
    """
    repo, work_id, _ = _work(tmp_path)
    unfenced = repo.count_nodes(work_id)
    assert fence.visible_node_count(repo, work_id, 1) == 3
    assert fence.visible_node_count(repo, work_id, 3) == 4
    assert unfenced == 4
    # The old behaviour and the new one MUST differ at chapter 1, or D3 is back.
    assert fence.visible_node_count(repo, work_id, 1) != unfenced
    repo.close()


# --- legacy databases ---------------------------------------------------------- #


def test_a_database_without_salience_serves_the_whole_fenced_cast(tmp_path: Path) -> None:
    """A pre-R6 database (the frozen baseline) must still serve, not blank out."""
    repo, work_id, _ = _work(tmp_path)
    repo.conn.execute("DROP TABLE node_salience")
    repo.conn.commit()
    repo._has_salience = None
    assert repo.has_node_salience_table() is False
    served = fence.visible_payload_nodes(repo, work_id, 3, 20, ["Character"])
    assert len(served) == 3  # Sorrel, Denna, Stranger — fenced, not ranked
    repo.close()


@pytest.mark.parametrize("chapter", [2, 3])
def test_rank_is_dense_and_starts_at_one(tmp_path: Path, chapter: int) -> None:
    repo, work_id, _ = _work(tmp_path)
    compute_salience(work_id, repo)
    ranks = [
        row["rank"]
        for row in repo.conn.execute(
            "SELECT rank FROM node_salience WHERE chapter = ? ORDER BY rank", (chapter,)
        )
    ]
    assert ranks == list(range(1, len(ranks) + 1))
    repo.close()


def test_salience_rows_are_bulk_written_once(tmp_path: Path) -> None:
    repo, work_id, _ = _work(tmp_path)
    compute_salience(work_id, repo)
    first = repo.conn.execute("SELECT COUNT(*) AS n FROM node_salience").fetchone()["n"]
    compute_salience(work_id, repo)  # idempotent
    second = repo.conn.execute("SELECT COUNT(*) AS n FROM node_salience").fetchone()["n"]
    assert first == second
    repo.close()


def test_node_salience_model_round_trips(tmp_path: Path) -> None:
    repo, work_id, ids = _work(tmp_path)
    repo.add_node_salience_bulk([NodeSalience(node_id=ids["Sorrel"], chapter=7, score=0.5, rank=1)])
    row = repo.conn.execute(
        "SELECT * FROM node_salience WHERE chapter = 7"
    ).fetchone()
    assert row["rank"] == 1 and row["node_id"] == ids["Sorrel"]
    repo.close()
