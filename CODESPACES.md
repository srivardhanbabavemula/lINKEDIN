# Running in GitHub Codespaces

You are in the **cloud** — great for analyzing data and reviewing messages.  
**LinkedIn login and "Open in LinkedIn" only work on your laptop.**

---

## Step 1 — Setup (first time only)

In the **Terminal** at the bottom:

```bash
bash scripts/setup.sh
```

Or if the devcontainer already ran setup:

```bash
source .venv/bin/activate
```

---

## Step 2 — Configure your profile

Edit `.env` in the **project root** (not inside `scripts/`):

```bash
nano .env
```

Set at minimum:

```env
MY_NAME=Your Name
MY_SCHOOL=University at Buffalo
MY_DEGREE=MS in Data Science
MY_TARGET_ROLE=Data Engineering internships
```

You do **not** need LinkedIn email/password in Codespaces.

---

## Step 3 — Load connections & generate messages

```bash
source .venv/bin/activate
python copilot.py import --template
# Edit data/sample_import.csv with your connections, then:
python copilot.py run --import-file data/sample_import.csv --no-llm
```

Or use sample data to try it:

```bash
python copilot.py seed
python copilot.py run --no-llm
```

---

## Step 4 — Open the dashboard

```bash
cd dashboard/nextjs-app
npm run dev
```

1. Click the **PORTS** tab (next to TERMINAL)
2. Find port **3000**
3. Click the **globe icon** to open the dashboard in your browser

---

## What works in Codespaces vs your laptop

| Feature | Codespaces | Your laptop |
|---------|------------|-------------|
| Import CSV | Yes | Yes |
| Score & analyze network | Yes | Yes |
| Generate draft messages | Yes | Yes |
| Dashboard (review messages) | Yes | Yes |
| Export CSV / Markdown | Yes | Yes |
| LinkedIn login | No | Yes |
| Scrape connections | No | Yes (small batches) |
| Open in LinkedIn (pre-fill) | No | Yes |

---

## Recommended workflow

```text
Codespaces (cloud)          Your laptop
─────────────────          ────────────
Import CSV                 python copilot.py login
Analyze & generate    →    python copilot.py dashboard
Export / review drafts     Open in LinkedIn → tap Send
```

---

## Quick commands

```bash
source .venv/bin/activate
python copilot.py safety
python copilot.py export
python copilot.py dashboard   # from project root
```

---

## `.env` location

Put `.env` here:

```text
/workspaces/lINKEDIN/.env
```

**Not** in `scripts/.env`.
