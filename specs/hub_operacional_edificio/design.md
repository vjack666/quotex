# Design — hub_operacional_edificio (Feature 41)

Este diseño se apoya en el código YA existente (no se reinventa): `app.py`, `hub/server.py`, `hub/static/index.html`, `src/edificio_executor.py`, `src/edificio_contratacion.py`, `src/black_box_recorder.py`, `src/massaniello_engine.py`, `src/massaniello_persistence.py`, `src/hub_bankroll_store.py`, `src/connection.py`, `config.py`. La feature 40 (fábrica de herramientas) ya enchufó el gate en `edificio_contratacion.py`.

## Contexto encontrado (hechos del disco)
- `hub/server.py`: ya lee `bot.massaniello` (líneas 201-244) y expone `/api/contract/execute`, `/api/contract/probe`, `/api/stake-mode`, `/api/config`, `/api/massaniello/preview`. El auto-start del bot al abrir el hub está en `app.py:142`.
- `src/edificio_executor.py`: ya consume `CONTRATADO` y llama `place_order(client, account_type=...)` con `EDIFICIO_SEND_ORDERS_ENABLED` y `EDIFICIO_ACCOUNT_TYPE` (de `config.py`).
- `src/black_box_recorder.py`: ya guarda `candles_1m`, `candles_5m`, `candles_15m`, `candles_post`, `stoch_m1/m5/m15`. Tiene `RETENTION_DAYS = 30` y `_cleanup_old_files()` que BORRA DBs >30 días (esto contradice R8; se cambia a 0).
- `feature 40` gate ya enchufado en `edificio_contratacion.py` (import `_fab`, CAPA FABRICA en bloque CONTRATADO).

## Decisiones técnicas

### D1 — Acceso directo (.lnk)
Crear `C:\Users\v_jac\Desktop\QUOTEX Web App.lnk` apuntando a `python app.py` (launcher FastAPI que abre el hub en `0.0.0.0:8080`). En Windows, el .lnk apunta al intérprete python del venv activo + ruta absoluta a `app.py`, con `StartIn` = raíz del repo. Script auxiliar `scripts/make_webapp_lnk.py` (genera el .lnk vía `winshell` o `pywin32` si están disponibles; si no, crea un `.bat` equivalente y documenta). Alternativa descartada: atajo manual — se prefiere script reproducible para no depender de edición a mano.

### D2 — Envío a cuenta (R2/R3)
No se toca `edificio_executor.py` en su lógica de envío; ya soporta `account_type`. La integración es:
- `config.EDIFICIO_ACCOUNT_TYPE` se lee al arranque (ya existe).
- El hub expone el modo en `/api/state` (`base["account_type"]`) y en panel de config (R10).
- La única novedad: un flag de seguridad `EDIFICIO_ALLOW_REAL` (default `False`) en `config.py` que BLOQUEA `account_type=REAL` a menos que el humano lo ponga explícitamente + credenciales presentes. Esto cumple la regla de no tocar credenciales y de no enviar a REAL sin OK humano.

### D3 — Massaniello desde el inicio (R4/R5)
- En `consolidation_bot.py` (BotRunner.start), asegurar que `self.massaniello = build_manager(...)` se instancie ANTES del primer ciclo de scan (ya existe la referencia; se confirma el orden de init).
- `edificio_executor.execute_contratados` ya recibe `amount`; se sobreescribe con `bot.massaniello.next_stake(payout)` cuando `STAKE_MODE=massaniello` y el manager existe.
- `hub_bankroll_store.apply_bankroll_shape_to_manager` ya aplica forma en vivo; se invoca en el arranque para fijar la curva desde el comienzo.

### D4 — Caja negra 1m agresiva (R6/R7/R8/R9)
- `BlackBoxRecorder.RETENTION_DAYS = 0` (desactiva `_cleanup_old_files`). Se sustituye el borrado por un job de EXPORT periódico a `exports/black_box/` (zip/jsonl) que NO borra el raw.
- Nuevo método `record_piso1_snapshot(asset, candles_1m, stoch_m1)` llamado desde `edificio_contratacion.py` cuando un activo entra a PISO_1.
- `record_candidate` ya guarda `candles_1m`; se amplía la ventana a 60 velas previas (R9) leyendo del buffer del bot (`bot._candle_cache_1m` o equivalente) en lugar de las 5 fijas.
- Post-cierre: `update_candidate` ya escribe `candles_post`; se extiende hasta la resolución de la orden (loop en `edificio_executor`).

### D5 — Mejora del hub (+110%) (R10)
Sobre `index.html` (2293 líneas) y `server.py`:
- Añadir KPI de modo de cuenta (demo/real) con color.
- Añadir panel de Massaniello "en vivo" (ya hay datos en `/api/state`; se renderiza con barras de progreso de bankroll).
- Añadir tab "Caja Negra" con filtros (por estrategia, por activo, por fecha) usando `/api/blackbox`.
- Añadir botón "Exportar caja negra" que descarga el zip de `exports/`.
- Menos pasos para operar: el ctrl-bar ya tiene start/stop/reconnect/force-kill/shutdown; se verifica cada uno (R12).

### D6 — Eliminación de redundancia (R11)
- `StratFPanel` / `strat_f_panel.py` / refs STRAT-F en el hub: el Edificio es la única estrategia viva (feature_list.json id 36). Se audita si `hub/strat_f_panel.py` y el tab STRAT-F del index.html son huérfanos. Si lo son, se eliminan o se reconvirtieron a vista del Edificio. Se documenta en `progress/impl_hub_operacional.md`. NO se borra código del motor del Edificio.

### D7 — Verificación física (R12)
Se usa navegador (browser_navigate + snapshot + click + type) contra `http://127.0.0.1:8080` con el hub corriendo en background. Checklist: cada tab, cada botón del ctrl-bar, cada `<select>` de config (probar TODAS las opciones, no una), cada botón de guardar. Evidencia en `reports/hub_verificacion/` (capturas + log de respuestas `/api/*`).

## Alternativas descartadas
- Reactivar STRAT-F: descartado (arquitectura muerta, AGENTS.md).
- LSTM/torch para predicción en vivo: descartado (EXP-084 mostró AUC 0.52; fuera de scope operativo).
- Borrar caja negra por retención: descartado por R8 (Ruben: "nunca se borra vela").

## Riesgos
- Enviar a REAL sin querer: mitigado por `EDIFICIO_ALLOW_REAL=False` por defecto (D2).
- Export masivo de caja negra: mitigado por export periódico, no borrado.
- Hub no arranca en Windows (rutas): mitigado por el .lnk con `StartIn` correcto y `app.py` ya UTF-8-safe.
