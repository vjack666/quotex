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
| Veredicto A1 | PASA; AUTORIZADO Databento; BLOQUEO DE API KEY |
| Scripts listos (sin ejecutar) | scripts/lab_ew_acquire_cme.py, scripts/lab_ew_verify_cme.py |
| Búsqueda gratuita (NO pagar) | concluida: no hay M15/1min gratis 2022-26; unica gratuita completa = Yahoo 6E=F DIARIO |
| Reframe objetivo | "comprobar si EW tiene capacidad predictiva"; FASE 1 GRATIS = diario 2022-26, gate antes de pagar |
| Adquisición Fase1 | EJECUTADA: Yahoo 6E=F DIARIO 2022-26 -> 1,150 barras raw intactas (parquet gitignored) |
| Verificación | 6/7 OK; 2025 2.38% missing vol (6 barras, precio real). Opcion2: MISSING, no imputar, no borrar |
| EW-1 escala | adaptado M15 -> D1 en diseno |
| Ejecución EW-1 | NO ejecutada. PENDIENTE GATE DE CONGELACION (OK explicito del Trader-Humano) |
