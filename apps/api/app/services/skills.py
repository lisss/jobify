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


def classify_cv_against_requirements(
    top_skills: list[tuple[str, int, float]],
    cv_skills: list[str],
) -> tuple[list[str], list[str]]:
    """Return (matched requirement names, unmatched CV skills)."""
    req_by_lower = {skill.lower(): skill for skill, _, _ in top_skills}
    matched: list[str] = []
    unmatched: list[str] = []
    seen_matched: set[str] = set()
    seen_unmatched: set[str] = set()

    for raw in cv_skills:
        canonical = canonicalize_cv_skill(raw)
        if not canonical:
            continue
        key = canonical.lower()
        if key in req_by_lower:
            name = req_by_lower[key]
            if name not in seen_matched:
                seen_matched.add(name)
                matched.append(name)
        elif key not in seen_unmatched:
            seen_unmatched.add(key)
            unmatched.append(canonical)
    return matched, unmatched


def missing_skills(
    top_skills: list[tuple[str, int, float]],
    cv_skills: list[str],
    min_percentage: float = 20.0,
) -> list[tuple[str, int, float]]:
    cv_normalized = {canonicalize_cv_skill(s) for s in cv_skills}
    cv_normalized = {s for s in cv_normalized if s}
    if not cv_normalized:
        # No CV / skills provided — do not invent gaps
        return []
    cv_lower = {s.lower() for s in cv_normalized}
    gaps = []
    for skill, count, pct in top_skills:
        if pct < min_percentage:
            continue
        if skill.lower() not in cv_lower:
            gaps.append((skill, count, pct))
    return gaps
