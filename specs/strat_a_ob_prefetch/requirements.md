# Requirements — strat_a_ob_prefetch

> Feature id=21. Fase SA-5 del track STRAT-A (`docs/ROADMAP_STRAT_A.md`).
> Cerrar gaps entre orquestación de prefetch existente (#3) y acceptance literal:
> blocks precalculados, cero I/O OB en evaluate, cache TTL coherente.
> Depende de #20 `strat_a_htf_zone_wiring`.
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Prefetch OB 3m en fase dedicada (paralelo)

CUANDO `scan_all` ejecuta el ciclo de prefetch, el sistema DEBE descargar velas OB
3m (`ORDER_BLOCK_TF_SEC = 180`) mediante `asyncio.gather` con semáforo
`CANDLE_FETCH_CONCURRENCY` y `candle_cache`, **antes** de
`_scan_phase_evaluate_assets`.

La fase 3b (`prefetch_strat_a_secondary`) cumple este requisito: OB se pide en
paralelo (no secuencial por activo) con el mismo patrón de concurrencia que 5m/1m.
No se exige un único `gather` compartido con 5m/1m si ello implica fetches OB para
activos que nunca llegan a STRAT-A.

## R2 — Subconjunto strat_a_symbols para OB

CUANDO el prefetch secundario OB+H1 se ejecuta, el sistema DEBE limitar fetches OB
3m a `symbols_needing_strat_a_prefetch` (activos con velas 5m suficientes y filtros
de skip aplicados), reutilizando `candles_5m` ya prefetched.

## R3 — Sin fetch OB en hot path evaluate

CUANDO `_scan_phase_evaluate_assets` evalúa cada activo, el sistema NO DEBE invocar
`fetch_candles_with_retry` ni `cache.get_or_update` con `tf_sec=180` (OB 3m) dentro
de ese bucle.

## R4 — Campo blocks_by_symbol en ScanCycleData

El sistema DEBE extender `ScanCycleData` con
`blocks_by_symbol: dict[str, dict[str, list[OrderBlock]]]` poblado durante el
prefetch secundario.

## R5 — Precálculo detect_order_blocks en prefetch

CUANDO `prefetch_strat_a_secondary` (o su evolución) resuelve `candles_ob` y
`ob_tf_labels` por símbolo, el sistema DEBE calcular
`blocks_by_symbol[sym] = detect_order_blocks(candles_ob[sym])` en esa fase, no en
evaluate.

## R6 — Consumo de blocks precalculados en scanner

CUANDO `_scan_phase_evaluate_assets` prepara la evaluación STRAT-A de un activo, el
sistema DEBE obtener blocks desde `cycle.blocks_by_symbol.get(sym, {"bull": [], "bear": []})`
y NO DEBE invocar `detect_order_blocks` en el bucle de evaluación.

## R7 — evaluate_strat_a recibe blocks del ciclo

CUANDO el scanner invoca `evaluate_strat_a`, el sistema DEBE pasar el mismo dict
`blocks` obtenido de `cycle.blocks_by_symbol` para ese símbolo (tras fallback vacío
si no hubo prefetch).

## R8 — Fallback 5m para velas OB insuficientes

CUANDO el fetch OB 3m devuelve menos de 6 velas para un símbolo, el sistema DEBE
resolver velas OB con fallback a `candles_5m` (`ob_tf_label = "5m_fallback"`) y DEBE
calcular blocks sobre esas velas resueltas, conservando `_resolve_ob_candles`.

## R9 — Cache OB por activo con TTL coherente

CUANDO el prefetch OB usa `bot.candle_cache`, el sistema DEBE almacenar/recuperar
velas bajo clave `(asset, ORDER_BLOCK_TF_SEC)` con TTL `CANDLE_CACHE_TTL_SEC`
(300s), permitiendo actualización incremental en hits de cache.

## R10 — order_blocks_by_asset para radar

CUANDO el scanner consume `cycle.blocks_by_symbol` en evaluate, el sistema DEBE
seguir asignando `self.bot.order_blocks_by_asset[sym] = blocks` para que
`radar_watch_tick` reutilice blocks del último full scan.

## R11 — Eliminar código muerto _fetch_ob_candles

El sistema DEBE eliminar el método `AssetScanner._fetch_ob_candles` y limpiar imports
huérfanos asociados; no debe quedar call site activo a fetch OB per-asset en
`scanner.py`.

## R12 — Telemetría de prefetch

El sistema DEBE mantener el log `scan_fetch_elapsed_ms` en prefetch primario y DEBE
registrar la fase `3b/5` con conteo de símbolos OB. Opcional (P2): añadir
`blocks_precalc=N` al log de prefetch secundario.

## R13 — Rendimiento no lineal en I/O OB

El tiempo de prefetch OB para N activos elegibles NO DEBE escalar linealmente como
N fetches secuenciales; un test con mocks DEBE verificar paralelismo (p. ej.
`prefetch_span < sequential * 0.75` con N≥4) o ausencia total de I/O OB en evaluate
(R3).

## R14 — Test blocks_by_symbol poblado

El sistema DEBE incluir un test que verifique que tras `prefetch_strat_a_secondary`
(orquestación equivalente), `blocks_by_symbol[sym]` contiene keys `bull` y `bear`.

## R15 — Test equivalencia blocks

El sistema DEBE incluir un test que verifique que `blocks_by_symbol[sym]` es
idéntico al resultado de `detect_order_blocks(candles_ob[sym])` invocado
directamente (regresión).

## R16 — Test fallback 5m blocks

El sistema DEBE incluir un test que verifique blocks calculados sobre velas 5m cuando
el mock OB devuelve menos de 6 velas.

## R17 — Test cache OB incremental

El sistema DEBE incluir un test que verifique que una segunda llamada de prefetch OB
para el mismo `(sym, 180)` no repite full fetch innecesario cuando el cache está
vigente (mock contador de llamadas).

## R18 — Test cero fetch OB en evaluate

El sistema DEBE incluir un test que verifique ausencia de llamadas a
`fetch_candles_with_retry` con `tf_sec=180` durante `_scan_phase_evaluate_assets`.

## R19 — Test blocks llegan a evaluate_strat_a

El sistema DEBE incluir un test que inyecte blocks conocidos en `ScanCycleData` y
verifique (spy) que `evaluate_strat_a` recibe exactamente esos blocks.

## R20 — Regresión suite existente

CUANDO se ejecuta `python -m pytest tests/ -v`, todos los tests existentes DEBEN
permanecer verdes tras los cambios de esta feature, incluidos
`test_scan_all_prefetches_before_eval` (actualizado si cambian conteos de fase).

## R21 — Trazabilidad R→test

El implementer DEBE documentar en `progress/impl_strat_a_ob_prefetch.md` el mapa
completo `R<n> → nombre_de_test` para cada requirement de este spec.

## R22 — init.ps1 en verde

CUANDO se ejecuta `.\init.ps1`, el sistema DEBE terminar con código de salida 0.