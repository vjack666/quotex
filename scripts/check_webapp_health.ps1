[CmdletBinding()]
param()

$ErrorActionPreference = 'SilentlyContinue'
$log = Join-Path $PSScriptRoot '..\runtime\webapp_watchdog.log'
$url = 'http://127.0.0.1:8080/'
$ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

function Write-Log([string]$msg) {
  "$ts $msg" | Out-File -FilePath $log -Append -Encoding utf8
}

try {
  $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
  if ($r.StatusCode -eq 200) {
    Write-Log "OK status=$($r.StatusCode)"
    exit 0
  }
  Write-Log "BAD status=$($r.StatusCode)"
  exit 1
} catch {
  Write-Log "DOWN $($_.Exception.Message)"
  exit 2
}
