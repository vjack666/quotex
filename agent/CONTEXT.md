# CONTEXT — Persistent Technical Knowledge

> Facts future sessions must remember. Update when domain logic changes.
> Do not duplicate Harness coding rules — see `docs/conventions.md`.

---

## 1. Trading domain

### Platform
- **Broker:** Quotex (binary options, OTC assets).
- **API:** `pyquotex` (WebSocket + REST via `stable_api.Quotex`).
- **Account types:** `PRACTICE` (demo), `REAL` (live). Massaniello phase forces PRACTICE.

### Order parameters
- Default duration: 30s (`DURATION_SEC` in `config.py`).
- Minimum payout: 80% (`MIN_PAYOUT`).
- Scan interval: 60s (`SCAN_INTERVAL_SEC`).

### Session goal (Massaniello)
- **5 operations** per session (`MASSANIELLO_OPERATIONS`).
- **3 wins required** (`MASSANIELLO_EXPECTED_WINS`).
- **60-minute** window (`SESSION_MAX_MIN`).
- Success log: `🎯 SESIÓN MASSANIELLO CUMPLIDA`.

---

## 2. Strategy A — Consolidation (5m)

**Module:** `strat_a.py`

Detects price consolidation zones on 5-minute candles:
- Minimum consolidation bars: 12 (`MIN_CONSOLIDATION_BARS`).
- Max range: 0.3% (`MAX_RANGE_PCT`) or dynamic ATR-based.
- Entry on breakout with volume confirmation (`is_high_volume_break`).
- H1 trend filter optional (`H1_CONFIRM_ENABLED`).

Signals: CALL on ceiling breakout, PUT on floor breakdown, or rejection candles at zone edges.

**Pure logic** — receives `List[Candle]`, returns signal or `None`. No broker calls.

---

## 3. Strategy B — Wyckoff Spring / Upthrust

**Module:** `strat_b.py` (wraps `strategy_spring_sweep.py`)

Wyckoff concepts:
- **Spring:** False breakdown below support → reversal CALL.
- **Upthrust:** False breakout above resistance → reversal PUT.
- **Sweep:** Liquidity grab beyond swing level followed by rejection.

Uses candles converted to DataFrame for pattern detection.

---

## 4. SMC concepts (planned — feature #2)

Smart Money Concepts modules not yet implemented:
- `smc_analysis.py` — market structure, BOS/CHoCH, order blocks, FVG.
- `smc_decision_engine.py` — rule engine for SMC signals.
- `smc_auto_trader.py` — SMC-specific trading loop.

Referenced in root `README.md` but **missing from `src/`**. Feature #2 will create them.

---

## 5. Scoring system

**Module:** `entry_scorer.py`

- Score range: 0–100 per candidate entry.
- Adaptive threshold: base 65, adjusts between 62–68 based on recent acceptance rate.
- Executor only enters if score ≥ current threshold.
- Scanner collects all candidates; executor picks highest score.

---

## 6. Massaniello risk management

**Modules:** `massaniello_engine.py`, `massaniello_risk.py`

Mathematical staking grid:
- Given N operations and M required wins, calculates optimal stake per (wins, losses) state.
- `_is_finished`: wins ≥ expected_itm OR losses ≥ (ops - expected_itm + 1) OR played ≥ ops.
- `effective_profit`: payout as multiplier (0.92 → profit factor).
- No intra-trade martingale — stake recalculated on next entry only.

**Deprecated:** `martingale_calculator.py` (fixed $2 increment, 10% risk rule, intra-trade gales).

---

## 7. Detection & scan pipeline

```
get_open_assets() → prefetch paralelo (5m + 1m) vía parallel_fetch.py
    → for each OTC asset:
    → strat_a.evaluate() + strat_b.evaluate()
    → entry_scorer.score()
    → executor picks best candidate
    → massaniello.next_stake(payout)
    → place_order()
    → await result → massaniello.register_win/loss()
```

Concurrency: `CANDLE_FETCH_CONCURRENCY = 2` (semáforo en `parallel_fetch.py`; subir en producción según carga).

---

## 8. Constraints & limits

| Constraint | Value | Source |
|------------|-------|--------|
| Max concurrent trades | 1 | `config.py` |
| Max loss per session | 20% drawdown | `MAX_LOSS_SESSION` |
| Entry max lag | 1.5s | `ENTRY_MAX_LAG_SEC` (target <300ms in #5) |
| Greylist | `USDDZD_otc` | `GREYLIST_ASSETS` |
| Asset loss streak limit | 3 → blacklist 60min | `ASSET_LOSS_STREAK_LIMIT` |
| Tests must not use broker | mock in `conftest.py` | Harness rule |

---

## 9. ML assumptions

**Current state:** No ML models in production pipeline.

- `dynamic_weight_calibration` (#10) will adjust scorer weights from trade history — not ML, rule-based optimization.
- `kelly_criterion_sizing` (#13) uses historical win rate — statistical, not neural.
- If ML is introduced later, it must: (a) have SDD spec, (b) not call broker from model code, (c) have synthetic tests.

---

## 10. Coding conventions (summary)

Full rules: `docs/conventions.md`.

| Rule | Standard |
|------|----------|
| Python | 3.10+, PEP 8, 100 char lines |
| Strings | Double quotes |
| Async | `asyncio.sleep()`, never `time.sleep()` |
| Errors | Domain exceptions in `errors.py` |
| Tests | `tests/test_<module>.py`, pytest, synthetic data |
| Logging | stdlib `logging` in bot; `loguru` per conventions doc |
| Class example | `MassanielloRiskManager` (not MartingaleCalculator) |

---

## 11. Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `QUOTEX_EMAIL` | Yes | Broker login |
| `QUOTEX_PASSWORD` | Yes | Broker login |
| `QUOTEX_DEMO_SSID` | No | Skip login if set |

**Never commit `.env`.** Never print credentials in logs or chat.

---

## 12. Document cross-reference

| Topic | Authoritative doc |
|-------|-------------------|
| Feature states | `feature_list.json` |
| Roadmap phases | `docs/ROADMAP.md` |
| Architecture layers | `docs/architecture.md` |
| Session handoff | `agent/HANDOFF.md` |
| SDD process | `docs/specs.md` |
| Quality gates | `CHECKPOINTS.md` |