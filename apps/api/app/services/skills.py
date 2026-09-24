from __future__ import annotations

import re
from collections import Counter

# Canonical skill vocabulary used for extraction + matching.
SKILL_ALIASES: dict[str, str] = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "python": "Python",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "sql": "SQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "git": "Git",
    "github": "GitHub",
    "ci/cd": "CI/CD",
    "graphql": "GraphQL",
    "rest": "REST",
    "html": "HTML",
    "css": "CSS",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "java": "Java",
    "spring": "Spring",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "c++": "C++",
    "c#": "C#",
    "f#": "F#",
    "haskell": "Haskell",
    ".net": ".NET",
    "linux": "Linux",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "spark": "Apache Spark",
    "kafka": "Kafka",
    "airflow": "Airflow",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "scikit-learn",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "llm": "LLMs",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "data structures": "Data Structures",
    "algorithms": "Algorithms",
    "system design": "System Design",
    "agile": "Agile",
    "scrum": "Scrum",
    "jira": "Jira",
    "figma": "Figma",
    "communication": "Communication",
}


def normalize_skill(raw: str) -> str | None:
    key = raw.strip().lower()
    if not key:
        return None
    return SKILL_ALIASES.get(key)


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    found: set[str] = set()
    # Longer phrases first so "machine learning" wins over "ml"
    for alias in sorted(SKILL_ALIASES.keys(), key=len, reverse=True):
        pattern = r"(?<![a-z0-9.+#])" + re.escape(alias) + r"(?![a-z0-9.+#])"
        if re.search(pattern, lowered):
            found.add(SKILL_ALIASES[alias])
    return sorted(found)


def skill_frequency(job_skill_lists: list[list[str]]) -> list[tuple[str, int, float]]:
    if not job_skill_lists:
        return []
    counter: Counter[str] = Counter()
    for skills in job_skill_lists:
        counter.update(set(skills))
    total = len(job_skill_lists)
    ranked = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
    return [(skill, count, round(100.0 * count / total, 1)) for skill, count in ranked]


def canonicalize_cv_skill(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    return normalize_skill(text) or text


# Related skills: having one can partially cover another requirement.
_SKILL_FAMILIES: list[set[str]] = [
    {"SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis"},
    {"JavaScript", "TypeScript", "Node.js"},
    {"React", "Next.js", "JavaScript", "TypeScript"},
    {"Python", "FastAPI", "Django", "Flask"},
    {"Java", "Spring", "Kotlin"},
    {"AWS", "GCP", "Azure"},
    {"Docker", "Kubernetes", "CI/CD"},
    {"HTML", "CSS", "Tailwind CSS"},
    {"System Design", "REST", "GraphQL"},
    {"Algorithms", "Data Structures"},
]


def _family_mates(skill: str) -> set[str]:
    key = skill.lower()
    mates: set[str] = set()
    for family in _SKILL_FAMILIES:
        if any(member.lower() == key for member in family):
            mates.update(family)
    mates.discard(skill)
    # Also drop case-variants of self
    return {m for m in mates if m.lower() != key}


def classify_cv_against_requirements(
    top_skills: list[tuple[str, int, float]],
    cv_skills: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """Return (matched, partial, unmatched) against role requirements."""
    req_by_lower = {skill.lower(): skill for skill, _, _ in top_skills}
    cv_canonical = [s for s in (canonicalize_cv_skill(x) for x in cv_skills) if s]
    cv_lower = {s.lower() for s in cv_canonical}

    matched: list[str] = []
    partial: list[str] = []
    seen_matched: set[str] = set()
    seen_partial: set[str] = set()

    for skill, _, _ in top_skills:
        key = skill.lower()
        if key in cv_lower:
            if skill not in seen_matched:
                seen_matched.add(skill)
                matched.append(skill)
            continue
        # Related stack skill → partial cover
        mates = {m.lower() for m in _family_mates(skill)}
        if cv_lower & mates:
            if skill not in seen_partial:
                seen_partial.add(skill)
                partial.append(skill)

    unmatched: list[str] = []
    seen_unmatched: set[str] = set()
    covered_keys = {s.lower() for s in matched} | {s.lower() for s in partial}
    for canonical in cv_canonical:
        key = canonical.lower()
        if key in req_by_lower or key in covered_keys:
            continue
        # Skill that only contributes as a family mate still counts as "used"
        used_as_partial = any(
            key in {m.lower() for m in _family_mates(req)} for req, _, _ in top_skills
        )
        if used_as_partial:
            continue
        if key not in seen_unmatched:
            seen_unmatched.add(key)
            unmatched.append(canonical)

    return matched, partial, unmatched


def missing_skills(
    top_skills: list[tuple[str, int, float]],
    cv_skills: list[str],
    min_percentage: float = 20.0,
) -> list[tuple[str, int, float]]:
    matched, partial, _ = classify_cv_against_requirements(top_skills, cv_skills)
    if not cv_skills:
        # No CV / skills provided — do not invent gaps
        return []
    covered = {s.lower() for s in matched} | {s.lower() for s in partial}
    gaps = []
    for skill, count, pct in top_skills:
        if pct < min_percentage:
            continue
        if skill.lower() not in covered:
            gaps.append((skill, count, pct))
    return gaps