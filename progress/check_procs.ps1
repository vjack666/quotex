$p = Get-CimInstance Win32_Process -Filter "Name='python.exe'"
$q = $p | Where-Object { $_.CommandLine -like '*QUOTEX*' }
if ($q) { foreach ($x in $q) { Write-Host "QUOTEX PID $($x.ProcessLine): $($x.CommandLine)" } }
else { Write-Host "NO HAY PROC QUOTEX" }
$w = $p | Where-Object { $_.CommandLine -like '*watchdog*' }
if ($w) { foreach ($x in $w) { Write-Host "WATCHDOG PID $($x.ProcessId): $($x.CommandLine)" } }
else { Write-Host "NO HAY WATCHDOG" }
