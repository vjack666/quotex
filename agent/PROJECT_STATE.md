# PROJECT_STATE

> Last updated: 2026-07-02 (cierre #22 strat_a_live_validation — track STRAT-A completo)
> Update this file at the end of every work session.

---

## Project identity

| Field | Value |
|-------|-------|
| Name | quotex-hft-bot |
| Type | HFT binary options bot for Quotex |
| Language | Python 3.10+ (running 3.13) |
| Risk manager | **Massaniello** (5 ops / 3 ITM / 60 min / PRACTICE) |
| Roadmap progress | **13 / 22** features done (59 %) |
| **Priority track** | **STRAT-A** — **6 / 6 done** ✅ |

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
scan_prefetch.py   →  OB blocks precalculados (STRAT-A)
htf_scanner.py     →  15m background + zone_memory
```

SMC stack (feature #2, invocable vía módulos / `asyncio.run(main())`):

```
smc_analysis.py → smc_decision_engine.py → smc_auto_trader.py
filter_and_sell_otc.py (payout scan + PUT)
```

### STRAT-A status (track #17–#22) — COMPLETO

| Component | Wired? | Notes |
|-----------|--------|-------|
| `strat_a.py` pure logic | ✅ | `evaluate_strat_a()` (#17) |
| STRAT-A test suite | ✅ | unit + E2E (#18) |
| STRAT-A in `scanner.py` | ✅ | delegación a `evaluate_strat_a` |
| Quality filters (PLAN MAESTRO) | ✅ | payout ≥87%, score ≥75, zona ≥30min (#19) |
| `htf_scanner.py` | ✅ | asyncio background (#20) |
| `zone_memory.py` | ✅ | poblado en candidatos (#20) |
| OB prefetch paralelo | ✅ | `blocks_by_symbol` (#21) |
| STRAT-A radar watchlist | ✅ | Top-5 readiness + tick 1m |
| Live demo validation | ✅ | 10 rechazos reject-first PRACTICE (#22) |

---

## Current milestone

**Track STRAT-A completo.** Retomar backlog global.

- ⏳ **Siguiente:** #7 `strategy_reversal_swing`
- Roadmap STRAT-A: `docs/ROADMAP_STRAT_A.md`

**Fases globales completadas:**

- ✅ Fase 0 — Fundamentos (#1, #2, #16)
- ✅ Fase 1 — Rendimiento scanner (#3–#5)
- ⏳ Fase 2 — Otras estrategias (#7–#8; #6 done)
- ✅ Track STRAT-A (#17–#22)

---

## Implemented systems

| System | Feature | Notes |
|--------|---------|-------|
| Modular bot architecture | #1 | Facade + core modules |
| Strategy A (consolidation 5m) | #1, #17–#22 | Full track complete |
| STRAT-A test suite | #18 | E2E scanner + pending + executor |
| STRAT-A quality filters | #19 | Reject-first PLAN MAESTRO |
| HTF zone wiring | #20 | HTFScanner + zone_memory |
| OB prefetch | #21 | `scan_prefetch.py` |
| Strategy B (Wyckoff spring/sweep) | #1 | Via `strategy_spring_sweep.py` |
| SMC analysis + decision engine | #2 | HTF dictatorship H4/M15/M1 |
| Entry scorer | pre-existing | Adaptive threshold |
| Massaniello session manager | #16 | Replaces martingale runtime |
| Parallel candle prefetch | #3 | `parallel_fetch.py` |
| Incremental candle cache | #4 | `candle_cache.py` |
| Entry sync precision | #5 | `EntrySynchronizer`; lag ≤ 0.3s |
| Strategy momentum 1m | #6 | `strat_momentum.py` |
| STRAT-A radar watchlist | ops | `strat_a_radar.py`; tick 1m top-5 |
| Test suite | #1–#6, #16–#22 | 135 tests, all green |

---

## Systems under development

_None — awaiting #7 spec._

---

## Known problems

| ID | Problem | Severity | Owner action |
|----|---------|----------|--------------|
| P1 | `consolidation_bot.log` ~50 MB | low | Rotar log |
| P2 | T17 `parallel_fetch` DRY para OB (opcional) | low | Feature backlog |
| P3 | Demo #22: 0 entradas en sesión validación | low | Mercado/filtros; reject-first OK |

---

## Next objectives (ordered)

1. **#7** `strategy_reversal_swing` — SDD spec + implement
2. **#8** `strategy_order_block` — generalizar OB
3. **#11** `massaniello_persistence` — sesiones largas demo

---

## Validation status

| Check | Status |
|-------|--------|
| `.\init.ps1` | ✅ exit 0 |
| `pytest tests/` | ✅ 135 passed |
| Live broker connection | ✅ PRACTICE login OK |
| STRAT-A demo session | ✅ #22 — 10 rechazos reject-first |

---

## Key file locations

| Purpose | Path |
|---------|------|
| Entry point | `main.py` |
| Feature roadmap (JSON) | `feature_list.json` |
| Global roadmap | `docs/ROADMAP.md` |
| **STRAT-A roadmap** | `docs/ROADMAP_STRAT_A.md` |
| PLAN MAESTRO (quality targets) | `Documentos/files/PLAN_MAESTRO.md` |
| Agent memory | `agent/*` |
| Live validation evidence | `progress/impl_strat_a_live_validation.md` |