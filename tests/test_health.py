"""Phase 0: the health endpoint serves at /api/v1/health."""

from __future__ import annotations

from fastapi.testclient import TestClient

from storyweave import __version__
from storyweave.api.app import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
