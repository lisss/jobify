from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Optional

from sqlmodel import Session, col, or_, select

from app.models.job import Job
from app.services.skills import extract_skills


SAMPLE_JOBS: list[dict] = [
    {
        "external_id": "sample-1",
        "source": "sample",
        "title": "Senior React Engineer",
        "company": "Northwind Labs",
        "location": "Remote",
        "description": "Build product UI with React, TypeScript, Next.js, GraphQL. Collaborate on system design and CI/CD.",
        "url": "https://example.com/jobs/1",
        "salary_min": 140000,
        "salary_max": 180000,
        "currency": "USD",
    },
    {
        "external_id": "sample-2",
        "source": "sample",
        "title": "Full Stack Engineer (React + Node)",
        "company": "Brightline",
        "location": "Berlin",
        "description": "React, Node.js, PostgreSQL, Docker, AWS. Strong communication and Agile experience.",
        "url": "https://example.com/jobs/2",
        "salary_min": 75000,
        "salary_max": 95000,
        "currency": "EUR",
    },
    {
        "external_id": "sample-3",
        "source": "sample",
        "title": "Python Backend Engineer",
        "company": "Dataform",
        "location": "Remote",
        "description": "Python, FastAPI, PostgreSQL, Redis, Kafka, Docker, Kubernetes. Machine Learning familiarity a plus.",
        "url": "https://example.com/jobs/3",
        "salary_min": 120000,
        "salary_max": 155000,
        "currency": "USD",
    },
    {
        "external_id": "sample-4",
        "source": "sample",
        "title": "Frontend Developer",
        "company": "Pixel & Co",
        "location": "London",
        "description": "HTML, CSS, JavaScript, React, Tailwind CSS, Figma, Git. REST APIs.",
        "url": "https://example.com/jobs/4",
        "salary_min": 55000,
        "salary_max": 75000,
        "currency": "GBP",
    },
    {
        "external_id": "sample-5",
        "source": "sample",
        "title": "Platform Engineer",
        "company": "Cloudspan",
        "location": "Remote US",
        "description": "AWS, Terraform, Kubernetes, Docker, Linux, Python, CI/CD, System Design.",
        "url": "https://example.com/jobs/5",
        "salary_min": 150000,
        "salary_max": 190000,
        "currency": "USD",
    },
    {
        "external_id": "sample-6",
        "source": "sample",
        "title": "React Native / TypeScript Engineer",
        "company": "MobileFirst",
        "location": "Amsterdam",
        "description": "TypeScript, React, Node.js, GraphQL, Git, Agile. Algorithms and Data Structures interviews.",
        "url": "https://example.com/jobs/6",
        "salary_min": 70000,
        "salary_max": 90000,
        "currency": "EUR",
    },
    {
        "external_id": "sample-7",
        "source": "sample",
        "title": "ML Engineer",
        "company": "Signal AI",
        "location": "Remote",
        "description": "Python, PyTorch, TensorFlow, Pandas, NumPy, AWS, Docker, Machine Learning, LLMs.",
        "url": "https://example.com/jobs/7",
        "salary_min": 145000,
        "salary_max": 185000,
        "currency": "USD",
    },
    {
        "external_id": "sample-8",
        "source": "sample",
        "title": "Junior React Developer",
        "company": "StarterKit",
        "location": "Remote",
        "description": "JavaScript, React, HTML, CSS, Git, REST. Willingness to learn TypeScript and Next.js.",
        "url": "https://example.com/jobs/8",
        "salary_min": 50000,
        "salary_max": 65000,
        "currency": "USD",
    },
]


def _upsert_job(session: Session, payload: dict) -> Job:
    skills = extract_skills(
        f"{payload.get('title', '')} {payload.get('description', '')} {payload.get('company', '')}"
    )
    existing = session.exec(select(Job).where(Job.external_id == payload["external_id"])).first()
    if existing:
        existing.title = payload["title"]
        existing.company = payload.get("company", "")
        existing.location = payload.get("location", "")
        existing.description = payload.get("description", "")
        existing.url = payload.get("url", "")
        existing.salary_min = payload.get("salary_min")
        existing.salary_max = payload.get("salary_max")
        existing.currency = payload.get("currency", "USD")
        existing.skills = skills
        existing.source = payload.get("source", existing.source)
        session.add(existing)
        return existing

    job = Job(
        external_id=payload["external_id"],
        source=payload.get("source", "unknown"),
        title=payload["title"],
        company=payload.get("company", ""),
        location=payload.get("location", ""),
        description=payload.get("description", ""),
        url=payload.get("url", ""),
        salary_min=payload.get("salary_min"),
        salary_max=payload.get("salary_max"),
        currency=payload.get("currency", "USD"),
        skills=skills,
        posted_at=payload.get("posted_at"),
    )
    session.add(job)
    session.flush()
    return job


def seed_sample_jobs(session: Session) -> int:
    count = 0
    for payload in SAMPLE_JOBS:
        _upsert_job(session, payload)
        count += 1
    session.commit()
    return count


def seniority_rank(title: str) -> int:
    """Lower = higher priority. Prefer mid → senior over staff/exec and junior."""
    t = title.lower()
    if any(
        k in t
        for k in (
            "staff",
            "principal",
            "distinguished",
            "fellow",
            "director",
            "vp ",
            "vice president",
            "head of",
            "chief ",
            "cto",
            "cpo",
        )
    ):
        return 5
    if any(k in t for k in ("intern", "graduate", "entry level", "entry-level", "junior", "jr ", "associate")):
        return 4
    if any(k in t for k in ("mid-level", "mid level", "midlevel", "middle")):
        return 0
    if "senior" in t or t.startswith("sr ") or " sr " in f" {t} ":
        return 1
    if any(k in t for k in ("tech lead", "team lead", "engineering lead", "lead ")):
        return 2
    return 3


def suggest_roles(
    session: Session,
    q: str = "",
    limit: int = 10,
    marketplace_first: list[dict] | None = None,
) -> list[dict]:
    """Return live job listings (with marketplace URLs) matching the query."""
    needle = q.strip()
    candidates: list[dict] = []
    seen_titles: set[str] = set()

    def title_ok(title: str) -> bool:
        if not needle:
            return True
        tokens = [t for t in re.split(r"[\s,/|+]+", needle.lower()) if len(t) >= 2]
        return all(
            re.search(rf"(?<![a-z0-9]){re.escape(tok)}(?![a-z0-9])", title, re.I) for tok in tokens
        )

    def push(item: dict) -> None:
        title = (item.get("title") or "").strip()
        url = item.get("url") or ""
        if not title or not url:
            return
        if not title_ok(title):
            return
        key = title.lower()
        if key in seen_titles:
            return
        seen_titles.add(key)
        candidates.append(
            {
                "id": item.get("id"),
                "title": title,
                "company": item.get("company") or "",
                "location": item.get("location") or "",
                "url": url,
                "source": item.get("source") or "",
            }
        )

    for item in marketplace_first or []:
        push(item)

    like = f"%{needle}%" if needle else "%"
    title_jobs = list(
        session.exec(
            select(Job)
            .where(col(Job.title).ilike(like), col(Job.url) != "")
            .order_by(col(Job.created_at).desc())
            .limit(max(limit * 6, 60))
        ).all()
    )
    for job in title_jobs:
        push(
            {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "url": job.url,
                "source": job.source,
            }
        )

    candidates.sort(
        key=lambda item: (
            seniority_rank(item["title"]),
            0 if item.get("source") not in {"sample", "suggestion"} else 1,
            item["title"].lower(),
        )
    )
    listings = candidates[:limit]

    # Curated labels only when boards returned nothing usable
    if not listings:
        curated = [
            "Senior Software Engineer",
            "Mid-level Software Engineer",
            "Software Engineer",
            "Senior Frontend Engineer",
            "Frontend Engineer",
            "Senior Backend Engineer",
            "Backend Engineer",
            "Full Stack Engineer",
            "Senior React Engineer",
            "React Engineer",
            "React Developer",
            "Python Developer",
            "DevOps Engineer",
            "Data Engineer",
            "ML Engineer",
            "Platform Engineer",
        ]
        lower = needle.lower()
        for title in curated:
            if lower and lower not in title.lower():
                continue
            listings.append(
                {
                    "id": None,
                    "title": title,
                    "company": "",
                    "location": "",
                    "url": "",
                    "source": "suggestion",
                }
            )
            if len(listings) >= limit:
                break

    return listings


def suggest_locations(session: Session, q: str = "", limit: int = 10) -> list[str]:
    curated = [
        "Remote",
        "Remote US",
        "Remote Europe",
        "Worldwide",
        "Berlin",
        "London",
        "Amsterdam",
        "Paris",
        "Dublin",
        "Lisbon",
        "New York",
        "San Francisco",
        "Seattle",
        "Austin",
        "Toronto",
        "Warsaw",
        "Munich",
        "Stockholm",
        "Singapore",
        "Tokyo",
    ]
    locations = [loc for loc in session.exec(select(Job.location)).all() if loc]
    # Flatten multi-value locations like "Berlin, Germany"
    expanded: list[str] = []
    for loc in locations:
        expanded.append(loc)
        for part in loc.replace("/", ",").split(","):
            part = part.strip()
            if part:
                expanded.append(part)
    pool = list(dict.fromkeys([*curated, *expanded]))
    needle = q.strip().lower()
    if needle:
        pool = [t for t in pool if needle in t.lower()]
    return pool[:limit]


def search_jobs(
    session: Session,
    query: str,
    location: str = "",
    limit: int = 50,
) -> list[Job]:
    statement = select(Job)
    filters = []
    tokens = [t for t in query.split() if t.strip()]
    for token in tokens:
        like = f"%{token}%"
        filters.append(
            or_(
                col(Job.title).ilike(like),
                col(Job.description).ilike(like),
                col(Job.company).ilike(like),
            )
        )
    if location:
        filters.append(col(Job.location).ilike(f"%{location}%"))
    if filters:
        statement = statement.where(*filters)
    # Fetch a wider pool, then prefer mid/senior titles over staff/exec
    statement = statement.order_by(col(Job.created_at).desc()).limit(max(limit * 3, 80))
    jobs = list(session.exec(statement).all())
    jobs.sort(key=lambda j: (seniority_rank(j.title), j.title.lower()))
    return jobs[:limit]


def salary_distribution(jobs: list[Job], buckets: int = 5) -> list[dict]:
    mids: list[float] = []
    for job in jobs:
        if job.salary_min is not None and job.salary_max is not None:
            mids.append((job.salary_min + job.salary_max) / 2)
        elif job.salary_min is not None:
            mids.append(job.salary_min)
        elif job.salary_max is not None:
            mids.append(job.salary_max)
    if not mids:
        return []

    low, high = min(mids), max(mids)
    if low == high:
        return [{"label": f"${int(low):,}", "count": len(mids), "min_salary": low, "max_salary": high}]

    width = (high - low) / buckets
    result = []
    for i in range(buckets):
        start = low + i * width
        end = high if i == buckets - 1 else start + width
        count = sum(1 for v in mids if (start <= v <= end if i == buckets - 1 else start <= v < end))
        result.append(
            {
                "label": f"${int(start):,}–${int(end):,}",
                "count": count,
                "min_salary": round(start, 2),
                "max_salary": round(end, 2),
            }
        )
    return result


def _parse_salary_text(text: str) -> tuple[Optional[float], Optional[float]]:
    import re

    nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", text)]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def stable_demo_id(seed: str) -> str:
    return hashlib.sha1(seed.encode()).hexdigest()[:12]
