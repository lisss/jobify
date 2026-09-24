from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, text
from pathlib import Path
import uuid

from app.core.config import get_settings
from app.core.db import get_session
from app.models.schemas import (
    HealthResponse,
    InsightsRequest,
    InsightsResponse,
    JobOut,
    SalaryBucket,
    SkillStat,
)
from app.services.cv import extract_skills_from_cv_text, extract_text_from_pdf
from app.services.boards import fetch_all_marketplaces
from app.services.jobs import (
    salary_distribution,
    search_jobs,
    seed_sample_jobs,
    suggest_locations,
    suggest_roles,
)
from app.services.resources import build_roadmap, resources_for
from app.services.skills import missing_skills, skill_frequency

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(session: Session = Depends(get_session)) -> HealthResponse:
    try:
        session.connection().execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return HealthResponse(status="ok", database=db_status)


@router.post("/jobs/sync")
async def sync_jobs(
    query: str = "software engineer",
    location: str = "",
    session: Session = Depends(get_session),
) -> dict:
    sample = seed_sample_jobs(session)
    marketplace = await fetch_all_marketplaces(session, query=query, location=location, per_source=40)
    by_source: dict[str, int] = {}
    for item in marketplace:
        by_source[item["source"]] = by_source.get(item["source"], 0) + 1
    return {"sample": sample, "marketplace": len(marketplace), "by_source": by_source}


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    q: str = "",
    location: str = "",
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[JobOut]:
    jobs = search_jobs(session, query=q, location=location, limit=limit)
    return [_job_out(j) for j in jobs]


@router.get("/suggest/roles")
async def role_suggestions(
    q: str = "",
    limit: int = 8,
    session: Session = Depends(get_session),
) -> dict:
    marketplace: list[dict] = []
    if len(q.strip()) >= 2:
        marketplace = await fetch_all_marketplaces(
            session,
            query=q.strip(),
            per_source=35,
        )
    return {
        "suggestions": suggest_roles(
            session,
            q=q,
            limit=limit,
            marketplace_first=marketplace,
        )
    }


@router.get("/suggest/locations")
def location_suggestions(q: str = "", limit: int = 40, session: Session = Depends(get_session)) -> dict:
    return {"suggestions": suggest_locations(session, q=q, limit=min(max(limit, 1), 80))}


@router.post("/insights", response_model=InsightsResponse)
async def insights(
    body: InsightsRequest,
    session: Session = Depends(get_session),
) -> InsightsResponse:
    seed_sample_jobs(session)
    # Always scrape/aggregate boards for this query so results stay fresh
    await fetch_all_marketplaces(
        session,
        query=body.query,
        location=body.location,
        per_source=40,
    )

    jobs = search_jobs(session, query=body.query, location=body.location, limit=body.limit)
    if not jobs:
        jobs = search_jobs(session, query=body.query, location="", limit=body.limit)

    skill_lists = [j.skills or [] for j in jobs]
    top = skill_frequency(skill_lists)
    gaps = missing_skills(top, body.cv_skills)
    focus_skills = [s for s, _, _ in (gaps or top)[:10]]

    roadmap, study_hours = build_roadmap(top, body.cv_skills)

    return InsightsResponse(
        query=body.query,
        location=body.location,
        job_count=len(jobs),
        jobs=[_job_out(j) for j in jobs],
        top_skills=[SkillStat(skill=s, count=c, percentage=p) for s, c, p in top[:20]],
        missing_skills=[SkillStat(skill=s, count=c, percentage=p) for s, c, p in gaps[:15]],
        salary_distribution=[SalaryBucket(**b) for b in salary_distribution(jobs)],
        interview_questions=resources_for(focus_skills, "interview"),
        books=resources_for(focus_skills, "book"),
        courses=resources_for(focus_skills, "course"),
        github_projects=[],
        certifications=resources_for(focus_skills, "certification"),
        roadmap=roadmap,
        estimated_study_hours=study_hours,
    )


@router.post("/cv/parse")
async def parse_cv(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise HTTPException(status_code=400, detail="Upload a PDF or TXT CV")

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid.uuid4().hex}{suffix}"

    content = await file.read()
    dest.write_bytes(content)

    try:
        if suffix == ".pdf":
            text = extract_text_from_pdf(dest)
        else:
            text = dest.read_text(encoding="utf-8", errors="ignore")
    finally:
        dest.unlink(missing_ok=True)

    skills = extract_skills_from_cv_text(text)
    return {"skills": skills, "char_count": len(text)}


def _job_out(job) -> JobOut:
    return JobOut(
        id=job.id,
        source=job.source,
        title=job.title,
        company=job.company,
        location=job.location,
        url=job.url,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        currency=job.currency,
        skills=job.skills or [],
    )
