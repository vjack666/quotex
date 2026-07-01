# Design — massaniello_risk

## Módulos

| Archivo | Rol |
|---------|-----|
| `src/massaniello_engine.py` | Port de `masaniello.py`: `Settings`, `calculate_stake`, `simulate` |
| `src/massaniello_risk.py` | `MassanielloRiskManager`: sesión 1h, wins/losses, API del bot |
| `src/config.py` | Constantes Massaniello + `RISK_MANAGER` |
| `src/executor.py` | Stakes, bloqueo de entradas, sin martingala |
| `src/consolidation_bot.py` | Instancia `massaniello`, `session_start_time`, force PRACTICE |

## Flujo

1. `set_session_start_balance` → `massaniello.set_balance` + `session_start_time`.
2. Antes de entrar → `can_enter()` / `_massaniello_session_blocks_entry()`.
3. Monto → `next_stake(payout_pct)`.
4. Cierre WIN/LOSS → `register_win` / `register_loss`; si sesión termina → `session_stop_hit`.

## Desactivación martingala

Cuando `RISK_MANAGER == "massaniello"`:

- `_try_enter_martin_now`, `_process_pending_martin`, `_monitor_trade_live` (martin) no operan.
- `compensation_pending` no bloquea entradas.
- `stage == "martin"` rechazado en `enter_trade`.