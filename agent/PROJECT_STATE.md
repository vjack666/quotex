# PROJECT_STATE

> Last updated: 2026-07-04 (roadmap complete — 22/22 features done)
> Update this file at the end of every work session.

---

## Project identity

| Field | Value |
|-------|-------|
| Name | quotex-hft-bot |
| Type | HFT binary options bot for Quotex |
| Language | Python 3.10+ (running 3.13) |
| Risk manager | **Massaniello** (5 ops / 3 ITM / 60 min / PRACTICE) |
| Roadmap progress | **22 / 22** features done (100 %) |
| **Priority track** | **STRAT-A** — **6 / 6 done** ✅ |

---

## Current architecture

Four-layer design (see `docs/architecture.md`):

```
connection.py  →  scanner.py  →  strats (A / B / momentum / swing / OB)  →  executor.py
                                                                          ↘ massaniello_risk.py
                                                                          ↘ entry_sync.py
                                                                          ↘ diversification_enforcer.py
                                                                          ↘ alerter.py
```

Performance layer:

```
parallel_fetch.py  →  candle_cache.py (incremental prefetch)
scan_prefetch.py   →  OB blocks precalculados
htf_scanner.py     →  15m background + zone_memory
```

Intelligence layer:

```
backtester.py      →  grid-search sobre historial de trades
weight_calibrator.py →  pesos dinámicos por hora/volatilidad (Sharpe)
kelly_sizer.py     →  sizing conservador (25% fraccional Kelly)
massaniello_persistence.py →  estado SQLite entre reinicios
```

SMC stack (invocable vía módulos / `asyncio.run(main())`):

```
smc_analysis.py → smc_decision_engine.py → smc_auto_trader.py
filter_and_sell_otc.py (payout scan + PUT)
```

---

## Implemented systems

| System | Feature | Notes |
|--------|---------|-------|
| Modular bot architecture | #1 | Facade + core modules |
| Strategy A (consolidation 5m) | #1, #17–#22 | Full track complete |
| Strategy B (Wyckoff spring/sweep) | #1 | Via `strategy_spring_sweep.py` |
| SMC analysis + decision engine | #2 | HTF dictatorship H4/M15/M1 |
| Entry scorer | pre-existing | Adaptive threshold |
| Massaniello session manager | #16 | Replaces martingale runtime |
| Parallel candle prefetch | #3 | `parallel_fetch.py` |
| Incremental candle cache | #4 | `candle_cache.py` |
| Entry sync precision | #5 | `EntrySynchronizer`; lag ≤ 0.3s |
| Strategy momentum 1m | #6 | `strat_momentum.py` |
| Strategy reversal swing | #7 | `strat_reversal_swing.py` |
| Strategy order block | #8 | `strat_order_block.py` |
| Backtesting engine | #9 | `backtester.py` — grid-search 5 origins |
| Dynamic weight calibration | #10 | `weight_calibrator.py` — Sharpe optimization |
| Massaniello persistence | #11 | `massaniello_persistence.py` — SQLite save/load |
| Hub live WebSocket | #12 | FastAPI+WS server |
| Kelly criterion sizing | #13 | `kelly_sizer.py` — 25% fractional Kelly |
| Diversification enforcer | #14 | `diversification_enforcer.py` — 3 configurable limits |
| Telegram alerts | #15 | `alerter.py` — 4 event types + cooldown |
| STRAT-A radar watchlist | ops | `strat_a_radar.py`; tick 1m top-5 |
| Test suite | all | 251 tests, all green |

---

## Known problems

| ID | Problem | Severity | Owner action |
|----|---------|----------|--------------|
| P1 | `consolidation_bot.log` ~63 MB (rotado) | low | Rotar periódicamente |
| P2 | `parallel_fetch` DRY para OB (opcional) | low | Feature backlog |
| P3 | Demo #22: 0 entradas en sesión validación | low | Mercado/filtros; reject-first OK |

---

## Validation status

| Check | Status |
|-------|--------|
| `.\init.ps1` | ✅ exit 0 |
| `pytest tests/` | ✅ 251 passed |
| Live broker connection | ✅ PRACTICE login OK |
| Full system live validation | ⏳ **Pendiente** |
