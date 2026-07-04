# START — Autonomous Agent Entry Point

> When the user types only **`start`**, execute this workflow **exactly**.
> Do **not** modify code automatically after startup. Wait for instructions.

---

## Trigger

```
start
```

Any agent session triggered by this single word must treat this file as the
mandatory entry point.

---

## Startup Workflow (ordered)

### Phase A — Git synchronization

1. Confirm the current git branch (`git branch --show-current`).
2. Run `git status`.
3. Pull latest changes from GitHub (`git pull`).
4. If merge conflicts exist → **stop immediately**, report conflicts, and wait.
   Do not proceed to documentation reads until conflicts are resolved or the
   human instructs otherwise.

### Phase B — Agent memory (read in this exact order)

Read every file in `/agent`:

| Order | File |
|-------|------|
| 1 | `agent/START.md` (this file) |
| 2 | `agent/PROJECT_STATE.md` |
| 3 | `agent/HANDOFF.md` |
| 4 | `agent/TASKS.md` |
| 5 | `agent/DECISIONS.md` |
| 6 | `agent/CHANGELOG.md` |
| 7 | `agent/CONTEXT.md` |
| 8 | `agent/SESSION_PROTOCOL.md` |

### Phase C — Repository orientation

9. Read the repository root `README.md`.
10. Locate and read every roadmap, architecture, or planning document:

| Path | Role |
|------|------|
| `docs/ROADMAP.md` | Human-readable roadmap (phases, progress) |
| `feature_list.json` | Machine-readable feature states + acceptance |
| `AGENTS.md` | Harness navigation map |
| `CHECKPOINTS.md` | Objective quality gates |
| `docs/architecture.md` | Layer rules and data flow |
| `docs/conventions.md` | Coding standards |
| `docs/specs.md` | Spec Driven Development process |
| `docs/verification.md` | Test and traceability rules |
| `progress/current.md` | Active session state (Harness SDD) |
| `progress/history.md` | Completed session log (Harness SDD) |
| `CLAUDE.md` | Leader agent role (if using Claude) |
| `.claude/agents/leader.md` | Orchestration protocol |

11. Read the **Harness documentation completely** (`AGENTS.md` + linked `docs/*`
    + `CHECKPOINTS.md` + `init.ps1` purpose).
12. Extract and internalize:
    - Project rules (one feature at a time, SDD gate, tests required)
    - Coding standards (`docs/conventions.md`)
    - Validation rules (`.\init.ps1`, pytest, reviewer checkpoints)
    - Autonomous workflow (leader → spec_author → implementer → reviewer)
13. Run `.\init.ps1`. If it fails → report failure in startup summary; do not
    start coding until environment is green (unless human overrides).

### Phase D — Context synthesis

14. Build an internal model of current project state by reconciling:
    - `agent/PROJECT_STATE.md`
    - `agent/HANDOFF.md`
    - `feature_list.json`
    - `docs/ROADMAP.md`
    - `progress/current.md`

### Phase E — Startup summary (required output)

15. Produce a **short startup summary** for the user:

```
## Startup Summary

**Branch:** <branch>
**Git:** <clean | uncommitted changes | conflicts>
**init.ps1:** <OK | FAIL>

### Current objective
<one sentence>

### Implementation status
<2-4 bullets>

### Pending tasks
<from agent/TASKS.md — Next section, top items>

### Current priorities
<ordered list, max 3>

### Possible blockers
<from feature_list.json roadmap.blockers + agent/PROJECT_STATE.md>
```

16. **Wait for instructions.** Never auto-start implementation.

17. Si Engram MCP está activo, busca contexto previo (`mem_search` / `mem_context`).
    Ver `docs/engram.md`.

---

## Notificación al humano (obligatorio)

Cuando la sesión **necesite atención del usuario** (spec listo, feature done,
bloqueo, error de entorno), ejecuta **antes** de pedir respuesta en chat:

```powershell
.\scripts\notify-attention.ps1 -Task "<descripción>" -Reason approval|done|blocked|error
```

Esto abre una ventana con **Aceptar** y trae Cursor/terminal al frente.

---

## Authority hierarchy

When documents conflict, resolve in this order:

1. Harness hard rules (`AGENTS.md`, `CHECKPOINTS.md`)
2. `agent/SESSION_PROTOCOL.md`
3. `feature_list.json` + approved `specs/<feature>/`
4. `agent/DECISIONS.md`
5. `docs/ROADMAP.md` (readable view; JSON is authoritative for feature status)
6. `agent/CONTEXT.md`

---

## Relationship to Harness SDD

This repository uses **two complementary memory systems**:

| System | Location | Purpose |
|--------|----------|---------|
| **Agent memory** | `/agent/*` | Cross-machine resumability, handoffs, decisions |
| **Harness SDD** | `feature_list.json`, `specs/`, `progress/` | Feature specs, implementation traceability |

Always keep both synchronized at session end (see `SESSION_PROTOCOL.md`).

---

## Quick reference commands

```powershell
.\init.ps1                          # Validate environment + tests
python -m pytest tests/ -v          # Run test suite
python main.py --live --loop        # Demo bot loop (PRACTICE)
git status && git pull              # Sync before work
```