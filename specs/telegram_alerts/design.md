# Design — Telegram Alerts

## Files

| File | Action | Description |
|------|--------|-------------|
| `src/alerter.py` | **CREATE** | `TelegramAlerter` class + module-level singleton |
| `tests/test_alerter.py` | **CREATE** | 8+ tests with mocked `requests.post` |
| `src/massaniello_risk.py` | **MODIFY** | Add alerter calls in `register_win` / `register_loss` |
| `src/executor.py` | **MODIFY** | Add alerter call in `refresh_balance_and_risk` |
| `src/consolidation_bot.py` | **MODIFY** | Add alerter call on connection failure in main loop |

## Module: `src/alerter.py`

### Class: `TelegramAlerter`

- Constructor reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from `os.environ`.
- If either is empty/falsy, `_enabled = False` and all methods no-op returning `False`.
- Uses `requests.post` to `https://api.telegram.org/bot{token}/sendMessage` with JSON payload.
- Timeout: 10 seconds. Errors are logged at WARNING level, never propagated.
- `parse_mode: "HTML"` for bold text and formatting.

### Methods

| Method | Signature | Event |
|--------|-----------|-------|
| `send_message` | `(text: str) -> bool` | Raw message (low-level) |
| `alert_session_complete` | `(wins: int, capital: float) -> bool` | R4 |
| `alert_losing_streak` | `(losses: int, capital: float) -> bool` | R5 |
| `alert_connection_lost` | `() -> bool` | R6 |
| `alert_stop_loss` | `(drawdown_pct: float, capital: float) -> bool` | R7 |

### Cooldown Mechanism (R10)

- Internal dict `_last_alert: dict[str, float]` tracks last send time per event_type.
- Configurable `COOLDOWNS = {"connection_lost": 300, "default": 60}`.
- `_can_alert(event_type: str) -> bool` checks and updates the timestamp.
- Each alert method passes a unique event_type key.

### Module-level singleton

```python
alerter = TelegramAlerter()
```
Any module can `from alerter import alerter` and call methods directly.
This avoids dependency injection for a simple cross-cutting concern.

## Integration Hooks

### `massaniello_risk.py` — register_win (R4)

After `log.info("🎯 SESIÓN MASSANIELLO CUMPLIDA")`, add:
```python
from alerter import alerter
alerter.alert_session_complete(self.wins, self.current_balance or 0.0)
```

### `massaniello_risk.py` — register_loss (R5)

After `status = "SESSION_FAILED"`, add:
```python
from alerter import alerter
alerter.alert_losing_streak(self.losses, self.current_balance or 0.0)
```

### `executor.py` — refresh_balance_and_risk (R7)

At the stop-loss trigger (line ~631-637), after `self.bot.session_stop_hit = True`, add:
```python
from alerter import alerter
alerter.alert_stop_loss(drawdown * 100, bal)
```

### `consolidation_bot.py` — main loop (R6)

When `ensure_connection()` returns `False` (line ~341-343), add:
```python
from alerter import alerter
alerter.alert_connection_lost()
```

## Discarded Alternatives

1. **python-telegram-bot library** — Heavy dependency (20MB+) for a simple REST call.
   `requests` already installed, so it adds zero new deps (per architecture.md §3).

2. **Dependency Injection / Observer pattern** — Over-engineered for 4 event types.
   Module-level import is simple, testable (we mock requests, not the class), and
   matches existing patterns in the project (e.g., `metrics = PipelineMetrics()` in
   `instrumentation_layer.py`, `get_journal()` in `trade_journal.py`).

3. **urllib.request** — Works but more verbose and harder to mock cleanly.
   `requests` is already at 2.32.4, no reason to avoid it.

## Traceability

| Requirement | Test(s) |
|------------|---------|
| R1 | `test_send_message_success` |
| R2 | `test_send_message_disabled_when_no_env` |
| R3 | (covered by using existing `requests` lib) |
| R4 | `test_alert_session_complete` |
| R5 | `test_alert_losing_streak` |
| R6 | `test_alert_connection_lost` |
| R7 | `test_alert_stop_loss` |
| R8 | All tests in `test_alerter.py` |
| R9 | `test_alert_session_complete`, `test_alert_stop_loss` |
| R10 | `test_cooldown_suppresses_duplicates` |
