#Requires -Version 5.1
# Kill all QUOTEX webapp leftovers: venv python, hub Edge, waiters, locks.
$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $Root) { $Root = (Get-Location).Path }

# 1) Project venv python (app.py / uvicorn)
Get-CimInstance Win32_Process |
    Where-Object {
        $_.ExecutablePath -and (
            $_.ExecutablePath -like "*\QUOTEX\.venv\Scripts\python*" -or
            $_.ExecutablePath -like "*\QUOTEX\.venv\Scripts\pythonw*"
        )
    } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

# 2) Any app.py still pointing at this project
Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and (
            $_.CommandLine -like "*\QUOTEX\*app.py*" -or
            ($_.CommandLine -like "*app.py*" -and $_.CommandLine -like "*QUOTEX*")
        )
    } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

# 3) Hub Edge profile tree
Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and ($_.CommandLine -like "*quotex_hub_edge*")
    } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

# 4) Leftover helper scripts
Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and (
            $_.CommandLine -like "*open_hub_when_ready.ps1*" -or
            $_.CommandLine -like "*cleanup_webapp_orphans.ps1*"
        )
    } |
    ForEach-Object {
        # Do not kill ourselves
        if ($_.ProcessId -ne $PID) {
            Stop-Process -Id $_.ProcessId -Force
        }
    }

# 5) Locks
$lockDir = Join-Path $Root "runtime"
@(
    (Join-Path $lockDir "main.lock"),
    (Join-Path $lockDir "webapp.pid")
) | ForEach-Object {
    if (Test-Path $_) { Remove-Item $_ -Force }
}

Start-Sleep -Milliseconds 300
exit 0
