"""Follow-up tracking and outreach status management."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.db import OUTREACH_STATUSES, get_connection, init_db, utc_now


def update_outreach_status(
    connection_id: int,
    status: str,
    notes: Optional[str] = None,
) -> None:
    if status not in OUTREACH_STATUSES:
        raise ValueError(f"Invalid status. Must be one of: {OUTREACH_STATUSES}")

    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO outreach (connection_id, status, notes, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(connection_id) DO UPDATE SET
                status = excluded.status,
                notes = COALESCE(excluded.notes, outreach.notes),
                updated_at = excluded.updated_at
            """,
            (connection_id, status, notes, now),
        )


def mark_message_sent(connection_id: int, message_id: int) -> None:
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            "UPDATE messages SET status = 'SENT', sent_at = ?, updated_at = ? WHERE id = ?",
            (now, now, message_id),
        )
        conn.execute(
            """
            INSERT INTO outreach (connection_id, status, message_sent, last_contacted_at, updated_at)
            VALUES (?, 'CONTACTED', 1, ?, ?)
            ON CONFLICT(connection_id) DO UPDATE SET
                status = 'CONTACTED',
                message_sent = 1,
                last_contacted_at = excluded.last_contacted_at,
                updated_at = excluded.updated_at
            """,
            (connection_id, now, now),
        )


def mark_response_received(connection_id: int, referred: bool = False) -> None:
    now = utc_now()
    status = "REFERRED" if referred else "REPLIED"
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE outreach SET
                status = ?,
                response_received = 1,
                last_response_at = ?,
                updated_at = ?
            WHERE connection_id = ?
            """,
            (status, now, now, connection_id),
        )


def mark_follow_up_sent(connection_id: int) -> None:
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE outreach SET
                follow_up_sent = 1,
                last_contacted_at = ?,
                updated_at = ?
            WHERE connection_id = ?
            """,
            (now, now, connection_id),
        )


def get_pending_follow_ups(days_since_contact: int = 7) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.company, o.last_contacted_at, o.status
            FROM outreach o
            JOIN connections c ON c.id = o.connection_id
            WHERE o.status = 'CONTACTED'
              AND o.response_received = 0
              AND o.follow_up_sent = 0
              AND o.last_contacted_at IS NOT NULL
              AND datetime(o.last_contacted_at) <= datetime('now', ?)
            ORDER BY o.last_contacted_at ASC
            """,
            (f"-{days_since_contact} days",),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_no_response(connection_id: int) -> None:
    update_outreach_status(connection_id, "NO_RESPONSE")


def list_outreach() -> None:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.name, c.company, o.status, o.message_sent,
                   o.response_received, o.follow_up_sent, o.last_contacted_at
            FROM outreach o
            JOIN connections c ON c.id = o.connection_id
            ORDER BY o.updated_at DESC
            """
        ).fetchall()

    for row in rows:
        print(
            f"{row['name']} | {row['company']} | {row['status']} | "
            f"sent={row['message_sent']} replied={row['response_received']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage outreach follow-ups")
    sub = parser.add_subparsers(dest="command")

    list_cmd = sub.add_parser("list", help="List all outreach records")
    follow_cmd = sub.add_parser("follow-ups", help="Show pending follow-ups")
    follow_cmd.add_argument("--days", type=int, default=7)

    status_cmd = sub.add_parser("status", help="Update outreach status")
    status_cmd.add_argument("connection_id", type=int)
    status_cmd.add_argument("status", choices=OUTREACH_STATUSES)
    status_cmd.add_argument("--notes", type=str, default=None)

    args = parser.parse_args()
    init_db()

    if args.command == "list":
        list_outreach()
    elif args.command == "follow-ups":
        pending = get_pending_follow_ups(days_since_contact=args.days)
        for item in pending:
            print(f"{item['name']} @ {item['company']} — last contacted {item['last_contacted_at']}")
        if not pending:
            print("No pending follow-ups.")
    elif args.command == "status":
        update_outreach_status(args.connection_id, args.status, notes=args.notes)
        print(f"Updated connection {args.connection_id} to {args.status}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
