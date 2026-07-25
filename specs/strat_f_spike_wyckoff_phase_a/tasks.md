# Tasks — Mejora del SPIKE con agotamiento verdadero (Fase A de Wyckoff)

> Implementación tras aprobación SDD. Orden sugerido. Cada task marca `[x]` al cerrar.

## T1 — Ampliar `StratFEvaluation` con campos Wyckoff (R5, R8)
- [ ] Añadir `wyckoff_event: Optional[str] = None` ("spring"/"upthrust"/None) a `StratFEvaluation` en `strat_fractal.py`.
- [ ] Añadir `exhaustion_candle: Optional[str] = None` (martillo/doji/estrellafugaz/atrapado) a `StratFEvaluation`.
- [ ] Test unitario: `StratFEvaluation` acepta ambos campos sin romper.

## T2 — Reusar `stoch_exhaustion` como motor del SPIKE (D1, R1–R4, R4-bis)
- [ ] En `evaluate_strat_f`, tras validar fractal + banda + M1 rechaza, calcular:
  `stoch_m15 = compute_stoch(candles_15m, direction)` (ya existe patrón).
  `stoch_m5 = compute_stoch(candles_5m, direction)`.
- [ ] Llamar `apply_stoch_help(k_m15, direction, STRAT_F_STOCH_MODE,
  stoch_full=stoch_m15, candles_15m=última_M15_abierta, candles_1m=candles_1m,
  lookback=15, zone_lo=zone.floor, zone_hi=zone.ceiling, stoch_m5=stoch_m5,
  zone_strength=zona_aplicada)`.
- [ ] SI `apply_stoch_help.action == "BOOST"` y `exhaustion.path in ("ruptura","atrapado")`
  con `exhaustion_candle` presente → `entry_mode="SPIKE"`, `spike=True`,
  `wyckoff_event = "spring" if direction=="CALL" else "upthrust"`,
  `exhaustion_candle = exhaustion.exhaustion_candle`.
- [ ] SI NO → `entry_mode="REBOUND"` (R6 intacto).
- [ ] Eliminar el bloque SPIKE inline actual (líneas 392–412) que usa
  `stoch_m5_exhausted` + `band*0.0015` + "cuerpo a favor" (ver T-body).

## T3 — `apply_stoch_help` delega en `evaluate_exhaustion` (D1)
- [ ] Confirmar que `stochastic_zones.apply_stoch_help` ya pasa `zone_lo/zone_hi`
  y `stoch_m5` a `evaluate_exhaustion` (lo hace desde la zona adaptativa previa).
- [ ] Añadir parámetro `zone_strength` a `apply_stoch_help` y pasarlo a
  `evaluate_exhaustion` para que la banda use zone_strength (D8/R7).
- [ ] Verificar que en Z1 CALL / Z5 PUT devuelve BOOST 12 con `exhaustion` poblado
  cuando hay cruce M15 + M5 alineado + vela de rechazo (camino ruptura) O
  %K atrapado (camino atrapado).
- [ ] Test: `apply_stoch_help` con `stoch_m5` en contra → action "WAIT" (no BOOST).
- [ ] Test: `apply_stoch_help` con %K atrapado en extremo + cruce + M5 alineado →
  BOOST 12 con `path="atrapado"` (R4-bis).

## T4 — ZONA S/R fractal + zone_strength como fuente principal (R1, R7, D8)
- [ ] `evaluate_strat_f` ya construye `zone.floor/ceiling` del fractal. Pasarlos
  como `zone_lo/zone_hi`. Confirmar que `evaluate_exhaustion` usa la banda de
  `zone_strength` (grosor × [1−velocidad]) cuando aplica, y solo cae a
  `adaptive_zone` si zone_strength no está disponible.
- [ ] Test: banda de zona usa zone_strength cuando se pasa; fallback adaptive_zone
  cuando no.
- [ ] Test: vela en franja de la zona fractal (no pips fijos) → confirmado.

## T5 — INTRAVELA: evaluar la M15 en curso vía M1 (R10, D9)
- [ ] En `evaluate_strat_f`, la "última_M15_abierta" = `candles_15m[-1]` (la vela
  que aún no cerró). Pasarla como `candles_15m` a `evaluate_exhaustion` junto
  con `candles_1m` y `lookback=15`. NO requiere cambiar la frecuencia del scan
  (el scanner ya trae M1 cada ciclo vía prefetch_primary_candles).
- [ ] Test (R11-e): inyectar una M15 abierta + 15 velas M1 de la ventana donde se
  forma el agotamiento, y confirmar que el SPIKE dispara SIN esperar el cierre de
  la M15. Es decir: señal detectada ANTES de que cierre la vela M15.

## T6 — Reemplazo cuerpo-a-favor por clasificación de vela (R4, D5)
- [ ] Dejar documentado en el código (comentario en `evaluate_strat_f`) que se
  reemplaza "cuerpo a favor ≥ ratio" por `classify_exhaustion_candle` porque la
  mecha de rechazo marca el rechazo real (más preciso), no pérdida accidental.
- [ ] Test: vela con cuerpo a favor pero SIN mecha de rechazo (no es martillo/doji/
  estrellafugaz) → NO promueve a SPIKE por R4 (pero podría por R4-bis atrapado).

## T7 — Caja negra trazable (R8/R9)
- [ ] En `scanner.py`, al armar `strategy_details`, incluir `wyckoff_event` y
  `exhaustion_candle` de `f_eval` (cuando existan).
- [ ] Confirmar que `stoch_m15`/`stoch_m5` ya se graban en `scan_candidates`.
- [ ] Test: candidato SPIKE graba `wyckoff_event` en `strategy_details` JSON.

## T8 — Regresión y nuevos tests (R11)
- [ ] `tests/test_strat_f_spike.py` añadir casos:
  (a) cruce M15 confirmado + M5 alineado + vela rechazo en zona → SPIKE + wyckoff_phase_a.
  (b) sin cruce M15 → REBOUND.
  (c) M5 en contra (presente no confirma M15) → REBOUND.
  (d) camino atrapado (R4-bis): %K atrapado en extremo sin vela de rechazo → SPIKE.
  (e) INTRAVELA (R10): señal ANTES de cerrar M15 vía M1 lookback=15.
  (f) `wyckoff_event` presente en (a).
- [ ] Ejecutar `pytest tests/test_strat_f_spike.py tests/test_strat_f_maturing_recheck.py tests/test_stoch_exhaustion.py tests/test_stochastic_zones.py -m "not slow"` → TODO VERDE.
- [ ] Ejecutar subset amplio del scanner para no romper pipeline vivo.

## T9 — Verificación final y cierre SDD
- [ ] `init.ps1` en verde (o equivalente pytest del proyecto).
- [ ] Actualizar `progress/current.md` con el resumen.
- [ ] Marcar feature id 30 `done` en `feature_list.json` (tras aprobar reviewer).
- [ ] Commit con `git add` de archivos ESPECÍFICOS (regla: nunca -A).
