# Design — kelly_criterion_sizing (Enhanced)

> **Feature ID:** 20
> **Architecture layer:** Execution (risk management)
> **Replaces:** Original kelly_sizer.py (Feature 13)

---

## Updated Module

### `src/kelly_sizer.py` (enhanced)

| Method | Signature | Purpose |
|--------|-----------|---------|
| `calculate` | `(strategy: str = None, ml_confidence: float = None) -> dict` | Calculate Kelly with full details |
| `_rolling_win_rate` | `(n: int = 50, strategy: str = None) -> tuple[int, int]` | Get wins/total from last N trades |
| `_edge` | `(win_rate: float, avg_payout: float) -> float` | Calculate edge |
| `_dynamic_fraction` | `(edge: float) -> float` | Fraction based on edge strength |
| `_confidence_adjust` | `(fraction: float, confidence: float) -> float` | Adjust for ML confidence |

### Return Format

```python
{
    "kelly_full": 0.28,       # Full Kelly factor
    "kelly_adjusted": 0.14,   # After fraction + confidence
    "win_rate": 0.60,         # Rolling win rate
    "avg_payout": 0.90,       # Average payout
    "edge": 0.14,             # Edge = wr*payout - (1-wr)
    "fraction": 0.5,          # Applied fraction (dynamic)
    "confidence": 0.72,       # ML confidence if available
    "stake": 3.15,            # Final stake in dollars
    "strategy": "STRAT-F",    # Strategy filter
}
```

---

## Rolling Win Rate

```python
def _rolling_win_rate(self, n: int = 50, strategy: str = None) -> tuple[int, int]:
    """Get wins/total from last N resolved trades."""
    query = """
        SELECT COUNT(*) as total,
               SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins
        FROM candidates
        WHERE decision = 'ACCEPTED'
          AND outcome IN ('WIN', 'LOSS')
    """
    params = []
    if strategy:
        query += " AND strategy_origin = ?"
        params.append(strategy)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(n)

    row = self.conn.execute(query, params).fetchone()
    return (row["wins"] or 0, row["total"] or 0)
```

---

## Dynamic Fraction

```python
def _dynamic_fraction(self, edge: float) -> float:
    """Choose fraction based on edge strength."""
    if edge > 0.2:
        return 0.5   # Half-Kelly
    elif edge > 0.1:
        return 0.3   # Conservative
    elif edge > 0.0:
        return 0.1   # Minimal
    else:
        return 0.0   # No edge → don't trade
```

---

## Confidence Adjustment

```python
def _confidence_adjust(self, fraction: float, confidence: float) -> float:
    """Adjust fraction based on ML confidence."""
    if confidence is None:
        return fraction  # No ML → use base fraction

    if confidence > 0.7:
        return fraction * 1.2
    elif confidence > 0.4:
        return fraction * 1.0
    else:
        return fraction * 0.5
```

---

## Stake Calculation

```python
def _calculate_stake(self, balance: float, kelly_adjusted: float) -> float:
    """Calculate final stake with limits."""
    MIN_STAKE = 1.0
    MAX_STAKE_PCT = 0.05

    raw_stake = balance * kelly_adjusted
    max_stake = balance * MAX_STAKE_PCT

    return max(MIN_STAKE, min(raw_stake, max_stake))
```

---

## Integration

### 1. Scanner (per-trade)

After LightGBM prediction, before order placement:

```python
# Kelly sizing per trade
kelly = kelly_sizer.calculate(
    strategy="STRAT-F",
    ml_confidence=confidence,  # from LightGBM
)
if kelly["stake"] > 0:
    amount = kelly["stake"]
    log.info(
        f"[KELLY] WR={kelly['win_rate']:.1%} payout={kelly['avg_payout']:.0%} "
        f"edge={kelly['edge']:.3f} → stake=${amount:.2f}"
    )
```

### 2. Config (`config.py`)

```python
KELLY_ENABLED = True
KELLY_FRACTION = 0.5              # Half-Kelly default
KELLY_MIN_TRADES = 10             # Minimum for statistical significance
KELLY_ROLLING_WINDOW = 50         # Last N trades for rolling WR
KELLY_MIN_STAKE = 1.0
KELLY_MAX_STAKE_PCT = 0.05        # 5% of balance
```

---

## File Changes

| File | Action | What |
|------|--------|------|
| `src/kelly_sizer.py` | MODIFY | Enhance with rolling WR, dynamic fraction, confidence |
| `src/config.py` | MODIFY | Add KELLY_* constants |
| `src/scanner.py` | MODIFY | Use Kelly per-trade instead of fixed initial_amount |
| `tests/test_kelly_sizer.py` | MODIFY | Add tests for new features |

---

## Alternatives Discarded

1. **Per-asset Kelly:** Not enough data per asset yet. Global STRAT-F Kelly for v1.

2. **Bayesian Kelly:** More complex, same result for our data volume. Simple rolling WR is sufficient.

3. **Replace Massaniello entirely:** Too risky. Kelly adjusts the capital; Massaniello still manages the session structure.

4. **Real-time Kelly (update after each trade):** Adds complexity. Recalculate every 10 trades instead for stability.
