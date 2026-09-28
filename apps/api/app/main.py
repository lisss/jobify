from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.core.db import engine, init_db
from app.models import cv_upload as _cv_upload  # noqa: F401 — register table
from app.models import job as _job  # noqa: F401 — register table
from app.services.jobs import seed_sample_jobs
from sqlmodel import Session

# Built Vite app (copied next to the API in Docker / Render builds).
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        init_db()
        with Session(engine) as session:
            seed_sample_jobs(session)
    except Exception as exc:
        # Allow API to boot even if DB is temporarily unavailable
        print(f"[jobify] DB init warning: {exc}")
    yield


settings = get_settings()

app = FastAPI(
    title="Jobify API",
    description="Job + learning insights aggregator",
    version="0.1.0",
    lifespan=lifespan,
)

_cors_origins = settings.cors_origins or ["*"]
# Browsers reject Allow-Origin: * together with credentials.
_cors_credentials = _cors_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/api")
def api_root() -> dict:
    return {"name": "jobify-api", "docs": "/docs"}


if STATIC_DIR.is_dir():
    # Must be last: API routes above take priority.
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="spa")
else:

    @app.get("/")
    def root() -> dict:
        return {"name": "jobify-api", "docs": "/docs", "hint": "UI not bundled"}
