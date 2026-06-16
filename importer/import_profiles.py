"""Import LinkedIn profiles from CSV or JSON — safest collection method."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_connection, init_db, upsert_connection

PROFILE_FIELDS = [
    "name", "headline", "company", "role", "location",
    "education", "about", "experience", "skills", "mutual_connections",
]

SAMPLE_CSV = PROJECT_ROOT / "data" / "sample_import.csv"


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    linkedin_url = (
        row.get("linkedin_url")
        or row.get("url")
        or row.get("profile_url")
        or f"https://www.linkedin.com/in/imported-{row.get('name','unknown').lower().replace(' ', '-')}"
    )
    profile = {field: str(row.get(field, "") or "").strip() for field in PROFILE_FIELDS}
    profile["linkedin_url"] = linkedin_url.strip()
    profile["name"] = profile["name"] or "Unknown"
    profile["scraped_at"] = now

    if not profile["role"] and profile["headline"]:
        from scraper.collect_profiles import _parse_headline
        role, company = _parse_headline(profile["headline"])
        profile["role"] = profile["role"] or role
        profile["company"] = profile["company"] or company

    return profile


def import_csv(path: Path) -> int:
    init_db()
    saved = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with get_connection() as conn:
        for row in rows:
            profile = _normalize_row(row)
            upsert_connection(conn, profile)
            saved += 1
            print(f"  Imported: {profile['name']}")

    print(f"Imported {saved} profiles from {path}")
    return saved


def import_json(path: Path) -> int:
    init_db()
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("profiles", data.get("connections", [data]))

    saved = 0
    with get_connection() as conn:
        for row in data:
            profile = _normalize_row(row)
            upsert_connection(conn, profile)
            saved += 1
            print(f"  Imported: {profile['name']}")

    print(f"Imported {saved} profiles from {path}")
    return saved


def import_profiles(path: Path) -> int:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return import_csv(path)
    if suffix == ".json":
        return import_json(path)
    raise ValueError(f"Unsupported format: {suffix}. Use .csv or .json")


def create_sample_template() -> Path:
    SAMPLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not SAMPLE_CSV.exists():
        SAMPLE_CSV.write_text(
            "name,headline,company,role,location,education,about,experience,skills,linkedin_url\n"
            "John Doe,Senior Data Engineer at Amazon,Amazon,Senior Data Engineer,Seattle WA,"
            "University at Buffalo,Building data pipelines at scale,Amazon - 3 yrs,Python Spark SQL,"
            "https://www.linkedin.com/in/john-doe\n",
            encoding="utf-8",
        )
    return SAMPLE_CSV


def main() -> None:
    parser = argparse.ArgumentParser(description="Import profiles from CSV/JSON (safest method)")
    parser.add_argument("--file", type=Path, required=True, help="Path to CSV or JSON file")
    parser.add_argument("--template", action="store_true", help="Create sample CSV template")
    args = parser.parse_args()

    if args.template:
        path = create_sample_template()
        print(f"Sample template created: {path}")
        return

    import_profiles(args.file)


if __name__ == "__main__":
    main()
