# BITÁCORA EXPERIMENTAL — Laboratorio de Estrategias

> **Propósito**: Registro cronológico de experimentos, descubrimientos, fallos y errores del Laboratorio de Estrategias.
> **Alcance**: EXP-001 a EXP-038.
> **Última actualización**: 2026-08-05.

---

## Fase 1 — Experimentos iniciales y baseline (EXP-001 a EXP-007)

### EXP-001 — Filtro por separación K/D y tiempo de freno
- **Hipótesis**: Un cruce estocástico con separación amplia (`cross_separation >= 4.5`) y espera larga desde el freno (`minutes_brake_to_cross >= 16`) mejora el baseline.
- **Resultado**: 126 eventos, WR 47.62%, EV -0.0476, PF 0.91.
- **Veredicto**: INCONCLUSIVE (1/7 criterios).
- **Logro**: Estableció el baseline comparativo del 37.1% WR y demostró que los umbrales iniciales no pasan el tribunal.

### EXP-002 — Features estructurales multi-par
- **Hipótesis**: Features estructurales agregadas mejoran la señal.
- **Resultado**: 24,461 eventos, WR 48.87%, EV -0.0225, PF 0.956.
- **Veredicto**: FAIL.
- **Logro**: Confirmó que features genéricas no superan el baseline; necesidad de aislar condiciones específicas del Edificio.

### EXP-003 — Freno + martillo exacto
- **Hipótesis**: Combinar `brake_transition` con martillo exacto en ventana corta mejora WR.
- **Resultado**: 18 a 41 eventos, WR 50.00%, EV 0.0000, PF 1.0.
- **Veredicto**: INCONCLUSIVE (0/7).
- **Logro**: Demostró que la condición combinada es muy rara; señal nula por muestra insuficiente.

### EXP-004 — Pipeline completo del Edificio
- **Hipótesis**: La secuencia completa (freno → cruce estocástico → validación → martillo M15) reproduce el modelo cognitivo y mejora WR.
- **Resultado**: 1,155 eventos, WR 47.79%, EV -0.0442, PF 0.915.
- **Veredicto**: INCONCLUSIVE (1/7).
- **Descubrimiento clave**: El pipeline completo es perdedor; la secuencia completa mata la señal del freno.

### EXP-005 — Solo freno en zona POI
- **Hipótesis**: Restringir a frenos en zona POI mejora la calidad.
- **Resultado**: 1,234 eventos, WR 47.33%, EV -0.0535, PF 0.898.
- **Veredicto**: INCONCLUSIVE (1/7).
- **Descubrimiento clave**: La zona POI por sí sola no mejora el freno; posiblemente descarta eventos válidos.

### EXP-006 — Solo cruce estocástico zona extrema
- **Hipótesis**: El cruce estocástico en zona extrema tiene señal predictiva.
- **Resultado**: 24,289 eventos, WR 50.27%, EV +0.0055, PF 1.011.
- **Veredicto**: INCONCLUSIVE.
- **Logro**: Señal marginalmente positiva, pero insuficiente para tribunal.

### EXP-007 — Solo martillo M15
- **Hipótesis**: El martillo M15 como condición aislada es predictivo.
- **Resultado**: 19,993 eventos, WR 49.21%, EV -0.0159, PF 0.969.
- **Veredicto**: FAIL.
- **Descubrimiento clave**: El martillo aislado no tiene valor predictivo en M15 multi-par.

---

## Fase 2 — Descomposición y variantes de martillo (EXP-008 a EXP-009)

### EXP-008 — Martillo post-cruce
- **Hipótesis**: El martillo posterior al cruce estocástico mejora respecto al martillo aislado.
- **Resultado**: 22,972 eventos, WR 49.34%, EV -0.0131, PF 0.974.
- **Veredicto**: FAIL (3/7).
- **Logro**: Confirmó que combinar martillo + cruce no genera señal robusta.

### EXP-009 — Freno puro (`brake_transition`)
- **Hipótesis**: El freno aislado tiene señal predictiva.
- **Resultado**: 46,767 eventos, WR 54.11%, EV +0.0823, PF 1.179.
- **Veredicto**: FAIL (3/7).
- **Descubrimiento clave**: El freno puro es el único componente con señal real (EV positivo), pero no pasa robustness ni power.

---

## Fase 3 — Filtros de calidad del freno (EXP-010 a EXP-019)

### EXP-010 — Filtros de calidad del freno (body_n y brake_ratio)
- **Hipótesis**: Filtrar por `body_n >= 0.8` y `brake_ratio >= 1.5` mejora robustez.
- **Resultado inicial**: Error por columna inexistente `body_n_brake`.
- **Corrección**: Reemplazada por columnas válidas `body_n` y `brake_ratio`.
- **Resultado final**: Múltiples variantes, mejor WR 56.1%, pero robustness 1/5 y power 0.0.
- **Lección**: Los filtros de calidad mejoran correlación, no reproducibilidad.

### EXP-011 — Filtros estrictos + horizonte 2 velas
- **Hipótesis**: Ampliar horizonte a 2 velas con filtros estrictos mejora robustez.
- **Resultado**: 1,370 eventos, WR 59.34%, EV +0.187, PF 1.46.
- **Veredicto**: FAIL (power y robustness).
- **Descubrimiento**: Muy pocos eventos; trade-off estrictez/muestra insuficiente.

### EXP-012 — Filtro intermedio (1.5, 1.5) + horizonte 2 velas
- **Hipótesis**: Relajar filtros y ampliar horizonte mejora muestra sin perder señal.
- **Resultado**: ~3,900 eventos, WR ~57%, EV ~+0.15, PF ~1.35.
- **Veredicto**: FAIL (power y robustness).
- **Logro**: Confirmó que más eventos no resuelve el problema de robustez.

### EXP-013 — Filtro de `kd_dist` mínimo
- **Hipótesis**: Agregar separación K/D en el freno mejora predictibilidad.
- **Resultado**: ~46,000 eventos, WR ~46%, PF ~1.18.
- **Veredicto**: FAIL.
- **Descubrimiento clave**: `kd_dist` no aporta selectividad; la señal del freno no depende de la separación estocástica en el momento del freno.

### EXP-014 — Horizonte 3 velas con filtro intermedio
- **Hipótesis**: Evaluar en vela idx+3 mejora respecto a horizonte 2.
- **Resultado**: Menos eventos y PF inferior a EXP-012.
- **Veredicto**: FAIL.
- **Lección**: Ampliar horizonte más allá de 2 velas con el mismo filtro no ayuda.

### EXP-015 — Freno alineado con `trend` de corto plazo
- **Hipótesis**: Exigir alineación direccional con `trend` mejora robustez.
- **Resultado**: 37,331 eventos, WR 54.14%, EV +0.0827, PF 1.18.
- **Veredicto**: FAIL (power y robustness).
- **Descubrimiento**: La alineación con `trend` no mejora; incluso reduce PF.

### EXP-016 — Filtro de volumen relativo (`rvol`) alto
- **Hipótesis**: `rvol` alto en el freno indica convicción y mejora robustez.
- **Resultado**: Mejor variante `rvol=3.0` → WR 58.83%, EV +0.1767, PF 1.43, 583 eventos.
- **Veredicto**: FAIL (power 0.0, robustness 1/5).
- **Logro**: `rvol` es el filtro que más acerca PF al umbral 1.3, pero aún insuficiente.

### EXP-017 — `rvol>=1.5` + horizonte 4 velas
- **Hipótesis**: Combinar `rvol>=1.5` con horizonte extendido mejora robustez.
- **Resultado**: 9,045 eventos, WR 58.10%, EV +0.162, PF 1.39.
- **Veredicto**: FAIL (power y robustness).
- **Lección**: Más eventos y PF alto no bastan; el tribunal exige reproducibilidad.

### EXP-018 — Solo rebote post-brake (`rebote_mask`)
- **Hipótesis**: El rebote estructural después de un brake tiene señal predictiva.
- **Resultado**: Error de ejecución — columna `rebote_mask` no existe.
- **Veredicto**: FAIL por construcción.
- **Lección crítica**: Verificar existencia de columnas antes de diseñar experimentos.

### EXP-019 — Score combinado `body_n * brake_ratio`
- **Hipótesis**: El producto captura interacción no lineal y mejora robustez.
- **Resultado**: Mejor variante `score>=3.0` → WR 57.87%, EV +0.1574, PF 1.37, 4,593 eventos.
- **Veredicto**: FAIL (power y robustness).
- **Descubrimiento**: El score combinado no rompe la barrera de robustez; los filtros están capturando correlación, no reproducibilidad.

---

## Fase 4 — Consistencia temporal (EXP-020 a EXP-029)

### EXP-020 — Consistencia multi-horizonte (1 a 5 velas)
- **Hipótesis**: Requierir consistencia en múltiples horizontes mejora robustez.
- **Resultado**: WR 85.31%, EV 0.7062, PF 5.81, power ~1.0.
- **Veredicto**: FAIL (robustness 2/5).
- **Hallazgo**: WR/PF altos, pero la señal no sobrevive a stress/perturbaciones.

### EXP-021 — Consistencia endurecida 4/5
- **Hipótesis**: Endurecer a 4/5 reduce falsos positivos sin perder demasiados eventos.
- **Resultado**: WR 94.55%, EV 0.8909, PF 17.34, power ~1.0.
- **Veredicto**: FAIL (robustness 1/5).
- **Hallazgo**: Más estricto no arregla robustness; reduce aún más la reproducibilidad.

### EXP-022 — Consistencia 3/5 con evaluación alineada idx+1
- **Hipótesis**: Evaluar en la misma vela que la consistencia reduce desfase.
- **Resultado**: WR 75.73%, EV 0.5145, PF 3.12, power ~1.0.
- **Veredicto**: FAIL (robustness 2/5).
- **Hallazgo**: Cambiar el horizonte de evaluación tampoco rompe la barrera de robustez.

### EXP-023 — Consistencia 3/5 con evaluación en idx+3
- **Hipótesis**: Un horizonte intermedio equilibra desfase y señal.
- **Resultado**: WR 91.28%, EV 0.8256, PF 10.47, power ~1.0.
- **Veredicto**: FAIL (robustness 2/5).

### EXP-024 — Consistencia estricta 3/3 en horizontes 1-3
- **Hipótesis**: Ventana corta + consistencia perfecta mejora estabilidad.
- **Resultado**: WR 90.36%, EV 0.8072, PF 9.37, power ~1.0.
- **Veredicto**: FAIL (robustness 2/5).
- **Hallazgo**: Consistencias extremas siguen sin pasar el tribunal por falta de reproducibilidad.

### EXP-025 — Refuerzo de baseline / sanity
- **Hipótesis**: Sanity check de baseline y features estables.
- **Resultado**: WR 54.11%, EV 0.0823, PF 1.18, power 1.0.
- **Veredicto**: FAIL (robustness 2/5).

### EXP-026 — Señal pura: dirección del impulso tras brake_transition
- **Hipótesis**: La dirección del impulso post-brake es suficiente sin consistencia.
- **Resultado**: WR 54.11%, EV 0.0823, PF 1.18, power 1.0.
- **Veredicto**: FAIL (robustness 2/5).
- **Hallazgo**: Señal pura no supera la prueba de stress.

### EXP-027 — Consistencia 3/5 con alineación de impulso y precio
- **Hipótesis**: Agregar consistencia de `impulse_net` mejora robustness.
- **Resultado**: WR 83.37%, EV 0.6675, PF 5.01, power ~1.0.
- **Veredicto**: FAIL (robustness 2/5).

### EXP-028 — Consistencia relajada 2/5
- **Hipótesis**: Relajar a 2/5 mejora robustness respecto a 3/5.
- **Resultado**: WR 79.07%, EV 0.5815, PF 3.78, power 1.0.
- **Veredicto**: FAIL (robustness 2/5).

### EXP-029 — Consistencia 3/5 con filtro `rvol >= 1.5`
- **Hipótesis**: Agregar `rvol` reduce ruido sin eliminar demasiados eventos.
- **Resultado**: WR 85.31%, EV 0.7062, PF 5.81, power 0.994.
- **Veredicto**: FAIL (robustness 1/5).
- **Hallazgo**: Incluso con filtro de volumen, robustness sigue por debajo del umbral.

### EXP-030 — Clasificación de secuencias P2→P3→entrada
- **Hipótesis**: Variantes del pipeline Edificio tienen valor predictivo clasificable.
- **Resultado**: WR 48.63%, EV -0.0273, PF 0.947, power 0.986.
- **Veredicto**: INCONCLUSIVE.
- **Hallazgo**: Clasificación de secuencias sola no explica resultados; requiere features adicionales o redefinición de estados.

### EXP-031 — Secuencias del pipeline Edificio con validación estructurada
- **Hipótesis**: El pipeline secuencial P2→P3→entrada mejora cuando se valida como máquina de estados.
- **Resultado**: Documentación estructurada; sin resultado numérico aislado por superposición con integración de secuencia.
- **Veredicto**: NO APLICA COMO EXPERIMENTO AISLADO.
- **Hallazgo**: El foco se trasladó a `sequence_engine.py` como fuente única de verdad.

### EXP-032 — Pipeline aislado de freno confirmado
- **Hipótesis**: Medir solo `brake_confirmed` sin combinaciones prematuras.
- **Resultado**: WR 53.29%, EV +116, PF 1.14, n=1,764.
- **Veredicto**: FAIL.
- **Hallazgo**: El brake confirmado muestra correlación, pero no alcanza robustness suficiente.

### EXP-033 — Cruce limpio confirmado post-cierre
- **Hipótesis**: `cross_clean_confirmed` como gate estricto post-cierre.
- **Resultado**: WR 60.34%, PF 1.52, n=58.
- **Veredicto**: INCONCLUSIVE.
- **Hallazgo**: Muestra pequeña; el gate puede tener valor, pero requiere aislamiento mayor.

### EXP-034 — Pipeline completo secuencial
- **Hipótesis**: Pipeline completo secuencial aislado reproduce la señal Edificio.
- **Resultado**: 5 eventos, WR 40%.
- **Veredicto**: FAIL por construcción.
- **Hallazgo**: El pipeline secuencial reduce drásticamente los eventos y no mejora WR.

### EXP-034B — Pipeline secuencial v1 y v2
- **Hipótesis**: Ajustes de pipeline mejoran cantidad de eventos y WR.
- **Resultado v1**: WR 71.43%, PF 2.5, n=7.
- **Resultado v2**: WR 47.2%, PF 0.89, n=750.
- **Veredicto**: FAIL.
- **Hallazgo**: La variante v2 muestra falsación; ampliar muestra rompe la señal inicial.

### EXP-035 — Diagnóstico de cuello de botella por piso
- **Hipótesis**: Identificar qué piso elimina más candidatos antes de calibrar thresholds.
- **Resultado**: Diagnóstico completado; cuello de botella principal en acceso a CEREBRO y validación de `kd_distance`.
- **Veredicto**: INCONCLUSIVE.
- **Hallazgo**: El problema no era robustness de filtros, era falta de features capturadas para `kd_distance`.

### EXP-036 — Live vs backtest con validación estricta de secuencia
- **Hipótesis**: El sistema actual acepta candidatos que no pasan la secuencia Edificio.
- **Resultado live**: 118 candidatos, 108 aceptados actualmente.
- **Resultado bajo `sequence_engine`**: 0 llegaron a `ENTRADA`; 20 rechazados en RECEPCIÓN, 108 en CEREBRO.
- **Veredicto**: PASS.
- **Hallazgo clave**: El cuello de botella real es la validación de secuencia, no los thresholds; además la base live `black_box_strat_2026-08-03.db` tiene 100% de `kd_distance` en `None`/`0.0` y velas/stochs vacíos en registros EDIFICIO, impidiendo cualquier calibración posterior con ese dataset.

### EXP-037 — Barrido de sensibilidad de acceso a piso
- **Hipótesis**: Existe una configuración de `kd_distance`, `dwell_ticks` y `cross_limpieza_ok` que maximiza llegadas a `ENTRADA`.
- **Resultado inicial sobre base live**: 0 `ENTRADA` en 18 configuraciones.
- **Causa raíz**: No es sensibilidad de thresholds, es deuda de captura de features en la base live.
- **Dataset offline**: `data/exports/exp037_kd_distance_dataset.csv` desde `EURUSD_M15.parquet`, 113,083 filas, `kd_distance` real media 6.07, mediana 4.68, máx 31.55.
- **Barrido completo sobre dataset offline**:
  - `cross_clean=True` es condición necesaria: sin él, 0 entradas en todas las configs.
  - `dwell_cerebro=2` con `cross_clean=True` elimina todo en este dataset.
  - `dwell_cerebro=0` y `dwell_cerebro=1` con `cross_clean=True` son idénticos por nivel de `kd_distance`: 0.0→100%, 1.0→87.4%, 1.5→81.4%, 2.0→75.5%, 2.5→70.1%, 3.0→65.0%, 4.0→55.6%.
- **Config candidata**: `kd_distance=2.0, dwell_cerebro=1, cross_limpieza_ok=True`.
- **Veredicto**: PENDIENTE DE ESTABILIDAD TEMPORAL.
- **Próximo paso**: EXP-038 evalúa train/test 70/30 sobre esa configuración.

### EXP-038 — Estabilidad temporal de config ganadora
- **Hipótesis**: La configuración ganadora de EXP-037 mantiene entrada_rate similar en train vs test.
- **Dataset**: mismo offline de 113,083 filas; split 70/30 por timestamp.
- **Config evaluada**: `kd_distance=2.0, dwell_cerebro=1, cross_limpieza_ok=True`.
- **Resultado**:
  - Train: 75,158 eventos, 59,734 entradas, rate=0.7546.
  - Test: 33,925 eventos, 25,697 entradas, rate=0.7575.
  - Delta: 0.2848%.
- **Veredicto**: ESTABLE.
- **Conclusión**: La configuración es apta para convertirse en default empírico sin tunear a mano.

---

## Fase 5 — Integración de motor de secuencia (2026-08-05)

- **Cambio**: `sequence_engine.py` pasa a ser fuente única de verdad de transiciones.
- **Integración**:
  - `src/edificio_contratacion.py`: gate `CONTRATADO` consulta `_sync_sequence_card()` antes de emitir `CONTRATADO`.
  - `src/edificio_executor.py`: registra `kd_distance`, `cross_limpieza_ok`, `stoch_m15`, `stoch_m5`, `candle_15m_prev`, `candle_5m_prev`, `post_brake_*`, `rule_version`, `filters_applied`.
  - `src/black_box_recorder.py`: agrega fallback desde `strategy_details` para `stoch_*` y velas cuando llegan vacíos.
- **Verificación**: 119 passed, 0 failed en módulos afectados.

---

## Fase 7 — Motor de Secuencia Libre (LAB-SEC) y eliminación de look-ahead (2026-08-05)

### Contexto
El usuario opera por intuición: "la hipótesis nace con freno en POI y mayor atención cuando el estocástico cruza". EXP-004 midió el orden impuesto `freno → cruce → martillo` y dio WR 47.79% (INCONCLUSIVE, mataba la señal del freno). La pregunta abierta: ¿el orden que el usuario intuye es distinto al que el pipeline asumía?

### Cambio 1 — Motor de Secuencia Libre (`src/strategy_lab/secuencia_libre.py` + `run_lab_secuencia.py`)
- **Diseño**: a diferencia de `backtest_edificio.py`, NO impone orden. Detecta 5 eventos de forma independiente por vela — `extremo`, `freno`, `separacion`, `cruce`, `martillo` — y abre un expediente (`birth_idx`) en cada `freno` (Ley 1: el freno nunca mira al futuro).
- **Invalidación por zona muerta**: un expediente muere si el estocástico vuelve a [20,80] (zona media de 50 = peor caso) antes de completar; se descarta el escenario. NO usa timeout de 10h.
- **Etiqueta Ley 12**: `win` binario de 1 vela (close vs open de la vela de entrada), separado de la decisión de entrada. Sin TP.
- **Firma de secuencia**: registra el orden real de eventos como string (`extremo>freno>martillo>cruce`), la "gramática" que el usuario cree que existe.
- **Verificación ad-hoc dirigida (fresca)**: 14/14 PASS — causalidad (`idx_freno == birth_idx`), `win ∈ {-1,0,1}`, `win!=-1` solo en completas, firma coherente, `win` binario end-to-end coincide, ausencia de `i+1/i+2` en el módulo, zona muerta correcta.

### Cambio 2 — Eliminación de look-ahead en `compute_features.py` (líneas 203-230)
- **Hallazgo**: `brake_confirmed` y `cross_clean_confirmed` decidían la vela `i` usando `i+1` (rango futuro y contexto futuro). Look-ahead: el dataset de entrada del motor nacía contaminado.
- **Reescritura causal (no parche)**: ambas confirmaciones ahora usan solo `i`/`i-1`:
  - `brake_confirmed[i]` = freno en `i` + rango de `i` en contracción vs `i-1` + contexto de zona ya visible en `i`.
  - `cross_clean_confirmed[i]` = en `i` el estocástico ya está fuera de zona muerta (K y D ≤20 o ≥80) y `kd_dist ≥ 2.0`. Estado observable, no predicho.
- **Verificación**: ad-hoc 4/4 PASS (loop sin `i+1/i+2`; `brake_confirmed ⇒ brake_transition` en `i`; `cross_clean` observable en `i`). `pytest tests/strategy_lab/` → 4 passed. Suite completa 499 passed / 22 failed, pero los 22 fallos son en runtime del bot (`test_multi_duration_entry`, `test_parallel_scan_fase3`, `test_session_lifecycle`, `test_smart_order_place`) y **son preexistentes** (confirmado con `git stash`: fallan igual sin mi cambio; no importan `strategy_lab`). Mi cambio no introdujo regresión.

### Resultado del embudo (dataset ya limpio, 7 pares M15)
- 46,891 expedientes nacidos · 6,259 completas · 40,632 muertos en zona muerta.
- WR global de completas: **0.3208** (peor que azar) — el universo de "freno en POI" es mayoritariamente ruido.
- **Firmas con WR > 0.50 (todas con martillo ANTES del cruce)**:
  - `extremo>freno>martillo>cruce` → 0.5676 (n=111)
  - `extremo>freno>cruce>martillo` → 0.5556 (n=126)
  - `freno>extremo>separacion>martillo>cruce` → 0.6750 (n=40)
  - `extremo>freno>separacion>martillo>cruce` → 0.5401 (n=985, validación cruzada: 7/7 pares > 0.50)
- **Confirmación de la intuición del usuario**: martillo ANTES del cruce → WR 0.4467; martillo DESPUÉS del cruce → 0.2443 (Δ20 pts). El orden importa, en el sentido que el usuario planteó.
- **Por qué EXP-004 falló**: medía `freno→cruce→martillo`; el usuario intuye `freno→martillo→cruce`. El pipeline imponía un orden que no es el del trader.

### Veredicto
**INCONCLUSIVE / PENDIENTE DE TRIBUNAL.** Las firmas >0.50 son sugestivas y coherentes con la hipótesis del usuario, pero NO han superado el tribunal (sin barrido de ≥5 semillas, sin control negativo, sin validación por par no visto, n pequeñas). Pueden ser ruido de muestra. La deuda de look-ahead está saldada; el dataset de entrada es honesto.

### Archivos
- `src/strategy_lab/secuencia_libre.py` (nuevo)
- `src/strategy_lab/run_lab_secuencia.py` (nuevo)
- `src/strategy_lab/compute_features.py` (reescritura causal de confirmaciones)
- `data/strategy_lab/secuencia_libre_events.parquet` (expedientes regenerados)
- `data/strategy_lab/secuencia_libre_funnel.csv` (embudo Ley 11)

### Próximos pasos (Fase 4 y 5, pendientes de OK humano)
1. **Fase 4 — Red neuronal**: rankear firmas de secuencia (Ley 12: solo rankea, no decide). Entrada = one-hot de eventos ordenados por vela; salida = score de WR esperado.
2. **Fase 5 — Tribunal**: barrido ≥5 semillas, control negativo (permutar firmas), validación por par no visto, AUC temporal > 0.50. Solo entonces un lift cuenta.

---

## Estado del Laboratorio

- **Experimentos documentados**: 38
- **Experimentos PASS**: 1
- **Experimentos INCONCLUSIVE**: 8
- **Experimentos FAIL**: 28
- **Experimentos pendientes/necesitan repetición**: 0

## Próximos Pasos

1. Ejecutar protocolo live corto de validación (`docs/LIVE_VALIDATION_PROTOCOL.md`).
2. Si `noise_count > 0`, endurecer `edificio_executor.py` para consultar `SequenceEngine` antes de enviar.
3. Registrar resultados en `src/strategy_lab/results/exp039_live_validation.json` y actualizar bitácora.

---

## Fase 6 — Protocolo de validación live (2026-08-05)

- **Config calibrada**: `kd_distance >= 2.0`, `dwell_cerebro = 1`, `cross_limpieza_ok = True`.
- **Documento**: `docs/LIVE_VALIDATION_PROTOCOL.md`.
- **Default fijado en código**: `src/edificio_contratacion.py` instancia `SequenceEngine` con `min_kd_distance=2.0`.
- **Criterios**: `entrada_count > 0` y `noise_count = 0`.
- **Siguiente acción**: ejecutar captura live y registrar en EXP-039.

---

## Fase 5 — Veredicto real del tribunal + parche FDR/Bonferroni (2026-08-05)

### Contexto (el hueco del revisor externo)
Cuando se evalúan 36 firmas juntas, cada una con su p-valor binomial contra el
baseline, por azar algunas caen "arriba" del umbral. Sin ajuste por comparaciones
múltiples el tribunal promovería basura. Lo detectó el revisor externo.

### Cambio 1 — Parche FDR en `tribunal_v1.yaml`
Sección nueva `multiple_comparisons`:
- `enabled: true`, `default_method: fdr_bh` (Benjamini-Hochberg).
- Alternativa `bonferroni` (FWER, más conservadora: alpha/N).
- `seed: 20260805` fija para cualquier control negativo/permutación.

### Cambio 2 — `src/strategy_lab/multiple_comparisons.py` (nuevo)
Funciones puras, solo stdlib:
- `bonferroni(pvalues, alpha)` → p_ajustado = min(1, p*N).
- `benjamini_hochberg(pvalues, alpha)` → step-up FDR, p_ajustados monotonicos cap a 1.
- `adjust_pvalues(pvalues, method, alpha, ids)` → dispatcher que etiqueta por id.

### Cambio 3 — `evaluate_family()` en `promotion_gate.py` (nuevo)
Recibe la lista de `GateDecision` individuales, ajusta el p-valor de cada miembro
por FDR/Bonferroni ANTES del veredicto, y re-clasifica:
- si el ajuste hunde la significancia → `INCONCLUSIVE` (no `REFUTADO`: el ajuste
  por azar no prueba que la señal sea falsa, solo que no es distinguible).
- emite `FamilyDecision` con `promoted/inconclusive/refuted_members`.

### Verificación
- `tests/test_promotion_gate.py`: +4 tests (Bonferroni escala, BH monotono,
  `evaluate_family` hunde ruido bajo comparaciones múltiples, `evaluate_family`
  promueve señal real). Suite promotion_gate: **10/10 verde**.
- FDR rechaza una firma con p=0.04 crudo sobre 36 (Bonferroni: 0.04*36=1.44→cap 1.0);
  BH promueve solo señal con p=1e-6 sobre 10.

### PASO 2 — Veredicto sobre las 9 firmas con n≥100 (datos reales)
Dataset: `data/strategy_lab/secuencia_libre_events.parquet`
(46,891 expedientes · 6,259 completas · WR global 0.3208).

**Baseline del tribunal = 0.5 (azar puro).** Nota: usar 0.3208 (WR global del
motor libre) es tramposo — es el promedio de todas las firmas, no un nulo. Se
descarta ese baseline para el veredicto.

| Firma (n≥100) | n | WR | p crudo | power | Veredicto |
|---|---|---|---|---|---|
| extremo>freno>separacion>cruce>martillo | 2019 | 0.3041 | 5.1e-71 | 0.77 | INCONCLUSIVE |
| extremo>freno>separacion>martillo>cruce | 985 | 0.5401 | 1.3e-02 | 0.47 | INCONCLUSIVE |
| freno>separacion>extremo>cruce>martillo | 783 | 0.2503 | 4.3e-46 | 0.39 | INCONCLUSIVE |
| freno>separacion>extremo>martillo>cruce | 676 | 0.4320 | 4.6e-04 | 0.34 | INCONCLUSIVE |
| extremo>freno>martillo>separacion>cruce | 326 | 0.4785 | 4.7e-01 | 0.19 | INCONCLUSIVE |
| extremo>freno>cruce>separacion>martillo | 266 | 0.0263 | 3.0e-67 | 0.16 | INCONCLUSIVE |
| cruce>extremo>freno>separacion>martillo | 191 | 0.2408 | 3.9e-13 | 0.13 | INCONCLUSIVE |
| extremo>freno>cruce>martillo | 126 | 0.5556 | 2.5e-01 | 0.10 | INCONCLUSIVE |
| extremo>freno>martillo>cruce | 111 | 0.5676 | 1.8e-01 | 0.09 | INCONCLUSIVE |

`evaluate_family(method=fdr_bh)` → **PROMOVIDAS: 0 · INCONCLUSIVE: 9 · REFUTADAS: 0**
`evaluate_family(method=bonferroni)` → idéntico (0 promovidas).

### ¿Por qué ninguna pasa? (causas reales, NO el ajuste FDR)
El ajuste FDR **pasa** en todas; lo que hunde el veredicto es el propio tribunal:
1. **power < 0.80** en las 9 (rango 0.09–0.77). El tribunal exige poder mínimo.
2. **IC de win_rate incluye el nulo 0.5** en las firmas de WR medio (0.48–0.57):
   por definición del tribunal, inconclusive.
3. **robustez 0/5** y **systemic_impact no evaluado** (pendientes de ejecutar).

### Conclusión Fase 5
**INCONCLUSIVE para todas las candidatas.** El ajuste FDR no cambia el veredicto
(era esperable: el problema es muestra/poder, no comparaciones múltiples). La
mejor candidata (`extremo>freno>martillo>cruce`, n=111, WR=0.5676, +6.8pp sobre
azar) tiene power 0.09 — insuficiente para promover con confianza.

### PASO 3 — Decisión de datos (PENDIENTE DE ELECCIÓN DEL USUARIO)
El veredicto es "inconcluso por muestra", no "refutado". Dos caminos:
- **A) Aceptar** que la hipótesis no es promovible con los datos actuales y cerrar.
- **B) Recolectar más datos** (ventana temporal más larga y/o más pares M15) para
  llevar las firmas prometedoras a n≥500 y power≥0.80.
- Nota: correr más código no arregla falta de muestra; es trabajo de recolección.

### Archivos
- `src/strategy_lab/config/tribunal_v1.yaml` (sección `multiple_comparisons`)
- `src/strategy_lab/multiple_comparisons.py` (nuevo)
- `src/strategy_lab/promotion_gate.py` (`evaluate_family` + `FamilyDecision`)
- `tests/test_promotion_gate.py` (+4 tests FDR)
- Sin commit: pendiente de OK humano por §15 del tribunal.

---

## Fase 5 — Cierre (2026-08-06)

- **Commit FDR**: `1df48aa` (feat(lab): parche FDR/Bonferroni en tribunal + evaluate_family),
  pusheado a origin/main. 5 archivos, 436 inserciones, suite 10/10 verde.
- El ajuste FDR/Bonferroni quedó operativo en `evaluate_family()` (promotion_gate.py).
- Decisión humana: ejecutar Fase 1 (datos reales amplios) antes de cerrar. Ver abajo.

---

## Fase 1 — Prueba de existencia del efecto (cohorte REAL, aislada) (2026-08-06)

**Principio medicina**: Fase 1 = laboratorio con cohorte REAL (EURUSD real 2004-2024).
Fase 2 (OTC) = ensayo clínico, COMPLETAMENTE SEPARADO. No se mezclan jamás.

- **Fuente**: `C:\Users\v_jac\Desktop\backtest quotex\datos de velas\data\EURUSD\M15\2004..2024.csv`
  (datos REALES HistData; NO OTC — el repo no tiene CSV OTC, confirmado en
  `backtest quotex/docs/DECISION_OTC_SIN_HORARIO.md`).
- **Cohorte aislada** (sin tocar SMC_ROOT compartido, para no contaminar camino OTC):
  `data/strategy_lab/cohorte_real_eurusd/EURUSD_M15.parquet` → 543.310 velas M15.
- **Motor libre**: `run_secuencia_libre(pairs=["EURUSD"], root=WORK_ROOT)` — SOLO EURUSD real.
- **Resultado**:
  - Expedientes nacidos: 65.344 · Completas: 7.975 · WR global completas: 0.2866.
  - Firmas distintas: 39 · Firmas con n≥100: 12.
  - FDR-BH sobre las 12: **PROMOVIDAS=0 · INCONCLUS=12 · REFUTADAS=0**.
- **Detalle (n, WR, p_raw, power)**:
  - extremo>freno>separacion>cruce>martillo: n=2436 WR=0.2775 p=1.8e-110 power=0.84 → INCONCLUSIVE (WR<0.5)
  - extremo>freno>separacion>martillo>cruce: n=1176 WR=0.5298 p=4.4e-02 power=0.54 → INCONCLUSIVE
  - freno>separacion>extremo>cruce>martillo: n=1071 WR=0.2372 p=2.0e-69 power=0.50 → INCONCLUSIVE
  - freno>separacion>extremo>martillo>cruce: n=907 WR=0.4344 p=8.7e-05 power=0.44 → INCONCLUSIVE
  - extremo>freno>martillo>separacion>cruce: n=396 WR=0.4747 p=3.4e-01 power=0.22 → INCONCLUSIVE
  - extremo>freno>cruce>martillo: n=183 WR=0.5301 p=4.6e-01 power=0.12 → INCONCLUSIVE
  - extremo>freno>martillo>cruce (intuición trader): n=118 WR=0.6102 p=2.1e-02 power=0.10 → INCONCLUSIVE
  - cruce>freno>martillo: n=113 WR=0.0088 p=2.2e-32 power=0.09 → INCONCLUSIVE (anti-efecto)
- **Veredicto Fase 1**: el efecto de ORDEN de eventos NO sobrevive el tribunal ni con
  20 años de datos reales. Firmas con n grande (2000+) tienen WR<0.30 (peor que azar);
  firmas con WR>0.5 tienen n pequeño y power<0.2. El FDR no promueve ninguna.
- **Conclusión**: tal como pidió el humano ("enterarnos ahora"), la hipótesis de orden
  freno>martillo>cruce queda REFUTADA-EN-REAL (efecto no promovible con muestra amplia).
- **Fase 2 (OTC)**: pendiente, OPCIONAL. Como el laboratorio real ya negó el efecto,
  el ensayo clínico OTC tiene bajo valor esperado. Se mantiene el dataset OTC separado
  para validación externa si el humano lo requiere.

### Archivos de Fase 1
- `data/strategy_lab/cohorte_real_eurusd/EURUSD_M15.parquet` (cohorte real concatenada)
- `data/strategy_lab/cohorte_real_eurusd/secuencia_libre_events_real.parquet` (expedientes)
- No se commiteó el parquet (es artifact de datos, no código del lab).

---

## Cierre de ciclo (2026-08-06)

- FDR commiteado (`1df48aa`). Fase 1 ejecutada y documentada. Fase 2 OTC pendiente/opcional.
- Hipótesis "orden de eventos (freno>martillo>cruce)" declarada INCONCLUSIVE-POR-MUESTRA-AMPLIA
  en cohorte real; no promovible. El Edificio sigue con su configuración Fase 6 (sin cambios).

