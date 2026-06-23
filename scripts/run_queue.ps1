# LinkedIn Copilot — 30 message queue (local Windows)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host ""
Write-Host "=== LinkedIn Copilot - 30 Message Queue ===" -ForegroundColor Cyan
Write-Host ""

& .\.venv\Scripts\Activate.ps1

Write-Host "Commands to run in this session:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. python copilot.py login --manual"
Write-Host "  2. python copilot.py scrape --limit 30"
Write-Host "  3. python copilot.py score"
Write-Host "  4. python copilot.py queue build --limit 30"
Write-Host "  5. python copilot.py queue list"
Write-Host ""
Write-Host "  Repeat for each message (up to 30):" -ForegroundColor Green
Write-Host "    python copilot.py queue next"
Write-Host "    (tap SEND on LinkedIn)"
Write-Host "    python copilot.py queue done"
Write-Host ""

$step = Read-Host "Run full setup now? (y/n)"
if ($step -eq "y") {
    python copilot.py init
    python copilot.py login --manual
    python copilot.py scrape --limit 30
    python copilot.py score
    python copilot.py queue build --limit 30
    python copilot.py queue list
}
