#Requires -Version 5.1
# Wait until QUOTEX hub API is healthy, then open one Edge app window.
param(
    [int]$Port = 8080,
    [int]$MaxAttempts = 60,
    [int]$DelayMs = 500
)

$ErrorActionPreference = "Continue"
$statusUrl = "http://127.0.0.1:$Port/api/bot/status"
$hubUrl = "http://127.0.0.1:$Port/"

$ok = $false
for ($i = 0; $i -lt $MaxAttempts; $i++) {
    try {
        Invoke-WebRequest -Uri $statusUrl -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ok = $true
        break
    } catch {
        Start-Sleep -Milliseconds $DelayMs
    }
}

if (-not $ok) {
    Write-Host "[WARN] Hub wait: server never became healthy on port $Port"
    exit 1
}

$edge = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

$prof = Join-Path $env:TEMP "quotex_hub_edge"

if ($edge) {
    Start-Process -FilePath $edge -ArgumentList @(
        "--app=$hubUrl",
        "--user-data-dir=$prof",
        "--no-first-run",
        "--new-window"
    )
    Write-Host "[OK] Hub opened (Edge) → $hubUrl"
} else {
    Start-Process $hubUrl
    Write-Host "[OK] Hub opened (default browser) → $hubUrl"
}

exit 0
