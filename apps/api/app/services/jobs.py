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


def suggest_locations(session: Session, q: str = "", limit: int = 40) -> list[str]:
    from app.services.locations import _is_excluded_label, suggest_city_locations

    # Library catalog (Remote + main cities/countries)
    results = suggest_city_locations(q=q, limit=limit)

    # Merge any locations already seen in scraped jobs
    needle = q.strip().lower()
    job_locs = [loc for loc in session.exec(select(Job.location)).all() if loc]
    extras: list[str] = []
    for loc in job_locs:
        parts = [loc, *[p.strip() for p in loc.replace("/", ",").split(",") if p.strip()]]
        for part in parts:
            if _is_excluded_label(part) or any(
                blocked in part.lower() for blocked in ("russia", "belarus")
            ):
                continue
            if needle and needle not in part.lower():
                continue
            if part not in results and part not in extras:
                extras.append(part)

    merged = list(dict.fromkeys([*results, *extras]))
    return merged[:limit]


ROLE_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "for",
    "to",
    "in",
    "engineer",
    "engineers",
    "developer",
    "developers",
    "programmer",
    "specialist",
    "expert",
    "lead",
    "senior",
    "junior",
    "mid",
    "mid-level",
    "middle",
    "level",
    "staff",
    "principal",
    "sr",
    "jr",
}


def significant_role_tokens(query: str) -> list[str]:
    """Tech/domain tokens from a role title (drops generic words like Engineer)."""
    return [
        t
        for t in re.split(r"[\s,/|+]+", query.strip())
        if t and t.lower() not in ROLE_STOPWORDS and len(t) >= 2
    ]


def title_relevance(query: str, title: str) -> int:
    """Higher = better title match for the selected role."""
    title_l = (title or "").lower()
    query_l = query.strip().lower()
    if not query_l:
        return 0
    score = 0
    if title_l == query_l:
        score += 1000
    if query_l in title_l:
        score += 400
    sig = significant_role_tokens(query)
    if sig:
        hits = sum(1 for t in sig if re.search(rf"(?<![a-z0-9]){re.escape(t.lower())}(?![a-z0-9])", title_l))
        score += hits * 120
        if hits == len(sig):
            score += 300
        # Penalize titles that add unrelated major stacks when query is specific
        if hits == len(sig):
            extras = ("react", "angular", "vue", "frontend", "mobile", "ios", "android")
            query_joined = " ".join(sig).lower()
            for extra in extras:
                if extra not in query_joined and re.search(rf"(?<![a-z0-9]){extra}(?![a-z0-9])", title_l):
                    score -= 80
    # Generic token overlap (engineer etc.) as weak signal
    for tok in query.split():
        if tok.lower() in ROLE_STOPWORDS:
            if tok.lower() in title_l:
                score += 5
        elif re.search(rf"(?<![a-z0-9]){re.escape(tok.lower())}(?![a-z0-9])", title_l):
            score += 40
    return score


def search_jobs(
    session: Session,
    query: str,
    location: str = "",
    limit: int = 50,
) -> list[Job]:
    statement = select(Job)
    filters = []
    sig = significant_role_tokens(query)
    # Prefer matching distinctive role tokens; fall back to full token AND
    match_tokens = sig or [t for t in query.split() if t.strip()]
    for token in match_tokens:
        like = f"%{token}%"
        filters.append(
            or_(
                col(Job.title).ilike(like),
                col(Job.description).ilike(like),
            )
        )
    if location:
        filters.append(col(Job.location).ilike(f"%{location}%"))
    if filters:
        statement = statement.where(*filters)
    statement = statement.order_by(col(Job.created_at).desc()).limit(max(limit * 4, 100))
    jobs = list(session.exec(statement).all())

    # Strong title matches first (all significant tokens in title)
    strong = [
        j
        for j in jobs
        if sig
        and all(
            re.search(rf"(?<![a-z0-9]){re.escape(t.lower())}(?![a-z0-9])", (j.title or "").lower())
            for t in sig
        )
    ]
    pool = strong if len(strong) >= min(3, limit) else jobs

    pool.sort(
        key=lambda j: (
            -title_relevance(query, j.title or ""),
            seniority_rank(j.title or ""),
            (j.title or "").lower(),
        )
    )
    # Drop weak matches when we have strong ones
    if strong:
        pool = [j for j in pool if title_relevance(query, j.title or "") >= 200] or pool
    return pool[:limit]


def currency_for_location(location: str) -> str:
    """Pick a display currency from the user's location filter."""
    loc = (location or "").lower()
    if not loc:
        return "USD"
    if any(
        k in loc
        for k in (
            "united kingdom",
            "uk",
            "england",
            "scotland",
            "wales",
            "northern ireland",
            "london",
            "manchester",
            "birmingham",
            "edinburgh",
            "glasgow",
            "bristol",
            "leeds",
            "britain",
            "british",
        )
    ):
        return "GBP"
    if any(
        k in loc
        for k in (
            "euro",
            "germany",
            "france",
            "netherlands",
            "spain",
            "italy",
            "portugal",
            "ireland",
            "belgium",
            "austria",
            "finland",
            "berlin",
            "munich",
            "paris",
            "amsterdam",
            "dublin",
            "lisbon",
            "madrid",
            "rome",
            "remote europe",
            "emea",
        )
    ):
        return "EUR"
    if "canada" in loc or "toronto" in loc or "vancouver" in loc or "montreal" in loc:
        return "CAD"
    if "australia" in loc or "sydney" in loc or "melbourne" in loc:
        return "AUD"
    if "switzerland" in loc or "zurich" in loc or "geneva" in loc:
        return "CHF"
    if "japan" in loc or "tokyo" in loc:
        return "JPY"
    if "poland" in loc or "warsaw" in loc or "krakow" in loc or "kraków" in loc:
        return "PLN"
    return "USD"


def currency_symbol(code: str) -> str:
    return {
        "USD": "$",
        "GBP": "£",
        "EUR": "€",
        "CAD": "C$",
        "AUD": "A$",
        "CHF": "CHF ",
        "JPY": "¥",
        "PLN": "zł ",
    }.get((code or "USD").upper(), f"{code} ")


def _format_money(amount: float, currency: str) -> str:
    sym = currency_symbol(currency)
    if amount >= 1000:
        return f"{sym}{int(round(amount)):,}"
    return f"{sym}{amount:g}"


def salary_distribution(
    jobs: list[Job],
    buckets: int = 5,
    location: str = "",
) -> list[dict]:
    """
    Build a histogram from matched jobs' salary midpoints.

    Uses the currency implied by the selected location (e.g. UK → GBP)
    and only includes jobs in that currency so USD remote pay isn't mixed in.
    """
    preferred = currency_for_location(location)
    mids: list[float] = []
    for job in jobs:
        cur = (job.currency or "USD").upper()
        if cur != preferred:
            continue
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
        return [
            {
                "label": _format_money(low, preferred),
                "count": len(mids),
                "min_salary": low,
                "max_salary": high,
                "currency": preferred,
            }
        ]

    width = (high - low) / buckets
    result = []
    for i in range(buckets):
        start = low + i * width
        end = high if i == buckets - 1 else start + width
        count = sum(1 for v in mids if (start <= v <= end if i == buckets - 1 else start <= v < end))
        result.append(
            {
                "label": f"{_format_money(start, preferred)}–{_format_money(end, preferred)}",
                "count": count,
                "min_salary": round(start, 2),
                "max_salary": round(end, 2),
                "currency": preferred,
            }
        )
    return result


def _parse_salary_text(text: str) -> tuple[Optional[float], Optional[float], str]:
    """Parse free-text salary and detect currency when possible."""
    raw = text or ""
    upper = raw.upper()
    currency = "USD"
    if "£" in raw or "GBP" in upper:
        currency = "GBP"
    elif "€" in raw or "EUR" in upper:
        currency = "EUR"
    elif "CHF" in upper:
        currency = "CHF"
    elif "A$" in raw or "AUD" in upper:
        currency = "AUD"
    elif "C$" in raw or "CAD" in upper:
        currency = "CAD"
    elif "¥" in raw or "JPY" in upper:
        currency = "JPY"
    elif "$" in raw or "USD" in upper:
        currency = "USD"

    nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", raw)]
    # Treat small numbers as thousands (e.g. "80-100k")
    if "k" in raw.lower() and nums:
        nums = [n * 1000 if n < 1000 else n for n in nums]
    if len(nums) >= 2:
        return nums[0], nums[1], currency
    if len(nums) == 1:
        return nums[0], nums[0], currency
    return None, None, currency


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def stable_demo_id(seed: str) -> str:
    return hashlib.sha1(seed.encode()).hexdigest()[:12]
