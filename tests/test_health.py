"""Phase 0/6: the health endpoint serves at /api/v1/health with DB status."""

from __future__ import annotations

from fastapi.testclient import TestClient

from storyweave import __version__
from storyweave.api.app import create_app
from storyweave.api.deps import get_repository
from storyweave.db.repository import Repository


def test_health_endpoint() -> None:
    repo = Repository(":memory:")
    repo.initialize_schema()
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repo

    resp = TestClient(app).get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["database"] == "ok"
