# Requirements — strat_a_quality_filters

> Feature id=19. Fase SA-3 del track STRAT-A (`docs/ROADMAP_STRAT_A.md`).
> Endurecer filtros *reject-first* del PLAN MAESTRO para STRAT-A: payout ≥87%,
> score ≥75 fijo, zona ≥30 min en rebotes, patrón 1m obligatorio en rebotes.
> **Fuera de alcance:** cableado HTF 15m y `zone_memory` (#20).
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Constantes de configuración STRAT-A

El sistema DEBE definir en `src/config.py` las constantes
`STRAT_A_MIN_PAYOUT=87`, `STRAT_A_MIN_SCORE=75` y
`STRAT_A_ZONE_MIN_AGE_REBOUND=30`.

## R2 — Exclusión por payout en scan STRAT-A

CUANDO un activo OTC abierto tiene `payout < STRAT_A_MIN_PAYOUT`, el sistema
DEBE excluirlo de la evaluación STRAT-A en ese ciclo de scan y DEBE registrar
un log que identifique el activo, el payout observado y el umbral
`STRAT_A_MIN_PAYOUT`.

## R3 — Edad mínima de zona en rebotes

CUANDO `evaluate_strat_a()` evalúa un rebote (`entry_mode` en
`rebound_ceiling` o `rebound_floor`) y la edad de la zona es menor que
`STRAT_A_ZONE_MIN_AGE_REBOUND` minutos, el sistema DEBE devolver
`has_signal=False` con `skip_reason="zone_too_young"`.

## R4 — Patrón 1m obligatorio en rebotes

CUANDO `evaluate_strat_a()` evalúa un rebote y no existe patrón 1m confirmado
(`pattern_name="none"` o `confirms=False` o `strength` menor que el mínimo de
rebote para la dirección), el sistema DEBE devolver `has_signal=False` y NO
DEBE devolver `has_signal=True` para ese rebote.

## R5 — Log explícito de rechazo por patrón en rebote

CUANDO el scanner descarta un rebote STRAT-A por patrón 1m insuficiente o
ausente (`skip_reason` en `pattern_insufficient`, `pattern_missing` o
`strict_pattern_veto`), el sistema DEBE registrar un log que contenga el
símbolo del activo, el modo de entrada rebote y una referencia explícita al
patrón 1m (p. ej. `patrón 1m`, `sin patrón` o el nombre del patrón).

## R6 — Umbral fijo de score para STRAT-A en select_best

CUANDO el pipeline de selección invoca `select_best` sobre candidatos del
ciclo, los candidatos STRAT-A con `score < STRAT_A_MIN_SCORE` NO DEBEN
aparecer en la lista `selected` devuelta por `select_best`.

## R7 — Umbral STRAT-A independiente del adaptativo global

CUANDO el umbral dinámico de sesión (`session_threshold` derivado de
`ADAPTIVE_THRESHOLD_*`) es menor que `STRAT_A_MIN_SCORE`, el sistema DEBE
aplicar `STRAT_A_MIN_SCORE` como umbral efectivo para candidatos STRAT-A en
`select_best`.

## R8 — Sin regresión en otras estrategias

CUANDO existen candidatos STRAT-B o STRAT-MOMENTUM en el mismo ciclo, el
sistema DEBE seguir aplicando el umbral dinámico de sesión a esos candidatos
sin elevar su umbral a `STRAT_A_MIN_SCORE`.

## R9 — Payout global sin cambio

El sistema NO DEBE modificar el valor de `MIN_PAYOUT` (80) ni el filtro global
de `get_open_assets` usado por STRAT-B, STRAT-MOMENTUM u otros módulos.

## R10 — Test unitario veto payout

El sistema DEBE incluir un test que verifique que un activo con
`payout < STRAT_A_MIN_PAYOUT` no produce candidato STRAT-A en el ciclo de
evaluación.

## R11 — Test unitario veto edad de zona

El sistema DEBE incluir un test que verifique que un rebote con zona de edad
inferior a `STRAT_A_ZONE_MIN_AGE_REBOUND` devuelve `has_signal=False` y
`skip_reason="zone_too_young"`.

## R12 — Test unitario veto patrón en rebote

El sistema DEBE incluir un test que verifique que un rebote sin patrón 1m
confirmado devuelve `has_signal=False` y no genera candidato STRAT-A puntuado.

## R13 — Test integración veto score en select_best

El sistema DEBE incluir un test que verifique que un candidato STRAT-A con
`score` entre el umbral adaptativo y `STRAT_A_MIN_SCORE` (p. ej. score=70 con
`session_threshold=65`) queda fuera de `selected` tras `select_best`.

## R14 — Regresión de suite existente

CUANDO se ejecuta `python -m pytest tests/ -v`, todos los tests existentes
DEBEN permanecer verdes tras los cambios de esta feature.

## R15 — Trazabilidad R→test

El implementer DEBE documentar en `progress/impl_strat_a_quality_filters.md` el
mapa completo `R<n> → nombre_de_test` para cada requirement de este spec.

## R16 — init.ps1 en verde

CUANDO se ejecuta `.\init.ps1`, el sistema DEBE terminar con código de salida 0.