"""30-message approval queue — one personalized message per profile per session."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
from analyzer.classify_profiles import analyze_profile
from analyzer.generate_messages import _fallback_message, generate_message
from database.db import get_connection, init_db, migrate_db, utc_now
from safety.guards import check_message_generation_allowed, record_messages_generated


def _get_active_session(conn) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM queue_sessions WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def build_queue(limit: int | None = None, use_llm: bool = False, min_score: int = 35) -> int:
    """Create a session queue of personalized messages (default 30)."""
    limit = limit or config.MESSAGES_PER_SESSION
    check_message_generation_allowed(limit)

    init_db()
    migrate_db()
    now = utc_now()

    with get_connection() as conn:
        active = _get_active_session(conn)
        if active:
            pending = conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM messages
                WHERE queue_session_id = ? AND status IN ('DRAFT', 'APPROVED')
                """,
                (active["id"],),
            ).fetchone()["cnt"]
            if pending > 0:
                print(f"Active queue #{active['id']} still has {pending} messages to send.")
                print("Finish with: python copilot.py queue next")
                return active["id"]

            conn.execute(
                "UPDATE queue_sessions SET status = 'COMPLETE', updated_at = ? WHERE id = ?",
                (now, active["id"]),
            )

        cursor = conn.execute(
            """
            INSERT INTO queue_sessions (status, total_count, sent_count, created_at, updated_at)
            VALUES ('ACTIVE', 0, 0, ?, ?)
            """,
            (now, now),
        )
        session_id = cursor.lastrowid

        candidates = conn.execute(
            """
            SELECT c.*, a.referral_score
            FROM connections c
            JOIN analysis a ON c.id = a.connection_id
            WHERE a.referral_score >= ?
              AND c.id NOT IN (
                  SELECT connection_id FROM messages
                  WHERE status IN ('DRAFT', 'APPROVED', 'SENT')
              )
            ORDER BY a.referral_score DESC
            LIMIT ?
            """,
            (min_score, limit * 2),
        ).fetchall()

        if not candidates:
            # Analyze unscored profiles first
            rows = conn.execute(
                """
                SELECT c.* FROM connections c
                LEFT JOIN analysis a ON c.id = a.connection_id
                WHERE a.id IS NULL
                """
            ).fetchall()
            for row in rows:
                profile = dict(row)
                result = analyze_profile(profile, use_llm=use_llm)
                from database.db import upsert_analysis
                upsert_analysis(conn, profile["id"], result)

            candidates = conn.execute(
                """
                SELECT c.*, a.referral_score
                FROM connections c
                JOIN analysis a ON c.id = a.connection_id
                WHERE a.referral_score >= ?
                  AND c.id NOT IN (
                      SELECT connection_id FROM messages
                      WHERE status IN ('DRAFT', 'APPROVED', 'SENT')
                  )
                ORDER BY a.referral_score DESC
                LIMIT ?
                """,
                (min_score, limit * 2),
            ).fetchall()

        created = 0
        position = 1
        for row in candidates:
            if created >= limit:
                break
            profile = dict(row)
            first_name = profile.get("name", "there").split()[0]

            if use_llm:
                try:
                    content = generate_message(profile, message_type="networking")
                except Exception:
                    content = _fallback_message(profile, first_name)
            else:
                content = _fallback_message(profile, first_name)

            conn.execute(
                """
                INSERT INTO messages (
                    connection_id, message_type, content, status,
                    queue_session_id, queue_position, created_at, updated_at
                ) VALUES (?, 'networking', ?, 'DRAFT', ?, ?, ?, ?)
                """,
                (profile["id"], content, session_id, position, now, now),
            )
            created += 1
            position += 1
            print(f"  [{created}/{limit}] {profile['name']} @ {profile.get('company', '')} (score {profile.get('referral_score')})")

        conn.execute(
            "UPDATE queue_sessions SET total_count = ?, updated_at = ? WHERE id = ?",
            (created, now, session_id),
        )

    if created > 0:
        record_messages_generated(created)

    print(f"\nQueue session #{session_id} ready: {created} personalized messages.")
    print("Review:  python copilot.py queue list")
    print("Send:    python copilot.py queue next   (repeat up to 30 times)")
    return session_id


def list_queue(session_id: Optional[int] = None) -> None:
    init_db()
    migrate_db()
    with get_connection() as conn:
        if session_id is None:
            active = _get_active_session(conn)
            if not active:
                print("No active queue. Run: python copilot.py queue build")
                return
            session_id = active["id"]

        session = conn.execute(
            "SELECT * FROM queue_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not session:
            print(f"Queue session {session_id} not found.")
            return

        rows = conn.execute(
            """
            SELECT m.id, m.queue_position, m.status, m.content,
                   c.name, c.company, a.referral_score
            FROM messages m
            JOIN connections c ON c.id = m.connection_id
            LEFT JOIN analysis a ON a.connection_id = c.id
            WHERE m.queue_session_id = ?
            ORDER BY m.queue_position ASC
            """,
            (session_id,),
        ).fetchall()

    print(f"\n=== Queue Session #{session_id} ({session['sent_count']}/{session['total_count']} sent) ===\n")
    for row in rows:
        preview = (row["content"] or "")[:80].replace("\n", " ")
        print(f"#{row['queue_position']:02d}  [{row['status']:8s}]  {row['name']} @ {row['company']}  (score {row['referral_score']})")
        print(f"     {preview}...")
        print()


def get_next_message_id(session_id: Optional[int] = None) -> Optional[int]:
    init_db()
    migrate_db()
    with get_connection() as conn:
        if session_id is None:
            active = _get_active_session(conn)
            if not active:
                return None
            session_id = active["id"]

        row = conn.execute(
            """
            SELECT m.id FROM messages m
            WHERE m.queue_session_id = ?
              AND m.status IN ('DRAFT', 'APPROVED')
            ORDER BY m.queue_position ASC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
    return row["id"] if row else None


def open_next_in_linkedin(session_id: Optional[int] = None) -> bool:
    """Open next queued message in LinkedIn browser — user taps Send."""
    msg_id = get_next_message_id(session_id)
    if not msg_id:
        print("Queue complete! No more messages to send.")
        return False

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT m.id, m.queue_position, c.name,
                   (SELECT total_count FROM queue_sessions WHERE id = m.queue_session_id) AS total
            FROM messages m
            JOIN connections c ON c.id = m.connection_id
            WHERE m.id = ?
            """,
            (msg_id,),
        ).fetchone()

    print(f"\nOpening message #{row['queue_position']} of {row['total']}: {row['name']}")
    print(">>> Review in LinkedIn, then TAP SEND <<<")
    print(">>> Then run: python copilot.py queue done\n")

    from scraper.draft_in_linkedin import open_draft_in_browser
    open_draft_in_browser(msg_id, keep_open=True, wait_in_terminal=False)
    return True


def mark_done(message_id: Optional[int] = None) -> None:
    """Mark message sent after user tapped Send on LinkedIn."""
    from scraper.draft_in_linkedin import get_message_for_draft, mark_sent_after_user_tapped

    init_db()
    migrate_db()

    if message_id is None:
        with get_connection() as conn:
            active = _get_active_session(conn)
            if not active:
                print("No active queue.")
                return
            row = conn.execute(
                """
                SELECT id FROM messages
                WHERE queue_session_id = ? AND status = 'APPROVED'
                ORDER BY queue_position ASC LIMIT 1
                """,
                (active["id"],),
            ).fetchone()
            if not row:
                row = conn.execute(
                    """
                    SELECT id FROM messages
                    WHERE queue_session_id = ? AND status = 'DRAFT'
                    ORDER BY queue_position ASC LIMIT 1
                    """,
                    (active["id"],),
                ).fetchone()
            if not row:
                print("No message to mark done.")
                return
            message_id = row["id"]

    data = get_message_for_draft(message_id)
    mark_sent_after_user_tapped(message_id, data["connection_id"])

    now = utc_now()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT queue_session_id FROM messages WHERE id = ?", (message_id,)
        ).fetchone()
        if row and row["queue_session_id"]:
            conn.execute(
                """
                UPDATE queue_sessions SET
                    sent_count = sent_count + 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, row["queue_session_id"]),
            )
            session = conn.execute(
                "SELECT * FROM queue_sessions WHERE id = ?", (row["queue_session_id"],)
            ).fetchone()
            remaining = conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM messages
                WHERE queue_session_id = ? AND status IN ('DRAFT', 'APPROVED')
                """,
                (row["queue_session_id"],),
            ).fetchone()["cnt"]
            print(f"Marked sent. Session progress: {session['sent_count']}/{session['total_count']}")
            if remaining == 0:
                conn.execute(
                    "UPDATE queue_sessions SET status = 'COMPLETE', updated_at = ? WHERE id = ?",
                    (now, row["queue_session_id"]),
                )
                print("Session complete!")
            else:
                print(f"{remaining} messages left. Run: python copilot.py queue next")
