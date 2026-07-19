# Requirements — strat_f_maturing_m15_recheck

> Feature #16 (SDD). Corrección de la sala de espera STRAT-F (maturing_watchlist)
> para no promover entradas contra la tendencia M15 visible, aplicando la teoría
> de "agotamiento del contra-movimiento" (confirmación por estocástico M5).

## Contexto (evidencia previa)

Auditoría 2026-07-18 sobre 43 operaciones demo de 5min grabadas:
- `evaluate_strat_f` YA tiene el filtro R1 (strat_fractal.py:274-277): si M15
  bajista y direction=CALL → salta; si M15 alcista y direction=PUT → salta.
- PERO 13/43 operaciones aceptadas eran CONTRA la tendencia M15 visible.
- Causa raíz: `maturing_watchlist` promueve (`mark_promoted`) usando
  `f_eval.m15_context` = contexto de CUANDO se detectó la zona, NO el actual
  al promover (scanner.py:2436, 2468). Si la tendencia viró mientras la
  zona maduraba, la entrada sale contra-tendencia sin re-chequeo.

## R1

CUANDO el scanner promueve una entrada STRAT-F desde `maturing_watchlist`
(llamada a `mark_promoted`, modo live o shadow), el sistema DEBE re-evaluar el
contexto M15 **actual** del activo (no el contexto capturado en la detección).

## R2

SI tras el re-chequeo M15 la dirección propuesta queda contra-tendencia
(M15=`downtrend` y direction=`CALL`, o M15=`uptrend` y direction=`PUT`),
ENTONCES el sistema NO DEBE promover la entrada sin confirmación de agotamiento.

## R3

DONDE la dirección quedó contra-tendencia (R2), el sistema DEBE exigir
confirmación de agotamiento del contra-movimiento mediante el estocástico M5 en
zona extrema a favor de la dirección propuesta:
- CALL contra-M15-bajista → stoch M5 `%K` < 20 (sobreventa = el impulso
  bajista se agotó).
- PUT contra-M15-alcista → stoch M5 `%K` > 80 (sobrecompra = el impulso
  alcista se agotó).

## R4

SI la dirección quedó contra-tendencia (R2) Y NO hay confirmación de
agotamiento (R3), ENTONCES el sistema DEBE descartar la entrada (`drop` de la
watchlist) en vez de promoverla u operarla.

## R5

SI la dirección está alineada con el contexto M15 actual (no contra-tendencia),
EL SISTEMA DEBE promover la entrada con la lógica existente (sin exigir stoch).

## R6

MIENTRAS una entrada está en la sala de espera (`maturing_watchlist`), el
sistema DEBE seguir escaneando y operando otras señales normales
(no bloquear el ciclo del scanner por la espera).

## R7

El conteo Massaniello (sesión) NO DEBE incrementarse en la promoción: solo se
incrementa en el `buy()` real. La promoción/descarte de la watchlist no consume
una operación de la sesión.

## R8

El sistema DEBE registrar en el log el motivo de cada promoción o descarte
re-chequeado (ej. `MATURING promote ok (m15 aligned)` o
`MATURING drop (contra-tendencia sin agotamiento stoch)`), para auditoría.
