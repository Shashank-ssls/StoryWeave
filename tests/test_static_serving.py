"""One-origin serving (integration phase Part C.1): the built frontend, served from
the same FastAPI process as the API — no CORS needed in this mode.

Uses a fake `dist/` (monkeypatched in place of the real `frontend/dist`) rather than
requiring a real `npm run build` in this test run, so the light-venv pytest gate
doesn't need Node — but the fake tree has the exact same shape a real Vite build
produces (`index.html`, `assets/`, `favicon.svg`, `og-image.png`), so the routing
logic itself is exercised for real.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import storyweave.api.app as app_module


@pytest.fixture
def fake_dist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>StoryWeave</title>", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    (dist / "og-image.png").write_bytes(b"\x89PNG\r\n")
    (dist / "assets" / "index-abc123.js").write_text("console.log('hi')", encoding="utf-8")
    monkeypatch.setattr(app_module, "_FRONTEND_DIST", dist)
    return dist


def test_no_dist_means_no_static_routes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The default state on this repo's own test run (and every CI run that never
    built the frontend): create_app() must not error, and must not mount anything."""
    monkeypatch.setattr(app_module, "_FRONTEND_DIST", tmp_path / "does-not-exist")
    app = app_module.create_app()
    client = TestClient(app)
    # No dist -> no catch-all -> an unmatched path is a plain 404, not index.html.
    resp = client.get("/")
    assert resp.status_code == 404


def test_root_serves_index_html(fake_dist: Path) -> None:
    app = app_module.create_app()
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "StoryWeave" in resp.text


def test_asset_is_served_from_the_assets_mount(fake_dist: Path) -> None:
    app = app_module.create_app()
    client = TestClient(app)
    resp = client.get("/assets/index-abc123.js")
    assert resp.status_code == 200
    assert "console.log" in resp.text


def test_favicon_and_og_image_served(fake_dist: Path) -> None:
    app = app_module.create_app()
    client = TestClient(app)
    assert client.get("/favicon.svg").status_code == 200
    assert client.get("/og-image.png").status_code == 200


def test_unmatched_path_falls_back_to_index_html(fake_dist: Path) -> None:
    """The hash router never sends its own routes to the server, but the fallback
    is a real catch-all regardless — a client requesting a path-style URL directly
    (bookmarked, or a future history-API router) still gets the SPA shell, not a
    404."""
    app = app_module.create_app()
    client = TestClient(app)
    resp = client.get("/work/some-slug/entity/1")
    assert resp.status_code == 200
    assert "StoryWeave" in resp.text


def test_api_routes_still_win_over_the_catch_all(fake_dist: Path) -> None:
    """The one thing that must never happen: /api/v1/* swallowed by the SPA
    fallback. A real work lookup 404s with the API's own JSON error, not HTML."""
    app = app_module.create_app()
    client = TestClient(app)
    resp = client.get("/api/v1/works/does-not-exist/graph?n=1")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
