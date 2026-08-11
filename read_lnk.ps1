$s = (New-Object -COM WScript.Shell).CreateShortcut("C:\Users\v_jac\Desktop\QUOTEX Web App.lnk")
Write-Output "TargetPath=$($s.TargetPath)"
Write-Output "WorkingDirectory=$($s.WorkingDirectory)"
Write-Output "Arguments=$($s.Arguments)"
Write-Output "IconLocation=$($s.IconLocation)"
