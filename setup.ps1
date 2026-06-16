# One-command setup for Windows
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== LinkedIn Networking Copilot Setup ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\pip install -r requirements.txt -q
& .\.venv\Scripts\playwright install chromium

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env - edit with your profile (LinkedIn creds optional)" -ForegroundColor Yellow
}

& .\.venv\Scripts\python copilot.py init
& .\.venv\Scripts\python copilot.py seed

Push-Location dashboard\nextjs-app
npm install
Pop-Location

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "SAFE workflow (recommended):" -ForegroundColor Cyan
Write-Host "  python copilot.py import --template"
Write-Host "  python copilot.py run --import-file data/sample_import.csv --no-llm"
Write-Host "  python copilot.py dashboard"
Write-Host ""
Write-Host "Check safety limits:" -ForegroundColor Cyan
Write-Host "  python copilot.py safety"
Write-Host ""
Write-Host "Read SAFETY.md before any scraping." -ForegroundColor Yellow
