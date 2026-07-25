# Requirements — Mejora del SPIKE con agotamiento verdadero (Fase A de Wyckoff)

> Feature: `strat_f_spike_wyckoff_phase_a` (mejora de `strat_fractal.evaluate_strat_f`,
> modo SPIKE existente + `stochastic_zones.apply_stoch_help` + `stoch_exhaustion`).
> NO reescribe el SPIKE: lo eleva de "M5 en extremo + cuerpo a favor" a
> "agotamiento verdadero en la ZONA S/R con cruce M15 confirmado + M5 alineado".
> Mapea el evento a la Fase A de Wyckoff (Spring / Upthrust = parada de tendencia).

## R1 — Anclaje a la ZONA S/R del fractal (NO se olvida la zona)
MIENTRAS el SPIKE evalúa una señal, el sistema DEBE anclar la zona de agotamiento
a la banda del fractal Wyckoff (suelo para CALL, techo para PUT) ya calculada en
`evaluate_strat_f`, usando `zone.floor`/`zone.ceiling` del `ConsolidationZone`.
El sistema NO DEBE usar un umbral de pips fijo (`band * 0.0015`); en su lugar
DEBE usar la banda de tolerancia de la zona calculada por `zone_strength`
(grosor × [1−velocidad], fuente principal) o, en su defecto, por `adaptive_zone`
(rango % del precio). Ver R7.

## R2 — Cruce M15 confirmado (nuevo, del watchdog)
CUANDO el SPIKE detecta agotamiento, el sistema DEBE exigir que el estocástico
M15 tenga un cruce %K/%D confirmado en la dirección de la entrada con
`cross_ago >= 1` (>=1 vela M15 desde el cruce), usando `_cross_ago_in_series`
de `stochastic_m15.compute_stoch`. SI no hay cruce confirmado, el sistema
DEBE dejar la señal en modo REBOUND (no SPIKE).

## R3 — M15 y M5 AMBOS alineados (filtro de paciencia, NO suma de fuerza)
CUANDO el SPIKE evalúa la dirección, el sistema DEBE exigir que el estocástico
M5 esté alineado con la entrada (M5 bajista para PUT, M5 alcista para CALL),
vía `_m5_aligned` de `stoch_exhaustion`. Esto reemplaza el `stoch_m5_exhausted`
(k<20/k>80) actual que solo miraba extremo sin dirección de cruce.
Significado exacto (acordado con el usuario 2026-07-25): NO es "sumar fuerza"
a la tendencia — es un **filtro de paciencia**. M15 es la "foto grande" (la
tendencia que ya viene diciendo a dónde va); M5 es el "presente" (lo que pasa
minuto a minuto). El SPIKE solo entra cuando el corto plazo (M5) YA CONFIRMÓ lo
que el largo plazo (M15) anunciaba: ambos deben decir la misma dirección EN EL
PRESENTE. SI el M5 va en contra (el presente aún no confirmó lo que M15 dijo),
el sistema DEBE descartar el SPIKE (mantener REBOUND). Esto evita entrar "muy
pronto" (la pérdida de $1 fue exactamente M15 diciendo "baja" pero M5 subiendo).

## R4 — Vela de agotamiento en la franja (rechazo con mecha)
CUANDO el precio toca la ZONA S/R (R1) con cruce M15 confirmado (R2) y M5
alineado (R3), el sistema DEBE confirmar una vela de rechazo (martillo /
doji / estrella fugaz) en la franja de la zona, usando
`classify_exhaustion_candle` de `stoch_exhaustion`. SI hay vela de rechazo,
el sistema DEBE promover la señal a `entry_mode="SPIKE"`, `spike=True`.
NOTA: esto reemplaza la confirmación vieja de "cuerpo a favor ≥ ratio" por la
clasificación de vela (ver design D5). No es pérdida accidental de
comportamiento: es más preciso (la mecha de rechazo marca el rechazo real, el
cuerpo a favor solo marcaba convicción de cierre).

## R4-bis — Camino "atrapado en extremo" (tan válido como la vela de rechazo)
CUANDO el precio está en la ZONA S/R (R1) con cruce M15 confirmado (R2) y M5
alineado (R3), el sistema DEBE ACEPTAR como confirmación de SPIKE el camino
alternativo del estocástico **atrapado en el extremo**: %K permaneciendo en la
banda extrema (>=80 para PUT / <=20 para CALL) durante `trap_window` velas
consecutivas SIN salir hacia la zona media (sin acercarse a la línea 80/20
contraria), aunque NO haya una vela de rechazo con mecha (R4). Este camino B
es condición de entrada tan válida como R4 (es la regla que el usuario validó
en USDPKR: "atrapado en el extremo sin salir de la línea"). El sistema DEBE
promover a SPIKE en cualquiera de los dos caminos (R4 o R4-bis).

## R5 — Mapeo a Fase A de Wyckoff (evento nombrado)
CUANDO el SPIKE se confirma (R1–R4 o R1–R3+R4-bis), el sistema DEBE etiquetar
el evento como Fase A de Wyckoff: `spring` para CALL en suelo (acumulación) o
`upthrust` para PUT en techo (distribución). El `pattern_name` / campo de
auditoría DEBE incluir `wyckoff_phase_a` para diferenciarlo del rebote base.

## R6 — Conservación del rebote base
MIENTRAS el SPIKE no se confirma (falta R2, R3 o ambos R4/R4-bis), el sistema
DEBE mantener el comportamiento REBOUND actual intacto (el SPIKE es condición
ADICIONAL, no reemplaza el rebote). Ninguna señal REBOUND válida de hoy debe
dejar de generarse.

## R7 — Banda de tolerancia de zona: zone_strength es fuente PRINCIPAL
MIENTRAS el sistema calcula la banda de tolerancia de la ZONA S/R (R1), el
sistema DEBE usar `zone_strength` (grosor × [1−velocidad], la "línea
imaginaria" medible acordada en conversaciones pasadas) como fuente PRINCIPAL
de la banda cuando esté disponible para el activo. Solo SI `zone_strength` no
aplica (activo sin datos de eficacia) el sistema DEBE caer a `adaptive_zone`
(rango % del precio reciente). NO es opcional: la "línea imaginaria" es la
banda de decisión, no un plus.

## R8 — Sin I/O en el evaluador puro
EL sistema DEBE mantener `evaluate_strat_f` como evaluador puro (sin red):
recibe `candles_15m/5m/1m` ya disponibles y calcula M15/M5/M1 internamente
(ya lo hace hoy con `compute_stoch`). El estocástico M15 y M5 se computan
desde las velas recibidas; no se consulta la base de datos ni la red.

## R9 — Trazabilidad en la caja negra
CUANDO el SPIKE se confirma, el sistema DEBE registrar en `scan_candidates`
el `stoch_m15` y `stoch_m5` (ya existe) más el nuevo campo `wyckoff_event`
(spring/upthrust) y `exhaustion_candle` (martillo/doji/estrellafugaz/atrapado),
para auditoría post-mortem. El `agent_tag` existente (BOT/WATCHDOG/HUMAN) se
respeta.

## R10 — Evaluación INTRAVELA (la vela M15 EN CURSO, no solo las cerradas)
CUANDO el scanner evalúa STRAT-F en su ciclo normal (que YA trae `candles_1m`
en cada ciclo vía `prefetch_primary_candles`), el sistema DEBE poder evaluar
el agotamiento del SPIKE también sobre la **vela M15 en curso** usando las
velas M1 de esa ventana (lookback ~15 velas M1 = la vida de la M15 abierta),
igual que `audusd_exhaust_watchdog.py` con `lookback=15`. El sistema NO DEBE
limitarse a evaluar solo sobre `candles_15m` ya cerradas: el agotamiento se
forma DENTRO de la vela M15 viva y, si solo se revisa al cerrar, la señal se
pierde o llega tarde (el problema ya vivido con el watchdog). El mecanismo es
DENTRO de `evaluate_strat_f` (no requiere correr el scan más seguido): la
última vela de `candles_15m` es la M15 abierta; se evalúa con `candles_1m`
como ventana intravela pasándolas a `evaluate_exhaustion(..., lookback=15)`.

## R11 — Tests de regresión y nuevos casos
EL sistema DEBE mantener verdes los tests existentes de SPIKE
(`test_strat_f_spike.py`) y maturing_recheck (`test_strat_f_maturing_recheck.py`),
y AÑADIR tests que cubran:
(a) SPIKE con cruce M15 confirmado + M5 alineado + vela de rechazo en zona
    fractal → SPIKE + wyckoff_phase_a.
(b) SPIKE sin cruce M15 → REBOUND.
(c) SPIKE con M5 en contra (presente no confirma lo que M15 dijo) → REBOUND.
(d) Camino atrapado (R4-bis): %K atrapado en extremo sin vela de rechazo →
    SPIKE.
(e) INTRAVELA (R10): señal detectada ANTES de que cierre la vela M15, usando
    M1 como ventana — el test debe inyectar una M15 abierta + M1 de la ventana
    y confirmar que el SPIKE dispara sin esperar el cierre.
(f) Etiqueta `wyckoff_event` presente en el caso (a).
