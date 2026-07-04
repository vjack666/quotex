<#
.SYNOPSIS
    Instala Engram y configura MCP para Cursor en este proyecto.
#>
$ErrorActionPreference = "Stop"

function ok   { Write-Host "[OK]    $args" -ForegroundColor Green }
function warn { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function fail { Write-Host "[FAIL]  $args" -ForegroundColor Red; exit 1 }

$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

Write-Host "--- Instalando Engram ---" -ForegroundColor Cyan

# 1. Binary
$engram = Get-Command engram -ErrorAction SilentlyContinue
if (-not $engram) {
    $goBin = Join-Path $env:USERPROFILE "go\bin\engram.exe"
    if (Test-Path $goBin) {
        $env:Path = "$(Split-Path $goBin -Parent);$env:Path"
        ok "engram encontrado en $goBin (añadido a PATH de sesión)"
    } else {
        warn "engram no está en PATH. Intentando go install..."
        if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
            fail "Instala Go 1.24+ o descarga engram desde https://github.com/Gentleman-Programming/engram/releases"
        }
        go install github.com/Gentleman-Programming/engram/cmd/engram@latest
        $env:Path = "$(Join-Path $env:USERPROFILE 'go\bin');$env:Path"
    }
}

$engram = Get-Command engram -ErrorAction SilentlyContinue
if (-not $engram) {
    fail "engram sigue sin estar en PATH. Añade %USERPROFILE%\go\bin al PATH de usuario."
}
ok "engram -> $($engram.Source)"

# 2. Project config (ya en repo)
if (-not (Test-Path ".engram\config.json")) {
    New-Item -ItemType Directory -Path ".engram" -Force | Out-Null
    @{ project_name = "quotex-hft-bot" } | ConvertTo-Json | Set-Content ".engram\config.json" -Encoding UTF8
}
ok "Proyecto Engram: quotex-hft-bot (.engram/config.json)"

# 3. OpenCode (agente principal en este entorno)
& engram setup opencode
if ($LASTEXITCODE -ne 0) {
    warn "engram setup opencode falló — revisa ~/.config/opencode/opencode.jsonc"
} else {
    ok "engram setup opencode completado (MCP + plugin)"
}

# 4. Cursor (opcional, si también usas Cursor)
& engram setup cursor
if ($LASTEXITCODE -ne 0) {
    warn "engram setup cursor falló — el proyecto ya tiene .cursor/mcp.json local"
} else {
    ok "engram setup cursor completado"
}

# 5. Verificación
& engram version
& engram doctor 2>$null
if ($LASTEXITCODE -ne 0) {
    warn "engram doctor reportó avisos — revisa manualmente"
}

Write-Host ""
Write-Host "Siguiente paso:" -ForegroundColor Yellow
Write-Host "  1. Reinicia OpenCode para activar MCP Engram (agente principal)"
Write-Host "  2. Si usas Cursor también, reinícialo y verifica MCP en Settings"
Write-Host "  3. Lee docs/engram.md para uso diario"
Write-Host ""
ok "Instalación Engram finalizada."