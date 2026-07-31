# Edificio de Contratación — Troubleshooting

Bitácora de problemas reales, causa raíz y solución aplicada.

---

## 1. Hub con lock antiguo impide arrancar

- **Síntoma:** `Another QUOTEX webapp instance is already running (lock: ...\runtime\main.lock)`
- **Causa:** `stop_webapp.bat` no terminaba instancias previas; lockfile quedaba vivo por proceso Edge residual.
- **Solución:** usar lockfile como fuente de verdad; no matar PIDs directamente. Reiniciar con `stop_webapp.bat` y luego `app.py` en comandos separados.

## 2. Bot no inyectado en hub al inicio (`bot_no_edificio`)

- **Síntoma:** `/api/contract/execute` devolvía `bot_no_edificio` en el primer request.
- **Causa:** `_bot_ref=None` hasta un segundo request; race condition entre startup y primer request.
- **Solución:** fallback lazy en endpoints hacia `app._runner.bot`; mantener `set_bot()` como inyección principal.

## 3. `/api/contract/probe` cargaba pero daba 500

- **Síntoma:** traceback `NameError: name 'CONTRACT_DEFAULT_AMOUNT' is not defined`.
- **Causa:** patch anterior no persistió constantes en `hub/server.py`.
- **Solución:** definir `CONTRACT_DEFAULT_AMOUNT = 1.0` y `CONTRACT_DEFAULT_DURATION = 900` en módulo.

## 4. Proceso combinado `stop + start` moría con exit 127

- **Síntoma:** `cmd.exe /c stop_webapp.bat && sleep 2 && python app.py` fallaba.
- **Causa:** shell sin job control + lockfile; el `&&` no garantizaba estado limpio.
- **Solución:** separar stop y start en comandos distintos.

## 5. Código cacheado sin parches (`bot_no_edificio` repetido)

- **Síntoma:** error reaparecía aunque el código estaba corregido.
- **Causa:** proceso hub cargaba código viejo desde `__pycache__`.
- **Solución:** reinicio explícito con limpieza de `__pycache__` antes de relanzar.

## 6. Historial de contratados contaminado

- **Síntoma:** `contratados_recientes` acumulaba eventos de pruebas previas.
- **Solución:** método `reset_contratados_recientes()` + snapshot inicial en `data\logs\edificio_snapshot_<timestamp>.json`.

## 7. Caja negra no registraba eventos detallados

- **Síntoma:** logs existían pero sin contexto de edificio.
- **Solución:** auditoría confirmó DB y log activos; próximamente inyectar `black_box_cid` y detalle de piso/condiciones en cada `ContratadoEvent`.

## 8. CONTRATADO en el hub pero la orden nunca sale al broker (2026-07-31)

- **Síntoma:** el activo aparece en `CONTRATADO` (piso 4) y en "Contratados recientes", pero no llega ninguna orden al broker. Reportado con NZDCAD_otc.
- **Causa raíz:** el único consumidor de `pop_contratados()` era `_auto_contract_loop` (hub/server.py), que SOLO se arrancaba dentro de `hub.server.run_server()`. El arranque real (`start_webapp.bat → app.py → uvicorn.run(_hub_app)`) nunca pasa por `run_server` → el loop jamás corría. El import `run_server as _hub_run_server` en app.py estaba muerto.
- **Solución (aplicada):** la ejecución de contratados ahora la hace el **BOT** en cada ciclo de scan (`src/edificio_executor.py::execute_contratados`, llamado en scanner.py tras `_feed_edificio`), usando el socket único (regla de oro). `_auto_contract_loop` del hub fue eliminado para evitar doble orden. Los eventos fallidos se re-encolan (máx. `EDIFICIO_MAX_ORDER_TRIES`), ya no se pierden.
- **Extras del fix:** filtro `cross_sticky` ahora se calcula y pasa al edificio (`EDIFICIO_STICKY_THRESHOLD`); logger `edificio_contratacion` conectado a la bitácora del bot; el hub renderiza el piso 4 con estado de la orden (enviada/falló/esperando).
- **Gate de frescura (2026-07-31):** si el evento CONTRATADO espera más de `EDIFICIO_MAX_EVENT_AGE_SEC` (120s — p.ej. por un trade abierto), la señal ya no es válida: NO se envía la orden obsoleta y el activo vuelve a P3 con sus POIs intactos para re-contratar solo con una señal fresca. Ver `_expire_event` en `src/edificio_executor.py`.
- **✅ RESUELTO EN VIVO (2026-07-31 12:32):** 3 órdenes enviadas al broker con id confirmado (USDNGN CALL, XAGUSD PUT, XRPUSD CALL) — flujo P1→P2→P3→CONTRATADO→ORDEN ENVIADA en el mismo ciclo de scan, sin re-encolados ni rechazos.
- **Trazabilidad pendiente:** las órdenes del edificio no quedan en scan_candidates (black box) ni en trade_journal.candidates; solo en el log. Considerar registrar order_id en black box para resultados.
- **⚠ REINICIO REQUERIDO:** el proceso vivo corre código viejo. Reiniciar con `start_webapp.bat` (o `stop_webapp.bat` + `app.py`) para activar el fix.
