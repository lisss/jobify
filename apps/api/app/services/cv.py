from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from app.services.skills import SKILL_ALIASES, extract_skills, normalize_skill


def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def extract_skills_from_cv_text(text: str) -> list[str]:
    """Pull skills from an explicit Skills section when present, plus full-text aliases."""
    found: dict[str, str] = {}  # lower -> display

    def add(raw: str) -> None:
        token = raw.strip().strip("•-*·|")
        token = re.sub(r"\s+", " ", token).strip(" .;:")
        if not token or len(token) < 2 or len(token) > 48:
            return
        # Skip obvious non-skills
        if re.search(r"\d{4}|@|http|www\.|curriculum|vitae|resume", token, re.I):
            return
        if token.lower() in {"and", "or", "skills", "technologies", "tools", "proficient"}:
            return

        canonical = normalize_skill(token)
        if canonical:
            found[canonical.lower()] = canonical
            return

        # Keep free-text tokens from a skills section (Title Case-ish)
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9.+#/\- ]{1,46}", token):
            # Prefer known casing from aliases when close
            key = token.lower()
            if key in SKILL_ALIASES:
                found[key] = SKILL_ALIASES[key]
            else:
                display = token if token.isupper() and len(token) <= 5 else token.title() if token.islower() else token
                found[key] = display

    # 1) Known vocabulary across the whole CV
    for skill in extract_skills(text):
        found[skill.lower()] = skill

    # 2) Explicit skills / technologies section tokens
    section = _skills_section(text)
    if section:
        for part in re.split(r"[,;|/•·\n]+", section):
            # Also split "Skill (years)" patterns
            part = re.sub(r"\([^)]*\)", "", part)
            add(part)

    # Stable-ish order: known aliases alphabetically already, keep insertion by sorting
    return sorted(found.values(), key=lambda s: s.lower())


def _skills_section(text: str) -> str | None:
    match = re.search(
        r"(?is)(?:skills|technical skills|tech stack|technologies|tools)\s*[:\-]?\s*\n?(.+?)(?:\n\s*\n|\n(?=[A-Z][A-Za-z ]{2,30}\s*$)|\n(?:experience|education|projects|work history|employment|summary|profile)\b|$)",
        text,
    )
    if not match:
        return None
    return match.group(1)
