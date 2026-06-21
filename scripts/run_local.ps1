# LinkedIn Copilot — run on YOUR laptop (local machine)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host ""
Write-Host "=== LinkedIn Copilot - Local Run ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".venv")) {
    Write-Host "Run setup first: .\setup.ps1" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env — edit MY_NAME, MY_TARGET_ROLE=internship opportunities" -ForegroundColor Yellow
    notepad .env
    Write-Host "Save .env and run this script again."
    exit 0
}

& .\.venv\Scripts\Activate.ps1

Write-Host "Step 1: Re-score network and generate internship messages..." -ForegroundColor Green
python copilot.py score
python copilot.py messages --limit 10

Write-Host ""
Write-Host "Step 2: Starting dashboard at http://localhost:3000" -ForegroundColor Green
Write-Host "  -> Messages tab -> Open in LinkedIn -> YOU tap Send" -ForegroundColor Yellow
Write-Host ""

Set-Location dashboard\nextjs-app
npm run dev
