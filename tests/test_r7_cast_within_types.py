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

from storyweave.graph.salience import compute_salience
from storyweave.query import fence
from tests.test_r6_salience_and_query import _work

EVERY_TYPE = ["Character", "Organization", "Place", "Item"]


def _eligible(repo, work_id: int, chapter: int, types: list[str]) -> int:
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


@pytest.mark.parametrize("chapter", [1, 2, 3])
@pytest.mark.parametrize("cast_size", [1, 2, 20])
def test_cast_n_characters_means_n_characters(
    tmp_path: Path, chapter: int, cast_size: int
) -> None:
    repo, work_id, _ = _work(tmp_path)
    compute_salience(work_id, repo)
    served = fence.visible_payload_nodes(repo, work_id, chapter, cast_size, ["Character"])
    expected = min(cast_size, _eligible(repo, work_id, chapter, ["Character"]))
    assert len(served) == expected
    assert {n.type for n in served} <= {"Character"}
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
