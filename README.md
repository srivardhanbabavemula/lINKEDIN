# LinkedIn Networking Copilot

**Safe, free, manual-approval networking for Data Engineering internships.**

Collect profiles → score with local AI → generate draft messages → **you approve** → copy → send manually on LinkedIn.

## Core safety guarantees

| Guarantee | How |
|-----------|-----|
| No auto-send | Hardcoded `AUTO_SEND_ENABLED = False` |
| Manual approval | Dashboard blocks Copy until Approved, blocks Sent until Approved |
| Rate-limited scraping | Max 15/session, 25/day, 3s delays |
| No GitHub credentials | LinkedIn login runs on your laptop only |
| Free stack | Python, SQLite, Ollama/LM Studio, Next.js |

Read [SAFETY.md](SAFETY.md) for full policy.

---

## Architecture (free, laptop-first)

```text
Your Laptop
    ↓
Import CSV  OR  Small Playwright scrape (optional)
    ↓
SQLite
    ↓
Ollama / LM Studio / Qwen (free local AI)
    ↓
Score + Rank (UB alumni, recruiters, target companies)
    ↓
Generate DRAFT messages
    ↓
Dashboard / CSV / Markdown — YOU approve
    ↓
Copy → Paste on LinkedIn manually
```

---

## Quick start

```powershell
cd linkedin-copilot
.\setup.ps1

# Safest path: import profiles manually
python copilot.py import --template
# Edit data/sample_import.csv, then:
python copilot.py run --import-file data/sample_import.csv --no-llm

# Review & approve every message
python copilot.py dashboard
```

Open **http://localhost:3000**

---

## Recommended workflow (account-safe)

### Step 1 — Collect profiles (choose one)

**Option A: Manual import (safest)**
```powershell
python copilot.py import --file data/sample_import.csv
```

**Option B: Small scrape (local only, rate-limited)**
```powershell
python copilot.py login          # saves session locally
python copilot.py scrape --limit 10
python copilot.py safety         # check daily limits
```

### Step 2 — Analyze & score
```powershell
ollama pull qwen2.5:7b           # free local AI
python copilot.py analyze        # or --no-llm for rules only
```

### Step 3 — Generate drafts (max 10/week)
```powershell
python copilot.py messages --limit 10
```

### Step 4 — Review, approve, send manually
```powershell
python copilot.py export         # CSV + Markdown in output/
python copilot.py dashboard
```

**In dashboard:** Edit → **Approve** → **Copy** → paste on LinkedIn → **I Sent This on LinkedIn**

---

## Unified CLI

```powershell
python copilot.py init              # Database setup
python copilot.py seed              # Sample data
python copilot.py safety            # Rate limits & policy
python copilot.py import --file X   # CSV/JSON import (recommended)
python copilot.py run               # Full safe pipeline
python copilot.py analyze           # Local LLM analysis
python copilot.py messages          # Generate DRAFTS only
python copilot.py export            # output/outreach_drafts.csv + .md
python copilot.py followups list    # Track responses
python copilot.py weekly            # Sunday pipeline (local)
python copilot.py dashboard         # Approval UI
```

---

## Scoring priorities

1. **UB alumni** (+30)
2. **Data Engineers at target companies** (Amazon, Microsoft, Meta +20 role)
3. **Recruiters** (university recruiter +25, technical +18)
4. **Job matches** (+15 if company has opening in `data/target_jobs.json`)
5. **Hyderabad / Telangana / same degree** alumni affinity

---

## Output files

| File | Contents |
|------|----------|
| `output/outreach_drafts.csv` | Name, Company, Score, Message |
| `output/weekly_review_*.md` | Top 10 with checkboxes for review |
| `reports/weekly.csv` | Latest weekly report |

---

## Weekly automation

**Run locally every Sunday** (not on GitHub with credentials):

```powershell
.\scripts\run_weekly.ps1
```

GitHub Actions (`weekly.yml`) only validates the pipeline with sample data — **no LinkedIn login**.

---

## Project structure

```
linkedin-copilot/
├── copilot.py              # Unified CLI
├── config.py               # Settings + safety limits
├── SAFETY.md               # Account protection policy
├── safety/                 # Rate limits, approval guards
├── importer/               # CSV/JSON import (safest)
├── scraper/                # Optional Playwright (rate-limited)
├── analyzer/               # LLM, scoring, messages, follow-ups
├── output/                 # CSV + Markdown exports
├── dashboard/nextjs-app/   # Approval dashboard
├── data/target_jobs.json   # Job matching config
└── .github/workflows/      # Safe CI only (no credentials)
```

---

## LLM providers (free)

| Provider | Setup |
|----------|-------|
| **Ollama** | `ollama pull qwen2.5:7b` — set `LLM_PROVIDER=ollama` |
| **LM Studio** | Start local server — set `LLM_PROVIDER=lmstudio` |

Check: `python copilot.py llm`

---

## License

MIT
