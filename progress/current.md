# Progress — 2026-08-07 — CIERRE DEL HILO DEL CLUSTERING (EXP-075 + EXP-074b-NULL)

## ⭐ Sesión actual: cerrar definitivamente el clustering antes de pivotar (orden Trader-Humano)

**Estado: EJECUTADO Y CERRADO. Hilo del clustering TERMINADO (binario 074b + continuo 075 + null 074b-NULL).**

### 1. EXP-075 (re-enfoque continuo de 074b) — RESULTADO NEGATIVO
- 3307 Fases A, EURUSD M15 2022-2026. TRAIN 2022-2024 (n=2066) / TEST 2025-2026 (n=1241).
- FDR-BH sobre 36 descriptores continuos × 2 targets: **0/36 significativos** (p_adj_fdr min 0.85).
- OR por cuartil `duration`: TRAIN aligned 1.045/clean 1.025; TEST OOS aligned 1.069/clean 1.015
  (todos p>0.6, cuartiles planos). Bootstrap OR_Q4 median=1.028 IC95%=[0.835,1.255] incluye 1.0.
- Duración continua NO predice resolución. Coherente con EXP-072/073.
- Archivos: scripts/lab_exp075_phaseA_continuous.py, reports/EXP-075/, specs/.../hypothesis|risks|validation_exp075.md

### 2. EXP-074b-NULL (control nulo + OOS temporal REAL) — VEREDICTO: NO SOPORTADA
- Null = shuffle independiente de columnas (B=200) preservando marginales.
- **Hallazgo clave y matiz honesto**: silhouette null (0.405) > REAL (0.2185). El null de
  shuffle de columnas es "fuerte" (geometría favorable) → NO se usa silhouette para refutar.
  El criteria congelado daba MIXTO; se explica y el veredicto se apoya en OOS + %minoritario.
- **OOS TRAIN 2022-2024 → TEST 2025-2026: TEST 100% "corto" → colapso total** (diff 81.8pp,
  silhouette TEST=nan). NO hay estabilidad temporal → evidencia decisiva.
- %minoritario REAL 24.4% en el borde del null (máx 21.6%) → el null lo explica casi igual.
- **VEREDICTO: hipótesis de población mixta NO SOPORTADA** como régimen estable del mercado.
  El clustering es geometría del método, no régimen natural. (Art. 13: descubrimiento, no edge.)
- Archivos: scripts/lab_exp074b_null.py, reports/EXP-074b_NULL/summary.txt + protocol_frozen.json,
  data/strategy_lab/exp074b_null_curves.parquet, specs/.../hypothesis|risks|validation_exp074b_null.md

### 3. Cierre formal del hilo
- EXP-074 (K=2, sil 0.22, 24/76) = partición conveniente del método, no 2 poblaciones del mercado.
- EXP-074b (algoritmo/ablation/bootstrap) = RECHAZO. EXP-075 (continuo) = NEGATIVO.
  EXP-074b-NULL (null + OOS) = OOS colapsa → NO SOPORTADA.
- Secuencia de Grok/ChatGPT validada por el Trader-Humano: 074→074b→074b-NULL→[RECHAZO]→sin 075.
- Hilo CERRADO. No se promueve nada al Edificio.

### 4. DISEÑO (NO EJECUTADO) — Energía Wyckoff — ⛔ BLOCKED POR INSTRUMENTO (no resultado negativo)
- `specs/lab_protocolo_cientifico/hypothesis_energia_wyckoff_design.md` escrito (solo diseño),
  marcado BLOCKED — DATA QUALITY (decisión Trader-Humano opción C, 2026-08-07).
- Verificación de datos (Paso 2): EURUSD M15 (SMC_ROOT) trae `tick_volume`, NO `volume` real;
  62912/114237 velas (55%) con `tick_volume=0`. → effort/efficiency/absorption artificiales/indefinidas.
- **NO se ejecuta EW-1 con este dataset** (ni A: filtrar tick_volume>0 → sesgo de selección; ni B:
  tratar ceros como esfuerzo nulo → masa en cero espuria). La hipótesis QUEDA VIVA como hipótesis
  científica; solo se cierra el uso de ESTE dataset.
- Conclusión correcta: **"Hipótesis NO EVALUADA por insuficiencia del instrumento de medición."**
- `specs/lab_protocolo_cientifico/DATA_REQUIREMENTS_EW.md` definido y ACTUALIZADO (2026-08-07 tarde):
  realidad FX OTC (no hay volumen centralizado), qué es volumen adecuado (jerarquía: bolsa>broker>tick),
  campos mínimos, umbral ≤2% ceros, cobertura ≥3a M15, checklist 6 pasos.
- **DECISIÓN A (2026-08-07 tarde) — candidato local EVALUADO y RECHAZADO**: se revisó EURUSD_M1 de
  Dukascopy ya en `SMC-SYSTEMS/data/raw` (usado por `build_m15_from_m1.py`, renombra a `volume`=suma
  ticks). Resultado: **99.7% de ceros en volumen M15** (tick volume del banco), peor que HistData 55%.
  FX spot OTC: el tick volume de cualquier feed individual es disperso/cero — inherente, no defecto
  de Dukascopy. NO se descargó nada nuevo, NO se congeló EW-1.
- **DECISIÓN A1 (2026-08-07) — CME 6E EVALUADO por factibilidad/semántica, SIN descarga**:
  - Contrato: CME Euro FX Futures, código **`6E`** (125,000 EUR/contrato; micro `M6E` 1/10).
  - `volume` = **nº de contratos negociados en CME Globex (central limit order book)** = REAL traded
    volume, NO tick, NO proxy de broker. Esto es exactamente lo que faltaba en FX spot.
  - Cubre M15 histórico vía Databento (`GLBX.MDP3`), Polygon.io, o CME directo; pasa split OOS
    2022-2024 / 2025-2026. Un solo proveedor da continuous contract 6E (roll por volumen).
  - **Limitación spot→futuros (documentar explícitamente):** cambia el instrumento experimental de
    EURUSD spot a **EUR/USD futures (6E)**. El precio rastrea al spot (correlación alta vía cost-of-
    carry) pero NO idéntico; hay base y rollovers. El rollover introduce **saltos artificiales en
    PRECIO** (afecta `move`/`rango`) pero el **VOLUMEN queda continuo y limpio**. Para EW (effort/result)
    el volumen centralizado es una MEJORA enorme; NO invalida EW. Resultados EW NO se comparan 1:1
    con EXP-071..075 (spot). Fase A de EW se define sobre 6E.
  - **Coste/acceso (cuello real):** Databento de pago (~$5/GB, crédito bienvenida, API `databento`);
    Polygon free limitado (~2a hist, 5 calls/min); CME directo de pago. NINGUNO gratis como HistData →
    el lab pasaría a datos de pago (requiere presupuesto/cuenta).
  - **VEREDICTO de factibilidad: CANDIDATO PASA** puntos 1–5 y 7 (salvedad coste); punto 6 = cambio de
    instrumento a documentar, no bloqueo. **Pendiente tu autorización de ADQUISICIÓN de datos (elegir
    proveedor) antes de descargar/modificar pipeline/congela EW-1.** Documentado en DATA_REQUIREMENTS_EW.md §2b.
- NO se buscó dataset por cuenta propia más allá de inspeccionar el candidato ya presente. NO EW-1/2/3.

### Archivos de la sesión (commiteables de esta sesión, commit pendiente de OK)
- scripts/lab_exp075_phaseA_continuous.py
- scripts/lab_exp074b_null.py
- specs/lab_protocolo_cientifico/{hypothesis,risks,validation}_exp075.md
- specs/lab_protocolo_cientifico/{hypothesis,risks,validation}_exp074b_null.md
- specs/lab_protocolo_cientifico/exp075_index.md
- specs/lab_protocolo_cientifico/exp074b_null_index.md
- specs/lab_protocolo_cientifico/hypothesis_energia_wyckoff_design.md  (marcado BLOCKED)
- specs/lab_protocolo_cientifico/DATA_REQUIREMENTS_EW.md  (nuevo, no ejecutado)
- specs/lab_protocolo_cientifico/ew_data_requirements_index.md
- reports/EXP-075/{summary.txt, protocol_frozen.json}
- reports/EXP-074b_NULL/{summary.txt, protocol_frozen.json}
- data/strategy_lab/exp075_phaseA_features.parquet  (gitignored data/, regenerable)
- data/strategy_lab/exp074b_null_curves.parquet     (gitignored data/, regenerable)
- agent/HANDOFF.md, agent/PROJECT_STATE.md, progress/current.md (estado real)

### Reglas que NO romper
- Una feature a la vez. SDD obligatorio para features sdd:true.
- No push sin OK. Commit = solo trabajo de la sesión.
- Bot corre PRACTICE por defecto; NUNCA REAL sin OK explícito.
- Datos REAL = descubrimiento; OTC = validación final (Art. 13).
- NO buscar más edge en clusters (orden Trader-Humano). NO ejecutar EXP-076.
- Energía Wyckoff: BLOQUEADA por instrumento (NO resultado negativo). NO ejecutar EW-1/2/3.
  NO buscar feed por cuenta propia. Bloqueo = insuficiencia del instrumento de medición.
