# Design — smart_order_place

## Problem (evidence from consolidation_bot.log)

1. `buy_timeout_60s` / `120s` / `200s` — user waits, no order, weak UI.
2. Broker `unexpected` on many OTC assets — retry loop logs always say "unexpected".
3. Flow today: wait open → **then** create trade_client (~4s) → buy.
4. Alt retries call full `sync_and_validate` again (can burn another minute).
5. Hub has no `last_order_attempt` — looks idle.

## Approach

| Change | Where |
|--------|--------|
| Prewarm trade_client before/during open wait | `executor.enter_trade` / `_sync_to_next_candle_open` |
| `skip_open_wait` / `reuse_open` flag for alt retries | `enter_trade` + `scanner` alt loop |
| Real reason in logs + quarantine cycles | `scanner` alt loop + `executor` fail path |
| `bot.last_order_attempt` | set in executor; read in `hub/server._enrich_with_bot` |
| UI line | `hub/static/index.html` near trade card / session |
| Config `ORDER_FAIL_QUARANTINE_CYCLES = 5` | `config.py` |

## enter_trade signature extension

```python
async def enter_trade(..., *, skip_open_wait: bool = False) -> bool:
```

- `skip_open_wait=False` (default): current behavior + **prewarm**:
  1. Start/create trade_client (await or concurrent with wait)
  2. `sync_and_validate` wait for open
  3. buy (client already warm)
- `skip_open_wait=True` (alts): `compute_timing` on **current** candle open only;
  if not ok → one full `sync_and_validate` then buy.

## last_order_attempt shape

```python
{
  "asset": "XAUUSD_otc",
  "direction": "call",
  "status": "failed",  # waiting_open | sending | accepted | failed
  "reason": "buy_timeout_60s",
  "ts": 1720000000.0,
}
```

## Non-goals

- Changing Massaniello stakes
- Changing STRAT-F signal logic / stoch zones
- Fixing Quotex broker itself
