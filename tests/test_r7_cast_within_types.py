"""Retrofit R7 step 0: the cast rank is computed WITHIN the requested node types.

R6 [MEASURED] that the stored `node_salience.rank` is global across all four node
types, so "Main cast (20)" served 12 Characters at chapter 40 -- the number on the
dial matched nothing the reader could count on screen. That miss is left unedited in
`evidence/retrofit/R6_RESULT.md`; this phase changes the behaviour it exposed.

The fence is untouched and still first. These tests pin both halves of that claim:
the dial now means what it says, AND re-ranking cannot smuggle an unrevealed node in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storyweave.db.repository import Repository
from storyweave.graph.salience import compute_salience
from storyweave.query import fence
from tests.test_r6_salience_and_query import _work

EVERY_TYPE = ["Character", "Organization", "Place", "Item"]


def _eligible(repo: Repository, work_id: int, chapter: int, types: list[str]) -> int:
    """How many nodes of these types are both fenced in and ranked at `chapter`."""
    placeholders = ", ".join("?" for _ in types)
    rows = repo.conn.execute(
        f"""SELECT COUNT(*) AS n FROM nodes n
              JOIN node_salience s ON s.node_id = n.id AND s.chapter = ?
             WHERE n.work_id = ? AND n.revealed_chapter <= ?
               AND n.type IN ({placeholders})""",
        [chapter, work_id, chapter, *types],
    ).fetchone()
    return int(rows["n"])


def _fenced(repo: Repository, work_id: int, chapter: int, types: list[str]) -> int:
    placeholders = ", ".join("?" for _ in types)
    row = repo.conn.execute(
        f"""SELECT COUNT(*) AS n FROM nodes
             WHERE work_id = ? AND revealed_chapter <= ? AND type IN ({placeholders})""",
        [work_id, chapter, *types],
    ).fetchone()
    return int(row["n"])


@pytest.mark.parametrize("chapter", [1, 2, 3])
@pytest.mark.parametrize("cast_size", [1, 2, 20])
def test_cast_n_characters_means_n_characters(
    tmp_path: Path, chapter: int, cast_size: int
) -> None:
    repo, work_id, _ = _work(tmp_path)
    compute_salience(work_id, repo)
    served = fence.visible_payload_nodes(repo, work_id, chapter, cast_size, ["Character"])
    if repo.has_salience_for(work_id, chapter):
        expected = min(cast_size, _eligible(repo, work_id, chapter, ["Character"]))
    else:
        # No ranking exists at this chapter at all, so the dial has nothing to rank by
        # and is not applied -- see `test_a_chapter_with_no_ranking_serves_the_fenced_set`.
        expected = _fenced(repo, work_id, chapter, ["Character"])
    assert len(served) == expected
    assert {n.type for n in served} <= {"Character"}
    repo.close()


def test_a_chapter_with_no_ranking_serves_the_fenced_set(tmp_path: Path) -> None:
    """R7 regression: a work with no salience rows must not serve an EMPTY default view.

    R6 made the `/graph` default Characters-at-cast-20, and the dial JOINs `node_salience`.
    A work that never ran `compute_salience` -- the seeded Hollow Crown demo, or anything
    analysed before R6 -- therefore joined against nothing and served zero nodes:
    [MEASURED] `/graph?n=4` returned 0 nodes while `cast=all` returned 6. A ranking that
    does not exist means the dial cannot be applied, not that nobody qualifies.
    """
    repo, work_id, _ = _work(tmp_path)  # deliberately NO compute_salience call
    assert not repo.has_salience_for(work_id, 3)
    served = fence.visible_payload_nodes(repo, work_id, 3, 20, ["Character"])
    assert len(served) == _fenced(repo, work_id, 3, ["Character"])
    assert len(served) > 0
    repo.close()


def test_a_ranking_that_excludes_your_types_still_binds(tmp_path: Path) -> None:
    """The other half of the rule, and the reason it is not "fall back whenever empty".

    If a ranking EXISTS at this chapter but contains none of the requested types, the
    dial still applies and the view is legitimately empty -- the ranker has run and
    judged that nobody of that type is significant yet. [MEASURED] on the real book: at
    chapter 1 `ninth_house_r6.db` holds 13 salience rows and **none** is a Character,
    while 4 Characters are fenced in, so the default view is empty and the UI says "No
    main cast yet" rather than quietly overriding the ranker.
    """
    repo, work_id, ids = _work(tmp_path)
    compute_salience(work_id, repo)
    # Keep only the Place's ranking rows: a ranking exists, but no Character is in it.
    repo.conn.execute(
        "DELETE FROM node_salience WHERE node_id <> ?", (ids["Gate"],)
    )
    repo.conn.commit()
    if repo.has_salience_for(work_id, 3):
        assert fence.visible_payload_nodes(repo, work_id, 3, 20, ["Character"]) == []
        assert len(fence.visible_payload_nodes(repo, work_id, 3, 20, ["Place"])) == 1
    repo.close()


def test_adding_an_overlay_does_not_evict_characters_from_the_dial(tmp_path: Path) -> None:
    """Turning "Places" on must ADD places, not silently drop people for them.

    Under R6's global rank a Place could outrank a Character and take one of the 20
    slots. The dial is now per request: each type set gets its own top-N.
    """
    repo, work_id, _ = _work(tmp_path)
    compute_salience(work_id, repo)
    chars = fence.visible_payload_nodes(repo, work_id, 3, 20, ["Character"])
    with_places = fence.visible_payload_nodes(repo, work_id, 3, 20, ["Character", "Place"])
    assert {n.id for n in chars} <= {n.id for n in with_places}
    repo.close()


def test_re_ranking_cannot_admit_an_unrevealed_node(tmp_path: Path) -> None:
    """The window function orders rows the fence already admitted -- it never adds one."""
    repo, work_id, ids = _work(tmp_path)
    compute_salience(work_id, repo)
    for cast_size in (1, 20, None):
        served = fence.visible_payload_nodes(repo, work_id, 2, cast_size, EVERY_TYPE)
        assert ids["Stranger"] not in {n.id for n in served}
    repo.close()
