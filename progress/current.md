# Estado de sesión

<!-- Plantilla — la sesión 2026-07-31 (purga: solo Edificio) está en progress/history.md -->

## 2026-07-31 — Backfill de auditoría de caja negra (COMPLETADO)

### Qué se hizo
- Backfill de las **16 órdenes EDIFICIO reales** (order_id UUID v4) en
  `data/db/black_box_strat_2026-07-31.db`: stoch_m15 (k/d), extreme_read,
  velas 15m/5m previas con shapes (`candle_15m_prev`/`candle_5m_prev` en
  strategy_details) y contexto de cierre (`close_candle_15m/5m`,
  `close_stoch_m15`, `exit_price`).
- Hallazgo: `get_candles` con `end_from_time` histórico **no es fiable**
  (broker ignora el timestamp, devuelve velas recientes y cruza respuestas
  del buzón compartido). Solución: `get_historical_candles(asset, 8h, period)`.
- Bot reiniciado (supervisor 28412 + hijo 27008, hub HTTP 200 en :8080).
- Commits en main: `47981c2` (feature auditoría), `15bb867` (fix STRAT-F
  dirección PUT + arranque), `9c691e9` (docs/bitácora).

### Pendiente
- Nada bloqueado. 41 tests pre-existentes fallando (NO tocar, deuda ajena).
- `runtime/main.lock` modificado = estado runtime del bot (no commitear).
