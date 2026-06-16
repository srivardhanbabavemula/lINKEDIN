"""Generate personalized outreach messages using Ollama."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
from analyzer.llm_client import generate as llm_generate
from database.db import get_connection, get_top_connections, init_db, utc_now
from safety.guards import check_message_generation_allowed, record_messages_generated

MY_NAME = config.MY_NAME
MY_SCHOOL = config.MY_SCHOOL
MY_DEGREE = config.MY_DEGREE
MY_TARGET_ROLE = config.MY_TARGET_ROLE


def load_prompt(name: str) -> str:
    path = PROJECT_ROOT / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def call_ollama(prompt: str) -> str:
    return llm_generate(prompt, temperature=0.7)


def generate_message(profile: dict[str, Any], message_type: str = "networking") -> str:
    prompt_template = load_prompt(message_type)
    first_name = profile.get("name", "there").split()[0]

    prompt = prompt_template.format(
        name=profile.get("name", ""),
        first_name=first_name,
        headline=profile.get("headline", ""),
        company=profile.get("company", ""),
        role=profile.get("role", ""),
        education=profile.get("education", "")[:500],
        about=profile.get("about", "")[:500],
        experience=profile.get("experience", "")[:500],
        my_name=MY_NAME,
        my_school=MY_SCHOOL,
        my_degree=MY_DEGREE,
        my_target_role=MY_TARGET_ROLE,
    )

    try:
        return call_ollama(prompt)
    except Exception:
        return _fallback_message(profile, first_name)


def _fallback_message(profile: dict[str, Any], first_name: str) -> str:
    parts = [f"Hi {first_name},"]
    if profile.get("education") and MY_SCHOOL.lower() in profile["education"].lower():
        parts.append(
            f"I noticed you're a {MY_SCHOOL} alumnus and currently work as a {profile.get('role', 'professional')} at {profile.get('company', 'your company')}."
        )
    else:
        parts.append(
            f"I came across your profile and was impressed by your work as a {profile.get('role', 'professional')} at {profile.get('company', 'your company')}."
        )
    parts.append(
        f"I'm pursuing my {MY_DEGREE} at {MY_SCHOOL} and preparing for {MY_TARGET_ROLE}. Your career path stood out to me, and I'd appreciate the opportunity to learn from your experience."
    )
    parts.append("Thank you for your time.")
    return "\n\n".join(parts)


def generate_for_top_candidates(
    limit: int = 10,
    message_type: str = "networking",
    min_score: int = 50,
) -> int:
    check_message_generation_allowed(limit)
    init_db()
    created = 0
    now = utc_now()

    with get_connection() as conn:
        candidates = get_top_connections(conn, limit=limit * 2)

        for row in candidates:
            profile = dict(row)
            if profile.get("referral_score", 0) < min_score:
                continue

            existing = conn.execute(
                """
                SELECT id FROM messages
                WHERE connection_id = ? AND status IN ('DRAFT', 'APPROVED', 'SENT')
                """,
                (profile["id"],),
            ).fetchone()
            if existing:
                continue

            content = generate_message(profile, message_type=message_type)
            conn.execute(
                """
                INSERT INTO messages (connection_id, message_type, content, status, created_at, updated_at)
                VALUES (?, ?, ?, 'DRAFT', ?, ?)
                """,
                (profile["id"], message_type, content, now, now),
            )
            created += 1
            print(f"Generated message for {profile['name']} (score: {profile['referral_score']})")

            if created >= limit:
                break

    if created > 0:
        record_messages_generated(created)

    print(f"Created {created} draft messages (DRAFT — requires your approval).")
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate personalized LinkedIn messages")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--type", choices=["networking", "referral"], default="networking")
    parser.add_argument("--min-score", type=int, default=50)
    args = parser.parse_args()
    generate_for_top_candidates(
        limit=args.limit,
        message_type=args.type,
        min_score=args.min_score,
    )


if __name__ == "__main__":
    main()
