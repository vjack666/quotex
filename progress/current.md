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

## 2026-07-31 — Diagnóstico forense EDIFICIO WIN/LOSS (sin cierres)

### Hallazgo
El edificio envía 60 órdenes (`order_id` presente, `decision=BUY`, `order_status=sent`),
pero **ninguna tiene `order_result` ni `profit`** en `black_box_strat_2026-07-31.db`.
Además, **STRAT-F tampoco muestra cierres** en esta DB.

### Causa raíz
`resolve_contratados()` **no está resolviendo**:
- La ruta de cierre de EDIFICIO depende de `check_win(order_ref)` y, ante `profit==0`
  o timeout, `_resolve_one()` marca la orden como `UNRESOLVED` y deja `resolved=True`
  localmente, pero **solo llama a `record_order_result()` cuando obtiene WIN/LOSS**.
- En la DB, **no hay evidencia de que el resolvedor haya escrito ningún cierre**
  para EDIFICIO, y las filas UUID únicas tampoco se cierran; por lo tanto,
  el problema no es duplicación de order_id, sino que el flujo de resolución
  no está completándose. Conclusión: **`resolve_contratados()` no está siendo
  llamado efectivamente, o `check_win()` nunca retorna un valor no-cero**
  para estas 60 órdenes**.

### Evidencia forense
- Script: `progress/forense_edificio_winloss_2026-07-31.py`
- Resultados:
  - `('EDIFICIO', None, 60)` → 60 órdenes enviadas, 0 con resultado.
  - `order_result=NULL` para todas las filas EDIFICIO con `order_id`.
  - 16 filas tienen `close_candle_15m/5m/stoch` no nulos; el resto,
    nunca tocados por el cierre.
  - No hay `order_id` duplicados relevantes más allá de OID-77/OID-88
    (test fixtures).
- Código revisado:
  - `src/edificio_executor.py`: `_record_sent_to_black_box()` registra el envío;
    `_resolve_one()` solo escribe `record_order_result()` cuando
    `interpret_broker_result()` devuelve `(WIN/LOSS, profit)`; si devuelve
    `None`, **no actualiza la DB** y deja `resolved=True`, impidiendo reintento
    posterior aunque el trade finalmente liquide.

### Siguiente paso recomendado
1. Confirmar con logs del proceso si `resolve_contratados()` realmente entra
   y cuántos intentos hace por orden.
2. Si `check_win()` retorna `0`/`None` hasta el vencimiento, el diagnóstico
   pasa al nivel de conexión/broker (`src/connection.py`).
3. No modificar lógica productiva hasta aislar si es llamada o broker.
