from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.db import engine, init_db
from app.services.jobs import seed_sample_jobs
from sqlmodel import Session


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"name": "jobify-api", "docs": "/docs"}
