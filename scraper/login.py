"""LinkedIn login and session management via Playwright."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTH_DIR = PROJECT_ROOT / "playwright" / ".auth"
SESSION_FILE = AUTH_DIR / "linkedin_session.json"

load_dotenv(PROJECT_ROOT / ".env")


def get_credentials() -> tuple[str, str]:
    email = os.getenv("LINKEDIN_EMAIL", "")
    password = os.getenv("LINKEDIN_PASSWORD", "")
    if not email or not password:
        raise ValueError(
            "Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env before running the scraper."
        )
    return email, password


def login(page: Page, email: str, password: str) -> None:
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
    page.fill('input[name="session_key"]', email)
    page.fill('input[name="session_password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url("https://www.linkedin.com/feed/**", timeout=60000)


def create_authenticated_context(
    headless: bool = False,
    force_login: bool = False,
) -> tuple[Browser, BrowserContext]:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)

    if SESSION_FILE.exists() and not force_login:
        context = browser.new_context(storage_state=str(SESSION_FILE))
        page = context.new_page()
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        if "login" in page.url:
            email, password = get_credentials()
            login(page, email, password)
            context.storage_state(path=str(SESSION_FILE))
        page.close()
        return browser, context

    email, password = get_credentials()
    context = browser.new_context()
    page = context.new_page()
    login(page, email, password)
    context.storage_state(path=str(SESSION_FILE))
    page.close()
    return browser, context


def main() -> None:
    force = "--force" in sys.argv
    browser, context = create_authenticated_context(headless=False, force_login=force)
    page = context.new_page()
    page.goto("https://www.linkedin.com/mynetwork/invite-connect/connections/")
    print(f"Logged in successfully. Current URL: {page.url}")
    input("Press Enter to close the browser...")
    context.close()
    browser.close()


if __name__ == "__main__":
    main()
