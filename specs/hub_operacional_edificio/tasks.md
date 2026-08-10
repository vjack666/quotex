# Tasks — hub_operacional_edificio (Feature 41)

Checklist ejecutable. Cada task referencia al menos un R<n>.

## Fase 1 — Acceso directo y modo de cuenta
- [ ] T1 — Crear `scripts/make_webapp_lnk.py` que genera `C:\Users\v_jac\Desktop\QUOTEX Web App.lnk` apuntando a `python app.py` con `StartIn` = raíz del repo. Fallback a `.bat` si faltan `winshell`/`pywin32`. Cubre: R1.
- [ ] T2 — Añadir `EDIFICIO_ALLOW_REAL = False` en `config.py` y lógica en `edificio_executor.py` que bloquea `account_type=REAL` salvo que `EDIFICIO_ALLOW_REAL=True` Y credenciales presentes. Cubre: R2, R3.
- [ ] T3 — Exponer `account_type` y `allow_real` en `/api/state` (server.py `_enrich_with_bot`). Cubre: R3.

## Fase 2 — Massaniello desde el inicio
- [ ] T4 — En `consolidation_bot.py` BotRunner.start, confirmar/garantizar que `self.massaniello` se construye ANTES del primer ciclo de scan y se aplica `apply_bankroll_shape_to_manager` al arranque. Cubre: R4.
- [ ] T5 — En `edificio_executor.execute_contratados`, derivar `amount` de `bot.massaniello.next_stake(payout)` cuando `STAKE_MODE=massaniello`. Cubre: R5.
- [ ] T6 — Tests: init temprano de Massaniello + derivación de monto. Cubre: R4, R5, R14.

## Fase 3 — Caja negra 1m agresiva sin borrado
- [ ] T7 — `BlackBoxRecorder.RETENTION_DAYS = 0`; desactivar `_cleanup_old_files` (reemplazar por export job). Cubre: R8.
- [ ] T8 — Añadir `record_piso1_snapshot(asset, candles_1m, stoch_m1)` y llamarlo desde `edificio_contratacion.py` al entrar a PISO_1. Cubre: R7.
- [ ] T9 — Ampliar ventana `candles_1m` a 60 velas previas y `candles_post` hasta resolución (leer buffer del bot). Cubre: R6, R9.
- [ ] T10 — Script de export periódico `scripts/export_blackbox.py` (zip/jsonl a `exports/black_box/`) sin borrar raw. Cubre: R8, R9.
- [ ] T11 — Tests: grabación 1m sin borrado + snapshot piso1 + ventana ampliada. Cubre: R6, R7, R8, R9, R14.

## Fase 4 — Mejora del hub (+110%) y limpieza
- [ ] T12 — Auditar `hub/strat_f_panel.py` y tab STRAT-F en index.html: si son huérfanos, eliminar o reconvertir a vista del Edificio. Documentar en `progress/impl_hub_operacional.md`. Cubre: R11.
- [ ] T13 — Añadir al hub: KPI modo cuenta, panel Massaniello en vivo, tab Caja Negra con filtros, botón Exportar. Cubre: R10.
- [ ] T14 — Eliminar endpoints/controles duplicados detectados en la auditoría. Cubre: R11.

## Fase 5 — Verificación física (R12) y cierre
- [ ] T15 — Arrancar hub en background (`python app.py --no-browser` o con HUB_NO_OPEN) y verificar con navegador: tabs, ctrl-bar (start/stop/reconnect/force-kill/shutdown), cada `<select>` de config (TODAS las opciones), botón exportar. Reparar o eliminar lo que no responda. Cubre: R12.
- [ ] T16 — Capturas + log de respuestas en `reports/hub_verificacion/`. Cubre: R12.
- [ ] T17 — Test de wiring de cada botón (llamadas `/api/*` reales vía TestClient o requests). Cubre: R12, R14.
- [ ] T18 — `pytest tests/` en verde para código nuevo. Cubre: R14.
- [ ] T19 — Marcar feature `done` en feature_list.json; mover resumen a `progress/history.md`; limpiar temp. Cubre: cierre.

## Trazabilidad
- R1 → T1
- R2 → T2
- R3 → T2, T3
- R4 → T4, T6
- R5 → T5, T6
- R6 → T9, T11
- R7 → T8, T11
- R8 → T7, T10, T11
- R9 → T9, T10, T11
- R10 → T13
- R11 → T12, T14
- R12 → T15, T16, T17
- R13 → T2 (trazabilidad en orden/edificio_executor ya hereda feature 40)
- R14 → T6, T11, T17, T18
