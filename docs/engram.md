# Engram — Memoria persistente en QUOTEX Bot

> Complementa el harness SDD (`agent/HANDOFF.md`, `progress/`) con memoria
> semántica buscable entre sesiones.

## Qué es

[Engram](https://github.com/Gentleman-Programming/engram) guarda decisiones, bugs y contexto en SQLite (`%USERPROFILE%\.engram\engram.db`). El agente accede vía **MCP** desde Cursor.

Proyecto registrado: **quotex-hft-bot** (`.engram/config.json`).

## Instalación (una vez)

```powershell
cd "C:\Users\v_jac\Desktop\QUOTEX - segunda estrategia - copia"
.\scripts\install-engram.ps1
```

El script configura **OpenCode** (principal) y **Cursor** (opcional).

### OpenCode (este proyecto)

- MCP en `%USERPROFILE%\.config\opencode\opencode.jsonc`
- Plugin en `%USERPROFILE%\.config\opencode\plugins\engram.ts`
- **Reinicia OpenCode** tras instalar

### Cursor (opcional)

- MCP en `~/.cursor/mcp.json` + `.cursor/mcp.json` del repo
- Reglas en `.cursor/rules/engram.mdc`
- Reinicia Cursor; verifica **Settings → MCP**

> El harness (`AGENTS.md`, specs, leader) es **agnóstico** — funciona igual con OpenCode.
> La carpeta `.cursor/` del repo la ignora OpenCode; no causa conflictos.

### Instalación manual (sin script)

```powershell
go install github.com/Gentleman-Programming/engram/cmd/engram@latest
# Añade %USERPROFILE%\go\bin al PATH de usuario
engram setup cursor
```

## Uso diario

### Tú (humano)

```powershell
engram tui                              # Explorador visual de memorias
engram search "STRAT-A pending"         # Buscar desde terminal
engram projects list                    # Ver proyectos con memoria
```

### El agente (automático vía MCP)

| Momento | Herramienta |
|---------|-------------|
| Inicio de sesión | `mem_session_start`, `mem_search`, `mem_context` |
| Tras fix/decisión importante | `mem_save` (What / Why / Where / Learned) |
| Fin de sesión | `mem_save` resumen + `mem_session_end` |

El protocolo completo está en `.cursor/rules/engram.mdc`.

## Notificación cuando necesita tu atención

Cuando el agente termina una tarea o necesita aprobación, ejecuta:

```powershell
.\scripts\notify-attention.ps1 -Task "Spec #19 listo" -Reason "approval"
```

| `-Reason` | Cuándo |
|-----------|--------|
| `approval` | Spec SDD listo — di **aprobado** |
| `done` | Feature completada y revisada |
| `blocked` | Bloqueo que requiere tu decisión |
| `error` | `init.ps1` o tests fallaron |

La ventana muestra **Aceptar**; al cerrarla, Cursor/terminal sube al frente.

## Engram vs harness

| Harness (`agent/`, `progress/`) | Engram |
|----------------------------------|--------|
| Proceso SDD y estado de features | Memoria semántica libre |
| Handoff estructurado por sesión | Búsqueda por palabras clave |
| Vive en el repo (git) | Vive en `~/.engram/` (local) |

**Usa ambos:** el harness dice *cómo trabajar*; Engram dice *qué recordar*.

## Troubleshooting

| Problema | Solución |
|----------|----------|
| MCP engram no aparece | Reinicia Cursor; ejecuta `.\scripts\install-engram.ps1` |
| `engram` no reconocido | Añade `%USERPROFILE%\go\bin` al PATH |
| `ambiguous_project` | Confirma `.engram/config.json` con `quotex-hft-bot` |
| Sin sonido en notify | Normal en algunos entornos; la ventana igual aparece |