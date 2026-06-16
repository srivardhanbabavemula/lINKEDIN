"""Seed the database with sample connections for dashboard development."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analyzer.classify_profiles import analyze_profile
from analyzer.generate_messages import generate_message
from database.db import get_connection, init_db, upsert_analysis, upsert_connection, utc_now

SAMPLE_PROFILES = [
    {
        "linkedin_url": "https://www.linkedin.com/in/john-doe-sample",
        "name": "John Doe",
        "headline": "Senior Data Engineer at Amazon",
        "company": "Amazon",
        "role": "Senior Data Engineer",
        "location": "Seattle, WA",
        "education": "University at Buffalo — MS Computer Science",
        "about": "Building large-scale data pipelines at Amazon. UB alumnus passionate about mentoring students.",
        "experience": "Amazon — Senior Data Engineer (3 yrs)\nStartup — Data Engineer (2 yrs)",
        "skills": "Python, Spark, AWS, SQL, Airflow",
        "mutual_connections": "12 mutual connections",
    },
    {
        "linkedin_url": "https://www.linkedin.com/in/jane-smith-sample",
        "name": "Jane Smith",
        "headline": "Technical Recruiter at Microsoft",
        "company": "Microsoft",
        "role": "Technical Recruiter",
        "location": "Redmond, WA",
        "education": "University of Washington",
        "about": "Hiring data engineers and ML engineers for Azure teams.",
        "experience": "Microsoft — Technical Recruiter (2 yrs)",
        "skills": "Recruiting, Technical Screening, Campus Hiring",
        "mutual_connections": "5 mutual connections",
    },
    {
        "linkedin_url": "https://www.linkedin.com/in/alex-chen-sample",
        "name": "Alex Chen",
        "headline": "Data Scientist at Meta",
        "company": "Meta",
        "role": "Data Scientist",
        "location": "Menlo Park, CA",
        "education": "University at Buffalo — BS Statistics",
        "about": "Working on experimentation platforms. Happy to chat with UB students.",
        "experience": "Meta — Data Scientist (2 yrs)\nConsulting — Analyst (1 yr)",
        "skills": "Python, R, A/B Testing, SQL",
        "mutual_connections": "8 mutual connections",
    },
    {
        "linkedin_url": "https://www.linkedin.com/in/sarah-patel-sample",
        "name": "Sarah Patel",
        "headline": "Software Engineer at Local Startup",
        "company": "Buffalo Tech",
        "role": "Software Engineer",
        "location": "Buffalo, NY",
        "education": "SUNY Buffalo State",
        "about": "Full-stack developer working on local SaaS products.",
        "experience": "Buffalo Tech — Software Engineer (1 yr)",
        "skills": "JavaScript, React, Node.js",
        "mutual_connections": "2 mutual connections",
    },
    {
        "linkedin_url": "https://www.linkedin.com/in/mike-johnson-sample",
        "name": "Mike Johnson",
        "headline": "Engineering Manager, Data Platform at Databricks",
        "company": "Databricks",
        "role": "Engineering Manager",
        "location": "San Francisco, CA",
        "education": "MIT — MS Computer Science",
        "about": "Leading data platform engineering. Previously at Google.",
        "experience": "Databricks — Engineering Manager (2 yrs)\nGoogle — Staff Engineer (4 yrs)",
        "skills": "Spark, Scala, Leadership, Data Engineering",
        "mutual_connections": "3 mutual connections",
    },
]


def seed(use_llm: bool = False) -> None:
    init_db()
    now = utc_now()

    with get_connection() as conn:
        for profile in SAMPLE_PROFILES:
            profile["scraped_at"] = now
            conn_id = upsert_connection(conn, profile)
            analysis = analyze_profile({**profile, "id": conn_id}, use_llm=use_llm)
            upsert_analysis(conn, conn_id, analysis)

            if analysis.get("should_contact"):
                content = generate_message({**profile, "id": conn_id})
                conn.execute(
                    """
                    INSERT INTO messages (connection_id, message_type, content, status, created_at, updated_at)
                    VALUES (?, 'networking', ?, 'DRAFT', ?, ?)
                    """,
                    (conn_id, content, now, now),
                )

    print(f"Seeded {len(SAMPLE_PROFILES)} sample connections.")


if __name__ == "__main__":
    seed(use_llm=False)
