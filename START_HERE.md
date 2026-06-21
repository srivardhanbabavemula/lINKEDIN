# START HERE — Local Machine (Windows)

**Run on your laptop, not GitHub Codespaces.**

Full guide: **[LOCAL_SETUP.md](LOCAL_SETUP.md)**

```
Login -> Scrape network -> Generate internship messages -> Open in LinkedIn -> YOU tap Send
```

Messages ask about **internship opportunities in general** — edit `MY_TARGET_ROLE` in `.env`.

---

## Quick start

```powershell
cd E:\LINKEDIN\linkedin-copilot
.\setup.ps1
notepad .env
```

Set in `.env`:

```env
MY_TARGET_ROLE=internship opportunities
LINKEDIN_EMAIL=your-email@buffalo.edu
LINKEDIN_PASSWORD=your-password
```

Then:

```powershell
.\scripts\run_local.ps1
```

Or step by step:

```powershell
.venv\Scripts\activate
python copilot.py login
python copilot.py scrape --limit 10
python copilot.py run --no-llm
python copilot.py dashboard
```

Open **http://localhost:3000** → **Open in LinkedIn** → **tap Send**.

---

## Commands cheat sheet

| What you want | Command |
|---------------|---------|
| Full local run | `.\scripts\run_local.ps1` |
| Login to LinkedIn | `python copilot.py login` |
| Scrape connections | `python copilot.py scrape --limit 10` |
| Generate messages | `python copilot.py run --no-llm` |
| Dashboard | `python copilot.py dashboard` |
| Open in LinkedIn | `python copilot.py draft --id 1` |

Read [SAFETY.md](SAFETY.md) for account safety rules.
