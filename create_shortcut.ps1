# Creates a desktop shortcut for QUOTEX Web App
$desktop = [Environment]::GetFolderPath("Desktop")
$target = Join-Path $PSScriptRoot "start_webapp.bat"
$shortcutPath = Join-Path $desktop "QUOTEX Web App.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "QUOTEX Trading Bot - Web Dashboard"
$shortcut.WindowStyle = 1  # Normal window
$shortcut.Save()

Write-Host "Shortcut created: $shortcutPath"
