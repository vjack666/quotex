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
- **AUTORIZADO (2026-08-07) — Databento / CME 6E**: proveedor Databento, dataset `GLBX.MDP3`, símbolo
  continuous `6E.v.0` (volume roll), schema `ohlcv-1m` (NO MBO, adquisición pequeña), `volume`=contratos
  reales, UTC, período 2022-01-01..2026-08-01. EW pasa a hipótesis sobre **EUR/USD Futures 6E** (no spot).
  - **BLOQUEO DE ACCESO:** cliente `databento` 0.83.0 instalado, PERO **SIN API key** (ni env, ni .env).
    Aún NO se descargó nada. Scripts listos SIN ejecutar: `scripts/lab_ew_acquire_cme.py` (descarga 1m)
    y `scripts/lab_ew_verify_cme.py` (checklist completo + inspección de rollovers: comparar contratos
    del contrato individual vs volumen de la serie continua alrededor de cada roll). **Falta la API key
    para correr acquire→verify.** Si pasa: presentar para autorizar congelación EW-1. Si falla: documentar
    y detener (sin imputar ni filtrar). NO se ejecutó EW-1/2/3.
- NO se buscó dataset por cuenta propia más allá de inspeccionar el candidato ya presente. NO EW-1/2/3.

- **NO PAGAR aún (2026-08-07) — BÚSQUEDA GRATUITA para CME 6E**: orden del Trader-Humano = no comprar
  Databento; buscar fuente gratuita (Barchart, contratos individuales, export OHLCV intradía). Búsqueda
  read-only concluye: NO existe fuente gratuita con M15/1-min de 6E y cobertura 2022-2026 completa.
  - Kaggle "Euro FX Futures (CME) 2000-2022": 266 CSV individuales OHLC+Vol, pero **hasta 2022** → no
    cubre TEST 2025-2026.
  - Yahoo `6E=F`: M15 solo 60d (0% ceros, volumen real); **DIARIO 2022-2026 COMPLETO** (1,150 barras,
    0.52% ceros, 0% missing) → la ÚNICA vía gratuita completa.
  - Barchart free: intradía ~10a pero **1 descarga/día + máx 10k registros** → inviable para 4a M15.
  - CME Volume/OI reports: solo diario (validación de volumen, no sustituye M15).
  - massive/firstratedata/portara: de pago.
  - **Conclusión:** construir continuo desde individuales gratuitos tampoco cierra (no llegan a 2025-26).
    Alternativas: **(A-gratis) EW en DIARIO con `6E=F`** (Yahoo, 2022-2026, volumen real; desvía spec M15→D,
    requiere aprobación); **(C-pago) Databento M15** 2022-2026; **(B) M15 60d** insuficiente para OOS.
  - **NO se compró nada. NO se ejecutó EW-1.** Pendiente elección del Trader-Humano.

- **REFRAME + FASE 1 GRATIS (2026-08-07, fin de sesión):** el Trader-Humano reframó el objetivo a
  *comprobar si EW tiene capacidad predictiva*. Conclusión: fuente gratuita M15 2022-2026 NO existe;
  única completa = Yahoo `6E=F` **DIARIO** 2022-2026 (~1,150 barras, volumen real, 0.52% ceros). Plan:
  1) diario 2022-2026 → 2) TRAIN 2022-2024 / TEST 2025-2026 → 3) EW-1. **Puerta de evidencia:** sin señal
  OOS → matar EW (no gastar en M15); con señal OOS → justifica pagar Databento M15 y refinar en mayor
  - **RESTRICCIÓN EXPLÍCITA:** NO congelar EW-1 ni ejecutar hasta que el cambio **M15→DIARIO**
    quede explícitamente autorizado como modificación del protocolo. Pendiente: "sí, hacemos A: diario gratis".
    **NO comprado, NO ejecutado.**

  - **AUTORIZADO A EJECUTADO (2026-08-07, fin de sesión):** el Trader-Humano dijo "hagamos A — diario gratis
    con 6E=F". EW-1 adaptado formalmente M15→**D1**. Adquisición real: `lab_ew_acquire_daily.py` descargó
    Yahoo `6E=F` DIARIO 2022-2026 → **1,150 barras** en `data/strategy_lab/ew_6e_daily.parquet` (raw intacto,
    gitignored). `volume` = contratos reales CME. Verificación (`lab_ew_verify_daily.py`): 6/7 OK; único desvío
    = 2025 con 2.38% missing de volumen (6 barras con precio real → laguna de reporte Yahoo, no día sin trading).
    **Opción 2 del Trader-Humano:** `volume==0` = MISSING (NO imputar, NO borrar del raw); EW-1 usa solo las
    **1,144 barras válidas** (`valid_volume = volume>0`); raw intacto para trazabilidad. Veredicto: APTO CON
    EXCLUSIÓN DOCUMENTADA. **GATE DE CONGELACIÓN PENDIENTE:** Hermes confirmó modificación documentada y SIN
    imputación; falta OK explícito del Trader-Humano para CONGELAR EW-1 (solo entonces se ejecuta). NO ejecutado.

  - **EW-1 EJECUTADO + AUDIT + RETRACCIÓN (2026-08-07):** TH dijo "congela y ejecuta EW-1". Corrí
    `scripts/lab_ew1_autocorrelacion.py` (Ljung-Box eficiencia/absorción, D1, 1,144 válidas, Opción 2).
    **FALSA ALARMA 1:** primer pase reportó "20 lags significativos TRAIN+TEST" → declaré "SEÑAL OOS
    justifica M15". AUDIT: `eficiencia` no estacionaria (Ljung-Box arrastraba tendencia) y `absorcion`
    binaria mal especificada. **RETRACCIÓN 1.** Tras corregir (Δeficiencia estacionaria, absorción
    centrada) seguía "20 lags". **FALSA ALARMA 2 / RETRACCIÓN 2:** segundo AUDIT (temp ya borrado) ancló
    que Ljung-Box está BIEN (12/200 rechazos ruido blanco) y Δeficiencia ACF lag-1 = **-0.52** en TRAIN
    y TEST, lags 2-5 ≈0 → MA(1) de REVERSIÓN de 1 paso (efecto mecánico ratio move/vol), NO memoria de
    energía direccional Wyckoff. Veredicto final: `reversion_ma1_mecanica` → EW NO halla lo que buscaba
    → **NO justifica pagar Databento M15**. Reporte inmutable: `data/strategy_lab/ew_reports/EW-1/`.
    **NO se pagó Databento. NO se ejecutó EW-2.** Siguiente: archivar EW o reformular (pendiente TH).

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

### NUEVA RUTA (2026-08-07) — edificio_wyckoff_phasea (feature id 39, spec_ready, APROBADO trader-humano)
Pivot del proyecto: objetivo final = Edificio como detector/timing de Fase A de Wyckoff para binarias.
- SDD creado: `specs/edificio_wyckoff_phasea/{requirements,design,tasks,trader_humano_review}.md`.
- ADR-039 (reglas de oro): (1) Edificio NO se modifica para encajar en Wyckoff; (2) volumen NUNCA requisito.
- Datos verificados en disco: `src/strategy_lab/results/edificio_events.parquet` (señales con `win`, `split` OOS,
  `brake_time`) + `data/strategy_lab/cohorte_real_eurusd/EURUSD_M15.parquet` (543k velas M15 spot, tick_volume).
- EW-1 (`move/vol` 6E) baja a investigación auxiliar; `lab_ew_brake_link.py` queda paralelo, NO ruta principal.
- Fases R0-R3 (esta feature): congelar Edificio → inventario OHLC → radiografía WIN/LOSS → descubrimiento estructural.
  R4-R10 (mapeo Wyckoff, Phase A Score, binarias, OOS, robustez, producción) = features siguientes.
- PODER: TH delegó a Hermes la toma de roles (trader-humano/scientist). Hermes dictó APROBADO y avanza experimentos;
  TH pide aviso "cuando consigas la estructura adecuada".
- Next: implementer ejecuta T1-T8 (script `lab_phaseA_radiografia.py`) sin tocar src/. Sin descargas.

### R4 EJECUTADO (2026-08-07) — Phase_A_Score solo precio + mapa Wyckoff + comp WIN/LOSS
- Script `scripts/lab_phaseA_r4_score.py` (standalone, sin imports del Edificio). 946 señales.
- Entregables: (1) `wyckoff_map.json` (PS/SC/AR/ST/Spring/UT -> evento OHLC puro);
  (2) `Phase_A_Score` 0..7 (rank/split de 7 componentes: agotamiento+compresion+solapamiento+
  fallos_ruptura+rechazo+reduc_continuacion+cambio_regimen); (3) comp WIN vs LOSS.
- RESULTADO HONESTO: separacion MODESTA. TEST/OOS d=0.27 (WIN 3.60 vs LOSS 3.46; %>4 WIN 6.5% vs LOSS 3.7%).
  TRAIN d=0.37 (WIN 3.68 vs LOSS 3.40; %>4 WIN 32.8% vs LOSS 21.5%).
- INTERPRETACION: estructura Fase A SI esta en los WIN (senal real, aparece OOS y en ambos lados),
  pero DEBIL — NO es el mecanismo dominante del Edificio. Falsacion parcial de la hipotesis fuerte
  ("Edificio = detector limpio de Fase A"): confirmada debilmente, no descartada, no triunfal.
- REGLA DE ORO cumplida: volumen NUNCA requisito; Edificio caja negra intacta; solo datos en disco.
- Reporte inmutable: `data/strategy_lab/ew_reports/PHASEA-R4/`. Commit pendiente de OK.

### R5 EJECUTADO (2026-08-07) — Estructura INDEPENDIENTE del Edificio (sin Edificio/win/volumen)
- Script `scripts/lab_phaseA_r5_independent.py`. 108.657 ventanas M15 (step 5, ventana 20).
- R5-A: Phase_A_Score sobre TODO el mercado (solo OHLC+tiempo, rank global).
- R5-B (trayectoria): autocorrelacion score lag1=**0.505**, lag2=0.22, lag3=0.16 -> score PERSISTENTE
  (es proceso/clúster, no vela aislada) -> coherente con Wyckoff como secuencia.
- R5-C (consecuencia sin Edificio): ret_3 por tercil de score ~**0** en todos
  (bajo +2.5e-6, medio -1.9e-6, alto -8.7e-6); OOS 2a mitad tambien ~0.
  => la estructura NO predice direccion ni expansion del mercado por si sola.
- Ablation: quitar compression/overlap/break_fail cambia corr con break_3 ~0.04-0.05;
  NINGUN componente domina -> senal repartida y DEBIL, no hay 2-3 piezas magicas.
- VERDICTO HONESTO (falsacion util): el Phase_A_Score tiene comportamiento propio
  (persistencia temporal) PERO NO genera edge direccional propio. Lo que R4 vio fue
  correlacion con CUANDO EL EDIFICIO ACIERTA, no con el movimiento del mercado.
  => Refuerza la arquitectura del TH: Wyckoff = CONTEXTO/FILTRO, no gatillo ni
  generador de direccion. R6 (cruzar contexto + Edificio) es el siguiente paso real.
- Regla de oro: sin volumen, sin Edificio, sin win/loss. Caja negra intacta.
- Reporte inmutable: `data/strategy_lab/ew_reports/PHASEA-R5/`. Commit pendiente de OK.

### R6 EJECUTADO (2026-08-07) — Contexto (Fase A) x Edificio (matriz)
- Script `scripts/lab_phaseA_r6_cross.py`. 946 senales. Score M15 previo al brake_time
  (solo OHLC+tiempo, rank POR SPLIT) -> terciles Fase A baja/media/alta -> cruce con win Edificio.
- MATRIZ RESULTADO:
  - TRAIN: baja=27.0% media=33.8% alta=47.6% | chi2=21.46 p≈0.000 (SIGNIFICATIVO, pendiente creciente)
  - TEST/OOS: baja=32.2% media=43.3% alta=43.3% | chi2=3.10 p≈0.54 (NO significativo, pendiente se aplana)
- VERDICTO HONESTO (falsacion parcial): en TRAIN el contexto Fase A SÍ filtra el timing del
  Edificio (27->34->48%), pero en TEST/OOS la pendiente se degrada (32->43->43) y pierde
  significancia. NO es el filtro robusto 52/56/63 esperado. El efecto existe en muestra y se
  debilita OOS -> NO meter el score en el Edificio (disciplina del TH mantenida).
- INTERPRETACION: el contexto Wyckoff aporta un filtrado MARGINAL y no robusto; el edge del
  Edificio NO se explica ni se amplifica de forma fiable por la estructura de Fase A medida.
- Regla de oro: sin volumen, Edificio caja negra intacta. Reporte: `data/strategy_lab/ew_reports/PHASEA-R6/`.

### R7 EJECUTADO (2026-08-07) — Edificio como BINARIA (direccion + expiracion), SIN filtro Wyckoff
- Script `scripts/lab_phaseA_r7_binary.py`. OFFLINE, caja negra intacta, sin volumen.
- Solo EURUSD tiene M15 en disco (286 eventos: 205 train / 81 test). BRECHA DE DATOS honesta
  (no se cambia de instrumento; otros 5 assets del Edificio no tienen precio en disco).
- Win recalculado DESDE EL PRECIO con horizonte H fijo (1-5 velas M15), payout asumido 80% (OFFLINE).
- RESULTADO (win rate / EV; break-even binario = 55.6% con payout 80%):
  - TRAIN: win_orig 37.1% | H1=44.9%(EV-0.19) H2=48.8%(-0.12) H3=48.8%(-0.12) H4=49.3%(-0.11) H5=46.8%(-0.16)
  - TEST:  win_orig 45.7% | H1=26.0%(-0.53) H2=28.4%(-0.49) H3=26.0%(-0.53) H4=29.6%(-0.47) H5=27.2%(-0.51)
- VERDICTO (falsacion clara de viabilidad binaria): el Edificio NO es rentable como binaria.
  El mejor caso (H4 train) llega a ~49% / EV -0.11; en TEST/OOS cae a 26-30% / EV -0.47..-0.53.
  El edge del Edificio NO es un edge de direccion binaria a horizonte fijo. R10 (produccion binaria)
  DESCARTADO para este dataset/horizontes. No es Wyckoff lo que lo arruina: la direccion no bate break-even.
- Regla de oro: offline, Edificio caja negra intacta, sin volumen, sin filtro Wyckoff.
  Limite: cobertura solo EURUSD (brecha de datos). Reporte: `data/strategy_lab/ew_reports/PHASEA-R7/`.
- CONCLUSION R0-R7: rama Wyckoff-como-filtro marginal/no robusta (R6) y Edificio como binaria no rentable (R7).
  Ambas lineas agotadas con evidencia. Decision del TH: archivar o reenfocar.


## EXP-POI-STOCH (2026-08-07)
H1=INCONCLUSA H2=INCONCLUSA H3=ACEPTADA | eventos=14269 EURUSD_otc M15. EURCHF_otc no disp (Token rejected).

## EXP-POI-STOCH (2026-08-07)
H1=REFUTADA H2=INCONCLUSA H3=REFUTADA | eventos=14269 EURUSD_otc M15. EURCHF_otc no disp (Token rejected).
