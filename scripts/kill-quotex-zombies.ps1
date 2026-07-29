$procs = Get-CimInstance Win32_Process | Where-Object { ($_.Name -match 'python') -and ($_.CommandLine -match 'QUOTEX') }
foreach ($p in $procs) {
  Write-Host "KILL $($p.ProcessId) :: $($p.CommandLine.Substring(0, [Math]::Min(120, $p.CommandLine.Length)))"
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
if (-not $procs) { Write-Host "SIN ZOMBIS" }
