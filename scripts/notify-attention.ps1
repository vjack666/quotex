<#
.SYNOPSIS
    Muestra ventana modal de atención y trae Cursor/terminal al frente.
.DESCRIPTION
    El leader y los subagentes deben ejecutar este script cuando necesiten
    aprobación humana, cierre de feature, bloqueo o error crítico.
.PARAMETER Task
    Descripción de la tarea o evento (ej. "Spec #19 listo — revisa specs/").
.PARAMETER Reason
    approval | done | blocked | error | attention
.EXAMPLE
    .\scripts\notify-attention.ps1 -Task "Feature #18 completada" -Reason "done"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Task,

    [ValidateSet("approval", "done", "blocked", "error", "attention")]
    [string]$Reason = "attention",

    [switch]$NoFocus
)

$ErrorActionPreference = "SilentlyContinue"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Media

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinFocus {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

$reasonLabels = @{
    approval  = "Aprobacion humana requerida (SDD)"
    done      = "Tarea completada"
    blocked   = "Bloqueo - intervencion necesaria"
    error     = "Error critico"
    attention = "Atencion requerida"
}

$title = "QUOTEX Bot - $($reasonLabels[$Reason])"
$body = @"
Tarea:
$Task

Motivo: $($reasonLabels[$Reason])

Pulsa Aceptar para cerrar esta ventana.
"@

try {
    [System.Media.SystemSounds]::Exclamation.Play()
} catch {}

[System.Windows.Forms.MessageBox]::Show(
    $body,
    $title,
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information
) | Out-Null

if (-not $NoFocus) {
    $patterns = @("OpenCode", "opencode", "Cursor", "QUOTEX", "Windows Terminal", "pwsh", "PowerShell", "Code")
    foreach ($pat in $patterns) {
        $proc = Get-Process |
            Where-Object { $_.MainWindowTitle -match $pat -and $_.MainWindowHandle -ne [IntPtr]::Zero } |
            Select-Object -First 1
        if ($proc) {
            [WinFocus]::ShowWindow($proc.MainWindowHandle, 9) | Out-Null
            [WinFocus]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
            break
        }
    }
}

Write-Host "[NOTIFY] $Reason -> $Task" -ForegroundColor Cyan