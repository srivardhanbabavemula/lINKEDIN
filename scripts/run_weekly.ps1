# SAFE weekly pipeline — run on YOUR laptop every Sunday
# Does NOT scrape LinkedIn. Does NOT use GitHub credentials.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "LinkedIn Copilot — Local Weekly Run (Safe Mode)" -ForegroundColor Cyan
Write-Host "No scraping. No auto-send. Manual approval required.`n"

& .\.venv\Scripts\python copilot.py weekly --no-llm --message-limit 10

Write-Host "`nOpen dashboard to approve messages:" -ForegroundColor Green
Write-Host "  python copilot.py dashboard"
