# EXP-EDF-01 — Máquina A (motor real) reparada + P3→CONTRATADO en paralelo M15 / M5

**Fecha:** 2026-08-08 · **Autor:** Hermes (medición sobre el motor real reparado)
**Script:** `scripts/audit_exp040.py` · **Datos:** EURUSD 2024 M15 (24970 velas) + M5 (74888 velas)

## Objetivo
EXP-VALVULA-P3 se midió sobre la Máquina B (simulación validada) porque la Máquina A
(Edificio real) tenía el embudo P2→P3 roto por diseño (return_to_extreme mal definido
→ 0 P3). EXP-EDF-01 aplica la lección: **repara el motor real y mide sobre él**, con datos
M15 (stoch + flags) y M5 (gate P3→CONTRATADO) en paralelo.

## Reparación aplicada (src, ya en el repo)
`_p2_return_tracking` en `src/edificio_contratacion.py`: la "zona" de retorno se definió
correctamente como la línea de extremo (k≤20 CALL / k≥80 PUT) y el retorno promueve tras
haber salido. El motor real ahora fluye idéntico a la Máquina B.

## Metodología
- Stoch FULL 14,3,3 con `compute_stoch_full` (mismo de la sim validada) → comparabilidad.
- Flags por vela fieles a `scanner.py` (brake_ok, extreme_ok, cross_ok, cross_sticky, direction).
- Vela M5 alineada por timestamp para alimentar el gate real de P3→CONTRATADO.
- Puerta P3→CONTRATADO medida en FORWARD-SCAN (velas post-P3), porque P3 se define por
  volver al extremo y la puerta evalúa la salida posterior (evita la contradicción de
  medir "salir del extremo" en la vela de "volver al extremo").
- WR fiel al bot: entry=i+1, exit=i+2 (close M15). H1 = primeras 12485 velas, H2 = resto.
- LÍMITE documentado: el bot real entra ~300s tras la señal; el CSV M15 no reconstruye
  ese openPrice intravela, así que i+1/i+2 es aproximación temporal.

## Resultados (motor real reparado, datos reales)

| Rama | P1 | P2 | P3 | CONTRATADOS | BLOQUEADOS_P3 | WR H1 | WR H2 |
|---|---|---|---|---|---|---|---|
| valvula (solo M15) | 0 | 896 | 855 | 352 | 503 | 50.3% (93W/92L) | 63.5% (106W/61L) |
| cruce_limpio (M15+M5) | 0 | 896 | 855 | 170 | 685 | 38.9% (35W/55L) | 52.5% (42W/38L) |

## Interpretación (consejo científico)
1. **La deuda de ingeniería se cerró:** el embudo del motor real reparado fluye P2=896,
   P3=855 — idéntico a la Máquina B. La Máquina A ya no está rota.
2. **Válvula K/D sobre el motor real:** CONTRATADOS=352/855 (filtra 503, 59% bloqueadas).
   WR H2=63.5% — MEJOR que la sim (que daba ~51%). PERO: H1=50.3%, y el salto H1→H2
   (50%→63%) es precisamente la firma de sobreajuste al descubrimiento H1. Con un solo
   año no se puede separar señal de ruido de muestreo. No es evidencia de edge.
3. **cruce_limpio + gate M5:** CONTRATADOS=170/855 (filtra 685, 80% bloqueadas). WR H2=52.5%
   (moneda). El gate M5 original es un filtro FUERTE (bloquea 80%) pero no mejora el acierto.
4. **Conclusión:** sobre el motor real reparado, ni la válvula K/D ni el cruce_limpio+M5
   muestran edge robusto fuera de muestra. La válvula sigue NO ADOPTADA (decisión de
   EXP-VALVULA-P3 se mantiene). El gate M5 es un filtro agresivo sin ventaja de acierto
   comprobable en 2024.

## Lo que SÍ se refutó / lo que NO (precisión quirúrgica)
- ✅ REFUTADA sobre motor real: la válvula K/D como filtro de calidad P3→CONTRATADO no
  muestra ventaja predictiva fuera de muestra robusta (H2 mejoró pero es sobreajuste H1).
- ❌ NO se refutó: que el stocástico completo no sirva.
- ❌ NO se refutó: que la secuencia extremo→retorno→salida esté mal (de hecho, el motor
  real ahora la ejecuta idéntico a la sim validada).
- ❌ NO se refutó: que todo el edificio esté mal.

## Disposición
- Motor real: embudo P2→P3 REPARADO y fluyendo (P3=855 en 2024). Listo para futuras
  mediciones sobre datos reales.
- Válvula K/D: sigue marcada [NO ADOPTADA] en src/config.py (decisión EXP-VALVULA-P3).
- Gate M5 (cruce_limpio): filtra 80% pero WR H2≈52%; no se recomienda como filtro de
  calidad sin más evidencia (otros años / otros pares).
- EXP-EDF-01 cierra: la deuda de ingeniería (Máquina A rota) quedó resuelta y la medición
  P3→CONTRATADO sobre datos reales M15+M5 está hecha.

## LIMITACIÓN
- WR aproximado (i+1/i+2 close M15), no openPrice del broker.
- Un solo año (2024): H1/H2 es holdout intra-año, no datos externos.
- Vela M5 alineada por timestamp de inicio; el gate usa body_pct>=0.5 (EDIFICIO_BODY_FILTER_MIN_RATIO).
