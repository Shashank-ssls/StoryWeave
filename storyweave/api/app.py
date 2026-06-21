"""FastAPI app factory.

Phase 0 ships only ``GET /api/v1/health``. Fenced graph/search routes arrive in
Phase 6 — and every data route will route through ``query/fence.py``.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from storyweave import __version__

API_PREFIX = "/api/v1"

router = APIRouter(prefix=API_PREFIX)


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "version": __version__}


def create_app() -> FastAPI:
    app = FastAPI(
        title="StoryWeave",
        version=__version__,
        description="A spoiler-aware knowledge engine for web novels.",
    )
    app.include_router(router)
    return app


app = create_app()
