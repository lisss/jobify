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
    SkillStat,
)
from app.services.cv import extract_skills_from_cv_text, extract_text_from_pdf
from app.services.jobs import suggest_locations
from app.services.roles import requirements_for_role, suggest_role_titles
from app.services.resources import build_roadmap, resources_for
from app.services.skills import missing_skills

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(session: Session = Depends(get_session)) -> HealthResponse:
    try:
        session.connection().execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return HealthResponse(status="ok", database=db_status)


@router.get("/suggest/roles")
def role_suggestions(q: str = "", limit: int = 12) -> dict:
    return {"suggestions": suggest_role_titles(q=q, limit=min(max(limit, 1), 30))}


@router.get("/suggest/locations")
def location_suggestions(q: str = "", limit: int = 40, session: Session = Depends(get_session)) -> dict:
    return {"suggestions": suggest_locations(session, q=q, limit=min(max(limit, 1), 80))}


@router.post("/insights", response_model=InsightsResponse)
def insights(body: InsightsRequest) -> InsightsResponse:
    """Requirements + learning materials for a role — no job matching."""
    reqs = requirements_for_role(body.query)
    # Adapt to missing_skills / roadmap helpers: (skill, count, percentage)
    top = [(skill, 1, pct) for skill, pct in reqs]
    gaps = missing_skills(top, body.cv_skills, min_percentage=0.0)
    focus = [skill for skill, _ in reqs]

    roadmap, study_hours = build_roadmap(top, body.cv_skills)

    return InsightsResponse(
        query=body.query,
        location=body.location,
        requirements=[SkillStat(skill=s, count=1, percentage=p) for s, p in reqs],
        missing_skills=[SkillStat(skill=s, count=c, percentage=p) for s, c, p in gaps],
        interview_questions=resources_for(focus, "interview"),
        books=resources_for(focus, "book"),
        courses=resources_for(focus, "course"),
        certifications=resources_for(focus, "certification"),
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
