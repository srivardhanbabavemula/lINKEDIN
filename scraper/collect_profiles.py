"""Collect LinkedIn connection profiles and store them in SQLite."""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from playwright.sync_api import Page

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_connection, init_db, upsert_connection
from scraper.login import create_authenticated_context

import config

CONNECTIONS_URL = "https://www.linkedin.com/mynetwork/invite-connect/connections/"


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _parse_headline(headline: str) -> tuple[str, str]:
    """Extract role and company from a LinkedIn headline."""
    headline = _clean_text(headline)
    if not headline:
        return "", ""

    at_match = re.search(r"\bat\b\s+(.+)$", headline, re.IGNORECASE)
    if at_match:
        role = _clean_text(headline[: at_match.start()])
        company = _clean_text(at_match.group(1))
        return role, company

    pipe_parts = [p.strip() for p in headline.split("|") if p.strip()]
    if len(pipe_parts) >= 2:
        return pipe_parts[0], pipe_parts[1]

    return headline, ""


def _scroll_connections_list(page: Page, max_scrolls: int = 30) -> None:
    previous_height = 0
    for _ in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)
        current_height = page.evaluate("document.body.scrollHeight")
        if current_height == previous_height:
            break
        previous_height = current_height


def collect_connection_links(page: Page, limit: Optional[int] = None) -> list[dict[str, str]]:
    page.goto(CONNECTIONS_URL, wait_until="domcontentloaded")
    time.sleep(2)
    _scroll_connections_list(page)

    cards = page.locator("li.mn-connection-card, div.mn-connection-card")
    count = cards.count()
    results: list[dict[str, str]] = []

    for i in range(count):
        card = cards.nth(i)
        link = card.locator('a[href*="/in/"]').first
        if link.count() == 0:
            continue

        href = link.get_attribute("href") or ""
        if "/in/" not in href:
            continue

        profile_url = urljoin("https://www.linkedin.com", href.split("?")[0])
        name = _clean_text(link.inner_text())
        headline = ""
        headline_el = card.locator("span.mn-connection-card__occupation, div.entity-result__primary-subtitle")
        if headline_el.count() > 0:
            headline = _clean_text(headline_el.first.inner_text())

        if name and profile_url:
            results.append(
                {
                    "name": name,
                    "headline": headline,
                    "linkedin_url": profile_url,
                }
            )

        if limit and len(results) >= limit:
            break

    # Deduplicate by URL
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in results:
        if item["linkedin_url"] not in seen:
            seen.add(item["linkedin_url"])
            unique.append(item)
    return unique


def scrape_profile_details(page: Page, profile_url: str) -> dict[str, Any]:
    page.goto(profile_url, wait_until="domcontentloaded")
    time.sleep(2)

    name = ""
    headline = ""
    location = ""
    about = ""
    education = ""
    experience = ""
    skills = ""
    mutual_connections = ""

    name_el = page.locator("h1").first
    if name_el.count() > 0:
        name = _clean_text(name_el.inner_text())

    headline_el = page.locator("div.text-body-medium, div.pv-text-details__left-panel div.text-body-medium")
    if headline_el.count() > 0:
        headline = _clean_text(headline_el.first.inner_text())

    location_el = page.locator("span.text-body-small.inline.t-black--light.break-words")
    if location_el.count() > 0:
        location = _clean_text(location_el.first.inner_text())

    about_section = page.locator("#about ~ div.display-flex, section.pv-about-section")
    if about_section.count() > 0:
        about = _clean_text(about_section.first.inner_text())[:2000]

    edu_section = page.locator("#education ~ div, section#education")
    if edu_section.count() > 0:
        education = _clean_text(edu_section.first.inner_text())[:1500]

    exp_section = page.locator("#experience ~ div, section#experience")
    if exp_section.count() > 0:
        experience = _clean_text(exp_section.first.inner_text())[:2000]

    skills_section = page.locator("#skills ~ div, section#skills")
    if skills_section.count() > 0:
        skills = _clean_text(skills_section.first.inner_text())[:1000]

    mutual_el = page.locator("a[href*='facetConnectionOf'], span:has-text('mutual connection')")
    if mutual_el.count() > 0:
        mutual_connections = _clean_text(mutual_el.first.inner_text())

    role, company = _parse_headline(headline)

    return {
        "linkedin_url": profile_url,
        "name": name,
        "headline": headline,
        "company": company,
        "role": role,
        "location": location,
        "education": education,
        "about": about,
        "experience": experience,
        "skills": skills,
        "mutual_connections": mutual_connections,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def collect_profiles(
    limit: Optional[int] = None,
    headless: bool = True,
    skip_existing: bool = True,
) -> int:
    from safety.guards import (
        SafetyError,
        enforce_scrape_limit,
        print_safety_banner,
        record_scrape,
    )

    print_safety_banner()

    try:
        safe_limit = enforce_scrape_limit(limit)
    except SafetyError as exc:
        print(f"SCRAPE BLOCKED: {exc}")
        return 0

    if limit is not None and safe_limit < limit:
        print(f"Limit clamped to {safe_limit} for account safety.")

    init_db()
    browser, context = create_authenticated_context(headless=headless)
    page = context.new_page()
    saved = 0

    try:
        connections = collect_connection_links(page, limit=safe_limit)
        print(f"Found {len(connections)} connections to process.")

        with get_connection() as conn:
            existing_urls: set[str] = set()
            if skip_existing:
                rows = conn.execute("SELECT linkedin_url FROM connections").fetchall()
                existing_urls = {row["linkedin_url"] for row in rows}

        for idx, connection in enumerate(connections, start=1):
            url = connection["linkedin_url"]
            if skip_existing and url in existing_urls:
                print(f"[{idx}/{len(connections)}] Skipping existing: {connection['name']}")
                continue

            print(f"[{idx}/{len(connections)}] Scraping: {connection['name']}")
            try:
                profile = scrape_profile_details(page, url)
                if not profile.get("name"):
                    profile["name"] = connection["name"]
                if not profile.get("headline"):
                    profile["headline"] = connection.get("headline", "")

                with get_connection() as conn:
                    upsert_connection(conn, profile)
                saved += 1
                time.sleep(config.SCRAPE_DELAY_SECONDS)
            except Exception as exc:
                print(f"  Error scraping {url}: {exc}")

    finally:
        context.close()
        browser.close()

    if saved > 0:
        record_scrape(saved)

    print(f"Saved {saved} profiles to database.")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect LinkedIn connection profiles")
    parser.add_argument("--limit", type=int, default=None, help="Max profiles to collect")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--force-rescrape", action="store_true", help="Re-scrape existing profiles")
    args = parser.parse_args()

    collect_profiles(
        limit=args.limit,
        headless=args.headless,
        skip_existing=not args.force_rescrape,
    )


if __name__ == "__main__":
    main()
