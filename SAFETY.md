# Account Safety Policy

This copilot is designed to **protect your LinkedIn account** while helping you network for internships.

## What we NEVER do

- **Never auto-send messages** — `AUTO_SEND_ENABLED` is hardcoded to `False`
- **Never run 24/7 bots** — no continuous scraping
- **Never store LinkedIn credentials in GitHub** — login runs locally only
- **Never scrape from GitHub Actions** — CI only tests with sample data

## What we DO

1. **Manual import (recommended)** — paste profiles from CSV/JSON
2. **Small-batch scraping (optional)** — max 15/session, 25/day, 3s delay
3. **Draft messages only** — status starts as `DRAFT`
4. **Your approval required** — must click Approve in dashboard
5. **You copy and send** — paste message on LinkedIn yourself
6. **You confirm sent** — click "I Sent This on LinkedIn" after manual send

## Approval workflow

```
DRAFT  →  [You review & edit]  →  APPROVED  →  [You copy]  →  [You paste on LinkedIn]  →  SENT
```

The system blocks `DRAFT → SENT` skips. Copy is disabled until approved.

## Rate limits (configurable in `.env`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `MAX_SCRAPE_PER_SESSION` | 15 | Profiles per scrape run |
| `MAX_SCRAPE_PER_DAY` | 25 | Daily scrape cap |
| `SCRAPE_DELAY_SECONDS` | 3.0 | Delay between profile visits |
| `WEEKLY_MESSAGE_LIMIT` | 10 | Max drafts per week |

Check limits: `python copilot.py safety`

## Recommended safe workflow

```powershell
# Best: import profiles you collected manually
python copilot.py import --file data/sample_import.csv

# Or small scrape (once, locally)
python copilot.py login
python copilot.py scrape --limit 10

# Analyze, generate drafts, export for review
python copilot.py run --no-llm

# Approve in dashboard, copy, send manually
python copilot.py dashboard
```

## GitHub Actions

The included workflow (`weekly.yml`) only:
- Seeds sample data
- Runs analysis without LinkedIn login
- Uploads CSV/Markdown reports as artifacts

**Do not add `LINKEDIN_EMAIL` or `LINKEDIN_PASSWORD` to GitHub Secrets.**

## If LinkedIn shows a security check

Stop scraping immediately. Switch to manual import:

```powershell
python copilot.py import --template
# Fill in data/sample_import.csv with profiles you copy manually
python copilot.py import --file data/sample_import.csv
```
