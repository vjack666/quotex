$s = (New-Object -COM WScript.Shell).CreateShortcut("C:\Users\v_jac\Desktop\QUOTEX Web App.lnk")
$s.TargetPath = "C:\Users\v_jac\Desktop\QUOTEX\.venv\Scripts\python.exe"
$s.Arguments = "main.py"
$s.WorkingDirectory = "C:\Users\v_jac\Desktop\QUOTEX"
$s.IconLocation = ",0"
$s.Save()
Write-Output "Updated shortcut to launch main.py"
