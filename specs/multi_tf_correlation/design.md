# Design — multi_tf_correlation

> **Feature ID:** 19
> **Architecture layer:** Analysis (scanner) — pure functions in new module

---

## New Module

### `src/multi_tf_correlation.py`

Pure functions, no I/O.

| Function | Signature | Purpose |
|----------|-----------|---------|
| `detect_trend` | `(candles: list[Candle], threshold: float = 0.001) -> str` | Returns "CALL", "PUT", or "NEUTRAL" |
| `calculate_confluence` | `(trends: dict[str, str], h1_available: bool = True) -> tuple[str, float]` | Returns (label, bonus) |
| `compute_confluence_bonus` | `(candles_1m, candles_5m, candles_15m, candles_1h, config) -> tuple[str, float, dict]` | Main entry point |

---

## Trend Detection

```python
import numpy as np

def detect_trend(candles: list[Candle], threshold: float = 0.001) -> str:
    """Detect trend using linear regression slope."""
    if len(candles) < 3:
        return "NEUTRAL"

    closes = np.array([c.close for c in candles[-10:]])  # Last 10 max
    x = np.arange(len(closes))

    # Linear regression: y = mx + b
    m, _ = np.polyfit(x, closes, 1)

    # Normalize slope by price level
    avg_price = np.mean(closes)
    normalized_slope = m / avg_price if avg_price > 0 else 0.0

    if normalized_slope > threshold:
        return "CALL"
    elif normalized_slope < -threshold:
        return "PUT"
    else:
        return "NEUTRAL"
```

---

## Confluence Calculation

```python
def calculate_confluence(
    trends: dict[str, str],
    h1_available: bool = True,
) -> tuple[str, float]:
    """Calculate confluence bonus from multi-TF trends.

    Returns (label, bonus).
    """
    # Count aligned trends (excluding NEUTRAL)
    call_count = sum(1 for t in trends.values() if t == "CALL")
    put_count = sum(1 for t in trends.values() if t == "PUT")
    total_active = call_count + put_count

    # Determine dominant direction
    if call_count > put_count:
        aligned = call_count
        direction = "CALL"
    elif put_count > call_count:
        aligned = put_count
        direction = "PUT"
    else:
        # Tie or all neutral
        return ("CONFLICT", -0.05)

    # Calculate bonus based on available timeframes
    if h1_available and len(trends) == 4:
        if aligned == 4:
            return (f"4/4_{direction}", 0.15)
        elif aligned == 3:
            return (f"3/4_{direction}", 0.05)
        else:
            return (f"{aligned}/4_{direction}", -0.05)
    else:
        # H1 not available — use 3 TF
        if aligned == 3:
            return (f"3/3_{direction}", 0.10)
        elif aligned == 2:
            return (f"2/3_{direction}", 0.03)
        else:
            return (f"{aligned}/3_{direction}", -0.03)
```

---

## Main Entry Point

```python
def compute_confluence_bonus(
    candles_1m: list[Candle],
    candles_5m: list[Candle],
    candles_15m: list[Candle],
    candles_1h: list[Candle] | None = None,
    threshold: float = 0.001,
) -> tuple[str, float, dict]:
    """Compute confluence bonus for a candidate.

    Returns (label, bonus, trend_details).
    """
    trends = {
        "M1": detect_trend(candles_1m, threshold),
        "M5": detect_trend(candles_5m, threshold),
        "M15": detect_trend(candles_15m, threshold),
    }

    h1_available = candles_1h is not None and len(candles_1h) >= 3
    if h1_available:
        trends["H1"] = detect_trend(candles_1h, threshold)

    label, bonus = calculate_confluence(trends, h1_available)

    return (label, bonus, trends)
```

---

## Integration Points

### 1. Scanner (`scanner.py`)

After STRAT-F evaluation, before acceptance check:

```python
# Multi-TF confluence
if CONFLUENCE_ENABLED:
    label, bonus, trends = compute_confluence_bonus(
        candles_1m, candles_5m, candles_15m, candles_1h,
        CONFLUENCE_TREND_THRESHOLD,
    )
    f_candidate.score = round(f_candidate.score + bonus, 1)
    log.info(
        f"[CONFLUENCE] {sym}: M1={trends['M1']} M5={trends['M5']} "
        f"M15={trends['M15']} H1={trends.get('H1','N/A')} → {label} {bonus:+.2f}"
    )
```

### 2. Config (`config.py`)

```python
# Multi-TF Confluence
CONFLUENCE_ENABLED = True
CONFLUENCE_BONUS_4OF4 = 0.15
CONFLUENCE_BONUS_3OF4 = 0.05
CONFLUENCE_PENALTY_LOW = -0.05
CONFLUENCE_TREND_THRESHOLD = 0.001
```

---

## File Changes

| File | Action | What |
|------|--------|------|
| `src/multi_tf_correlation.py` | CREATE | Pure functions |
| `src/config.py` | MODIFY | Add CONFLUENCE_* constants |
| `src/scanner.py` | MODIFY | Add confluence computation after STRAT-F eval |
| `tests/test_multi_tf_correlation.py` | CREATE | 12+ unit tests |

---

## Alternatives Discarded

1. **Weighted scoring per TF:** More complex, same result. Simple majority wins.

2. **Correlation coefficient (Pearson):** Overkill for 4 binary signals. Simple counting is sufficient.

3. **Dynamic thresholds per asset:** Would require per-asset history. Adds complexity. Use global threshold for v1.

4. **Add confluence as a new ML feature:** Better to keep it as explicit scoring first, then feed into LightGBM as feature in v2.
