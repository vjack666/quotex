# Desktop shortcut: only "QUOTEX Web App" -> start_webapp.bat (simple launcher)
$desktop = [Environment]::GetFolderPath("Desktop")
$root = $PSScriptRoot
$shell = New-Object -ComObject WScript.Shell

$startPath = Join-Path $desktop "QUOTEX Web App.lnk"
$sc = $shell.CreateShortcut($startPath)
$sc.TargetPath = Join-Path $root "start_webapp.bat"
$sc.WorkingDirectory = $root
$sc.Description = "QUOTEX Trading Bot - Web Dashboard"
$sc.WindowStyle = 1  # Normal window (see console + server)
$sc.Save()
Write-Host "Shortcut OK: $startPath"

$stopPath = Join-Path $desktop "QUOTEX Detener.lnk"
if (Test-Path -LiteralPath $stopPath) {
    Remove-Item -LiteralPath $stopPath -Force -ErrorAction SilentlyContinue
    Write-Host "Removed: $stopPath"
}
