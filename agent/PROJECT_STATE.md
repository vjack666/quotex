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
| Roadmap progress | **7 / 16** features done (44 %) |

---

## Current architecture

Four-layer design (see `docs/architecture.md`):

```
connection.py  →  scanner.py  →  strat_a / strat_b / strat_momentum  →  executor.py
                                                                      ↘ massaniello_risk.py
                                                                      ↘ entry_sync.py
```

Performance layer:

```
parallel_fetch.py  →  candle_cache.py (incremental prefetch)
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
| `candle_cache.py` | Performance (caché incremental) | ✅ |
| `entry_sync.py` | Performance (timing 1m) | ✅ |
| `executor.py` | Ejecución | ✅ |
| `strat_a.py` | Estrategia (consolidación) | ✅ |
| `strat_b.py` | Estrategia (Spring/Upthrust) | ✅ |
| `strat_momentum.py` | Estrategia (momentum 1m) | ✅ |
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

**Fase 1 — Rendimiento del scanner** (completa)

- ✅ #3 Parallel asset scan (prefetch 5m+1m)
- ✅ #4 Candle cache (actualización incremental)
- ✅ #5 Entry sync precision (<300ms guard)

**Fase 2 — Nuevas estrategias** (en curso)

- ✅ #6 Strategy momentum 1m
- ⏳ **Siguiente:** #7 `strategy_reversal_swing`

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
| Incremental candle cache | #4 | `candle_cache.py`; TTL + merge por activo/tf |
| Entry sync precision | #5 | `EntrySynchronizer`; lag ≤ 0.3s |
| Strategy momentum 1m | #6 | `strat_momentum.py`; `STRAT-MOMENTUM` |
| Test suite | #1–#6, #16 | 74 tests, all green |
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

1. **#7** `strategy_reversal_swing` — swing S/R dinámico
2. Fix Quotex credentials and validate Massaniello session in demo
3. **#8** `strategy_order_block` — order blocks institucionales
4. **#11** `massaniello_persistence` — survive bot restarts

---

## Validation status

| Check | Status |
|-------|--------|
| `.\init.ps1` | ✅ exit 0 |
| `pytest tests/` | ✅ 74 passed |
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