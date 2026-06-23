"""Rule-based scoring engine for LinkedIn connection referral potential."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
from analyzer.alumni_intelligence import detect_alumni_tags
from analyzer.job_matcher import best_job_match
from analyzer.recruiter_detector import detect_recruiter

TARGET_ROLES: dict[str, int] = {
    r"co-?op": 24,
    r"\bcoop\b": 22,
    r"intern": 22,
    r"internship": 20,
    r"university recruiter": 22,
    r"campus recruiter": 22,
    r"new grad": 20,
    r"early career": 18,
    r"recruiter": 18,
    r"talent acquisition": 16,
    r"software engineer": 14,
    r"data engineer": 14,
    r"data scientist": 14,
    r"analyst": 12,
    r"product manager": 12,
}

HIRING_MANAGER_PATTERNS = [
    r"hiring manager",
    r"engineering manager",
    r"director of engineering",
    r"vp of engineering",
    r"head of data",
    r"data engineering manager",
]

ACTIVE_POSTER_PATTERNS = [
    r"creator",
    r"speaker",
    r"thought leader",
    r"published",
]


def _search_text(profile: dict[str, Any]) -> str:
    parts = [
        profile.get("name", ""),
        profile.get("headline", ""),
        profile.get("company", ""),
        profile.get("role", ""),
        profile.get("location", ""),
        profile.get("education", ""),
        profile.get("about", ""),
        profile.get("experience", ""),
        profile.get("skills", ""),
    ]
    return " ".join(parts).lower()


def _match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def score_profile(profile: dict[str, Any]) -> dict[str, Any]:
    text = _search_text(profile)
    breakdown: dict[str, int] = {}
    flags: dict[str, Any] = {
        "is_ub_alumni": False,
        "is_recruiter": False,
        "is_hiring_manager": False,
        "is_relevant_internship": False,
        "is_referral_likely": False,
        "recruiter_type": None,
        "alumni_tags": [],
        "job_match": None,
    }

    # Alumni intelligence
    alumni_tags = detect_alumni_tags(profile)
    flags["alumni_tags"] = alumni_tags
    for tag in alumni_tags:
        bonus = config.ALUMNI_BONUS.get(tag, 0)
        if bonus:
            label = tag.replace("_", " ").title()
            breakdown[label] = breakdown.get(label, 0) + bonus
    flags["is_ub_alumni"] = "ub_alumni" in alumni_tags

    # Target companies
    for company, points in config.TARGET_COMPANIES.items():
        if company in text:
            breakdown[company.title()] = points
            break

    # Relevant roles
    for pattern, points in TARGET_ROLES.items():
        if re.search(pattern, text, re.IGNORECASE):
            breakdown["Relevant Role"] = points
            flags["is_relevant_internship"] = True
            break

    # Recruiter detector (prioritized subtypes)
    is_recruiter, recruiter_type = detect_recruiter(profile)
    if is_recruiter and recruiter_type:
        flags["is_recruiter"] = True
        flags["recruiter_type"] = recruiter_type
        bonus = config.RECRUITER_BONUS.get(recruiter_type, 15)
        breakdown[recruiter_type.replace("_", " ").title()] = bonus
        flags["is_referral_likely"] = True

    if _match_any(text, HIRING_MANAGER_PATTERNS):
        breakdown["Hiring Manager"] = 20
        flags["is_hiring_manager"] = True
        flags["is_referral_likely"] = True

    if _match_any(text, ACTIVE_POSTER_PATTERNS):
        breakdown["Active on LinkedIn"] = 10

    mutual = profile.get("mutual_connections", "")
    if mutual and re.search(r"\d+", mutual):
        breakdown["Mutual Connections"] = 5

    # Job matching bonus
    job = best_job_match(profile)
    if job:
        flags["job_match"] = job
        breakdown["Job Match"] = 15
        flags["is_referral_likely"] = True

    rule_score = min(sum(breakdown.values()), 100)

    if flags["is_ub_alumni"] and flags["is_relevant_internship"]:
        flags["is_referral_likely"] = True

    flags["should_contact"] = rule_score >= config.MIN_CONTACT_SCORE

    return {
        "rule_score": rule_score,
        "score_breakdown": breakdown,
        **flags,
    }


if __name__ == "__main__":
    from database.db import get_connection, init_db, migrate_db, upsert_analysis, utc_now

    init_db()
    migrate_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM connections").fetchall()
        for row in rows:
            profile = dict(row)
            result = score_profile(profile)
            result["referral_score"] = result["rule_score"]
            result["llm_score"] = 0
            result["analyzed_at"] = utc_now()
            upsert_analysis(conn, profile["id"], result)
            print(f"{profile['name']}: {result['rule_score']} - {result['score_breakdown']}")
