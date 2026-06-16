"""Detect recruiter types and prioritize outreach."""

from __future__ import annotations

import re
from typing import Any

RECRUITER_RULES: list[tuple[str, list[str]]] = [
    ("university_recruiter", [r"university recruiter", r"campus recruiting lead"]),
    ("campus_recruiter", [r"campus recruiter", r"university relations"]),
    ("senior_recruiter", [r"senior recruiter", r"lead recruiter", r"principal recruiter"]),
    ("technical_recruiter", [r"technical recruiter", r"tech recruiter", r"engineering recruiter"]),
    ("talent_acquisition", [r"talent acquisition", r"talent partner", r"people partner"]),
    ("recruiter", [r"\brecruiter\b", r"recruiting", r"staffing"]),
]


def _text(profile: dict[str, Any]) -> str:
    return " ".join(
        profile.get(k, "") or ""
        for k in ("headline", "role", "about", "experience", "skills")
    ).lower()


def detect_recruiter(profile: dict[str, Any]) -> tuple[bool, str | None]:
    """Return (is_recruiter, recruiter_type). Highest-priority match wins."""
    text = _text(profile)
    for recruiter_type, patterns in RECRUITER_RULES:
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            return True, recruiter_type
    return False, None
