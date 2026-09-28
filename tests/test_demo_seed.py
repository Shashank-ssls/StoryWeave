"""Phase 8 slice: the CC0 demo seed + the server-side fence, proven at the PAYLOAD level.

The frontend never post-filters — so the guarantee that matters is that an unrevealed
element is ABSENT FROM THE CLIENT PAYLOAD, not merely hidden in the UI. These tests hit
the real API (TestClient) against the seeded demo DB and assert the signature bloom:
Wren==Caelum's SECRET_IDENTITY edge (and the Caelum node) do not exist in the graph
response at N=1 and appear at N=2.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from storyweave.api.app import app
from storyweave.api.deps import get_repository
from storyweave.db.repository import Repository
from storyweave.demo.seed import DEMO_SLUG, seed_hollow_crown
from storyweave.query import fence


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = str(tmp_path / "demo.sqlite")
    repo = Repository(db_path)
    repo.initialize_schema()
    seed_hollow_crown(repo)

    def _override() -> Iterator[Repository]:
        r = Repository(db_path)
        try:
            yield r
        finally:
            r.close()

    app.dependency_overrides[get_repository] = _override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        repo.close()


def _graph(client: TestClient, n: int) -> dict[str, Any]:
    resp = client.get(f"/api/v1/works/{DEMO_SLUG}/graph", params={"n": n})
    assert resp.status_code == 200
    elements: dict[str, Any] = resp.json()["elements"]
    return elements


def _relations(elements: dict[str, Any]) -> set[str]:
    return {e["data"]["relation"] for e in elements["edges"]}


def _labels(elements: dict[str, Any]) -> set[str]:
    return {node["data"]["label"] for node in elements["nodes"]}


def test_demo_is_listed_with_four_chapters(client: TestClient) -> None:
    works = client.get("/api/v1/works").json()["works"]
    hc = next(w for w in works if w["slug"] == DEMO_SLUG)
    assert hc["chapter_count"] == 4


def test_secret_identity_edge_absent_in_payload_at_n1_present_at_n2(client: TestClient) -> None:
    at1 = _graph(client, 1)
    # The reveal must not exist in the client payload at all (not merely be hidden).
    assert "SECRET_IDENTITY" not in _relations(at1)
    assert "Prince Caelum" not in _labels(at1)  # Caelum is revealed at ch2
    assert "Wren" in _labels(at1)  # Wren is revealed at ch1

    at2 = _graph(client, 2)
    assert "SECRET_IDENTITY" in _relations(at2)
    assert "Prince Caelum" in _labels(at2)
    # The layered TRANSMIGRATED_INTO reveal is still in the future at N=2.
    assert "TRANSMIGRATED_INTO" not in _relations(at2)


def test_layered_and_alias_reveals_bloom_at_their_chapters(client: TestClient) -> None:
    assert "ALIAS" not in _relations(_graph(client, 2))
    assert "ALIAS" in _relations(_graph(client, 3))  # Sparrow==Veris at ch3
    assert "TRANSMIGRATED_INTO" in _relations(_graph(client, 4))  # layered Wren==Caelum at ch4


def test_all_eight_node_types_stored_but_only_four_are_drawn(
    client: TestClient, tmp_path: Path
) -> None:
    """Retrofit R3 changed this test's contract, deliberately. Both halves are asserted.

    BEFORE R3 this asserted that the graph payload contained all eight v1 types. R3's
    decision (c) is that the payload serves only the four drawable ones, so that
    assertion now states the opposite of the intended behaviour and could not be kept.

    What the test was really protecting is preserved and strengthened: the Hollow Crown
    fixture still STORES one node of each of the eight types, and those rows still fence
    correctly - so the fixture continues to exercise the whole ontology. What changed is
    only what is DRAWN. The fixture's own rows are byte-identical (rule I2); no seeded
    data was touched to make this pass.
    """
    # 1. All eight types are still stored and still pass the fence, unchanged.
    # pytest hands the fixture and the test the same tmp_path, so this is the same file
    # the client is serving - no app state plumbing needed.
    with Repository(str(tmp_path / "demo.sqlite")) as repo:
        work = repo.get_work_by_slug(DEMO_SLUG)
        assert work is not None and work.id is not None
        stored = {n.type.value for n in fence.visible_nodes(repo, work.id, 4)}
        assert stored == {
            "Character", "Place", "Organization", "Item",
            "Ability", "Concept", "Event", "Title",
        }
        # 2. The graph read narrows the same fenced set to the four drawable types.
        drawn = {n.type.value for n in fence.visible_graph_nodes(repo, work.id, 4)}
        assert drawn == {"Character", "Place", "Organization", "Item"}

    # 3. And that is exactly what reaches the client.
    payload_types = {node["data"]["type"] for node in _graph(client, 4)["nodes"]}
    assert payload_types == {"Character", "Place", "Organization", "Item"}
