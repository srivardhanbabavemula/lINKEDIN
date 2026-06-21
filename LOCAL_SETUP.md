# Run on Your Local Machine (Windows)

Everything runs on **your laptop** — LinkedIn login, scraping, Open in LinkedIn, and Send.

---

## One-time setup

Open **PowerShell** in the project folder:

```powershell
cd E:\LINKEDIN\linkedin-copilot
.\setup.ps1
```

Edit `.env`:

```powershell
notepad .env
```

Set these (internship = general, not one specific role):

```env
MY_NAME=Srivardhan
MY_SCHOOL=University at Buffalo
MY_DEGREE=MS in Data Science
MY_TARGET_ROLE=internship opportunities
LINKEDIN_EMAIL=srivardh@buffalo.edu
LINKEDIN_PASSWORD=your-password-here
```

---

## Every time you use it

```powershell
cd E:\LINKEDIN\linkedin-copilot
.venv\Scripts\activate
```

Or run the all-in-one script:

```powershell
.\scripts\run_local.ps1
```

---

## Full local workflow

### 1. Log in to LinkedIn (once)

```powershell
python copilot.py login
```

Browser opens → log in → press Enter in terminal.

### 2. Load your network

```powershell
python copilot.py scrape --limit 10
```

Or import CSV:

```powershell
python copilot.py import --file data\sample_import.csv
```

### 3. Score network & generate messages

```powershell
python copilot.py run --no-llm
```

Messages ask about **internships in general**, not one specific role.

### 4. Open dashboard

```powershell
python copilot.py dashboard
```

Open **http://localhost:3000** → **Messages** tab.

### 5. Send (you tap Send = approval)

1. Click **Open in LinkedIn** — message appears in LinkedIn compose box
2. Read and edit if needed
3. **Tap SEND on LinkedIn**
4. Click **I Tapped Send on LinkedIn** in dashboard

---

## Quick commands

| Action | Command |
|--------|---------|
| Full local run | `.\scripts\run_local.ps1` |
| Login | `python copilot.py login` |
| Scrape 10 connections | `python copilot.py scrape --limit 10` |
| Generate messages | `python copilot.py messages --limit 10` |
| Open in LinkedIn (CLI) | `python copilot.py draft --id 1` |
| Dashboard | `python copilot.py dashboard` |

---

## Optional: Ollama for smarter messages

```powershell
ollama pull qwen2.5:7b
python copilot.py run
```

(without `--no-llm`)

---

## Not for GitHub Codespaces

Use your **local machine** for LinkedIn. Codespaces is only for reviewing exported CSV files.

See [START_HERE.md](START_HERE.md) for more detail.
