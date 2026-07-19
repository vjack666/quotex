#Requires -Version 5.1
# Single process: this PowerShell hosts python app.py only.
# Hub browser is opened by app.py (no second waiter window).
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Port = 8080
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$App = Join-Path $Root "app.py"
$Url = "http://127.0.0.1:$Port/"
$Waiter = Join-Path $Root "scripts\open_hub_when_ready.ps1"
$Cleanup = Join-Path $Root "scripts\cleanup_webapp_orphans.ps1"

function Test-Healthy {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/bot/status" -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-Path $Py)) { throw "Missing venv: $Py" }
if (-not (Test-Path $App)) { throw "Missing app.py" }

if (Test-Healthy) {
    Write-Host "[QUOTEX] Already running. Opening dashboard..."
    if (Test-Path $Waiter) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $Waiter -Port $Port -MaxAttempts 3
    }
    exit 0
}

if (Test-Path $Cleanup) {
    Write-Host "[QUOTEX] Cleaning orphans..."
    & powershell -NoProfile -ExecutionPolicy Bypass -File $Cleanup
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  QUOTEX Web App - single process"
Write-Host "  $Url"
Write-Host "  This window = python app.py only"
Write-Host "  Hub opens from app.py when ready"
Write-Host "  Ctrl+C or close this window to stop"
Write-Host "============================================================"
Write-Host ""

# No Start-Process waiter. One process: python in this shell.
& $Py $App --port $Port
$rc = $LASTEXITCODE
Write-Host "[QUOTEX] Server exited (code $rc)."
if ($rc -ne 0) {
    Write-Host "Tip: run stop_webapp.bat then start_webapp.bat once."
}
exit $rc
