"""Classify LinkedIn profiles using a local Ollama LLM."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analyzer.llm_client import generate as llm_generate
from analyzer.score_profiles import score_profile
from database.db import get_connection, get_connections_without_analysis, init_db, migrate_db, upsert_analysis, utc_now

load_dotenv(PROJECT_ROOT / ".env")

import config

ANALYSIS_PROMPT = """Analyze this LinkedIn profile for student networking outreach.

The student is looking for: {my_target_role}
(This includes internships, co-op programs, and full-time roles.)
School: {my_school}
Degree: {my_degree}

Determine:
1. Is this person likely to provide referrals or helpful advice?
2. Are they relevant for internships, co-ops, or full-time opportunities?
3. Are they a recruiter or campus/university recruiter?
4. Are they a hiring manager?
5. Are they an alumnus of {my_school}?
6. Should the student contact them?

Return ONLY valid JSON with this exact structure:
{{
  "is_referral_likely": true/false,
  "is_relevant_internship": true/false,
  "is_recruiter": true/false,
  "is_hiring_manager": true/false,
  "is_ub_alumni": true/false,
  "should_contact": true/false,
  "llm_score": 0-100,
  "reasoning": "brief explanation"
}}

Profile:
Name: {name}
Headline: {headline}
Company: {company}
Role: {role}
Location: {location}
Education: {education}
About: {about}
Experience: {experience}
Skills: {skills}
"""


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def call_ollama(prompt: str) -> str:
    return llm_generate(prompt, temperature=0.2)


def parse_llm_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def merge_scores(rule_result: dict[str, Any], llm_result: dict[str, Any]) -> dict[str, Any]:
    llm_score = int(llm_result.get("llm_score", 0) or 0)
    rule_score = int(rule_result.get("rule_score", 0))
    referral_score = min(round(rule_score * 0.6 + llm_score * 0.4), 100)

    merged = {
        "referral_score": referral_score,
        "rule_score": rule_score,
        "llm_score": llm_score,
        "is_referral_likely": bool(
            rule_result.get("is_referral_likely") or llm_result.get("is_referral_likely")
        ),
        "is_relevant_internship": bool(
            rule_result.get("is_relevant_internship") or llm_result.get("is_relevant_internship")
        ),
        "is_recruiter": bool(rule_result.get("is_recruiter") or llm_result.get("is_recruiter")),
        "is_hiring_manager": bool(
            rule_result.get("is_hiring_manager") or llm_result.get("is_hiring_manager")
        ),
        "is_ub_alumni": bool(rule_result.get("is_ub_alumni") or llm_result.get("is_ub_alumni")),
        "should_contact": bool(rule_result.get("should_contact") or llm_result.get("should_contact")),
        "score_breakdown": rule_result.get("score_breakdown", {}),
        "llm_reasoning": llm_result.get("reasoning", ""),
        "recruiter_type": rule_result.get("recruiter_type"),
        "alumni_tags": rule_result.get("alumni_tags", []),
        "job_match": rule_result.get("job_match"),
        "analyzed_at": utc_now(),
    }

    if merged["referral_score"] >= 60:
        merged["should_contact"] = True

    return merged


def analyze_profile(profile: dict[str, Any], use_llm: bool = True) -> dict[str, Any]:
    rule_result = score_profile(profile)
    if not use_llm:
        return {
            "referral_score": rule_result["rule_score"],
            "rule_score": rule_result["rule_score"],
            "llm_score": 0,
            "is_referral_likely": rule_result["is_referral_likely"],
            "is_relevant_internship": rule_result["is_relevant_internship"],
            "is_recruiter": rule_result["is_recruiter"],
            "is_hiring_manager": rule_result["is_hiring_manager"],
            "is_ub_alumni": rule_result["is_ub_alumni"],
            "should_contact": rule_result.get("should_contact", False),
            "score_breakdown": rule_result["score_breakdown"],
            "recruiter_type": rule_result.get("recruiter_type"),
            "alumni_tags": rule_result.get("alumni_tags", []),
            "job_match": rule_result.get("job_match"),
            "llm_reasoning": "",
            "analyzed_at": utc_now(),
        }

    prompt = ANALYSIS_PROMPT.format(
        my_target_role=config.MY_TARGET_ROLE,
        my_school=config.MY_SCHOOL,
        my_degree=config.MY_DEGREE,
        name=profile.get("name", ""),
        headline=profile.get("headline", ""),
        company=profile.get("company", ""),
        role=profile.get("role", ""),
        location=profile.get("location", ""),
        education=profile.get("education", ""),
        about=profile.get("about", "")[:800],
        experience=profile.get("experience", "")[:800],
        skills=profile.get("skills", "")[:400],
    )

    try:
        raw = call_ollama(prompt)
        llm_result = parse_llm_json(raw)
    except Exception as exc:
        llm_result = {"reasoning": f"LLM unavailable: {exc}", "llm_score": 0}

    return merge_scores(rule_result, llm_result)


def analyze_all_pending(use_llm: bool = True, limit: Optional[int] = None) -> int:
    init_db()
    migrate_db()
    analyzed = 0

    with get_connection() as conn:
        pending = get_connections_without_analysis(conn)
        if limit:
            pending = pending[:limit]

        for row in pending:
            profile = _row_to_dict(row)
            print(f"Analyzing: {profile['name']}")
            result = analyze_profile(profile, use_llm=use_llm)
            upsert_analysis(conn, profile["id"], result)
            analyzed += 1
            print(f"  Score: {result['referral_score']} | Contact: {result['should_contact']}")

    print(f"Analyzed {analyzed} profiles.")
    return analyzed


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify LinkedIn profiles with Ollama")
    parser.add_argument("--no-llm", action="store_true", help="Use rule-based scoring only")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    analyze_all_pending(use_llm=not args.no_llm, limit=args.limit)


if __name__ == "__main__":
    main()
