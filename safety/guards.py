"""Account safety: rate limits, scrape guards, manual-approval enforcement."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

SAFETY_DIR = config.PROJECT_ROOT / "safety"
SAFETY_LOG = SAFETY_DIR / "activity.json"

# Hard caps — protect your LinkedIn account
MAX_SCRAPE_PER_SESSION = int(getattr(config, "MAX_SCRAPE_PER_SESSION", 15))
MAX_SCRAPE_PER_DAY = int(getattr(config, "MAX_SCRAPE_PER_DAY", 25))
MAX_MESSAGES_PER_WEEK = int(getattr(config, "WEEKLY_MESSAGE_LIMIT", 10))
MIN_SCRAPE_DELAY = float(config.SCRAPE_DELAY_SECONDS)

# Manual approval is mandatory — never auto-send
AUTO_SEND_ENABLED = False


class SafetyError(Exception):
    """Raised when an action would violate safety limits."""


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_log() -> dict[str, Any]:
    SAFETY_DIR.mkdir(parents=True, exist_ok=True)
    if not SAFETY_LOG.exists():
        return {"daily": {}, "sessions": [], "warnings": []}
    return json.loads(SAFETY_LOG.read_text(encoding="utf-8"))


def _save_log(data: dict[str, Any]) -> None:
    SAFETY_DIR.mkdir(parents=True, exist_ok=True)
    SAFETY_LOG.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_daily_scrape_count() -> int:
    log = _load_log()
    return int(log.get("daily", {}).get(_today(), {}).get("scraped", 0))


def check_scrape_allowed(requested: int = 1) -> None:
    """Block scrape if daily cap would be exceeded."""
    current = get_daily_scrape_count()
    effective_limit = min(MAX_SCRAPE_PER_SESSION, MAX_SCRAPE_PER_DAY - current)

    if effective_limit <= 0:
        raise SafetyError(
            f"Daily scrape limit reached ({MAX_SCRAPE_PER_DAY}/day). "
            "Import profiles manually with: python copilot.py import --file profiles.csv"
        )

    if requested > effective_limit:
        raise SafetyError(
            f"Requested {requested} profiles but only {effective_limit} allowed today. "
            f"Use --limit {effective_limit} or import manually."
        )


def enforce_scrape_limit(requested_limit: int | None) -> int:
    """Clamp scrape limit to safe maximum."""
    check_scrape_allowed(1)
    current = get_daily_scrape_count()
    remaining_today = MAX_SCRAPE_PER_DAY - current
    cap = min(MAX_SCRAPE_PER_SESSION, remaining_today)

    if requested_limit is None:
        return cap
    return max(1, min(requested_limit, cap))


def record_scrape(count: int) -> None:
    log = _load_log()
    today = _today()
    daily = log.setdefault("daily", {})
    day_data = daily.setdefault(today, {"scraped": 0, "messages_generated": 0})
    day_data["scraped"] = day_data.get("scraped", 0) + count
    log["sessions"].append(
        {
            "type": "scrape",
            "count": count,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _save_log(log)


def check_message_generation_allowed(count: int) -> None:
    if count > MAX_MESSAGES_PER_WEEK:
        raise SafetyError(
            f"Weekly message cap is {MAX_MESSAGES_PER_WEEK}. "
            "Focus on top-quality outreach, not volume."
        )


def record_messages_generated(count: int) -> None:
    log = _load_log()
    today = _today()
    daily = log.setdefault("daily", {})
    day_data = daily.setdefault(today, {"scraped": 0, "messages_generated": 0})
    day_data["messages_generated"] = day_data.get("messages_generated", 0) + count
    _save_log(log)


def assert_manual_send_only() -> None:
    if AUTO_SEND_ENABLED:
        raise SafetyError("Auto-send is disabled by design. All messages require manual approval.")


def can_mark_sent(current_status: str) -> bool:
    """Dashboard/API gate: only APPROVED messages can be marked SENT."""
    return current_status == "APPROVED"


def get_safety_status() -> dict[str, Any]:
    log = _load_log()
    today = _today()
    day = log.get("daily", {}).get(today, {})
    return {
        "auto_send_enabled": AUTO_SEND_ENABLED,
        "manual_approval_required": True,
        "scraped_today": day.get("scraped", 0),
        "max_scrape_per_day": MAX_SCRAPE_PER_DAY,
        "max_scrape_per_session": MAX_SCRAPE_PER_SESSION,
        "remaining_scrapes_today": max(0, MAX_SCRAPE_PER_DAY - day.get("scraped", 0)),
        "messages_generated_today": day.get("messages_generated", 0),
        "max_messages_per_week": MAX_MESSAGES_PER_WEEK,
        "min_scrape_delay_seconds": MIN_SCRAPE_DELAY,
        "recommended_workflow": "import_or_small_scrape -> analyze -> generate -> approve -> copy -> send manually on LinkedIn",
    }


def print_safety_banner() -> None:
    status = get_safety_status()
    print("=" * 60)
    print("  LINKEDIN SAFETY MODE - Manual approval required")
    print("  No auto-send. No 24/7 bots. Small batches only.")
    print(f"  Scrapes today: {status['scraped_today']}/{status['max_scrape_per_day']}")
    print(f"  Remaining today: {status['remaining_scrapes_today']}")
    print("=" * 60)
