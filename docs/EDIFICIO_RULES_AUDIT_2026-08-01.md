# Auditoría de reglas EDIFICIO — 2026-08-01

Objetivo: marcar exactamente dónde vive cada regla del edificio para que cualquier
backtest, ajuste o rollback toque solo lo necesario.

## 1. Reglas vivas

| Regla | Valor | Código | Documentación | Backtest flag |
|---|---|---|---|---|
| Payout mínimo | `MIN_PAYOUT = 80` | `src/config.py:18` | `docs/EDIFICIO_CONTRATACION.md` | implícito |
| Sticky threshold | `EDIFICIO_STICKY_THRESHOLD = 3.0` | `src/config.py:62` | `docs/EDIFICIO_CONTRATACION.md` | Ninguna |
| Body 5m mínimo | `EDIFICIO_BODY_FILTER_MIN_RATIO = 0.03` | `src/config.py:63` | Pendiente | `strategy_details.filters_applied` |
| Versión de reglas | `EDIFICIO_RULE_VERSION = "2026-08-01b"` | `src/config.py:64` | Pendiente | `strategy_details.rule_version` |
| Max intentos orden | `EDIFICIO_MAX_ORDER_TRIES = 2` | `src/config.py:61` | `src/edificio_executor.py` | Ninguna |
| Frescura evento | `EDIFICIO_MAX_EVENT_AGE_SEC = 120` | `src/config.py:66` | `src/edificio_executor.py` | Ninguna |
| Entry sync vela | `ENTRY_SYNC_TO_CANDLE = True` | `src/config.py:36` | `src/scanner.py` | Ninguna |

## 2. Puerta de contratación P3

Lógica central: `src/edificio_contratacion.py:281-329`

```
if card.piso == PISO_3:
    if not payout_ok → expulsado
    calcular body_5m = body / total_range desde candles_5m[-1] o close_candle_5m
    contract_now = direction válida
                 and (cross_ok or cross_sticky)
                 and extreme_ok
                 and (body_5m is None or body_5m > 0.03)
```

Registro en black box: `src/edificio_executor.py:290-316`
- Guarda `rule_version` y `filters_applied` en `strategy_details`

## 3. Umbral estocástico

- Threshold sticky: `src/config.py:62`
- Cálculo: `src/edificio_executor.py:37`
- Uso en scanner: `src/scanner.py:1500`
- Tests: `tests/test_edificio_executor.py:210`

Decisión 2026-08-01: NO modificar threshold. Datos disponibles (21 trades
resueltos) no muestran correlación entre separación K/D y win rate.

## 4. Backtest / auditoría

- Versión de reglas: `EDIFICIO_RULE_VERSION` en `src/config.py:64`
- Flag por trade: `strategy_details.rule_version` + `filters_applied[]`
- Tabla black box: `data/db/black_box_strat_*.db/scan_candidates`
- No existe motor de backtest formal para EDIFICIO en este proyecto
- Cualquier nuevo filtro debe:
  1. Agregar constante en `src/config.py`
  2. Documentar en esta tabla
  3. Agregar campo en `strategy_details` de `src/edificio_executor.py`
  4. Test unitario en `tests/test_edificio_contratacion.py`

## 5. Qué no tocar sin autorización

- `src/edificio_contratacion.py` fuera de P3
- `src/edificio_executor.py` fuera de `_record_sent_to_black_box`
- `EDIFICIO_STICKY_THRESHOLD` (sin evidencia cuantitativa)
- Cualquier regla sin test verde previo
