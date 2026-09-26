from datetime import datetime
from pathlib import Path
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from sqlmodel import Session, col, select, text

from app.core.db import get_session
from app.core.session import ensure_session_id, get_session_id
from app.models.cv_upload import CvUpload
from app.models.schemas import (
    HealthResponse,
    InsightsRequest,
    InsightsResponse,
    SkillStat,
    SkillsForRoleRequest,
)
from app.services.cv import extract_skills_from_cv_text, extract_text_from_pdf
from app.services.jobs import suggest_locations
from app.services.roles import requirements_for_role, suggest_role_titles
from app.services.resources import build_roadmap, gather_online_resources
from app.services.skills import (
    canonicalize_cv_skill,
    classify_cv_against_requirements,
    missing_skills,
    relevant_skills_for_role,
)

router = APIRouter()


def _cv_public(cv: CvUpload) -> dict:
    return {
        "id": cv.id,
        "filename": cv.filename,
        "content_type": cv.content_type,
        "uploaded_at": cv.created_at.isoformat() + "Z",
        "download_url": "/api/cv/download",
        "all_skills": cv.skills or [],
    }


def _latest_cv(db: Session, session_id: str) -> CvUpload | None:
    return db.exec(
        select(CvUpload)
        .where(CvUpload.session_id == session_id)
        .order_by(col(CvUpload.created_at).desc())
    ).first()


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
    """Role requirements + live online learning materials for role + skills."""
    reqs = requirements_for_role(body.query)
    top = [(skill, 1, pct) for skill, pct in reqs]
    stack = [s for s in (canonicalize_cv_skill(x) for x in body.cv_skills) if s]
    matched, partial, unmatched = classify_cv_against_requirements(top, body.cv_skills)
    gaps = missing_skills(top, body.cv_skills, min_percentage=0.0)
    gap_names = [skill for skill, _, _ in gaps]

    bundle = gather_online_resources(body.query, stack, gap_names)
    roadmap, study_hours = build_roadmap(body.query, top, body.cv_skills, bundle=bundle)

    return InsightsResponse(
        query=body.query,
        location=body.location,
        requirements=[SkillStat(skill=s, count=1, percentage=p) for s, p in reqs],
        matched_skills=matched,
        partial_skills=partial,
        missing_skills=[SkillStat(skill=s, count=c, percentage=p) for s, c, p in gaps],
        unmatched_cv_skills=unmatched,
        interview_questions=bundle["interview_questions"],
        books=bundle["books"],
        courses=bundle["courses"],
        certifications=bundle["certifications"],
        roadmap=roadmap,
        estimated_study_hours=study_hours,
    )


@router.post("/cv/parse")
async def parse_cv(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    role: str = "",
    db: Session = Depends(get_session),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise HTTPException(status_code=400, detail="Upload a PDF or TXT CV")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Extract text via a temp file (PDF reader needs a path).
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        path = Path(tmp.name)
        if suffix == ".pdf":
            text_body = extract_text_from_pdf(path)
        else:
            text_body = path.read_text(encoding="utf-8", errors="ignore")

    all_skills = extract_skills_from_cv_text(text_body)
    role_title = role.strip()
    if role_title:
        reqs = requirements_for_role(role_title)
        skills = relevant_skills_for_role(reqs, all_skills, role_title=role_title)
    else:
        skills = all_skills

    session_id = ensure_session_id(request, response)

    # Replace previous CV for this session with the new upload.
    for old in db.exec(select(CvUpload).where(CvUpload.session_id == session_id)).all():
        db.delete(old)

    cv = CvUpload(
        id=uuid.uuid4().hex,
        session_id=session_id,
        filename=Path(file.filename).name,
        content_type=file.content_type or (
            "application/pdf" if suffix == ".pdf" else "text/plain"
        ),
        content=content,
        skills=all_skills,
        created_at=datetime.utcnow(),
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)

    return {
        "skills": skills,
        "all_skills": all_skills,
        "filtered_to_role": bool(role_title),
        "char_count": len(text_body),
        "cv": _cv_public(cv),
    }


@router.get("/cv/current")
def current_cv(request: Request, db: Session = Depends(get_session)) -> dict:
    sid = get_session_id(request)
    if not sid:
        return {"cv": None}
    cv = _latest_cv(db, sid)
    if not cv:
        return {"cv": None}
    return {"cv": _cv_public(cv)}


@router.get("/cv/download")
def download_cv(request: Request, db: Session = Depends(get_session)) -> Response:
    sid = get_session_id(request)
    if not sid:
        raise HTTPException(status_code=404, detail="No CV in this session")
    cv = _latest_cv(db, sid)
    if not cv:
        raise HTTPException(status_code=404, detail="No CV in this session")

    headers = {
        "Content-Disposition": f'attachment; filename="{cv.filename}"',
    }
    return Response(
        content=cv.content,
        media_type=cv.content_type or "application/octet-stream",
        headers=headers,
    )


@router.delete("/cv/current")
def delete_cv(
    request: Request,
    db: Session = Depends(get_session),
) -> dict:
    sid = get_session_id(request)
    if not sid:
        return {"ok": True}
    for row in db.exec(select(CvUpload).where(CvUpload.session_id == sid)).all():
        db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/cv/skills/for-role")
def skills_for_role(body: SkillsForRoleRequest) -> dict:
    """Re-filter a known skill list for a different role (e.g. after role change)."""
    role_title = body.role.strip()
    reqs = requirements_for_role(role_title)
    skills = relevant_skills_for_role(reqs, body.skills, role_title=role_title)
    return {"skills": skills, "role": role_title}