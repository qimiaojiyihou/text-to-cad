"""Text-to-CAD Web API (Unified)

FastAPI backend that turns natural language into STEP/GLB via LLM + build123d.
Uses an in-memory task queue so long-running CAD generation never blocks HTTP.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 加载 .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.db.database import init_db
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Text-to-CAD API", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_db()


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from app.api.v1 import auth as auth_router
from app.api.v1 import users as users_router
from app.api.v1 import cad as cad_router

app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_router.router, prefix="/api/v1/users", tags=["users"])
app.include_router(cad_router.router, prefix="/api", tags=["cad"])


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    from app.api.v1.cad import _get_openai_client, _get_llm_model
    client = _get_openai_client()
    return {
        "ok": True,
        "llm_configured": client is not None,
        "llm_model": _get_llm_model(),
        "llm_base_url": os.getenv("OPENAI_BASE_URL", "").strip() or "default (openai.com)",
        "repo_root": str(settings.REPO_ROOT),
    }


# ---------------------------------------------------------------------------
# Static frontend / admin (only when MOUNT_STATIC is not explicitly disabled)
# ---------------------------------------------------------------------------
MOUNT_STATIC = os.getenv("MOUNT_STATIC", "true").lower() != "false"
DIST_DIR = settings.REPO_ROOT / "web-app" / "frontend" / "dist"
ADMIN_DIR = settings.REPO_ROOT / "web-app" / "admin" / "dist"

if MOUNT_STATIC:
    if ADMIN_DIR.exists():
        app.mount("/admin-static", StaticFiles(directory=str(ADMIN_DIR), html=True), name="admin")
    if DIST_DIR.exists():
        app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="frontend")
