# Arranca el bot en demo, solo STRAT-A, con ordenes reales en PRACTICE.
Set-Location $PSScriptRoot
if (-not (Test-Path ".env")) {
    Write-Error "Falta .env en $PSScriptRoot"
    exit 1
}
python main.py --strat-a-only @args