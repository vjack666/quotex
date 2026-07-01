# DECISIONS — Architectural & Technical Log

> Record every important decision with date and reasoning.
> Newest entries at the top.

---

## 2026-06-29 — Agent autonomous workflow (`/agent`)

**Decision:** Create `/agent` folder as cross-machine session memory, complementary to Harness SDD.

**Reasoning:**
- Harness (`feature_list.json`, `specs/`, `progress/`) excels at feature traceability but lacks handoff context for new machines.
- `agent/HANDOFF.md` enables zero-context resume after `git pull`.
- `START.md` defines deterministic startup when user types `start`.

**Alternatives rejected:** Replacing Harness entirely (loses SDD spec traceability).

---

## 2026-06-29 — Massaniello replaces Martingale as active risk manager

**Decision:** Runtime risk management uses `MassanielloRiskManager` (5 ops / 3 ITM / 60 min). Martingale disabled.

**Reasoning:**
- User goal: 5 entries per hour, only need 3 wins — matches Massaniello grid math.
- Intra-trade martín (gale during candle) conflicts with Massaniello stake recalculation.
- Source logic ported from `masaniello.py` (proven calculator).

**Alternatives rejected:** Hybrid martingale + Massaniello (complexity, conflicting recovery models).

**Legacy:** `martingale_calculator.py` kept on disk but marked deprecated.

---

## 2026-06-29 — Feature #11 renamed: `massaniello_persistence`

**Decision:** Replace planned `martingale_persistence` with `massaniello_persistence`.

**Reasoning:** Persisting martingale state is irrelevant after #16. Session state (wins, losses, ops, capital, start time) must survive restarts.

---

## 2026-06-29 — Monolith refactor into four layers

**Decision:** Split `consolidation_bot.py` into `connection`, `scanner`, `executor`, `strat_a`, `strat_b`. Facade ≤500 lines.

**Reasoning:**
- 4000+ line monolith blocked parallel development and testing.
- Clear layer boundaries enforce strategy purity (no broker I/O in strategies).
- Each module gets dedicated test file.

**Reference:** Feature #1 spec `specs/refactor_monolith/`.

---

## 2026-06-29 — Spec Driven Development (SDD) harness

**Decision:** All features with `"sdd": true` require `specs/<name>/{requirements,design,tasks}.md` before implementation.

**Reasoning:**
- Prevents scope creep and ensures test traceability (`R<n>` ↔ test).
- Human approval gate between `spec_ready` and `in_progress`.
- Leader orchestrates; implementer/reviewer execute.

**Authority:** `AGENTS.md`, `docs/specs.md`, `.claude/agents/`.

---

## 2026-06-29 — Demo-only enforcement for Massaniello phase

**Decision:** Force `PRACTICE` account when Massaniello is active; warn and ignore `--real`.

**Reasoning:** User explicitly requested demo-only validation before live trading.

---

## 2026-06-29 — Roadmap dual representation

**Decision:** `feature_list.json` (authoritative states) + `docs/ROADMAP.md` (human view).

**Reasoning:**
- JSON machine-readable for agents and `init.ps1` validation.
- Markdown readable for humans with phases, diagrams, changelog.

---

## Pre-harness — Strategy selection model

**Decision:** Scanner collects candidates; `entry_scorer` scores 0-100; executor picks best.

**Reasoning:** Mathematical selection over first-signal-wins reduces false entries.

**Status:** Implemented in `scanner.py` + `entry_scorer.py` + `executor.py`.