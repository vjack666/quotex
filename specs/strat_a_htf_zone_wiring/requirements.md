# Requirements — strat_a_htf_zone_wiring

> Feature id=20. Fase SA-4 del track STRAT-A (`docs/ROADMAP_STRAT_A.md`).
> Cablear `HTFScanner` (15m en background) y `zone_memory` en el pipeline STRAT-A.
> Depende de #19 `strat_a_quality_filters` (done).
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Tarea asyncio HTFScanner

CUANDO `consolidation_bot.main()` inicia el bot tras conexión exitosa, el sistema DEBE
lanzar `HTFScanner.run_forever()` como tarea `asyncio.create_task` independiente del
loop de scan principal.

## R2 — Cancelación HTF en shutdown

CUANDO el bot finaliza (`shutdown_background_tasks` o bloque `finally` de `main`), el
sistema DEBE cancelar la tarea HTF activa.

## R3 — Import de fetch 15m

El sistema DEBE resolver `HTFScanner._fetch_15m` importando `fetch_candles_with_retry`
desde `connection`, no desde `consolidation_bot`.

## R4 — Payout HTF alineado con STRAT-A

CUANDO `HTFScanner` resuelve activos elegibles para refresco 15m, el sistema DEBE
usar `STRAT_A_MIN_PAYOUT` como umbral mínimo de payout.

## R5 — Lectura no bloqueante de 15m

CUANDO el scanner evalúa un activo STRAT-A con `has_signal=True`, el sistema DEBE
obtener velas 15m únicamente mediante `bot.htf_scanner.get_candles_15m(sym)`.

## R6 — Sin fetch 15m en hot path

CUANDO el scanner ejecuta la fase de evaluación STRAT-A por activo, el sistema NO
DEBE invocar `fetch_candles_with_retry` con `tf_sec=900` dentro de ese bucle.

## R7 — Veto HTF datos insuficientes

CUANDO `len(candles_15m) < 10` para una señal STRAT-A aceptada por
`evaluate_strat_a`, el sistema DEBE rechazar la señal y NO DEBE añadir candidato en
ese ciclo.

## R8 — Veto HTF tendencia contraria

CUANDO la tendencia 15m inferida con `infer_h1_trend` contradice la dirección de la
señal (`call` con `bearish` o `flat`, `put` con `bullish` o `flat`), el sistema DEBE
rechazar la señal y NO DEBE añadir candidato en ese ciclo.

## R9 — Veto HTF antes de candidato (ruta principal)

CUANDO `evaluate_strat_a` devuelve `has_signal=True` en `_scan_phase_evaluate_assets`,
el sistema DEBE aplicar el veto HTF antes de invocar `_candidate_from_strat_a_evaluation`.

## R10 — Veto HTF en ruta radar

CUANDO `radar_watch_tick` produce señal STRAT-A con `has_signal=True`, el sistema
DEBE aplicar el mismo veto HTF que en la ruta principal de scan.

## R11 — Log de rechazo HTF

CUANDO el scanner rechaza una señal STRAT-A por HTF, el sistema DEBE registrar un log
que identifique el activo y la razón de rechazo HTF.

## R12 — Población zone_memory

CUANDO se construye un `CandidateEntry` STRAT-A que supera el veto HTF, el sistema
DEBE asignar `candidate.zone_memory` con el resultado de
`query_nearby_zones(journal.db_path, sym, price)`.

## R13 — Score zone_memory con historia

CUANDO `query_nearby_zones` devuelve al menos una zona histórica relevante para el
precio y dirección del candidato, el sistema DEBE reflejar un valor distinto de cero
en `candidate.score_breakdown["zone_memory"]` tras `score_candidate`.

## R14 — Campo candles_15m en candidato

El sistema DEBE exponer en `CandidateEntry` un campo `candles_15m` poblado con las
velas 15m usadas para veto HTF.

## R15 — Trend score con velas 15m

CUANDO el candidato dispone de al menos 25 velas en `candles_15m`, el sistema DEBE
calcular el componente `trend` del score usando esas velas 15m.

## R16 — Veto muro zone_memory

CUANDO el ajuste `score_zone_memory` del candidato es menor o igual a `-10.0`, el
sistema DEBE rechazar el candidato antes de añadirlo a la lista de candidatos del
ciclo.

## R17 — Test veto HTF datos insuficientes

El sistema DEBE incluir un test que verifique rechazo cuando `get_candles_15m`
devuelve menos de 10 velas.

## R18 — Test veto HTF misaligned

El sistema DEBE incluir un test que verifique rechazo de señal CALL con tendencia 15m
bearish.

## R19 — Test zone_memory poblado y scoring

El sistema DEBE incluir un test con journal SQLite fixture que verifique
`candidate.zone_memory` no vacío y `score_breakdown["zone_memory"]` distinto de cero
cuando existe historia relevante.

## R20 — Test sin fetch 15m en hot path

El sistema DEBE incluir un test que verifique ausencia de fetch 15m durante la fase
de evaluación STRAT-A.

## R21 — Test import fetch HTF

El sistema DEBE incluir un test que verifique que `HTFScanner._fetch_15m` no lanza
`ImportError` al resolver el import de `connection.fetch_candles_with_retry`.

## R22 — Regresión de suite existente

CUANDO se ejecuta `python -m pytest tests/ -v`, todos los tests existentes DEBEN
permanecer verdes tras los cambios de esta feature.

## R23 — Trazabilidad R→test

El implementer DEBE documentar en `progress/impl_strat_a_htf_zone.md` el mapa completo
`R<n> → nombre_de_test` para cada requirement de este spec.

## R24 — init.ps1 en verde

CUANDO se ejecuta `.\init.ps1`, el sistema DEBE terminar con código de salida 0.