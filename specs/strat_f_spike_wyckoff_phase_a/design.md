# Design — Mejora del SPIKE con agotamiento verdadero (Fase A de Wyckoff)

## Contexto
El modo SPIKE de `strat_fractal.evaluate_strat_f` (líneas 392–412) hoy decide la
entrada "en el extremo con agotamiento" usando SOLO `stoch_m5_exhausted(k, dir)`
(M5 en extremo k<20/k>80) + cuerpo a favor en la banda fractal (`band*0.0015`).
Eso es más débil que la lógica que el usuario validó en su watchdog
(`stoch_exhaustion.evaluate_exhaustion`): ZONA adaptativa + cruce M15 confirmado
+ M5 alineado + vela de rechazo. El watchdog probó ser más preciso (evitó la
pérdida por M5 en contra). Objetivo: llevar esa precisión al SPIKE del bot,
manteniendo las ZONAS S/R del fractal Wyckoff y mapeando a Fase A de Wyckoff.

## Decisiones técnicas

### D1 — Reutilizar `stoch_exhaustion` como motor (NO duplicar lógica)
El SPIKE inline de `strat_fractal` se reemplaza por una llamada a
`apply_stoch_help(k, direction, mode, stoch_full=..., candles_15m=...,
zone_lo=zone.floor, zone_hi=zone.ceiling, stoch_m5=...)` (y, para intravela,
`candles_1m=...`). `apply_stoch_help` ya delega en `evaluate_exhaustion` (que
tiene zona, cruce M15 confirmado, M5 alineado, vela de rechazo y camino
atrapado). Esto evita duplicar la lógica y reusa los tests ya verdes. El SPIKE
pasa a ser una *configuración* de `evaluate_exhaustion` (modo extremo Z1/Z5).

### D2 — ZONA S/R del fractal como ancla (R1)
`evaluate_strat_f` ya construye `zone = ConsolidationZone(floor, ceiling)` desde
el fractal (suelo/techo Wyckoff). Esa zona se pasa como `zone_lo/zone_hi` a
`apply_stoch_help` — NO un `band*0.0015` fijo. Conserva tu regla
"S/R = línea imaginaria medible" y "ancla swing de la pierna" (la zona es del
fractal, no un rango arbitrario).

### D3 — Cruce M15 confirmado (R2)
`compute_stoch(candles_15m)` ya expone `cross_ago` y las series `k_vals/d_vals`.
Se pasan como `stoch_full` a `apply_stoch_help`. `evaluate_exhaustion` exige
`cross_ago >= 1` antes de confirmar. Sin cruce → EXHAUST_WAIT → el SPIKE no se
activa (queda REBOUND).

### D4 — M15 y M5 AMBOS alineados = filtro de PACIENCIA (R3)
El scanner ya calcula `stoch_m5_json` (k, d, cruce) en maturing_watchlist. Se
inyecta como `stoch_m5` a `apply_stoch_help`. `_m5_aligned` exige M5 en la
dirección (bajista para PUT / alcista para CALL). Reemplaza el
`stoch_m5_exhausted` actual (que solo miraba extremo).
Aclaración de significado (acordado 2026-07-25): NO es "sumar fuerza" a la
tendencia. M15 = la foto grande (lo que la tendencia ya viene diciendo); M5 =
el presente (lo que pasa minuto a minuto). El SPIKE entra solo cuando el corto
plazo (M5) YA CONFIRMÓ en el presente lo que el largo plazo (M15) anunciaba.
M5 en contra = el presente aún no confirmó → se descarta (evita entrar "muy
pronto", como la pérdida de $1: M15 "baja" pero M5 subía).

### D5 — Vela de rechazo: se REEMPLAZA cuerpo-a-favor por clasificación (R4)
Decisión consciente y documentada: el SPIKE viejo usaba "cuerpo a favor ≥ ratio"
como confirmación. Se REEMPLAZA por `classify_exhaustion_candle` (martillo /
doji / estrella fugaz) porque es más preciso: la MECHA de rechazo marca el
rechazo real en la zona (el rastro del rechazo de absorción), mientras que el
cuerpo a favor solo marcaba convicción de cierre. No es una pérdida accidental
de comportamiento — es un endurecimiento. Quien lea el spec sepa que el
"cuerpo a favor" desapareció a propósito.

### D6 — Camino "atrapado en extremo" explícito (R4-bis)
`evaluate_exhaustion` ya tiene el camino B (`_trapped_in_extreme`, trap_window
velas %K en banda extrema sin salir hacia la media). Se documenta como
condición de entrada TAN VÁLIDA como R4: el usuario lo validó en USDPKR
("atrapado en el extremo sin salir de la línea"). El SPIKE se activa en
cualquiera de los dos caminos. tasks.md y tests lo cubren explícitamente para
que nadie lo rompa sin darse cuenta.

### D7 — Mapeo Fase A de Wyckoff (R5)
Confirmado → `entry_mode="SPIKE"`, `spike=True`, `wyckoff_event="spring"`
(CALL en suelo) / `"upthrust"` (PUT en techo). El `pattern_name` incluye
`wyckoff_phase_a`.

### D8 — Banda de zona: zone_strength es FUENTE PRINCIPAL (R7, endurecido)
La banda de tolerancia de la zona NO es opcional: `zone_strength` (grosor ×
[1−velocidad], la "línea imaginaria" medible de conversaciones pasadas) es la
FUENTE PRINCIPAL de la banda cuando está disponible para el activo. Solo SI
`zone_strength` no aplica (activo sin datos de eficacia) se cae a
`adaptive_zone` (rango % del precio reciente) como fallback. Decisión de
diseño explícita: la "línea imaginaria" manda, no es un plus.

### D9 — INTRAVELA: mecanismo REAL en el ciclo de scan (R10)
El scanner YA trae `candles_1m` en CADA ciclo (prefetch_primary_candles con
TF_1M/TF_5M/TF_15M, scan_prefetch.py:170-186) y `evaluate_strat_f` ya recibe
las tres TFs (scanner.py:2352-2402). Por tanto NO hace falta correr el scan más
seguido: el M1 ya está en cada ciclo. El hueco es que `evaluate_strat_f` hoy
evalúa el agotamiento SOBRE `candles_15m` (velas M15 cerradas). El fix es
DENTRO de `evaluate_strat_f`: al evaluar el SPIKE, pasar a
`apply_stoch_help`/`evaluate_exhaustion` (1) la última vela de `candles_15m`
que es la M15 EN CURSO (abierta), y (2) `candles_1m` como ventana intravela con
`lookback=15` (15 velas M1 = vida de la M15 abierta), igual que el watchdog.
Así el SPIKE detecta el agotamiento DENTRO de la vela M15 viva, no al cerrar.
El costo: `evaluate_exhaustion` se invoca con `candles_15m=última M15 abierta`
+ `candles_1m=ventana` + `lookback=15`. El resto del pipeline (score, caja
negra) no cambia.

### D10 — Flujo en `evaluate_strat_f`
1. Calcular `stoch_m15 = compute_stoch(candles_15m, direction)`.
2. Calcular `stoch_m5 = compute_stoch(candles_5m, direction)`.
3. Tras validar fractal + banda + M1 rechaza (R1–R6 base), llamar
   `apply_stoch_help(k_m15, direction, STRAT_F_STOCH_MODE, stoch_full=stoch_m15,
   candles_15m=última_M15_abierta, candles_1m=candles_1m, lookback=15,
   zone_lo=zone.floor, zone_hi=zone.ceiling, stoch_m5=stoch_m5,
   zone_strength=zona_aplicada)`.
4. SI `action == "BOOST"` y `exhaustion.path in ("ruptura","atrapado")` →
   `entry_mode="SPIKE"`, `spike=True`, `wyckoff_event=spring/upthrust`,
   `exhaustion_candle=...`. SI NO → `entry_mode="REBOUND"` (R6 intacto).

### D11 — Caja negra (R9/R8)
`evaluate_strat_f` ya devuelve `zone`, `pattern_name`, `spring_margin`,
`math_quality`. Se AÑADE `wyckoff_event` y `exhaustion_candle` al
`StratFEvaluation`. El scanner ya graba `stoch_m15`/`stoch_m5` en
`scan_candidates`; se añade `wyckoff_event` al `strategy_details` JSON. El
`agent_tag` (BOT/WATCHDOG/HUMAN) se respeta sin cambios.

## Riesgos y mitigaciones
- **Cambio en bot vivo (AGENT_LIVE):** se implementa tras aprobación SDD y con
  tests verdes de SPIKE + maturing_recheck + stoch_exhaustion. El cambio es
  localizado en `strat_fractal` + `stochastic_zones` + `scanner` (inyección).
- **Menos señales (costo consciente):** al exigir cruce M15 + M5 alineado +
  intravela, el SPIKE disparará MENOS pero más limpio (filtro de paciencia). El
  REBOUND base cubre lo demás. Si el volumen cae mucho, se ajusta `cross_min_ago`
  o `trap_window`.
- **Regresión de tests:** `test_strat_f_spike.py` (4) y
  `test_strat_f_maturing_recheck.py` (13) deben seguir verdes; se añaden (a)-(f) de R11.
