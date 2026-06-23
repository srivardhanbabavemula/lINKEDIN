"""SQLite database schema and helpers for LinkedIn Networking Copilot."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "database" / "linkedin.db"

OUTREACH_STATUSES = (
    "NOT_CONTACTED",
    "CONTACTED",
    "REPLIED",
    "REFERRED",
    "NO_RESPONSE",
)

MESSAGE_STATUSES = (
    "DRAFT",
    "APPROVED",
    "SENT",
    "REJECTED",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db_path() -> Path:
    import os

    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        path = Path(env_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path
    return DEFAULT_DB_PATH


@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> Path:
    path = db_path or get_db_path()
    with get_connection(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                linkedin_url TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                headline TEXT,
                company TEXT,
                role TEXT,
                location TEXT,
                education TEXT,
                about TEXT,
                experience TEXT,
                skills TEXT,
                mutual_connections TEXT,
                scraped_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id INTEGER NOT NULL UNIQUE,
                referral_score INTEGER DEFAULT 0,
                rule_score INTEGER DEFAULT 0,
                llm_score INTEGER DEFAULT 0,
                is_referral_likely INTEGER DEFAULT 0,
                is_relevant_internship INTEGER DEFAULT 0,
                is_recruiter INTEGER DEFAULT 0,
                is_hiring_manager INTEGER DEFAULT 0,
                is_ub_alumni INTEGER DEFAULT 0,
                should_contact INTEGER DEFAULT 0,
                score_breakdown TEXT,
                llm_reasoning TEXT,
                analyzed_at TEXT,
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id INTEGER NOT NULL,
                message_type TEXT NOT NULL DEFAULT 'networking',
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                approved_at TEXT,
                sent_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS outreach (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id INTEGER NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'NOT_CONTACTED',
                message_sent INTEGER DEFAULT 0,
                response_received INTEGER DEFAULT 0,
                follow_up_sent INTEGER DEFAULT 0,
                last_contacted_at TEXT,
                last_response_at TEXT,
                notes TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_connections_company ON connections(company);
            CREATE INDEX IF NOT EXISTS idx_analysis_score ON analysis(referral_score DESC);
            CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach(status);
            CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);

            CREATE TABLE IF NOT EXISTS queue_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                total_count INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        migrate_db(conn)
    return path


def migrate_db(conn: sqlite3.Connection | None = None) -> None:
    """Add columns introduced after initial schema without rebuilding."""
    columns_to_add = [
        ("analysis", "recruiter_type", "TEXT"),
        ("analysis", "alumni_tags", "TEXT"),
        ("analysis", "job_match", "TEXT"),
        ("messages", "queue_session_id", "INTEGER"),
        ("messages", "queue_position", "INTEGER"),
    ]

    def _apply(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS queue_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                total_count INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        for table, column, col_type in columns_to_add:
            existing = {
                row[1]
                for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if column not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    if conn is not None:
        _apply(conn)
    else:
        with get_connection() as connection:
            _apply(connection)


def upsert_connection(conn: sqlite3.Connection, profile: dict[str, Any]) -> int:
    now = utc_now()
    existing = conn.execute(
        "SELECT id FROM connections WHERE linkedin_url = ?",
        (profile["linkedin_url"],),
    ).fetchone()

    fields = {
        "name": profile.get("name", ""),
        "headline": profile.get("headline", ""),
        "company": profile.get("company", ""),
        "role": profile.get("role", ""),
        "location": profile.get("location", ""),
        "education": profile.get("education", ""),
        "about": profile.get("about", ""),
        "experience": profile.get("experience", ""),
        "skills": profile.get("skills", ""),
        "mutual_connections": profile.get("mutual_connections", ""),
        "scraped_at": profile.get("scraped_at", now),
        "updated_at": now,
    }

    if existing:
        conn.execute(
            """
            UPDATE connections SET
                name = ?, headline = ?, company = ?, role = ?, location = ?,
                education = ?, about = ?, experience = ?, skills = ?,
                mutual_connections = ?, scraped_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                fields["name"],
                fields["headline"],
                fields["company"],
                fields["role"],
                fields["location"],
                fields["education"],
                fields["about"],
                fields["experience"],
                fields["skills"],
                fields["mutual_connections"],
                fields["scraped_at"],
                fields["updated_at"],
                existing["id"],
            ),
        )
        connection_id = existing["id"]
    else:
        cursor = conn.execute(
            """
            INSERT INTO connections (
                linkedin_url, name, headline, company, role, location,
                education, about, experience, skills, mutual_connections,
                scraped_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile["linkedin_url"],
                fields["name"],
                fields["headline"],
                fields["company"],
                fields["role"],
                fields["location"],
                fields["education"],
                fields["about"],
                fields["experience"],
                fields["skills"],
                fields["mutual_connections"],
                fields["scraped_at"],
                now,
                now,
            ),
        )
        connection_id = cursor.lastrowid
        conn.execute(
            """
            INSERT OR IGNORE INTO outreach (connection_id, status, updated_at)
            VALUES (?, 'NOT_CONTACTED', ?)
            """,
            (connection_id, now),
        )

    return connection_id


def upsert_analysis(conn: sqlite3.Connection, connection_id: int, analysis: dict[str, Any]) -> None:
    breakdown = analysis.get("score_breakdown")
    if isinstance(breakdown, dict):
        breakdown = json.dumps(breakdown)

    alumni_tags = analysis.get("alumni_tags")
    if isinstance(alumni_tags, list):
        alumni_tags = json.dumps(alumni_tags)

    job_match = analysis.get("job_match")
    if isinstance(job_match, dict):
        job_match = json.dumps(job_match)

    conn.execute(
        """
        INSERT INTO analysis (
            connection_id, referral_score, rule_score, llm_score,
            is_referral_likely, is_relevant_internship, is_recruiter,
            is_hiring_manager, is_ub_alumni, should_contact,
            score_breakdown, llm_reasoning, analyzed_at,
            recruiter_type, alumni_tags, job_match
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(connection_id) DO UPDATE SET
            referral_score = excluded.referral_score,
            rule_score = excluded.rule_score,
            llm_score = excluded.llm_score,
            is_referral_likely = excluded.is_referral_likely,
            is_relevant_internship = excluded.is_relevant_internship,
            is_recruiter = excluded.is_recruiter,
            is_hiring_manager = excluded.is_hiring_manager,
            is_ub_alumni = excluded.is_ub_alumni,
            should_contact = excluded.should_contact,
            score_breakdown = excluded.score_breakdown,
            llm_reasoning = excluded.llm_reasoning,
            analyzed_at = excluded.analyzed_at,
            recruiter_type = excluded.recruiter_type,
            alumni_tags = excluded.alumni_tags,
            job_match = excluded.job_match
        """,
        (
            connection_id,
            analysis.get("referral_score", 0),
            analysis.get("rule_score", 0),
            analysis.get("llm_score", 0),
            int(bool(analysis.get("is_referral_likely"))),
            int(bool(analysis.get("is_relevant_internship"))),
            int(bool(analysis.get("is_recruiter"))),
            int(bool(analysis.get("is_hiring_manager"))),
            int(bool(analysis.get("is_ub_alumni"))),
            int(bool(analysis.get("should_contact"))),
            breakdown,
            analysis.get("llm_reasoning", ""),
            analysis.get("analyzed_at", utc_now()),
            analysis.get("recruiter_type"),
            alumni_tags,
            job_match,
        ),
    )


def get_connections_without_analysis(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT c.* FROM connections c
        LEFT JOIN analysis a ON c.id = a.connection_id
        WHERE a.id IS NULL
        ORDER BY c.updated_at DESC
        """
    ).fetchall()


def get_top_connections(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT c.*, a.referral_score, a.should_contact, a.score_breakdown,
               o.status AS outreach_status
        FROM connections c
        JOIN analysis a ON c.id = a.connection_id
        LEFT JOIN outreach o ON c.id = o.connection_id
        WHERE a.should_contact = 1
        ORDER BY a.referral_score DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def get_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    total = conn.execute("SELECT COUNT(*) AS cnt FROM connections").fetchone()["cnt"]
    contacted = conn.execute(
        "SELECT COUNT(*) AS cnt FROM outreach WHERE status IN ('CONTACTED', 'REPLIED', 'REFERRED', 'NO_RESPONSE')"
    ).fetchone()["cnt"]
    replied = conn.execute(
        "SELECT COUNT(*) AS cnt FROM outreach WHERE status IN ('REPLIED', 'REFERRED')"
    ).fetchone()["cnt"]
    referred = conn.execute(
        "SELECT COUNT(*) AS cnt FROM outreach WHERE status = 'REFERRED'"
    ).fetchone()["cnt"]

    referral_rate = round((referred / contacted) * 100, 1) if contacted else 0.0

    return {
        "total_connections": total,
        "contacted": contacted,
        "replied": replied,
        "referred": referred,
        "referral_rate": referral_rate,
    }


if __name__ == "__main__":
    path = init_db()
    print(f"Database initialized at {path}")
