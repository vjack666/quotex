# Design — session_awareness

> **Feature ID:** 21
> **Architecture layer:** Analysis (scanner) — pure functions + config

---

## New Module

### `src/session_awareness.py`

Pure functions, no I/O.

| Function | Signature | Purpose |
|----------|-----------|---------|
| `detect_session` | `(utc_hour: int) -> str` | Returns session name |
| `get_session_config` | `(session: str) -> dict` | Returns config for session |
| `should_block` | `(session: str) -> bool` | True if session is blocked |
| `get_min_score` | `(session: str, default: int) -> int` | Returns adjusted min_score |

---

## Session Detection

```python
def detect_session(utc_hour: int) -> str:
    """Detect trading session from UTC hour."""
    if 0 <= utc_hour < 8:
        return "asian"
    elif 8 <= utc_hour < 16:
        return "london"
    elif 16 <= utc_hour < 21:
        return "new_york"
    else:  # 21-24
        return "off_hours"
```

---

## Session Config

```python
SESSION_CONFIGS = {
    "asian": {
        "min_score": 65,      # Higher bar — low volatility
        "enabled": True,
        "label": "Asian (00:00-08:00 UTC)",
    },
    "london": {
        "min_score": 60,      # Standard bar
        "enabled": True,
        "label": "London (08:00-16:00 UTC)",
    },
    "new_york": {
        "min_score": 55,      # Lower bar — high volatility
        "enabled": True,
        "label": "New York (16:00-21:00 UTC)",
    },
    "off_hours": {
        "min_score": 75,      # Very high bar — erratic
        "enabled": False,     # Block by default
        "label": "Off-hours (21:00-00:00 UTC)",
    },
}
```

---

## Main Entry Point

```python
from datetime import datetime, timezone

def get_current_session() -> tuple[str, dict]:
    """Get current session and its config."""
    utc_hour = datetime.now(timezone.utc).hour
    session = detect_session(utc_hour)
    config = SESSION_CONFIGS[session]
    return (session, config)

def get_effective_min_score(default: int = 60) -> int:
    """Get min_score adjusted for current session."""
    if not SESSION_AWARENESS_ENABLED:
        return default

    session, config = get_current_session()
    if not config["enabled"]:
        return 999  # Effectively block all

    return config["min_score"]
```

---

## Integration Points

### 1. Scanner (`scanner.py`)

At the start of each scan cycle:

```python
# Session awareness
if SESSION_AWARENESS_ENABLED:
    session, session_cfg = get_current_session()
    effective_min = session_cfg["min_score"]

    if not session_cfg["enabled"]:
        log.info(f"[SESSION] {session_cfg['label']} — entradas bloqueadas")
        continue  # Skip this scan

    log.info(f"[SESSION] {session_cfg['label']} | min_score={effective_min}")
else:
    effective_min = STRAT_F_MIN_SCORE
```

Then use `effective_min` instead of `STRAT_F_MIN_SCORE` in the acceptance check.

### 2. Config (`config.py`)

```python
# Session Awareness
SESSION_AWARENESS_ENABLED = True
SESSION_ASIAN_MIN_SCORE = 65
SESSION_LONDON_MIN_SCORE = 60
SESSION_NEWYORK_MIN_SCORE = 55
SESSION_OFF_HOURS_MIN_SCORE = 75
SESSION_OFF_HOURS_ENABLED = False
```

---

## File Changes

| File | Action | What |
|------|--------|------|
| `src/session_awareness.py` | CREATE | Pure functions |
| `src/config.py` | MODIFY | Add SESSION_* constants |
| `src/scanner.py` | MODIFY | Use session-aware min_score |
| `tests/test_session_awareness.py` | CREATE | 10+ unit tests |

---

## Alternatives Discarded

1. **Per-asset session config:** Too complex. OTC assets behave similarly across sessions.

2. **ML-based session detection:** Overkill. Simple time-of-day is sufficient for v1.

3. **Dynamic session boundaries:** Would require historical analysis. Fixed boundaries work for v1.

4. **Disable entire bot during off-hours:** Too aggressive. Better to just raise the threshold.
