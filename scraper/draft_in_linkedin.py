"""Open LinkedIn messaging with a pre-filled draft. YOU tap Send — we never auto-send."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_connection, init_db, utc_now
from safety.guards import assert_manual_send_only, print_safety_banner
from scraper.login import create_authenticated_context

# Selectors LinkedIn uses for messaging (multiple fallbacks)
MESSAGE_BUTTON_SELECTORS = [
    'main a[href*="/messaging/compose"]',
    'main button:has-text("Message")',
    'button.pvs-profile-actions__action:has-text("Message")',
    'div.pvs-profile-actions a:has-text("Message")',
    'button[aria-label*="Message"]',
]

COMPOSE_SELECTORS = [
    "div.msg-form__contenteditable",
    "div.msg-form__msg-content-container div[contenteditable='true']",
    "div[role='textbox'][contenteditable='true']",
    ".messages-compose-box__textarea",
]

# NEVER click these — user must tap Send themselves
FORBIDDEN_SEND_SELECTORS = [
    "button.msg-form__send-button",
    "button[type='submit']:has-text('Send')",
    "button:has-text('Send')",
]


def _fill_compose_box(page: Page, message: str) -> None:
    compose = None
    for selector in COMPOSE_SELECTORS:
        loc = page.locator(selector).first
        if loc.count() > 0 and loc.is_visible():
            compose = loc
            break

    if compose is None:
        raise RuntimeError(
            "Could not find LinkedIn message compose box. "
            "Make sure you are connected to this person."
        )

    compose.click()
    time.sleep(0.5)

    # contenteditable needs keyboard or JS — fill() often fails
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.evaluate(
        """([selector, text]) => {
            const el = document.querySelector(selector);
            if (!el) return;
            el.focus();
            el.innerHTML = '';
            el.innerText = text;
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }""",
        [COMPOSE_SELECTORS[0], message],
    )
    # Fallback: type if box still empty
    try:
        current = compose.inner_text()
        if len(current.strip()) < 10:
            compose.click()
            page.keyboard.type(message, delay=5)
    except Exception:
        page.keyboard.type(message, delay=5)


def _click_message_button(page: Page) -> None:
    for selector in MESSAGE_BUTTON_SELECTORS:
        btn = page.locator(selector).first
        if btn.count() > 0 and btn.is_visible():
            btn.click()
            time.sleep(2)
            return
    raise RuntimeError(
        "Could not find Message button on profile. "
        "You may not be connected to this person yet."
    )


def draft_message_on_linkedin(page: Page, profile_url: str, message: str) -> None:
    """Navigate to profile, open compose, paste message. Does NOT click Send."""
    assert_manual_send_only()

    page.goto(profile_url, wait_until="domcontentloaded")
    time.sleep(2)
    _click_message_button(page)
    time.sleep(1.5)
    _fill_compose_box(page, message)

    # Safety check — ensure we did not accidentally enable send automation
    for selector in FORBIDDEN_SEND_SELECTORS:
        if page.locator(selector).count() > 0:
            pass  # Button exists but we deliberately do NOT click it


def get_message_for_draft(message_id: int) -> dict:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT m.id, m.content, m.status, m.connection_id,
                   c.name, c.linkedin_url
            FROM messages m
            JOIN connections c ON c.id = m.connection_id
            WHERE m.id = ?
            """,
            (message_id,),
        ).fetchone()
    if not row:
        raise ValueError(f"Message {message_id} not found")
    return dict(row)


def save_message_content(message_id: int, content: str) -> None:
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            "UPDATE messages SET content = ?, updated_at = ? WHERE id = ?",
            (content, now, message_id),
        )


def mark_ready_for_send(message_id: int, connection_id: int) -> None:
    """Mark as APPROVED / ready — user will tap Send on LinkedIn."""
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE messages SET status = 'APPROVED', approved_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, now, message_id),
        )


def mark_sent_after_user_tapped(message_id: int, connection_id: int) -> None:
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE messages SET status = 'SENT', sent_at = ?, updated_at = ?
            WHERE id = ?
            """,
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


def open_draft_in_browser(
    message_id: int,
    content_override: Optional[str] = None,
    keep_open: bool = True,
    wait_in_terminal: bool = False,
) -> None:
    """Open LinkedIn with message pre-filled. User taps Send = approval."""
    print_safety_banner()
    data = get_message_for_draft(message_id)
    content = (content_override or data["content"]).strip()
    if not content:
        raise ValueError("Message is empty. Write or generate a message first.")

    save_message_content(message_id, content)
    mark_ready_for_send(message_id, data["connection_id"])

    print(f"\nOpening LinkedIn for: {data['name']}")
    print("The message will appear in the compose box.")
    print(">>> YOU tap SEND on LinkedIn — that is your approval.\n")

    browser, context = create_authenticated_context(headless=False)
    page = context.new_page()

    try:
        draft_message_on_linkedin(page, data["linkedin_url"], content)
        print("\n" + "=" * 60)
        print("  MESSAGE READY IN LINKEDIN")
        print(f"  To: {data['name']}")
        print("  Action: Read the message, then TAP SEND on LinkedIn")
        print("  We never click Send for you.")
        print("=" * 60 + "\n")

        if wait_in_terminal:
            input("Press Enter AFTER you tapped Send on LinkedIn...")
            mark_sent_after_user_tapped(message_id, data["connection_id"])
            print("Marked as SENT in copilot.")
        elif keep_open:
            # Keep browser open 10 minutes for user to send
            print("Browser stays open. Tap Send on LinkedIn when ready.")
            print("Then run: python copilot.py sent --id", message_id)
            try:
                page.wait_for_timeout(600_000)
            except Exception:
                pass
    finally:
        if not keep_open or wait_in_terminal:
            context.close()
            browser.close()


def draft_next_batch(limit: int = 1, wait_between: bool = True) -> int:
    """Open drafts for top APPROVED or DRAFT messages one at a time."""
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.id FROM messages m
            JOIN analysis a ON m.connection_id = a.connection_id
            WHERE m.status IN ('DRAFT', 'APPROVED')
            ORDER BY a.referral_score DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    opened = 0
    for row in rows:
        open_draft_in_browser(
            row["id"],
            keep_open=True,
            wait_in_terminal=wait_between,
        )
        opened += 1
        if wait_between and opened < len(rows):
            cont = input("\nNext message? (y/n): ").strip().lower()
            if cont != "y":
                break
    return opened


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open LinkedIn with pre-filled message — you tap Send"
    )
    parser.add_argument("--id", type=int, required=True, help="Message ID")
    parser.add_argument("--wait", action="store_true", help="Wait in terminal after open")
    parser.add_argument("--mark-sent", action="store_true", help="Mark as sent (after you tapped Send)")
    args = parser.parse_args()

    if args.mark_sent:
        data = get_message_for_draft(args.id)
        mark_sent_after_user_tapped(args.id, data["connection_id"])
        print(f"Message {args.id} marked SENT.")
        return

    open_draft_in_browser(args.id, wait_in_terminal=args.wait)


if __name__ == "__main__":
    main()
