# Índice — Energía Wyckoff / DATA REQUIREMENTS (EW)

| Campo | Valor |
|---|---|
| Línea | Energía Wyckoff (effort/result Wyckoff) |
| Diseño | `hypothesis_energia_wyckoff_design.md` (NO ejecutado) |
| DATA REQUIREMENTS | `DATA_REQUIREMENTS_EW.md` (definido 2026-08-07) |
| Estado al 2026-08-07 | **BLOCKED — DATA QUALITY (instrumento)**, NO resultado negativo |
| Motivo | EURUSD M15 = `tick_volume`, ~55% ceros → effort/efficiency/absorption artificiales |
| Ejecución EW-1/2/3 | NO ejecutada. Pendiente decisión A/B del Trader-Humano |
| Conclusión correcta | "Hipótesis no evaluada por insuficiencia del instrumento de medición" |
| Checklist de usabilidad | §5 de DATA_REQUIREMENTS_EW (6 pasos antes de congelar EW-1) |
| Candidato local rechazado (A) | Dukascopy M1 (SMC-SYSTEMS) — 99.7% ceros M15 |
| Candidato CME 6E EVALUADO (A1) | REAL traded volume (contratos CME Globex); pasa factibilidad §2b |
| Veredicto A1 | PASA; AUTORIZADO Databento; BLOQUEO DE ACCESO (sin API key) |
| Scripts listos (sin ejecutar) | scripts/lab_ew_acquire_cme.py, scripts/lab_ew_verify_cme.py |
| Ejecución EW-1/2/3 | NO ejecutada. Pendiente adquisición + verify + OK del Trader-Humano |
