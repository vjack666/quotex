# Hub — Bankroll Massaniello (Operación)

> Fecha: 2026-07-14

## Propósito

Permitir al usuario **asignar cuánto arriesgar** en binarias sin usar el balance
completo de la cuenta PRACTICE/REAL, y ver el **próximo stake** antes de
guardar o iniciar el bot.

## UI (pestaña Operación)

Card **Bankroll binarias** (después de Balance):

| Campo | Persistido al Guardar | Efecto |
|-------|----------------------|--------|
| Capital asignado | `massaniello_virtual_capital` | Bankroll de la secuencia Massaniello |
| Ops / ITM | `massaniello_ops` / `massaniello_wins` | Forma de la secuencia y stakes |
| Payout mín. % | `min_payout` | Piso del escáner + fórmula de stake |
| Próximo stake | (preview) | En vivo en el navegador; no requiere Guardar |

- Editable solo con bot **detenido**.
- **Guardar bankroll** aplica al proceso y deja traza en log.

## Motor

- Fórmula: `src/massaniello_engine.py` (`calculate_stake`) — paridad con
  `Desktop/massaniello/masaniello.py`.
- Preview API: `GET /api/massaniello/preview` (app.py).
- Preview JS: misma tabla de multiplicadores en `hub/static/index.html` para
  feedback instantáneo al cambiar Ops/ITM/capital/payout.

## Escáner

Al guardar `min_payout`, se actualizan:

- `config.MIN_PAYOUT`
- `config.STRAT_A_MIN_PAYOUT`
- `config.STRAT_F_MIN_PAYOUT`

El scan lista activos con `payout ≥ min_payout`.

## Resolve de resultados (relacionado)

No marcar LOSS si el broker aún no liquidó (`profitAmount == 0`). Ver
`TradeExecutor._interpret_broker_result` y constantes `MARTIN_RESOLVE_*` en
`config.py`.
