# Tasks — Detector Estructural de Fase A (R0–R3)

- [ ] T1 — Crear `scripts/lab_phaseA_radiografia.py` (standalone, sin imports del
      Edificio). Cubre: R1, R7.
- [ ] T2 — Cargar `EURUSD_M15.parquet` (cohorte_real_eurusd) e indexar por
      timestamp. Cubre: R2, R7.
- [ ] T3 — Cargar `edificio_events.parquet` y clasificar WIN/LOSS por columna
      `win`; respetar `split` para OOS. Cubre: R3, R9.
- [ ] T4 — Extraer features OHLC+tiempo (tendencia/impulso/compresión/lucha) en
      ventana N=20 previas a `brake_time`, sin usar volumen como requisito.
      Cubre: R2, R4, R6.
- [ ] T5 — Unir features a señales por timestamp; comparar distribuciones
      WIN vs LOSS (medias/medianas/effect size + prueba de separación).
      Cubre: R5, R9.
- [ ] T6 — Volcar reporte inmutable en `data/strategy_lab/ew_reports/PHASEA-RADIO/`
      (summary.md + result.json + protocol_frozen.json con hash/seed/entorno y
      declaración Charter). Cubre: R8.
- [ ] T7 — Temp ad-hoc de verificación (hermes-verify-*) que corra el script y
      confirme: no toca src/, usa solo datos en disco, reporte generado. Borrar
      temp al final. Cubre: R1, R7, R8.
- [ ] T8 — Commit del spec + script; push tras OK. Cubre: trazabilidad.
