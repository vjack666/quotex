# Design — Detector Estructural de Fase A

## Contexto y datos verificados (inspección real, no ejecución de experimento)

- `src/strategy_lab/results/edificio_events.parquet`: señales del Edificio ya
  etiquetadas. Columnas clave: `asset`, `direction`, `win` (0/1), `brake_time`
  (datetime UTC), `brake_ratio`, `k_brake`, `d_brake`, `kd_dist_brake`,
  `extreme_flag`, `hammer_flag`, `trend_brake`, `htf_bias_brake`, `split`
  (train/test). ~ miles de filas. OOS natural vía `split`.
- `data/strategy_lab/cohorte_real_eurusd/EURUSD_M15.parquet`: 543.310 velas M15,
  columnas `time, open, high, low, close, tick_volume`. Es SPOT EURUSD (tick
  volume, no real). Refuerza la regla de oro: estructura sin volumen real.
- `data/smc_borrowed/EURUSD_M15.parquet`: 385.258 velas M15, `volume` (igual, spot).

El Edificio opera sobre spot EURUSD M15/M5 — NO sobre futuros 6E. Por tanto la
ruta estructural usa spot M15, no el ratio `move/vol` de 6E (EW-1 queda como
investigación auxiliar, no pilar).

## Archivos nuevos

- `scripts/lab_phaseA_radiografia.py` — extrae features OHLC de contexto previo
  a cada `brake_time`, une con WIN/LOSS, compara grupos, vuelca reporte inmutable.
- `data/strategy_lab/ew_reports/PHASEA-RADIO/` — reporte (summary.md + result.json
  + protocol_frozen.json). Ya existe la carpeta `ew_reports/` (gitignored parquet/
  reports internos; el script y spec sí se commitean).

## Features estructurales (SOLO OHLC + tiempo, sin volumen como requisito)

Por ventana de N=20 velas M15 previas al `brake_time`:
- **Tendencia**: pendiente OLS del close, cuenta de HH/HL y LH/LL, continuidad.
- **Impulso**: rango medio, desplazamiento neto (close−open acumulado), velocidad
  (desplazamiento / N), persistencia direccional.
- **Compresión**: reducción de rango (ratio rango últimas 5 / primeras 5),
  solapamiento entre velas (min(high)−max(low) sobre cuerpos), body/range medio.
- **Lucha estructural**: mechas relativas (wick/range), fallos de ruptura (tosca
  de máximo/minimo previo que cierra adentro), repetición de niveles (clúster de
  cierres), cercanía de cierre al extremo de la vela.

## Decisiones y alternativas descartadas

- **Descartado**: usar `move/vol` (EW-1) como pilar de la hipótesis estructural.
  Motivo: el objetivo maestro es estructura de precio para binarias; el volumen
  real no está disponible en el feed del Edificio (spot tick volume). EW-1 pasa a
  investigación auxiliar (`lab_ew_brake_link.py` queda como experimento paralelo).
- **Descartado**: modificar el Edificio para inyectar Wyckoff. Motivo: sería
  circular (curve fitting conceptual). El Edificio es caja negra (R1).
- **Elegido**: unir features OHLC por timestamp a las señales ya etiquetadas del
  Edificio (aprovecha `split` OOS nativo, no requiere re-etiquetar).

## Riesgos metodológicos (ver risks en ciclo científico si se promueve a EXP)

- Solapamiento de ventanas entre señales cercanas (overlap) → se marca y se
  reporta; no se infla n artificialmente.
- Múltiples comparaciones de features → si se promueve, FDR/Bonferroni.
- Sesgo de supervivencia del Edificio (solo ve señales que pasaron filtros) → se
  documenta; el objetivo es radiografía relativa WIN vs LOSS, no tasa absoluta.

## Roadmap (fases siguientes, fuera de ESTA feature)

- R4 Mapeo Wyckoff: comparar patrones descubiertos con Fase A.
- R5 Phase A Score: detector estructural independiente (pesos por evidencia).
- R6 Confirmación: Phase A context + Edificio signal.
- R7 Binarias: dirección + expiración (horizonte natural del Edificio).
- R8 OOS / walk-forward; R9 Robustez; R10 Producción.
