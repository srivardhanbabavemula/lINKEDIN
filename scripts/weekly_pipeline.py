"""Weekly automation pipeline for LinkedIn Networking Copilot."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analyzer.classify_profiles import analyze_all_pending
from analyzer.generate_messages import generate_for_top_candidates
from database.db import get_connection, get_stats, init_db

REPORTS_DIR = PROJECT_ROOT / "reports"


def generate_weekly_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"weekly_{timestamp}.csv"

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                c.name, c.company, c.role, a.referral_score,
                o.status, m.content AS draft_message
            FROM connections c
            LEFT JOIN analysis a ON c.id = a.connection_id
            LEFT JOIN outreach o ON c.id = o.connection_id
            LEFT JOIN messages m ON c.id = m.connection_id AND m.status = 'DRAFT'
            ORDER BY a.referral_score DESC NULLS LAST
            """
        ).fetchall()
        stats = get_stats(conn)

    with report_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "company", "role", "score", "status", "draft_message"])
        for row in rows:
            writer.writerow([
                row["name"],
                row["company"],
                row["role"],
                row["referral_score"],
                row["status"] or "NOT_CONTACTED",
                row["draft_message"] or "",
            ])
        writer.writerow([])
        writer.writerow(["STATISTICS"])
        for key, value in stats.items():
            writer.writerow([key, value])

    # Canonical report path for dashboard / automation consumers
    canonical = REPORTS_DIR / "weekly.csv"
    canonical.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Weekly report saved to {report_path}")
    return report_path


def run_weekly_pipeline(
    scrape: bool = False,
    scrape_limit: int = 10,
    analyze_limit: int = 50,
    message_limit: int = 10,
    use_llm: bool = True,
) -> None:
    from exporter.export_report import export_all
    from safety.guards import print_safety_banner

    print("=== LinkedIn Networking Copilot - Weekly Pipeline ===\n")
    print_safety_banner()
    init_db()

    if scrape:
        print("Step 1: Collecting new connection profiles...")
        from scraper.collect_profiles import collect_profiles

        collect_profiles(limit=scrape_limit, headless=True, skip_existing=True)
    else:
        print("Step 1: Skipping scrape (use --scrape to enable)")

    print("\nStep 2: Analyzing profiles...")
    analyze_all_pending(use_llm=use_llm, limit=analyze_limit)

    print("\nStep 3: Generating messages for top candidates...")
    generate_for_top_candidates(limit=message_limit)

    print("\nStep 4: Creating weekly report...")
    report_path = generate_weekly_report()

    print("\nStep 5: Exporting CSV + Markdown review...")
    export_all()

    with get_connection() as conn:
        stats = get_stats(conn)

    print("\n=== Pipeline Complete ===")
    print(f"Total connections: {stats['total_connections']}")
    print(f"Contacted: {stats['contacted']}")
    print(f"Replied: {stats['replied']}")
    print(f"Referral rate: {stats['referral_rate']}%")
    print(f"Report: {report_path}")
    print("\nReview output/weekly_review_*.md and approve messages in dashboard.")
    print("NEVER auto-send. Copy approved messages to LinkedIn manually.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run weekly LinkedIn copilot pipeline")
    parser.add_argument("--scrape", action="store_true", help="Scrape new connections first")
    parser.add_argument("--scrape-limit", type=int, default=20)
    parser.add_argument("--analyze-limit", type=int, default=50)
    parser.add_argument("--message-limit", type=int, default=10)
    parser.add_argument("--no-llm", action="store_true", help="Skip Ollama, use rules only")
    args = parser.parse_args()

    run_weekly_pipeline(
        scrape=args.scrape,
        scrape_limit=args.scrape_limit,
        analyze_limit=args.analyze_limit,
        message_limit=args.message_limit,
        use_llm=not args.no_llm,
    )


if __name__ == "__main__":
    main()
