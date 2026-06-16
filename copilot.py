#!/usr/bin/env python3
"""Unified CLI for LinkedIn Networking Copilot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def cmd_init(_: argparse.Namespace) -> None:
    from database.db import init_db, migrate_db

    path = init_db()
    migrate_db()
    print(f"Database ready: {path}")


def cmd_safety(_: argparse.Namespace) -> None:
    from safety.guards import get_safety_status, print_safety_banner
    import json

    print_safety_banner()
    print(json.dumps(get_safety_status(), indent=2))


def cmd_import(args: argparse.Namespace) -> None:
    from importer.import_profiles import create_sample_template, import_profiles

    if args.template:
        path = create_sample_template()
        print(f"Template created: {path}")
        return
    import_profiles(args.file)


def cmd_export(args: argparse.Namespace) -> None:
    from output.export_report import export_all, export_csv, export_markdown

    if args.format == "csv":
        export_csv()
    elif args.format == "md":
        export_markdown()
    else:
        csv_path, md_path = export_all()
        print(f"CSV: {csv_path}")
        print(f"Markdown: {md_path}")


def cmd_run(args: argparse.Namespace) -> None:
    """Safe end-to-end workflow: import/analyze/messages/export (no scrape)."""
    from analyzer.classify_profiles import analyze_all_pending
    from analyzer.generate_messages import generate_for_top_candidates
    from output.export_report import export_all
    from safety.guards import print_safety_banner

    print_safety_banner()

    if args.import_file:
        from importer.import_profiles import import_profiles
        import_profiles(args.import_file)

    print("\n[1/3] Analyzing profiles...")
    analyze_all_pending(use_llm=not args.no_llm, limit=args.analyze_limit)

    print("\n[2/3] Generating draft messages (approval required)...")
    generate_for_top_candidates(limit=args.message_limit, min_score=args.min_score)

    print("\n[3/3] Exporting review files...")
    export_all()

    print("\nDone. Review output/weekly_review_*.md then open dashboard:")
    print("  python copilot.py dashboard")


def cmd_login(args: argparse.Namespace) -> None:
    from safety.guards import print_safety_banner
    from scraper.login import create_authenticated_context

    print_safety_banner()
    print("Login runs locally on YOUR machine only. Credentials never go to GitHub.\n")

    browser, context = create_authenticated_context(
        headless=args.headless, force_login=args.force
    )
    page = context.new_page()
    page.goto("https://www.linkedin.com/feed/")
    print(f"Session active: {page.url}")
    if not args.headless:
        input("Press Enter to close browser...")
    context.close()
    browser.close()


def cmd_scrape(args: argparse.Namespace) -> None:
    from scraper.collect_profiles import collect_profiles

    collect_profiles(
        limit=args.limit,
        headless=args.headless,
        skip_existing=not args.force,
    )


def cmd_analyze(args: argparse.Namespace) -> None:
    from analyzer.classify_profiles import analyze_all_pending

    analyze_all_pending(use_llm=not args.no_llm, limit=args.limit)


def cmd_score(args: argparse.Namespace) -> None:
    from database.db import get_connection, init_db, migrate_db, upsert_analysis, utc_now
    from analyzer.score_profiles import score_profile

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
            print(f"{profile['name']}: {result['rule_score']}")


def cmd_messages(args: argparse.Namespace) -> None:
    from analyzer.generate_messages import generate_for_top_candidates

    generate_for_top_candidates(
        limit=args.limit,
        message_type=args.type,
        min_score=args.min_score,
    )


def cmd_followups(args: argparse.Namespace) -> None:
    from analyzer.follow_up import get_pending_follow_ups, list_outreach, update_outreach_status

    if args.action == "list":
        list_outreach()
    elif args.action == "pending":
        pending = get_pending_follow_ups(days_since_contact=args.days)
        for item in pending:
            print(f"{item['name']} @ {item['company']} - last contacted {item['last_contacted_at']}")
        if not pending:
            print("No pending follow-ups.")
    elif args.action == "status":
        update_outreach_status(args.id, args.status, notes=args.notes)
        print(f"Connection {args.id} -> {args.status}")


def cmd_weekly(args: argparse.Namespace) -> None:
    from scripts.weekly_pipeline import run_weekly_pipeline

    if args.scrape:
        print("WARNING: Scraping from weekly pipeline. Keep --scrape-limit low (<=15).")
    run_weekly_pipeline(
        scrape=args.scrape,
        scrape_limit=args.scrape_limit,
        analyze_limit=args.analyze_limit,
        message_limit=args.message_limit,
        use_llm=not args.no_llm,
    )


def cmd_seed(_: argparse.Namespace) -> None:
    from scripts.seed_sample_data import seed

    seed(use_llm=False)


def cmd_llm(_: argparse.Namespace) -> None:
    from analyzer.llm_client import health_check
    import json

    print(json.dumps(health_check(), indent=2))


def cmd_sent(args: argparse.Namespace) -> None:
    from scraper.draft_in_linkedin import get_message_for_draft, mark_sent_after_user_tapped

    data = get_message_for_draft(args.id)
    mark_sent_after_user_tapped(args.id, data["connection_id"])
    print(f"Marked message {args.id} as SENT (after you tapped Send on LinkedIn).")


def cmd_draft(args: argparse.Namespace) -> None:
    from scraper.draft_in_linkedin import open_draft_in_browser

    open_draft_in_browser(args.id, wait_in_terminal=args.wait)


def cmd_dashboard(_: argparse.Namespace) -> None:
    import subprocess

    dashboard = PROJECT_ROOT / "dashboard" / "nextjs-app"
    subprocess.run(["npm", "run", "dev"], cwd=dashboard, check=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LinkedIn Networking Copilot — safe, manual-approval outreach"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize database").set_defaults(func=cmd_init)
    sub.add_parser("seed", help="Load sample data").set_defaults(func=cmd_seed)
    sub.add_parser("safety", help="Show safety limits and usage").set_defaults(func=cmd_safety)
    sub.add_parser("llm", help="Check Ollama/LM Studio connection").set_defaults(func=cmd_llm)

    imp = sub.add_parser("import", help="Import profiles from CSV/JSON (recommended)")
    imp.add_argument("--file", type=Path, help="CSV or JSON file")
    imp.add_argument("--template", action="store_true", help="Create sample CSV template")
    imp.set_defaults(func=cmd_import)

    exp = sub.add_parser("export", help="Export drafts to CSV/Markdown")
    exp.add_argument("--format", choices=["csv", "md", "all"], default="all")
    exp.set_defaults(func=cmd_export)

    run = sub.add_parser("run", help="Safe pipeline: import -> analyze -> messages -> export")
    run.add_argument("--import-file", type=Path, default=None, help="Optional CSV/JSON import first")
    run.add_argument("--no-llm", action="store_true")
    run.add_argument("--analyze-limit", type=int, default=50)
    run.add_argument("--message-limit", type=int, default=10)
    run.add_argument("--min-score", type=int, default=50)
    run.set_defaults(func=cmd_run)

    login = sub.add_parser("login", help="LinkedIn login (local only)")
    login.add_argument("--headless", action="store_true")
    login.add_argument("--force", action="store_true")
    login.set_defaults(func=cmd_login)

    scrape = sub.add_parser("scrape", help="Scrape profiles (rate-limited, use sparingly)")
    scrape.add_argument("--limit", type=int, default=10)
    scrape.add_argument("--headless", action="store_true")
    scrape.add_argument("--force", action="store_true")
    scrape.set_defaults(func=cmd_scrape)

    analyze = sub.add_parser("analyze", help="Analyze with local LLM + scoring")
    analyze.add_argument("--no-llm", action="store_true")
    analyze.add_argument("--limit", type=int, default=None)
    analyze.set_defaults(func=cmd_analyze)

    score = sub.add_parser("score", help="Rule-based scoring only")
    score.set_defaults(func=cmd_score)

    messages = sub.add_parser("messages", help="Generate DRAFT messages (you must approve)")
    messages.add_argument("--limit", type=int, default=10)
    messages.add_argument("--type", choices=["networking", "referral"], default="networking")
    messages.add_argument("--min-score", type=int, default=50)
    messages.set_defaults(func=cmd_messages)

    followups = sub.add_parser("followups", help="Track outreach follow-ups")
    followups.add_argument("action", choices=["list", "pending", "status"])
    followups.add_argument("--days", type=int, default=7)
    followups.add_argument("--id", type=int, default=None)
    followups.add_argument("--status", default=None)
    followups.add_argument("--notes", default=None)
    followups.set_defaults(func=cmd_followups)

    weekly = sub.add_parser("weekly", help="Weekly pipeline (run locally on Sunday)")
    weekly.add_argument("--scrape", action="store_true", help="Include scrape (not recommended in CI)")
    weekly.add_argument("--scrape-limit", type=int, default=10)
    weekly.add_argument("--analyze-limit", type=int, default=50)
    weekly.add_argument("--message-limit", type=int, default=10)
    weekly.add_argument("--no-llm", action="store_true")
    weekly.set_defaults(func=cmd_weekly)

    draft = sub.add_parser("draft", help="Open message pre-filled in LinkedIn (you tap Send)")
    draft.add_argument("--id", type=int, required=True)
    draft.add_argument("--wait", action="store_true", help="Wait for Enter after you tap Send")
    draft.set_defaults(func=cmd_draft)

    sent = sub.add_parser("sent", help="Mark message sent after you tapped Send on LinkedIn")
    sent.add_argument("--id", type=int, required=True)
    sent.set_defaults(func=cmd_sent)

    sub.add_parser("dashboard", help="Review & approve messages").set_defaults(func=cmd_dashboard)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "import" and not args.template and not args.file:
        parser.error("import requires --file or --template")

    args.func(args)


if __name__ == "__main__":
    main()
