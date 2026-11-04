"""CONTINUITY AI — FastAPI backend entry point."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from app.core.security import is_ai_configured
from app.database.db import init_db

VERSION = "1.0.0"

# Built frontend (frontend/dist). When present, the API server also serves the
# SPA so the whole app runs from a single process (see README "Production build").
_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CONTINUITY AI", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": VERSION,
        "ai_configured": is_ai_configured(),
        "ai_provider": "gemini",
    }


# Routers
from app.api import assistant, audit, documents, handover, knowledge, projects, settings  # noqa: E402

app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(knowledge.router)
app.include_router(assistant.router)
app.include_router(handover.router)
app.include_router(settings.router)
app.include_router(audit.router)

# ---------------------------------------------------------------------------
# Static frontend (production build). Registered last so /api and /health win.
# ---------------------------------------------------------------------------
if _DIST_DIR.is_dir():
    _index = _DIST_DIR / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa(full_path: str):
        # Never let the SPA fallback swallow unknown API routes — return a
        # proper JSON 404 so clients can surface real errors.
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        # Serve a real file from dist/ when it exists (assets, favicon, icons)
        candidate = (_DIST_DIR / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(_DIST_DIR):
            return FileResponse(candidate)
        # SPA fallback: any other route returns the app shell
        if _index.exists():
            return FileResponse(_index)
        return PlainTextResponse("Frontend build not found", status_code=404)