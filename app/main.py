"""FastAPI application entrypoint.

Run:  uvicorn app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.db.database import init_db

ROOT = Path(__file__).resolve().parent.parent
REACT_DIST = ROOT / "frontend-react" / "dist"
WEB_DIR = ROOT / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Autonomous follow-up: check for stale tasks on startup, then daily.
    # Drafts nudges only — never auto-sends (human reviews via /api/followups).
    from app.scheduler.followup import start_scheduler

    app.state.scheduler = start_scheduler()
    yield
    app.state.scheduler.shutdown(wait=False)


app = FastAPI(title="Meeting-to-Action Agent", version="0.1.0", lifespan=lifespan)
app.include_router(router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def index() -> RedirectResponse:
    """Send users to the React app."""
    return RedirectResponse("/app/")


# Serve the built React SPA at /app (same origin as /api, so no CORS needed).
if REACT_DIST.exists():
    app.mount("/app", StaticFiles(directory=str(REACT_DIST), html=True), name="app")
