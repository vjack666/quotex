# Requirements — strategy_reversal_swing

> Feature id=7. Estrategia de reversión en niveles de soporte/resistencia dinámicos.
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Señal PUT en resistencia

CUANDO el precio toca un nivel de resistencia dinámico con mecha superior (wick)
Y la vela cierra por debajo del máximo, `detect_reversal_swing` DEBE devolver
`("put", strength)` con fuerza proporcional al tamaño de la mecha.

## R2 — Señal CALL en soporte

CUANDO el precio toca un nivel de soporte dinámico con mecha inferior
Y la vela cierra por encima del mínimo, `detect_reversal_swing` DEBE devolver
`("call", strength)` con fuerza proporcional al tamaño de la mecha.

## R3 — Sin señal si no hay toque confirmado

CUANDO no se detecta ni toque de soporte ni de resistencia con confirmación de
mecha, `detect_reversal_swing` DEBE devolver `None`.

## R4 — Lógica pura sin I/O

`detect_reversal_swing` DEBE procesar cada conjunto de velas de forma aislada,
sin mantener estado entre llamadas ni realizar llamadas de red.

## R5 — Integración scanner

CUANDO el scanner ejecuta un ciclo de escaneo, DEBE evaluar reversal_swing para
cada activo OTC abierto, después del bloque momentum y antes del bloque STRAT-A.

## R6 — CandidateEntry con metadata

CUANDO `detect_reversal_swing` retorna una señal, el scanner DEBE crear un
`CandidateEntry` con `_strategy_origin="STRAT-REVERSAL-SWING"`, la `direction`
correspondiente y una pseudo-zone basada en el high/low de la vela actual.

## R7 — Tests con datos sintéticos

Los tests DEBEN verificar que una vela con mecha en resistencia genera PUT,
una vela con mecha en soporte genera CALL, y que sin toque no hay señal.
