#Requires -Version 5.1
# Apaga hub + bot QUOTEX y libera el puerto (sin tocar otros Python del sistema).
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Port = 8080

Write-Host "[QUOTEX] Deteniendo..."

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -and (
            $_.ExecutablePath -like "*\Desktop\QUOTEX\.venv\Scripts\python*" -or
            $_.ExecutablePath -like "*\QUOTEX\.venv\Scripts\python*"
        )
    } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "  python PID $($_.ProcessId)"
    }

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*quotex_hub_edge*" } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

try {
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object {
            $p = Get-CimInstance Win32_Process -Filter "ProcessId=$_" -ErrorAction SilentlyContinue
            if ($p -and ($p.ExecutablePath -like "*\QUOTEX\*" -or $p.CommandLine -like "*app.py*")) {
                Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
            }
        }
} catch { }

$lock = Join-Path $Root "runtime\main.lock"
if (Test-Path $lock) { Remove-Item $lock -Force -ErrorAction SilentlyContinue }

Write-Host "[QUOTEX] Listo. Puerto $Port liberado."
