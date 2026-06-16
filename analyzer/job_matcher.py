"""Match connections to open internship/job postings at their companies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import config

JOBS_FILE = config.PROJECT_ROOT / "data" / "target_jobs.json"


def load_target_jobs() -> list[dict[str, Any]]:
    if not JOBS_FILE.exists():
        return []
    return json.loads(JOBS_FILE.read_text(encoding="utf-8"))


def match_jobs(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Return job matches for a profile based on company and role overlap."""
    company = (profile.get("company") or "").lower()
    role_text = " ".join(
        profile.get(k, "") or "" for k in ("role", "headline", "skills", "experience")
    ).lower()

    if not company:
        return []

    matches: list[dict[str, Any]] = []
    for job in load_target_jobs():
        job_company = job.get("company", "").lower()
        if job_company not in company and company not in job_company:
            continue

        title = job.get("title", "").lower()
        keywords = [k.lower() for k in job.get("keywords", [])]
        if any(kw in role_text for kw in keywords) or any(kw in title for kw in keywords):
            matches.append(
                {
                    "company": job["company"],
                    "title": job["title"],
                    "url": job.get("url", ""),
                    "suggested_action": "Send networking message",
                }
            )

    return matches


def best_job_match(profile: dict[str, Any]) -> dict[str, Any] | None:
    matches = match_jobs(profile)
    return matches[0] if matches else None
