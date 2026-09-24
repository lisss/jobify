from __future__ import annotations

from app.models.schemas import ResourceOut, RoadmapStep
from app.services.skills import missing_skills


# Curated starter catalog — expand / replace with DB + live APIs later.
CATALOG: list[ResourceOut] = [
    ResourceOut(
        kind="book",
        title="Eloquent JavaScript",
        url="https://eloquentjavascript.net/",
        provider="Marijn Haverbeke",
        skills=["JavaScript"],
        description="Modern intro to JS language and programming.",
        estimated_hours=25,
    ),
    ResourceOut(
        kind="book",
        title="Learning React",
        url="https://www.oreilly.com/library/view/learning-react-2nd/9781492051718/",
        provider="O'Reilly",
        skills=["React", "JavaScript"],
        description="Component patterns, hooks, and modern React.",
        estimated_hours=20,
    ),
    ResourceOut(
        kind="book",
        title="Designing Data-Intensive Applications",
        url="https://dataintensive.net/",
        provider="Martin Kleppmann",
        skills=["System Design", "Kafka", "PostgreSQL"],
        description="Foundational systems thinking for backend roles.",
        estimated_hours=40,
    ),
    ResourceOut(
        kind="book",
        title="Fluent Python",
        url="https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/",
        provider="O'Reilly",
        skills=["Python"],
        description="Idiomatic Python for serious backend work.",
        estimated_hours=35,
    ),
    ResourceOut(
        kind="course",
        title="React - The Complete Guide",
        url="https://www.udemy.com/course/react-the-complete-guide-incl-redux/",
        provider="Udemy",
        skills=["React", "JavaScript"],
        description="Hooks, Redux, Next-adjacent React fundamentals.",
        estimated_hours=40,
    ),
    ResourceOut(
        kind="course",
        title="FastAPI - The Complete Course",
        url="https://www.udemy.com/course/fastapi-the-complete-course/",
        provider="Udemy",
        skills=["FastAPI", "Python"],
        description="Build production APIs with FastAPI.",
        estimated_hours=20,
    ),
    ResourceOut(
        kind="course",
        title="AWS Cloud Practitioner Essentials",
        url="https://www.aws.training/",
        provider="AWS",
        skills=["AWS"],
        description="Cloud fundamentals that show up in many JD's.",
        estimated_hours=12,
    ),
    ResourceOut(
        kind="course",
        title="System Design for Beginners",
        url="https://www.educative.io/courses/grokking-the-system-design-interview",
        provider="Educative",
        skills=["System Design"],
        description="Interview-oriented system design patterns.",
        estimated_hours=18,
    ),
    ResourceOut(
        kind="github",
        title="reactjs/react.dev",
        url="https://github.com/reactjs/react.dev",
        provider="GitHub",
        skills=["React"],
        description="Official React docs site — great for reading real code.",
        estimated_hours=8,
    ),
    ResourceOut(
        kind="github",
        title="tiangolo/fastapi",
        url="https://github.com/tiangolo/fastapi",
        provider="GitHub",
        skills=["FastAPI", "Python"],
        description="Study framework patterns and typed APIs.",
        estimated_hours=10,
    ),
    ResourceOut(
        kind="github",
        title="donnemartin/system-design-primer",
        url="https://github.com/donnemartin/system-design-primer",
        provider="GitHub",
        skills=["System Design"],
        description="Canonical open-source system design study guide.",
        estimated_hours=15,
    ),
    ResourceOut(
        kind="github",
        title="TheAlgorithms/Python",
        url="https://github.com/TheAlgorithms/Python",
        provider="GitHub",
        skills=["Python", "Algorithms", "Data Structures"],
        description="Interview algorithms implemented in Python.",
        estimated_hours=20,
    ),
    ResourceOut(
        kind="certification",
        title="AWS Certified Cloud Practitioner",
        url="https://aws.amazon.com/certification/certified-cloud-practitioner/",
        provider="AWS",
        skills=["AWS"],
        description="Useful signal for cloud-heavy roles; skip if JD never mentions AWS.",
        estimated_hours=30,
    ),
    ResourceOut(
        kind="certification",
        title="Meta Front-End Developer Certificate",
        url="https://www.coursera.org/professional-certificates/meta-front-end-developer",
        provider="Coursera / Meta",
        skills=["React", "JavaScript", "HTML", "CSS"],
        description="Helps juniors; seniors usually skip certs and ship projects.",
        estimated_hours=80,
    ),
    ResourceOut(
        kind="interview",
        title="Explain the React reconciliation / virtual DOM model",
        url="",
        provider="Common",
        skills=["React"],
        description="Expect follow-ups on keys, concurrent rendering, and memoization.",
    ),
    ResourceOut(
        kind="interview",
        title="How would you design a job search API with filters and pagination?",
        url="",
        provider="Common",
        skills=["System Design", "REST"],
        description="Cover indexing, caching, and ranking trade-offs.",
    ),
    ResourceOut(
        kind="interview",
        title="Difference between SQL joins and when you'd denormalize",
        url="",
        provider="Common",
        skills=["SQL", "PostgreSQL"],
        description="Classic backend screen question.",
    ),
    ResourceOut(
        kind="interview",
        title="Walk through debugging a slow Node/Python API endpoint",
        url="",
        provider="Common",
        skills=["Node.js", "Python"],
        description="Profiling, N+1 queries, and caching.",
    ),
    ResourceOut(
        kind="interview",
        title="What is the difference between authentication and authorization?",
        url="",
        provider="Common",
        skills=["REST", "System Design"],
        description="Often paired with JWT / session questions.",
    ),
]


def _matches_skills(resource: ResourceOut, skills: set[str]) -> bool:
    return bool(skills.intersection(resource.skills)) or not resource.skills


def resources_for(skills: list[str], kind: str, limit: int = 6) -> list[ResourceOut]:
    skill_set = set(skills)
    matched = [r for r in CATALOG if r.kind == kind and _matches_skills(r, skill_set)]
    if len(matched) < limit:
        extras = [r for r in CATALOG if r.kind == kind and r not in matched]
        matched.extend(extras)
    return matched[:limit]


def build_roadmap(
    top_skills: list[tuple[str, int, float]],
    cv_skills: list[str],
) -> tuple[list[RoadmapStep], float]:
    gaps = missing_skills(top_skills, cv_skills, min_percentage=15.0)[:8]
    if not gaps:
        # Strengthen existing top skills if CV already covers them
        gaps = top_skills[:4]

    steps: list[RoadmapStep] = []
    total_hours = 0.0
    chunk_size = 2
    order = 1
    for i in range(0, len(gaps), chunk_size):
        chunk = gaps[i : i + chunk_size]
        skill_names = [s for s, _, _ in chunk]
        related = [
            r
            for r in CATALOG
            if r.kind in {"course", "book", "github"} and set(r.skills).intersection(skill_names)
        ][:4]
        hours = sum((r.estimated_hours or 8) for r in related) or 12.0
        # Cap per step so estimates stay believable
        hours = min(hours, 30.0)
        total_hours += hours
        steps.append(
            RoadmapStep(
                order=order,
                title=f"Focus: {', '.join(skill_names)}",
                skills=skill_names,
                estimated_hours=hours,
                resources=related,
            )
        )
        order += 1

    # Final polish step
    steps.append(
        RoadmapStep(
            order=order,
            title="Interview polish & portfolio",
            skills=["System Design", "Communication"],
            estimated_hours=12,
            resources=resources_for(["System Design"], "interview", limit=3)
            + resources_for(["System Design"], "github", limit=1),
        )
    )
    total_hours += 12
    return steps, round(total_hours, 1)
