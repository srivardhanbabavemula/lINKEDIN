import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    auto_send_enabled: false,
    manual_approval_required: true,
    policy: "Open in LinkedIn → message pre-filled → YOU tap Send. We never auto-send.",
    scrape_policy: "Scraping is rate-limited and runs locally only. Never put LinkedIn credentials in GitHub.",
  });
}
