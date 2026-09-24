from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from app.services.skills import extract_skills


def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def extract_skills_from_cv_text(text: str) -> list[str]:
    # Prefer an explicit Skills section when present
    skills_section = _skills_section(text)
    source = skills_section or text
    return extract_skills(source)


def _skills_section(text: str) -> str | None:
    match = re.search(
        r"(?is)(?:skills|technical skills|technologies)\s*[:\n](.+?)(?:\n\s*\n|experience|education|projects|$)",
        text,
    )
    if not match:
        return None
    return match.group(1)
