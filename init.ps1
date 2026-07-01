<#
.SYNOPSIS
    init.ps1 - Verificacion e inicializacion del entorno para QUOTEX HFT Bot
.DESCRIPTION
    Este script lo ejecuta el agente al COMENZAR una sesion y antes de
    declarar cualquier tarea como 'done'. Si falla, la sesion no debe avanzar.
#>

param()

$EXIT_CODE = 0

function ok   { Write-Host "[OK]    $args" -ForegroundColor Green }
function warn { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function fail { Write-Host "[FAIL]  $args" -ForegroundColor Red }

Write-Host "--- 1. Verificando entorno ---" -ForegroundColor Cyan

# Python disponible
try {
    $pyVersion = & python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        ok "python -> $pyVersion"
    } else {
        fail "python no esta disponible"
        exit 1
    }
} catch {
    fail "python no esta instalado o no esta en PATH"
    exit 1
}

# Version minima 3.9 usando un script temporal
$verScript = [System.IO.Path]::GetTempFileName() + ".py"
try {
    Set-Content -Path $verScript -Value "import sys; v = sys.version_info; print(v.major, v.minor)" -Encoding UTF8
    $pyCheck = & python $verScript 2>&1
    if ($LASTEXITCODE -eq 0) {
        $parts = ($pyCheck.Trim() -split ' ')
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
            fail "Se requiere Python >= 3.9 (actual: $major.$minor)"
            exit 1
        }
        ok "Version de Python compatible ($major.$minor)"
    } else {
        fail "No se pudo determinar la version de Python"
        exit 1
    }
} finally {
    if (Test-Path $verScript) { Remove-Item $verScript -Force }
}

# Verificar dependencias criticas
$missingDeps = @()
$deps = @("pyquotex", "dotenv", "pandas", "loguru")
$depNames = @("pyquotex", "python-dotenv", "pandas", "loguru")
for ($i = 0; $i -lt $deps.Length; $i++) {
    $depScript = [System.IO.Path]::GetTempFileName() + ".py"
    try {
        Set-Content -Path $depScript -Value "import $($deps[$i])" -Encoding UTF8
        & python $depScript 2>$null
        if ($LASTEXITCODE -ne 0) {
            $missingDeps += $depNames[$i]
        }
    } finally {
        if (Test-Path $depScript) { Remove-Item $depScript -Force }
    }
}
if ($missingDeps.Count -gt 0) {
    warn "Faltan dependencias: $($missingDeps -join ', ')"
    warn "Ejecuta: pip install -r requirements.txt"
} else {
    ok "Dependencias principales instaladas"
}

Write-Host ""
Write-Host "--- 2. Verificando archivos base del harness ---" -ForegroundColor Cyan

$baseFiles = @(
    "AGENTS.md",
    "feature_list.json",
    "progress/current.md",
    "docs/architecture.md",
    "docs/conventions.md",
    "docs/verification.md",
    "CHECKPOINTS.md"
)
foreach ($f in $baseFiles) {
    if (Test-Path $f) {
        ok "Existe $f"
    } else {
        fail "Falta archivo base: $f"
        $EXIT_CODE = 1
    }
}

Write-Host ""
Write-Host "--- 3. Validando feature_list.json y specs ---" -ForegroundColor Cyan

$featScript = [System.IO.Path]::GetTempFileName() + ".py"
try {
    Set-Content -Path $featScript -Encoding UTF8 -Value @'
import json, os, sys
data = json.load(open("feature_list.json"))
valid = {"pending", "spec_ready", "in_progress", "done", "blocked"}
in_progress = [f for f in data["features"] if f["status"] == "in_progress"]
if len(in_progress) > 1:
    print(f"FAIL: Hay {len(in_progress)} features en in_progress (maximo 1)")
    sys.exit(1)
requires_spec = {"spec_ready", "in_progress", "done"}
spec_errors = []
for f in data["features"]:
    if f["status"] not in valid:
        print(f"FAIL: Estado invalido en feature {f['id']}: {f['status']}")
        sys.exit(1)
    if f.get("sdd") and f["status"] in requires_spec:
        spec_dir = os.path.join("specs", f["name"])
        for fname in ("requirements.md", "design.md", "tasks.md"):
            if not os.path.isfile(os.path.join(spec_dir, fname)):
                spec_errors.append(f"feature {f['id']} ({f['name']}) en {f['status']} sin {spec_dir}/{fname}")
if spec_errors:
    for e in spec_errors:
        print(f"FAIL: {e}")
    sys.exit(1)
print(f"OK: feature_list.json valido ({len(data['features'])} features)")
print(f"OK: Specs presentes para features sdd con estado no-pending")
'@
    $result = & python $featScript 2>&1
    if ($LASTEXITCODE -eq 0) {
        $result | ForEach-Object { Write-Host "[$_]" }
    } else {
        $result | ForEach-Object { Write-Host "[$_]" -ForegroundColor Red }
        $EXIT_CODE = 1
    }
} finally {
    if (Test-Path $featScript) { Remove-Item $featScript -Force }
}

Write-Host ""
Write-Host "--- 4. Ejecutando tests ---" -ForegroundColor Cyan

if (Test-Path "tests") {
    $testOutput = & python -m pytest tests/ -v 2>&1
    if ($LASTEXITCODE -eq 0) {
        ok "Todos los tests pasan"
    } else {
        fail "Hay tests rotos"
        $EXIT_CODE = 1
    }
} else {
    warn "Carpeta tests/ no existe todavia"
}

Write-Host ""
Write-Host "--- 5. Verificando estado del proyecto ---" -ForegroundColor Cyan

if (Test-Path "consolidation_bot.log") {
    try {
        $logSize = (Get-Item "consolidation_bot.log").Length / 1KB
        $logSizeRounded = [math]::Round($logSize)
        if ($logSize -gt 10240) {
            warn "consolidation_bot.log es muy grande ($logSizeRounded KB) - considera rotarlo"
        } else {
            ok "Log presente ($logSizeRounded KB)"
        }
    } catch {
        warn "No se pudo verificar el log"
    }
} else {
    warn "No existe consolidation_bot.log (normal si nunca se ha ejecutado)"
}

if (Test-Path ".env") {
    ok ".env presente"
} else {
    warn "No existe .env - copia .env.example a .env y configura credenciales"
}

Write-Host ""
Write-Host "--- 6. Resumen ---" -ForegroundColor Cyan

if ($EXIT_CODE -eq 0) {
    ok "Entorno listo. Puedes empezar a trabajar."
} else {
    fail "Entorno NO esta listo. Resuelve los errores antes de avanzar."
}

exit $EXIT_CODE
