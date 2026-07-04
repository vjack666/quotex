# SESSION_PROTOCOL — Mandatory Work Session Workflow

> Every agent work session must follow this protocol.
> Harness rules (`AGENTS.md`) are the highest implementation authority.

---

## 1. Startup (before any code change)

| Step | Action | Stop condition |
|------|--------|----------------|
| S1 | `git branch --show-current` | — |
| S2 | `git status` | Note uncommitted changes |
| S3 | `git pull` | **Stop** on merge conflicts |
| S4 | Read all `/agent` docs (order in `START.md`) | — |
| S5 | Read Harness (`AGENTS.md`, `docs/*`, `CHECKPOINTS.md`) | — |
| S6 | Read roadmap (`docs/ROADMAP.md`, `feature_list.json`) | — |
| S7 | Run `.\init.ps1` | **Stop** if exit code ≠ 0 (report, don't code) |
| S8 | Emit startup summary (`START.md` § Phase E) | — |
| S9 | Wait for human instruction | Never auto-implement |
| S10 | Si necesitas al humano → `.\scripts\notify-attention.ps1` | Ventana modal + foco en IDE |

---

## 2. During development

### Harness compliance

- **One feature at a time** (`feature_list.json` rules).
- Features with `"sdd": true` require spec before code:
  ```
  pending → spec_author → spec_ready → [human approve] → in_progress → implementer → reviewer → done
  ```
- Leader agent must **not** edit `src/` or `tests/` directly (delegate to implementer).
- Non-leader agents follow `specs/<feature>/tasks.md` step by step.

### Architecture preservation

- Respect four layers: `connection` → `scanner` → `strategies` → `executor`.
- Strategies are pure (no broker I/O).
- Active risk manager: **Massaniello** (`massaniello_risk.py`). Do not reintroduce martingale in runtime code.
- See `docs/architecture.md` for full data-flow diagram.

### Regression avoidance

- Write or update tests **with** every code change.
- Run `python -m pytest tests/ -v` before claiming a task complete.
- Run `.\init.ps1` before session end.
- Reviewer must verify `R<n>` ↔ test traceability for SDD features.

### Documentation sync

Update documentation when:

- Architecture changes → `docs/architecture.md` + `agent/DECISIONS.md`
- Roadmap changes → `feature_list.json` + `docs/ROADMAP.md` + `agent/TASKS.md`
- Session ends → `agent/HANDOFF.md`, `agent/PROJECT_STATE.md`, `agent/CHANGELOG.md`
- Harness session → `progress/current.md` → `progress/history.md` on close

**Rule:** Prefer updating existing docs over creating duplicates.

---

## 3. End of session (mandatory)

Execute in order:

| Step | File / action |
|------|---------------|
| E1 | Update `agent/PROJECT_STATE.md` (architecture, milestone, problems) |
| E2 | Update `agent/HANDOFF.md` (completed, remaining, files, validation) |
| E3 | Update `agent/TASKS.md` (move tasks between sections) |
| E4 | Append entry to `agent/CHANGELOG.md` |
| E5 | If SDD feature worked: update `progress/current.md` or move to `progress/history.md` |
| E6 | `git add` relevant files (never commit secrets: `.env`) |
| E7 | `git commit -m "<descriptive message>"` |
| E8 | `git push` to GitHub |

### Commit message format

```
<type>: <short summary>

<body: what changed and why>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Example:

```
feat: add massaniello session persistence (#11)

- Save wins/losses/ops to trade_journal.db after each trade
- Recover session state on bot restart
- 4 new unit tests; init.ps1 green
```

---

## 4. Session types

| Type | Protocol |
|------|----------|
| **Implementation** | Full startup → one feature → tests → reviewer → end-of-session docs |
| **Documentation only** | Startup → edit docs → end-of-session docs (no src/ changes) |
| **Investigation** | Startup → read-only exploration → update HANDOFF with findings |
| **Hotfix** | Startup → minimal fix + test → DECISIONS entry → push |

---

## 5. Failure handling

| Situation | Action |
|-----------|--------|
| `init.ps1` fails | Document in HANDOFF; do not mark tasks completed |
| Tests fail | Fix before session end or document blocker in PROJECT_STATE |
| Blocked on human input | Set feature `blocked` in JSON; note in HANDOFF |
| Merge conflict on pull | Stop; report; wait for human resolution |

---

## 6. Validation checklist (before push)

- [ ] `.\init.ps1` exit 0
- [ ] `python -m pytest tests/ -v` all green
- [ ] No secrets in staged files
- [ ] `agent/HANDOFF.md` written
- [ ] `agent/TASKS.md` sections accurate
- [ ] At most one feature `in_progress` in `feature_list.json`