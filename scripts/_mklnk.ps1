$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut('C:\Users\v_jac\Desktop\QUOTEX Web App.lnk')
$lnk.TargetPath = 'C:\Users\v_jac\Desktop\QUOTEX\scripts\launch_quotex_webapp.bat'
$lnk.WorkingDirectory = 'C:\Users\v_jac\Desktop\QUOTEX'
$lnk.Description = 'Hub Operacional del Edificio (Quotex)'
$lnk.IconLocation = 'C:\Windows\System32\shell32.dll,14'
$lnk.Save()
Write-Host "LNK created"
