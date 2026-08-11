$ErrorActionPreference = 'SilentlyContinue'
while ($true) {
    try {
        $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/health' -UseBasicParsing -TimeoutSec 10
        Write-Host (Get-Date -Format o) 'HEALTH' $r.StatusCode $r.Content
    }
    catch {
        Write-Host (Get-Date -Format o) 'HEALTH_ERR' $_.Exception.Message
    }
    Start-Sleep -Seconds 30
}
