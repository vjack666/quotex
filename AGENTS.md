# AGENTS.md — Mapa de navegación para agentes de IA

> Este archivo es el **punto de entrada** para cualquier agente que trabaje en este
> repositorio. NO es una biblia de reglas: es un **mapa**. Lee solo lo que
> necesites cuando lo necesites (divulgación progresiva).

---

## 1. Antes de empezar (obligatorio)

**Si el usuario escribe solo `start`:** sigue `agent/START.md` (workflow autónomo
completo). No modifiques código hasta recibir instrucciones.

**En cualquier otra sesión:**

1. Ejecuta `.\init.ps1` y verifica que termina sin errores. Si falla, **para**
   y resuelve el entorno antes de tocar código.
2. Lee `agent/HANDOFF.md` y `agent/PROJECT_STATE.md` (memoria entre máquinas).
3. Lee `progress/current.md` para entender en qué estado quedó la última sesión.
4. Lee `feature_list.json` y `docs/ROADMAP.md`. Toda feature nueva (`"sdd": true`) pasa por
   **Spec Driven Development** — ver `docs/specs.md` y §4 de este archivo.
5. Lee `docs/specs.md` antes de tocar cualquier spec o feature `sdd: true`.

## 2. Mapa del repositorio

| Archivo / carpeta | Qué contiene | Cuándo leerlo |
|---|---|---|
| `agent/START.md` | Workflow autónomo: usuario escribe `start` | Trigger `start` |
| `agent/HANDOFF.md` | Transferencia entre sesiones/máquinas | Siempre, al empezar |
| `agent/PROJECT_STATE.md` | Estado arquitectura, milestone, bloqueos | Siempre, al empezar |
| `agent/TASKS.md` | Tareas In Progress / Next / Completed | Siempre, al empezar |
| `docs/ROADMAP.md` | Roadmap legible: fases, progreso, dependencias, bloqueos | Siempre, al empezar (humano o agente) |
| `docs/BACKLOG_SYSTEM_IMPROVEMENTS.md` | Inventario + pendientes de mejora global (no STRAT-F) | Cuando se retome hardening del sistema; **no** es el foco actual |
| `feature_list.json` | Lista maestra de features con estado (pending / spec_ready / in_progress / done / blocked) | Siempre, al empezar |
| `progress/current.md` | Estado de la sesión actual | Siempre, al empezar |
| `progress/history.md` | Bitácora append-only de sesiones anteriores | Si necesitas contexto histórico |
| `specs/<feature>/` | requirements.md + design.md + tasks.md (Kiro-style) | Antes de implementar cualquier feature con "sdd": true |
| `docs/architecture.md` | Qué significa "hacer un buen trabajo" en este proyecto | Antes de implementar |
| `docs/conventions.md` | Reglas de estilo, nombres, estructura | Antes de escribir código |
| `docs/specs.md` | Proceso SDD: EARS notation, los 3 archivos, puerta de aprobación humana | Antes de redactar o leer un spec |
| `docs/verification.md` | Cómo verificar que tu trabajo funciona (incluye trazabilidad requirements) | Antes de declarar una tarea como done |
| `CHECKPOINTS.md` | Criterios objetivos de "estado final correcto" | Para auto-evaluarte |
| `docs/engram.md` | Memoria persistente Engram (MCP) + notificaciones | Al iniciar sesión / tras decisiones |
| `.cursor/mcp.json` | Servidor MCP Engram (proyecto) | Tras `.\scripts\install-engram.ps1` |
| `scripts/notify-attention.ps1` | Ventana modal cuando el agente necesita al humano | Leader al llegar a puerta SDD o cierre |
| `.claude/agents/` | Definiciones de subagentes (leader, spec_author, implementer, reviewer) | Si orquestas trabajo |
| `src/` | Código fuente del bot | Para implementar |
| `hub/` | Dashboard de monitoreo | Para modificar |
| `tests/` | Tests automáticos | Para verificar |

## 3. Reglas duras (no negociables)

- **Una sola feature a la vez.** No mezcles cambios de varias tareas en la misma sesión.
- **No declares una tarea `done` sin pruebas verdes.** Ejecuta `.\init.ps1` y
  asegúrate de que el bloque de tests pasa al 100%.
- **No saltes la fase de spec.** Toda feature con `"sdd": true` debe pasar
  por `spec_author` y obtener aprobación humana antes de tocar código.
- **No saltes la puerta de aprobación humana.** El leader detiene el flujo
  en `spec_ready` y espera.
- **Documenta lo que haces** en `progress/current.md` mientras trabajas, no al final.
- **Deja el repositorio limpio** antes de cerrar la sesión (ver §5).
- **Si no sabes algo, busca en `docs/`** antes de inventarlo.

## 4. Flujo de trabajo (SDD)

```
pending → [spec_author] → spec_ready → ⏸ HUMANO → in_progress → [implementer → reviewer] → done
```

1. El leader detecta la primera feature `pending` con `"sdd": true`.
2. El leader lanza `spec_author`, que crea `specs/<name>/{requirements,design,tasks}.md` y marca el status como `spec_ready`.
3. **Pausa.** El humano lee el spec en `specs/<name>/` y aprueba (o pide cambios).
4. Una vez aprobado, el leader cambia el status a `in_progress` y lanza `implementer`.
5. El implementer ejecuta `tasks.md` una a una, marcándolas `[x]`.
6. El reviewer verifica trazabilidad `R<n>` ↔ test y tasks completas; aprueba o rechaza.
7. Si aprueba, el implementer marca `done` y mueve el resumen a `progress/history.md`.

## 5. Cierre de sesión (lifecycle)

Antes de terminar:

1. Ejecuta `.\init.ps1` — todo verde.
2. Si la tarea está acabada: marca `status: "done"` en `feature_list.json`.
3. Mueve el resumen de `progress/current.md` al final de `progress/history.md`.
4. Vacía `progress/current.md` dejando solo la plantilla.
5. No dejes archivos temporales, ni `print()` de debug, ni TODOs sin contexto.

## 6. Engram (memoria) y notificaciones

- **Instalación:** `.\scripts\install-engram.ps1` (una vez; ver `docs/engram.md`).
- **Al iniciar:** `mem_search` / `mem_context` si MCP Engram está activo.
- **Tras decisiones importantes:** `mem_save` (complementa `agent/HANDOFF.md`).
- **Atención humana obligatoria:** cuando `spec_ready`, feature `done`, bloqueo o
  `init.ps1` en rojo, ejecuta:
  ```powershell
  .\scripts\notify-attention.ps1 -Task "<qué pasó>" -Reason approval|done|blocked|error
  ```

## 7. Si te bloqueas

- Relee la sección relevante de `docs/`.
- Si la herramienta no hace lo que esperas, **no inventes un workaround**:
  documenta el bloqueo en `progress/current.md` y para la sesión.
