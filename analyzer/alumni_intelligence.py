"""Alumni and geographic affinity detection for higher response rates."""

from __future__ import annotations

import re
from typing import Any

import config

UB_PATTERNS = [
    r"university at buffalo",
    r"\bub\b",
    r"suny buffalo",
    r"buffalo university",
]

HYDERABAD_PATTERNS = [r"hyderabad", r"\bhyd\b"]
TELANGANA_PATTERNS = [r"telangana", r"secunderabad"]

DEGREE_PATTERNS = [
    r"data science",
    r"computer science",
    r"statistics",
    r"information systems",
]


def _text(profile: dict[str, Any]) -> str:
    return " ".join(
        profile.get(k, "") or ""
        for k in ("headline", "education", "about", "experience", "location")
    ).lower()


def detect_alumni_tags(profile: dict[str, Any]) -> list[str]:
    text = _text(profile)
    tags: list[str] = []

    if any(re.search(p, text, re.IGNORECASE) for p in UB_PATTERNS):
        tags.append("ub_alumni")

    my_degree = config.MY_DEGREE.lower()
    if any(d in text for d in DEGREE_PATTERNS if d in my_degree or d in text):
        if any(re.search(p, text, re.IGNORECASE) for p in DEGREE_PATTERNS):
            tags.append("same_degree")

    if any(re.search(p, text, re.IGNORECASE) for p in HYDERABAD_PATTERNS):
        tags.append("hyderabad")

    if any(re.search(p, text, re.IGNORECASE) for p in TELANGANA_PATTERNS):
        tags.append("telangana")

    # Also check if connection shares your home region from config
    my_loc = config.MY_LOCATION.lower()
    if my_loc and my_loc in text and "hyderabad" not in tags:
        if "hyderabad" in my_loc:
            tags.append("hyderabad")

    return list(dict.fromkeys(tags))
