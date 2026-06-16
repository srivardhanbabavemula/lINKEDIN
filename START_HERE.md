# START HERE — What To Do Now

Your workflow is simple:

```
Copilot analyzes your network → drafts message in LinkedIn → YOU tap Send
```

**We never click Send for you.** Tapping Send on LinkedIn = your approval.

---

## Step 1 — One-time setup (5 minutes)

Open PowerShell in the project folder:

```powershell
cd E:\LINKEDIN\linkedin-copilot
.\setup.ps1
```

Edit `.env` with your name and school (LinkedIn email/password only needed for login).

---

## Step 2 — Log in to LinkedIn (once)

```powershell
.venv\Scripts\activate
python copilot.py login
```

A browser opens. Log in. Session is saved on your laptop only.

---

## Step 3 — Load your network

**Option A — Safest:** export connections to CSV and import:

```powershell
python copilot.py import --template
# Fill data/sample_import.csv with your connections, then:
python copilot.py import --file data/sample_import.csv
```

**Option B — Small scrape (max 10 at a time):**

```powershell
python copilot.py scrape --limit 10
```

---

## Step 4 — Analyze & generate messages

```powershell
python copilot.py run --no-llm
```

This scores your network and creates personalized draft messages for top contacts.

---

## Step 5 — Open dashboard & send

```powershell
python copilot.py dashboard
```

Open **http://localhost:3000** → go to **Messages** tab.

For each person:

1. **Edit** the message if you want (optional)
2. Click **Open in LinkedIn** — browser opens, message is already typed in the compose box
3. Read it on LinkedIn
4. **Tap SEND on LinkedIn** — that is your approval
5. Back in dashboard, click **I Tapped Send on LinkedIn**

---

## CLI alternative (no dashboard)

```powershell
python copilot.py draft --id 1 --wait
```

Opens LinkedIn with message filled. You tap Send. Press Enter in terminal when done.

---

## Weekly routine (every Sunday)

```powershell
.\scripts\run_weekly.ps1
python copilot.py dashboard
```

Review top 5–10 messages. Open each in LinkedIn. Tap Send.

---

## Commands cheat sheet

| What you want | Command |
|---------------|---------|
| Login to LinkedIn | `python copilot.py login` |
| Import connections | `python copilot.py import --file data/sample_import.csv` |
| Score + generate messages | `python copilot.py run --no-llm` |
| Open dashboard | `python copilot.py dashboard` |
| Open one message in LinkedIn | `python copilot.py draft --id 1` |
| Mark sent after you tapped Send | `python copilot.py sent --id 1` |
| Check safety limits | `python copilot.py safety` |

---

## Important

- **Tap Send on LinkedIn = your approval.** The bot only fills the draft.
- **Max 10 messages per week** — quality over quantity.
- **Never put LinkedIn password in GitHub.**

Read [SAFETY.md](SAFETY.md) for full details.
