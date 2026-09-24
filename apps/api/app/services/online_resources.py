from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings
from app.models.schemas import ResourceOut

USER_AGENT = "Jobify/1.0 (learning insights; +https://github.com/jobify)"
TIMEOUT = 8.0

# Tiny in-process TTL cache so repeat insights don't hammer public APIs.
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL_SEC = 60 * 30


def _cache_get(key: str) -> Any | None:
    hit = _CACHE.get(key)
    if not hit:
        return None
    expires, value = hit
    if time.time() > expires:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (time.time() + _CACHE_TTL_SEC, value)


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


def _clean(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _queries(role: str, stack: list[str], gaps: list[str]) -> list[str]:
    role = role.strip() or "software engineer"
    parts: list[str] = []
    for skill in stack[:4]:
        parts.append(f"{skill} {role}")
        parts.append(f"{skill} programming")
    for skill in gaps[:4]:
        parts.append(f"{skill} for {role}")
        parts.append(skill)
    if not parts:
        parts.append(role)
        parts.append(f"{role} interview")
    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for q in parts:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out[:6]


def _fetch_open_library_books(query: str, limit: int = 4) -> list[ResourceOut]:
    cache_key = f"ol:{query}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Bias toward programming/tech books rather than random keyword hits.
    search = f"({query}) AND (programming OR software OR engineering OR computer)"
    url = "https://openlibrary.org/search.json"
    params = {
        "q": search,
        "limit": max(limit * 2, 6),
        "fields": "key,title,author_name,first_publish_year,subject,language",
    }
    results: list[ResourceOut] = []
    try:
        with _client() as client:
            res = client.get(url, params=params)
            res.raise_for_status()
            docs = res.json().get("docs") or []
    except Exception:
        return []

    for doc in docs:
        title = (doc.get("title") or "").strip()
        if not title:
            continue
        subjects = " ".join(doc.get("subject") or []).lower()
        title_l = title.lower()
        # Soft filter: prefer clearly technical titles/subjects.
        technical = any(
            token in subjects or token in title_l
            for token in (
                "programming",
                "software",
                "computer",
                "engineering",
                "python",
                "java",
                "haskell",
                "backend",
                "web",
                "database",
                "api",
            )
        )
        if subjects and not technical:
            continue
        authors = doc.get("author_name") or []
        work_key = doc.get("key") or ""
        book_url = f"https://openlibrary.org{work_key}" if work_key else ""
        year = doc.get("first_publish_year")
        desc = ", ".join(authors[:2])
        if year:
            desc = f"{desc} ({year})" if desc else str(year)
        results.append(
            ResourceOut(
                kind="book",
                title=title,
                url=book_url,
                provider="Open Library",
                skills=_skills_from_query(query),
                description=_clean(desc or "Book match for your role and skills."),
                estimated_hours=25,
            )
        )
        if len(results) >= limit:
            break
    _cache_set(cache_key, results)
    return results


def _fetch_google_books(query: str, limit: int = 4) -> list[ResourceOut]:
    settings = get_settings()
    key = (settings.google_books_api_key or "").strip()
    cache_key = f"gbooks:{bool(key)}:{query}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params: dict[str, Any] = {"q": query, "maxResults": limit, "printType": "books"}
    if key:
        params["key"] = key
    try:
        with _client() as client:
            res = client.get("https://www.googleapis.com/books/v1/volumes", params=params)
            if res.status_code >= 400:
                return []
            items = res.json().get("items") or []
    except Exception:
        return []

    results: list[ResourceOut] = []
    for item in items:
        info = item.get("volumeInfo") or {}
        title = (info.get("title") or "").strip()
        if not title:
            continue
        authors = info.get("authors") or []
        link = info.get("infoLink") or info.get("canonicalVolumeLink") or ""
        desc = info.get("description") or ", ".join(authors[:2])
        results.append(
            ResourceOut(
                kind="book",
                title=title,
                url=link,
                provider="Google Books",
                skills=_skills_from_query(query),
                description=_clean(desc),
                estimated_hours=28,
            )
        )
    _cache_set(cache_key, results)
    return results


def _fetch_github_learning(query: str, limit: int = 4) -> list[ResourceOut]:
    settings = get_settings()
    cache_key = f"gh:{query}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Prefer tutorials / courses / roadmaps over random repos.
    q = f"{query} (tutorial OR course OR roadmap OR learn OR handbook)"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = (settings.github_token or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with _client() as client:
            res = client.get(
                "https://api.github.com/search/repositories",
                params={"q": q, "sort": "stars", "order": "desc", "per_page": max(limit * 2, 5)},
                headers=headers,
            )
            if res.status_code >= 400:
                res = client.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": f"{query} tutorial",
                        "sort": "stars",
                        "order": "desc",
                        "per_page": max(limit * 2, 5),
                    },
                    headers=headers,
                )
                if res.status_code >= 400:
                    return []
            items = res.json().get("items") or []
    except Exception:
        return []

    skip_names = {
        "python/cpython",
        "golang/go",
        "rust-lang/rust",
        "openjdk/jdk",
        "dotnet/runtime",
        "torvalds/linux",
    }
    results: list[ResourceOut] = []
    for item in items:
        name = (item.get("full_name") or item.get("name") or "").strip()
        html_url = item.get("html_url") or ""
        if not name or not html_url:
            continue
        if name.lower() in skip_names:
            continue
        stars = item.get("stargazers_count") or 0
        name_l = name.lower()
        desc = item.get("description") or "GitHub learning resource"
        desc_l = desc.lower()
        learningish = any(
            token in name_l or token in desc_l
            for token in ("roadmap", "awesome", "tutorial", "course", "learn", "handbook", "guide", "study")
        )
        # Skip mega language runtimes posing as courses.
        if stars > 50_000 and not learningish:
            continue
        results.append(
            ResourceOut(
                kind="course",
                title=name,
                url=html_url,
                provider="GitHub",
                skills=_skills_from_query(query),
                description=_clean(f"★ {stars} — {desc}"),
                estimated_hours=12,
            )
        )
        if len(results) >= limit:
            break
    _cache_set(cache_key, results)
    return results


def _fetch_youtube_courses(query: str, limit: int = 4) -> list[ResourceOut]:
    settings = get_settings()
    api_key = (settings.youtube_api_key or "").strip()
    if not api_key:
        return []

    cache_key = f"yt:{query}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {
        "part": "snippet",
        "type": "video",
        "maxResults": limit,
        "q": f"{query} course tutorial",
        "key": api_key,
        "safeSearch": "moderate",
        "relevanceLanguage": "en",
    }
    try:
        with _client() as client:
            res = client.get("https://www.googleapis.com/youtube/v3/search", params=params)
            if res.status_code >= 400:
                return []
            items = res.json().get("items") or []
    except Exception:
        return []

    results: list[ResourceOut] = []
    for item in items:
        snippet = item.get("snippet") or {}
        video_id = (item.get("id") or {}).get("videoId")
        title = (snippet.get("title") or "").strip()
        if not video_id or not title:
            continue
        results.append(
            ResourceOut(
                kind="course",
                title=title,
                url=f"https://www.youtube.com/watch?v={video_id}",
                provider=snippet.get("channelTitle") or "YouTube",
                skills=_skills_from_query(query),
                description=_clean(snippet.get("description") or "Video course / tutorial"),
                estimated_hours=8,
            )
        )
    _cache_set(cache_key, results)
    return results


def _fetch_stack_interview(query: str, limit: int = 4) -> list[ResourceOut]:
    cache_key = f"so:{query}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Prefer interview-tagged discussion; fall back to title search.
    params = {
        "order": "desc",
        "sort": "votes",
        "site": "stackoverflow",
        "pagesize": limit,
        "filter": "default",
    }
    # Use tagged search when query looks like a single skill token.
    token = re.sub(r"[^a-z0-9.+#]", "", query.lower().split()[0] if query else "")
    url = "https://api.stackexchange.com/2.3/search/advanced"
    if token and len(token) >= 2:
        params["tagged"] = token[:25]
        params["title"] = "interview"
    else:
        params["q"] = f"{query} interview"
        params["title"] = "interview"

    try:
        with _client() as client:
            res = client.get(url, params=params)
            if res.status_code >= 400:
                return []
            items = res.json().get("items") or []
    except Exception:
        return []

    results: list[ResourceOut] = []
    for item in items:
        title = (item.get("title") or "").strip()
        link = item.get("link") or ""
        if not title or not link:
            continue
        # Unescape very common HTML entities from the API
        title = (
            title.replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )
        results.append(
            ResourceOut(
                kind="interview",
                title=title,
                url=link,
                provider="Stack Overflow",
                skills=_skills_from_query(query),
                description=_clean("Community Q&A useful for interview prep."),
            )
        )
    _cache_set(cache_key, results)
    return results


def _fetch_certification_pages(query: str, limit: int = 3) -> list[ResourceOut]:
    """Discover certification-oriented pages via Open Library + GitHub."""
    cache_key = f"cert:{query}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    results: list[ResourceOut] = []
    cert_query = f"{query} certification"

    for book in _fetch_open_library_books(cert_query, limit=2):
        results.append(
            ResourceOut(
                kind="certification",
                title=book.title,
                url=book.url,
                provider=book.provider,
                skills=book.skills,
                description=_clean(book.description or "Certification-oriented material"),
                estimated_hours=30,
            )
        )

    for repo in _fetch_github_learning(f"{query} certification exam", limit=2):
        results.append(
            ResourceOut(
                kind="certification",
                title=repo.title,
                url=repo.url,
                provider="GitHub",
                skills=repo.skills,
                description=_clean(repo.description or "Certification study repo"),
                estimated_hours=20,
            )
        )

    # Always offer a live search deep-link so the UI isn't empty when catalogs miss.
    if len(results) < limit:
        results.append(
            ResourceOut(
                kind="certification",
                title=f"Search certifications: {query}",
                url=f"https://www.google.com/search?q={quote_plus(query + ' certification')}",
                provider="Web search",
                skills=_skills_from_query(query),
                description="Live search for current vendor certifications.",
                estimated_hours=None,
            )
        )

    results = _dedupe(results)[:limit]
    _cache_set(cache_key, results)
    return results


def _skills_from_query(query: str) -> list[str]:
    # Keep a couple of meaningful tokens for UI tagging.
    stop = {"for", "and", "the", "with", "a", "an", "to", "of", "in", "on"}
    tokens = [
        t.strip(".,")
        for t in query.replace("/", " ").split()
        if len(t.strip(".,")) > 1 and t.lower() not in stop
    ]
    return tokens[:3]


def _dedupe(items: list[ResourceOut]) -> list[ResourceOut]:
    seen: set[str] = set()
    out: list[ResourceOut] = []
    for item in items:
        key = (item.url or item.title).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _merge_queries(
    fetcher,
    queries: list[str],
    *,
    per_query: int,
    limit: int,
) -> list[ResourceOut]:
    collected: list[ResourceOut] = []
    # Parallelize a few public API calls; keep pool small to be polite.
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(queries)))) as pool:
        futures = {pool.submit(fetcher, q, per_query): q for q in queries}
        for fut in as_completed(futures):
            try:
                collected.extend(fut.result() or [])
            except Exception:
                continue
    return _dedupe(collected)[:limit]


def fetch_learning_bundle(
    role: str,
    stack_skills: list[str],
    gap_skills: list[str],
    *,
    limit: int = 6,
) -> dict[str, list[ResourceOut]]:
    """Live lookup of books/courses/certs/interview items for role + skills."""
    queries = _queries(role, stack_skills, gap_skills)
    skill_focus = (stack_skills[:3] or gap_skills[:3] or [role])[0]

    books = _merge_queries(
        lambda q, n: _fetch_google_books(q, n) or _fetch_open_library_books(q, n),
        queries[:3],
        per_query=3,
        limit=limit,
    )
    if not books:
        books = _fetch_open_library_books(f"{role} {skill_focus}", limit=limit)

    youtube = _merge_queries(_fetch_youtube_courses, queries[:2], per_query=3, limit=limit)
    github_courses = _merge_queries(
        _fetch_github_learning, queries[:3], per_query=3, limit=limit
    )
    # Prefer YouTube when configured; always include GitHub learning paths.
    courses = _dedupe([*youtube, *github_courses])[:limit]

    certifications = _merge_queries(
        _fetch_certification_pages,
        [skill_focus, role] + gap_skills[:2],
        per_query=2,
        limit=max(3, limit // 2),
    )

    interview_queries = [
        f"{s} interview" for s in (stack_skills[:2] + gap_skills[:2] or [role])
    ]
    interview_questions = _merge_queries(
        _fetch_stack_interview,
        interview_queries[:3],
        per_query=3,
        limit=limit,
    )

    return {
        "books": books,
        "courses": courses,
        "certifications": certifications,
        "interview_questions": interview_questions,
    }


def fetch_resources_for_topics(
    topics: list[str],
    role: str,
    *,
    kinds: set[str] | None = None,
    limit_per_topic: int = 3,
) -> list[ResourceOut]:
    """Fetch mixed materials for roadmap steps."""
    kinds = kinds or {"book", "course"}
    out: list[ResourceOut] = []
    for topic in topics:
        q = f"{topic} {role}".strip()
        if "book" in kinds:
            out.extend(_fetch_google_books(q, 2) or _fetch_open_library_books(q, 2))
        if "course" in kinds:
            yt = _fetch_youtube_courses(q, 2)
            out.extend(yt or _fetch_github_learning(q, 2))
    return _dedupe(out)[: limit_per_topic * max(1, len(topics))]
