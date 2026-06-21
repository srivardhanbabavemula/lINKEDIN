"""Export outreach drafts to CSV and Markdown for offline review."""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_connection, init_db

OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"


def export_csv(path: Path | None = None) -> Path:
    init_db()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = path or OUTPUT_DIR / "outreach_drafts.csv"

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                c.name, c.company, c.role, a.referral_score,
                COALESCE(o.status, 'NOT_CONTACTED') AS status,
                m.content AS message, m.status AS message_status
            FROM connections c
            LEFT JOIN analysis a ON c.id = a.connection_id
            LEFT JOIN outreach o ON c.id = o.connection_id
            LEFT JOIN messages m ON c.id = m.connection_id
                AND m.id = (
                    SELECT id FROM messages
                    WHERE connection_id = c.id
                    ORDER BY created_at DESC LIMIT 1
                )
            WHERE a.should_contact = 1 OR m.content IS NOT NULL
            ORDER BY a.referral_score DESC NULLS LAST
            """
        ).fetchall()

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Company", "Score", "Status", "MessageStatus", "Message"])
        for row in rows:
            writer.writerow([
                row["name"],
                row["company"],
                row["referral_score"],
                row["status"],
                row["message_status"] or "",
                row["message"] or "",
            ])

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    canonical = REPORTS_DIR / "weekly.csv"
    canonical.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Exported {len(rows)} rows to {out}")
    return out


def export_markdown(path: Path | None = None) -> Path:
    init_db()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = path or OUTPUT_DIR / f"weekly_review_{timestamp}.md"

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.name, c.company, c.role, a.referral_score, a.score_breakdown,
                   COALESCE(o.status, 'NOT_CONTACTED') AS status,
                   m.content AS message, m.status AS message_status
            FROM connections c
            LEFT JOIN analysis a ON c.id = a.connection_id
            LEFT JOIN outreach o ON c.id = o.connection_id
            LEFT JOIN messages m ON c.id = m.connection_id AND m.status IN ('DRAFT', 'APPROVED')
            WHERE a.should_contact = 1
            ORDER BY a.referral_score DESC
            LIMIT 10
            """
        ).fetchall()

    lines = [
        "# LinkedIn Networking Copilot - Weekly Review",
        "",
        f"Generated: {timestamp}",
        "",
        "> Manual approval required. Review each message before sending on LinkedIn.",
        "",
        "---",
        "",
    ]

    for i, row in enumerate(rows, 1):
        lines.extend([
            f"## {i}. {row['name']} - {row['company']} (Score: {row['referral_score']})",
            "",
            f"- **Role:** {row['role'] or 'N/A'}",
            f"- **Status:** {row['status']}",
            f"- **Message status:** {row['message_status'] or 'Not generated'}",
            "",
            "### Draft Message",
            "",
            "```",
            row["message"] or "(Run: python copilot.py messages --limit 10)",
            "```",
            "",
            "- [ ] Reviewed",
            "- [ ] Approved",
            "- [ ] Sent on LinkedIn",
            "",
            "---",
            "",
        ])

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported markdown review to {out}")
    return out


def export_all() -> tuple[Path, Path]:
    return export_csv(), export_markdown()


if __name__ == "__main__":
    export_all()
