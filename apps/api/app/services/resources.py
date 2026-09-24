from __future__ import annotations

from app.models.schemas import ResourceOut, RoadmapStep
from app.services.online_resources import fetch_learning_bundle, fetch_resources_for_topics
from app.services.skills import canonicalize_cv_skill, missing_skills


def _unique(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for skill in skills:
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(skill)
    return out


def learning_topics(
    role_skills: list[str],
    gap_skills: list[str],
    stack_skills: list[str],
) -> list[str]:
    """Order: your stack first (personalize), then role gaps you still need."""
    topics: list[str] = []
    for skill in stack_skills:
        topics.append(skill)
    for skill in gap_skills:
        topics.append(skill)
    if not topics:
        topics.extend(role_skills)
    return _unique(topics)


def gather_online_resources(
    role: str,
    stack_skills: list[str],
    gap_skills: list[str],
) -> dict[str, list[ResourceOut]]:
    return fetch_learning_bundle(role, stack_skills, gap_skills)


def _resources_for_chunk(
    chunk: list[str],
    role: str,
    bundle: dict[str, list[ResourceOut]] | None,
) -> list[ResourceOut]:
    needles = [c.lower() for c in chunk]
    picked: list[ResourceOut] = []
    if bundle:
        for kind in ("books", "courses", "interview_questions", "certifications"):
            for item in bundle.get(kind, []):
                hay = f"{item.title} {item.description} {' '.join(item.skills)}".lower()
                if any(n in hay for n in needles):
                    picked.append(item)
                if len(picked) >= 4:
                    return picked
    if len(picked) >= 2:
        return picked[:4]
    # Live top-up only when the shared bundle didn't cover this step.
    return fetch_resources_for_topics(
        chunk, role, kinds={"book", "course"}, limit_per_topic=2
    )[:4]


def build_roadmap(
    role: str,
    top_skills: list[tuple[str, int, float]],
    cv_skills: list[str],
    bundle: dict[str, list[ResourceOut]] | None = None,
) -> tuple[list[RoadmapStep], float]:
    role_skills = [skill for skill, _, _ in top_skills]
    stack = [s for s in (canonicalize_cv_skill(x) for x in cv_skills) if s]
    gap_rows = missing_skills(top_skills, cv_skills, min_percentage=15.0)[:8]
    gap_names = [skill for skill, _, _ in gap_rows]
    topics = learning_topics(role_skills, gap_names, stack)[:8]

    steps: list[RoadmapStep] = []
    total_hours = 0.0
    chunk_size = 2
    order = 1
    for i in range(0, len(topics), chunk_size):
        chunk = topics[i : i + chunk_size]
        related = _resources_for_chunk(chunk, role, bundle)
        hours = sum((r.estimated_hours or 8) for r in related) or 12.0
        hours = min(hours, 30.0)
        total_hours += hours
        if set(chunk) <= set(stack) and chunk:
            title = f"Strengthen your stack: {', '.join(chunk)}"
        else:
            title = f"Focus: {', '.join(chunk)}"
        steps.append(
            RoadmapStep(
                order=order,
                title=title,
                skills=chunk,
                estimated_hours=hours,
                resources=related,
            )
        )
        order += 1

    polish = []
    if bundle:
        polish.extend(bundle.get("interview_questions", [])[:2])
        polish.extend(bundle.get("courses", [])[:1])
    steps.append(
        RoadmapStep(
            order=order,
            title="Interview polish & portfolio",
            skills=_unique([*stack[:2], *gap_names[:2], "System Design"]),
            estimated_hours=12,
            resources=polish[:3],
        )
    )
    total_hours += 12
    return steps, round(total_hours, 1)
