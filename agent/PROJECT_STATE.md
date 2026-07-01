# PROJECT_STATE

> Last updated: 2026-06-30
> Update this file at the end of every work session.

---

## Project identity

| Field | Value |
|-------|-------|
| Name | quotex-hft-bot |
| Type | HFT binary options bot for Quotex |
| Language | Python 3.10+ (running 3.13) |
| Risk manager | **Massaniello** (5 ops / 3 ITM / 60 min / PRACTICE) |
| Roadmap progress | **4 / 16** features done (25 %) |

---

## Current architecture

Four-layer design (see `docs/architecture.md`):

```
connection.py  →  scanner.py  →  strat_a / strat_b  →  executor.py
                                                      ↘ massaniello_risk.py
```

SMC stack (feature #2, invocable vía módulos / `asyncio.run(main())`):

```
smc_analysis.py → smc_decision_engine.py → smc_auto_trader.py
filter_and_sell_otc.py (payout scan + PUT)
```

### Implemented modules (`src/`)

| Module | Layer | Status |
|--------|-------|--------|
| `consolidation_bot.py` | Facade (≤500 lines) | ✅ |
| `connection.py` | Conexión | ✅ |
| `scanner.py` | Análisis | ✅ |
| `parallel_fetch.py` | Performance (prefetch velas) | ✅ |
| `executor.py` | Ejecución | ✅ |
| `strat_a.py` | Estrategia (consolidación) | ✅ |
| `strat_b.py` | Estrategia (Spring/Upthrust) | ✅ |
| `massaniello_engine.py` | Riesgo (motor) | ✅ |
| `massaniello_risk.py` | Riesgo (sesión) | ✅ |
| `smc_analysis.py` | Estrategia (SMC puro) | ✅ |
| `smc_decision_engine.py` | Estrategia (SMC decisión) | ✅ |
| `smc_auto_trader.py` | Facade SMC | ✅ |
| `filter_and_sell_otc.py` | Facade filter-sell | ✅ |
| `config.py` | Configuración | ✅ |
| `models.py`, `errors.py`, `loop_utils.py` | Soporte | ✅ |
| `entry_scorer.py` | Scoring 0-100 | ✅ |
| `trade_journal.py` | SQLite journal | ✅ |
| `martingale_calculator.py` | Legacy | ⚠️ deprecado |

---

## Current milestone

**Fase 0 — Fundamentos** (completa)

- ✅ #1 Monolith refactor
- ✅ #2 Missing SMC / filter_sell modules
- ✅ #16 Massaniello risk management
- ✅ #3 Parallel asset scan (prefetch 5m+1m)

**Siguiente:** Fase 1 — Performance (#4 `candle_cache`)

---

## Implemented systems

| System | Feature | Notes |
|--------|---------|-------|
| Modular bot architecture | #1 | Facade + 5 core modules |
| Strategy A (consolidation 5m) | #1 | Pure signal logic |
| Strategy B (Wyckoff spring/sweep) | #1 | Via `strategy_spring_sweep.py` |
| SMC analysis + decision engine | #2 | HTF dictatorship H4/M15/M1 |
| SMC auto trader + filter-sell OTC | #2 | Dry-run + connection layer |
| Entry scorer | pre-existing | Adaptive threshold |
| Massaniello session manager | #16 | Replaces martingale runtime |
| Parallel candle prefetch | #3 | `parallel_fetch.py`; 5m+1m antes del bucle |
| Test suite | #1, #2, #3, #16 | 61 tests, all green |
| SDD harness | infra | `init.ps1`, specs, agents |

---

## Systems under development

_None — no feature currently `in_progress`._

---

## Known problems

| ID | Problem | Severity | Owner action |
|----|---------|----------|--------------|
| P1 | Quotex demo credentials rejected by broker | **blocking** | Update `QUOTEX_EMAIL` / `QUOTEX_PASSWORD` in `.env` |
| P2 | Massaniello demo validation not run live | medium | Requires P1 fix; goal: 5 entries / 3 wins in 1h |
| P3 | `README.md` outdated (paths, SMC wiring) | low | Update when convenient |
| P4 | Massaniello state not persisted across restarts | medium | Feature #11 `massaniello_persistence` pending |
| P5 | Root `README.md` references `src/main.py` but entry is `main.py` | low | Doc fix |
| P6 | `main.py` sin subcomandos `smc` / `filter-sell` | low | Wiring futuro (fuera de scope #2) |

---

## Next objectives (ordered)

1. **#4** `candle_cache` — incremental candle fetch
2. Fix Quotex credentials and validate Massaniello session in demo
3. **#5** `entry_sync_precision` — <300ms entry timing
4. **#11** `massaniello_persistence` — survive bot restarts

---

## Validation status

| Check | Status |
|-------|--------|
| `.\init.ps1` | ✅ exit 0 |
| `pytest tests/` | ✅ 61 passed |
| Live broker connection | ❌ login invalid |
| Massaniello demo session goal | ❌ not validated |

---

## Key file locations

| Purpose | Path |
|---------|------|
| Entry point | `main.py` |
| Feature roadmap (JSON) | `feature_list.json` |
| Feature roadmap (human) | `docs/ROADMAP.md` |
| Agent memory | `agent/*` |
| Specs | `specs/<feature>/` |
| Environment | `.env` (not in git) |