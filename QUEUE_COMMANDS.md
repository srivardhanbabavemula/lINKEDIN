# Exact Terminal Commands — 30 Message Queue (Local Windows)

Copy-paste these in **PowerShell** on your laptop.

---

## One-time setup

```powershell
cd E:\LINKEDIN\linkedin-copilot
git pull
.\setup.ps1
notepad .env
```

In `.env` set:
```env
MY_NAME=Your Name
MY_SCHOOL=University at Buffalo
MY_TARGET_ROLE=internship opportunities
MESSAGES_PER_SESSION=30
LINKEDIN_EMAIL=your-email@buffalo.edu
LINKEDIN_PASSWORD=your-password
```

---

## Every session (30 messages)

```powershell
cd E:\LINKEDIN\linkedin-copilot
.venv\Scripts\activate
```

### Step 1 — Login (once, or when session expires)

```powershell
python copilot.py login --manual
```
Browser opens → log in to **linkedin.com** → press **Enter** in terminal.

> LinkedIn Desktop app is separate. This saves a **browser** session for drafting messages.

### Step 2 — Collect your network (max 30 this session)

```powershell
python copilot.py scrape --limit 30
```

### Step 3 — Score every profile

```powershell
python copilot.py score
```

### Step 4 — Build queue of 30 personalized messages

```powershell
python copilot.py queue build --limit 30
```

### Step 5 — Review the queue

```powershell
python copilot.py queue list
```

### Step 6 — Send loop (repeat up to 30 times)

```powershell
python copilot.py queue next
```
→ LinkedIn opens with **personal message already typed**  
→ **You read it, tap SEND** (your approval)  
→ Then:

```powershell
python copilot.py queue done
```

Repeat `queue next` → tap Send → `queue done` until all 30 are sent.

---

## Optional: dashboard review before sending

```powershell
python copilot.py dashboard
```
Open http://localhost:3000 — edit messages, then use `queue next` to send.

---

## Optional: smarter messages with Ollama

```powershell
ollama pull qwen2.5:7b
python copilot.py queue build --limit 30 --llm
```

---

## Quick reference

| Step | Command |
|------|---------|
| Login | `python copilot.py login --manual` |
| Scrape 30 | `python copilot.py scrape --limit 30` |
| Score | `python copilot.py score` |
| Build queue | `python copilot.py queue build --limit 30` |
| View queue | `python copilot.py queue list` |
| Open in LinkedIn | `python copilot.py queue next` |
| After you tapped Send | `python copilot.py queue done` |

---

## Rules

- **30 messages max per session** — review each before sending
- **We never click Send** — only you do
- **One personalized message per person** — uses their name, company, school
