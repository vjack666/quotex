# Evolution Plan — quotex-hft-bot (Post Math Filters)

> **Objective:** Transform the bot from rule-based scoring to adaptive ML-driven trading.
> **Constraint:** OTC assets only — no news/sentiment analysis.
> **Workflow:** Zero human intervention during development. Human approves docs only.
> **Last updated:** 2026-07-20

---

## Current State

### What We Have
- STRAT-F strategy: fractal M5 + Wyckoff band + M15 context + M1 rejection
- Math filters: Hurst exponent, R² regression, price angle, Bollinger squeeze
- Contextual scoring: proportional zones + M15 weight + consensus bonus
- Stochastic V2: zone-based help with cross-aware vetos
- Black box: collecting math_quality, stoch zones, spring_margin, outcomes
- Risk management: Massaniello + daily loss guard
- Infrastructure: 24/7 operation, auto-reconnect, parallel evaluation

### What's Missing
1. **Adaptive learning** — Current scoring is a static formula. No learning from outcomes.
2. **Dynamic sizing** — Massaniello is fixed. Doesn't adapt to actual win rate.
3. **Multi-timeframe confluence** — Only checks M15 context. Doesn't measure alignment strength.
4. **Temporal patterns** — Ignores time-of-day effects on OTC volatility.

---

## Feature Roadmap

### Feature 18: LightGBM Adaptive Scorer
**Impact:** ⭐⭐⭐⭐⭐ | **Complexity:** High | **Duration:** 2-3 weeks

Replace the static scoring formula with a LightGBM model that predicts trade outcomes using the 30+ features already collected in the black box.

**Why first:** All other features benefit from better predictions. The data is already being collected.

**Key output:** `confidence` (0.0-1.0) that replaces the manual score_breakdown weights.

**Dependencies:** 500+ resolved trades in black box (currently collecting).

---

### Feature 19: Multi-TF Confluence Score
**Impact:** ⭐⭐⭐ | **Complexity:** Low | **Duration:** 3-5 days

Measure alignment strength between M1, M5, M15, and H1 timeframes. High confluence = high conviction. Low confluence = skip.

**Why second:** Simple to implement, immediate value, reduces false signals.

**Key output:** `confluence_bonus` (-0.15 to +0.15) added to final score.

**Dependencies:** None (H1 data already prefetched).

---

### Feature 20: Enhanced Kelly Criterion
**Impact:** ⭐⭐⭐⭐ | **Complexity:** Medium | **Duration:** 1 week

Upgrade the existing KellySizer to use rolling win rate, per-strategy filtering, and integration with LightGBM confidence scores.

**Why third:** Needs LightGBM (Feature 18) for accurate win rate per signal quality level.

**Key output:** Dynamic `kelly_fraction` that adjusts position size based on edge.

**Dependencies:** Feature 18 (LightGBM) for confidence-based win rate separation.

---

### Feature 21: Session Awareness
**Impact:** ⭐⭐ | **Complexity:** Low | **Duration:** 2-3 days

Detect trading session (Asian/London/NY/off-hours) and adjust minimum score thresholds and strategy selection.

**Why last:** Lowest impact but easy to implement. Can be done in parallel with Feature 19.

**Key output:** `session_config` dict that modifies bot behavior by time-of-day.

**Dependencies:** None.

---

## Execution Order — Multi-Agent Parallel Strategy

```
PHASE 1 (Parallel — 2 agents):
  Agent A (@implementer): Feature 18 — LightGBM Scorer
    T1-T5: deps + ml_features.py + ml_scorer.py + tests
  Agent B (@implementer): Feature 19 — Multi-TF Correlation
    T1-T3: multi_tf_correlation.py + config + tests

PHASE 2 (Sequential — depends on Phase 1):
  Feature 18 Integration (T10-T16): scanner wiring + auto-retrain + tests
  (Feature 19 already done in Phase 1)

PHASE 3 (Parallel — 2 agents):
  Agent A (@implementer): Feature 20 — Enhanced Kelly Criterion
    T1-T9: rolling WR + dynamic fraction + confidence adjust + tests
  Agent B (@implementer): Feature 21 — Session Awareness
    T1-T5: session detection + config + tests

PHASE 4 (Integration — 1 agent):
  Final integration: wire all features into scanner, smoke test, commit
```

### Why This Parallelization Works

| Feature | Files Touched | Conflict Risk |
|---------|---------------|---------------|
| #18 LightGBM | ml_scorer.py, ml_features.py, scanner.py (one section) | LOW — new files, isolated scanner section |
| #19 Multi-TF | multi_tf_correlation.py, scanner.py (different section) | LOW — new file, different scanner section |
| #20 Kelly | kelly_sizer.py (existing), scanner.py (different section) | MEDIUM — modifies existing file |
| #21 Session | session_awareness.py, scanner.py (different section) | LOW — new file, different scanner section |

### Agent Assignments

- **@implementer** × 2 in Phase 1: LightGBM and Multi-TF are completely independent (different new files, no overlap)
- **@implementer** × 2 in Phase 3: Kelly and Session are independent (Kelly modifies kelly_sizer.py, Session creates new file)
- **@auditor** reviews after each phase before merging

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Win rate | ~55% (estimated) | >60% with ML filtering |
| Signals per day | ~10-15 | 5-8 (fewer but higher quality) |
| Max drawdown | Unknown | <15% with Kelly |
| False signals | ~45% | <35% with confluence filter |

---

## Risk Mitigation

1. **LightGBM overfitting:** Use walk-forward validation, not single train/test split.
2. **Kelly ruin risk:** Always use half-Kelly (0.5x multiplier), never full Kelly.
3. **Model staleness:** Retrain weekly on latest 500+ trades.
4. **Feature drift:** Monitor feature distributions monthly, retrain if drift detected.

---

## Human Approval Points

1. **After doc review:** Approve this plan + all 4 specs → Hermes begins implementation.
2. **After Feature 18:** Review LightGBM accuracy metrics before deploying to production.
3. **After Feature 20:** Review Kelly sizing parameters before live trading.
4. **No other approvals needed** — all other decisions are documented in specs.
