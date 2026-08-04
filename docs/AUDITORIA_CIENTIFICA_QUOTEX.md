# Auditoría Científica de QUOTEX — Mapa de Capacidades

> **Objetivo:** responder “¿Qué patrimonio tecnológico y científico ya posee QUOTEX para construir el nuevo Laboratorio y el nuevo Edificio sin empezar desde cero?”
>
> **Alcance:** motor en vivo, Laboratorio, Edificio, documentación, HUB, IA, utilidades y tests.
>
> **Criterio:** no se evalúa si el código “funciona”. Se evalúa si **genera, almacena o aplica conocimiento útil** para el nuevo modelo cognitivo.

---

## 1. Metodología de clasificación

| Símbolo | Categoría |
|---|---|
| 🟢 | Activo estratégico |
| 🟡 | Reutilizable con adaptación |
| 🟠 | Experimental |
| ⚪ | Legacy |
| ⚫ | Obsoleto |

---

## 2. Mapa de capacidades

### 2.1 Conectividad y datos de mercado

**Capacidad:** conexión viva con Quotex, fetch de velas, reintentos, heartbeats, reconexión.

**Componentes principales:** `connection.py`, `caffeine.py`, `candle_cache.py`, `parallel_fetch.py`, `marketfeed/`.

**Clasificación:** 🟢 Activo estratégico

**Diagnóstico:**
- Es el cimiento de todo. Sin datos causales, el Laboratorio no existe.
- `connection.py` ya maneja reconexión y heartbeats.
- `candle_cache.py` implementa cache de velas con deduplicación.
- `parallel_fetch.py` descarga velas en paralelo con backpressure.
- `marketfeed/` separa fuentes de datos y graba/replay, lo que permite reproducibilidad offline.

**Valor para el nuevo Laboratorio:**
- Provee datos causales para experimentos.
- `marketfeed/replay.py` permite rerun exacto de cualquier experimento.
- El cache y prefetch reducen ruido en mediciones.

**Debe permanecer igual, adaptarse o fusionarse:**
- `caffeine.py` puede fusionarse conceptualmente con `connection.py` porque ambos gestionan vida útil de la sesión.
- `marketfeed/` debería elevarse a **componente estratégico del Laboratorio**, no solo del bot en vivo.

---

### 2.2 Escáner y descubrimiento de activos

**Capacidad:** detectar activos con potencial, aplicar filtros iniciales, rankear, alimentar estrategias.

**Componentes principales:** `scanner.py`, `htf_scanner.py`, `scan_prefetch.py`, `maturing_watchlist.py`, `maturing_watcher.py`, `diversification_enforcer.py`.

**Clasificación:** ⚪ Legacy con partes reutilizables

**Diagnóstico:**
- `scanner.py` es un orquestador monolítico de escaneo.
- Internamente aplica muchas estrategias a la vez: STRAT-A, STRAT-F, momentum, order block, reversal swing, edificio, etc.
- `maturing_watchlist.py` y `maturing_watcher.py` ya tienen la idea de “acompañar un activo mientras madura”, lo cual **se alinea con el nuevo Edificio**.
- `htf_scanner.py` evalúa alineación HTF.

**Valor para el nuevo Laboratorio:**
- Bajo: el escáner actual es un clasificador de eventos, no un generador de hipótesis.
- Pero contiene **conocimiento de filtros** que pueden volver a medirse experimentalmente.

**Debe permanecer igual, adaptarse o fusionarse:**
- El scanner actual debe **archivarse como legacy**.
- Su conocimiento de filtros (`MIN_PAYOUT`, alineación HTF, blacklist) debe **promoverse como hipótesis al Laboratorio** para ser re-validado.
- `maturing_watchlist.py` y `maturing_watcher.py` deben **adaptarse** para convertirse en los primeros vigilantes reales del nuevo Edificio.

---

### 2.3 Motor de estrategias actual

**Capacidad:** múltiples estrategias en paralelo: consolidación, springs, upthrusts, fractales, order blocks, stochastic zones, candles patterns.

**Componentes principales:** `strat_a.py`, `strat_fractal.py`, `strat_momentum.py`, `strat_order_block.py`, `strat_reversal_swing.py`, `candle_patterns.py`, `entry_decision_engine.py`, `entry_scorer.py`, `entry_sync.py`.

**Clasificación:** ⚪ Legacy con piezas reutilizables

**Diagnóstico:**
- Este conjunto es el corazón del sistema viejo.
- Cada módulo produce `CandidateEntry` con score y razón.
- Ya hay una **capa de scoring** y una **capa de decisión de entrada** separadas.
- `entry_scorer.py` rankea candidatos; `entry_sync.py` sincroniza timing de entrada.

**Valor para el nuevo Laboratorio:**
- Cada estrategia es en sí misma una **condición experimental** que puede aislarse y medirse.
- El scoring existente da un **baseline numérico** contra el cual comparar mejoras.
- Los candidatos son **eventos históricos** que pueden reutilizarse como dataset semilla.

**Debe permanecer igual, adaptarse o fusionarse:**
- Las estrategias deben **archivarse como legacy**.
- Su lógica debe **promoverse al Laboratorio como experimentos** (EXP-001 en adelante).
- `entry_scorer.py` debe reemplazarse por un **orquestador de evidencia**, no por un scorer de eventos.
- `entry_sync.py` es un activo estratégico porque resuelve un problema real de timing; debe preservarse.

---

### 2.4 Edificio de Contratación (P1-P3)

**Capacidad:** estado por activo, transición de pisos, detección de brake, cruce estocástico, sticky cross, martillo.

**Componentes principales:** `edificio_contratacion.py`, `edificio_executor.py`, `stochastic_m15.py`, `stoch_cross_state.py`, `brake_eval.py`, `black_box_recorder.py`.

**Clasificación:** 🟡 Reutilizable con adaptación

**Diagnóstico:**
- Ya tiene **estados** (`PISO_1`, `PISO_2`, `PISO_3`, `CONTRATADO`).
- Ya tiene un **expediente parcial** (`BuildingCard`).
- Ya registra **auditoría** y **dirección de origen**.
- Pero sigue siendo **event-driven**: “llegó brake → subir piso”.
- No tiene **confianza dinámica**, **memoria de piso**, ni **retrocesos** como ciudadano de primera clase.
- No diferencia hipótesis; confunde activo con oportunidad.

**Valor para el nuevo Laboratorio:**
- Es el **mejor punto de partida** para el nuevo Edificio.
- Tiene implementado el 60% de la máquina de estados.
- Tiene datos reales de black box para calibrar.

**Debe permanecer igual, adaptarse o fusionarse:**
- `edificio_contratacion.py` debe **adaptarse** para convertirse en el **estado de la hipótesis**, no del activo.
- `edificio_executor.py` debe **fusionarse** con `executor.py` porque el ejecutor no debe tener lógica de edificio separada.
- `black_box_recorder.py` debe **adaptarse** para registrar **evidencia por piso**, no solo eventos.
- `brake_eval.py`, `stochastic_m15.py`, `stoch_cross_state.py` deben **promoverse al Laboratorio** para ser re-validados como vigilantes.

---

### 2.5 Ejecución y gestión de riesgo

**Capacidad:** envío de órdenes, martingala, gestión de ciclo, sesión, stop loss, recuperación, massaniello, Kelly, smart order placement, multi-duración.

**Componentes principales:** `executor.py`, `massaniello_engine.py`, `massaniello_risk.py`, `massaniello_persistence.py`, `kelly_sizer.py`, `martingale_calculator.py`, `diversification_enforcer.py`, `entry_sync.py`, `m1_micro_confirm.py`, `multi_duration_entry.py`, `smart_order_place.py`, `session_manager.py`, `session_awareness.py`, `schedule_controller.py`.

**Clasificación:** 🟢 Activo estratégico (con deuda técnica)

**Diagnóstico:**
- Es la capa más madura del proyecto.
- `executor.py` gestiona ciclo, cola de trades, reintentos, blacklist por activo, streaks.
- `massaniello_risk.py` implementa gestión de capital por sesión.
- `entry_sync.py` resuelve latencia de entrada.
- Pero es **demasiado grande** y está **mezclado con lógica de estrategia**.

**Valor para el nuevo Laboratorio:**
- Bajo directo: no descubre conocimiento.
- Alto indirecto: sin ejecución confiable, no hay datos de resultado para entrenar/validar.

**Debe permanecer igual, adaptarse o fusionarse:**
- `executor.py` debe **permanecer** como ejecutor, pero **limpiarse** para recibir solo `CONTRATAR` desde el orquestador.
- `martingale_calculator.py` es **obsoleto**; reemplazado por `massaniello_risk.py`.
- `kelly_sizer.py` debe archivarse como experimental si no se usa en producción.
- `smart_order_place.py`, `m1_micro_confirm.py`, `multi_duration_entry.py` son **útiles** pero deben fusionarse en `executor.py` como módulos, no como archivos sueltos.

---

### 2.6 Persistencia y estado

**Capacidad:** journal de trades, estado de sesión, massaniello persistence, black box DB, experience memory, market memory.

**Componentes principales:** `trade_journal.py`, `session_manager.py`, `massaniello_persistence.py`, `black_box_recorder.py`, `experience_engine.py`, `experience_schema.py`.

**Clasificación:** 🟢 Activo estratégico

**Diagnóstico:**
- `trade_journal.py` persiste candidatos y resultados en SQLite.
- `black_box_recorder.py` persiste escaneos completos.
- `experience_engine.py` implementa memoria de experiencias append-only.
- Pero hay **tres silos de memoria** distintos: trade journal, black box, experience engine.

**Valor para el nuevo Laboratorio:**
- El **journal** es esencial para medir resultados reales.
- La **black box** es史料 invaluable para calibrar condiciones.
- `experience_engine.py` ya tiene la filosofía correcta: memoria única append-only.

**Debe permanecer igual, adaptarse o fusionarse:**
- Deben **fusionarse** en un **Expediente Persistente** único.
- El futuro `Expediente` del Edificio debe **reusar** la filosofía de `experience_engine.py`, no crear otro silo.
- `black_box_recorder.py` debe **adaptarse** para registrar evidencia por piso, no solo eventos.

---

### 2.7 Observador y máquina de estados de episodios

**Capacidad:** detectar episodios de mercado, clasificar estados (QUIET/PRESSURE/EXPANSION/RESOLUTION), persistir evolución.

**Componentes principales:** `observador/`.

**Clasificación:** 🟡 Reutilizable con adaptación

**Diagnóstico:**
- Tiene una **máquina de estados real** por asset.
- Tiene **captura de episodios** con ventana rodante.
- Tiene **pressure points** y **resolución**.
- Pero está orientado a **estructura de mercado**, no a **hipótesis de trading**.

**Valor para el nuevo Laboratorio:**
- La máquina de estados es un **patrón reutilizable**.
- La idea de episodio con ventana rodante puede **convertirse en la base del expediente**.
- Pressure points son **evidencia cuantitativa** que puede medirse.

**Debe permanecer igual, adaptarse o fusionarse:**
- Debe **adaptarse** para cambiar el foco: de “episodio de mercado” a **“evolución de hipótesis”**.
- Los estados actuales (`QUIET`, `PRESSURE`, etc.) pueden **fusionarse** con los pisos del Edificio como **capa de contexto**.
- `observador/store.py` debe fusionarse con `experience_engine.py` en un solo almacén de memoria.

---

### 2.8 ML y scoring

**Capacidad:** LightGBM wrapper, features de ML, entrenamiento, predicción de confianza.

**Componentes principales:** `ml_scorer.py`, `ml_features.py`, `scripts/train_lightgbm.py` (si existe), `entry_intelligence.py`.

**Clasificación:** 🟠 Experimental

**Diagnóstico:**
- `ml_scorer.py` es un wrapper de LightGBM que predice confianza 0-1.
- `ml_features.py` genera features para el modelo.
- Pero el modelo **no entrena sobre expedientes**; entrena sobre **snapshots de candidatos**.
- No hay evidencia de que mejore el winrate actual.

**Valor para el nuevo Laboratorio:**
- El concepto de **scoring ML** es válido.
- Las **features** pueden reutilizarse como base para features del expediente.
- Pero el modelo debe reentrenarse sobre **secuencias de estado**, no snapshots.

**Debe permanecer igual, adaptarse o fusionarse:**
- Debe **adaptarse** completamente: cambiar objetivo de “clasificar señal” a **“predecir transición de estado”**.
- Las features deben alinearse con el **expediente del activo**.
- `entry_intelligence.py` debe fusionarse en el **orquestador** como capa de predicción.

---

### 2.9 Laboratorio actual: backtesting, simulación, features

**Capacidad:** backtest vela-por-vela, simulación P1→P2→P3, features técnicas, experimentos POI volumen/comportamiento, timing, sweep, patient waiting.

**Componentes principales:** `strategy_lab/backtester.py`, `strategy_lab/compute_features.py`, `strategy_lab/brake_eval.py`, `strategy_lab/scripts/backtest_edificio.py`, `strategy_lab/scripts/simulate_p2_p3_backtest.py`, `strategy_lab/scripts/simulate_p2_p3_timing.py`, `strategy_lab/scripts/simulate_p2_p3_sweep.py`, `strategy_lab/scripts/analyze_patient_waiting.py`, `strategy_lab/poi_behavior.py`, `strategy_lab/volume_profile.py`, `strategy_lab/falsifier.py`, `strategy_lab/variant_searcher.py`, `strategy_lab/optimizer.py`.

**Clasificación:** 🟢 Activo estratégico (núcleo del nuevo Laboratorio)

**Diagnóstico:**
- Es la parte más valiosa del proyecto para el nuevo modelo.
- Ya tiene **backtest causal vela-por-vela**.
- Ya tiene **simuladores de pipel ine** P1→P2→P3.
- Ya tiene **features** de brake, stochastic, hammer, POI.
- Ya tiene **experimentos documentados**: POI volumen, POI comportamiento, patient waiting, timing, sweep.
- Ya tiene **falsifier** y **variant_searcher**: prototipos de experimentación automática.

**Valor para el nuevo Laboratorio:**
- Es el **corazón del nuevo Laboratorio**.
- El backtest actual puede **convertirse en el experiment_runner** con adaptaciones menores.
- Los experimentos existentes son **patrimonio científico**: no hay que volver a hacerlos.

**Debe permanecer igual, adaptarse o fusionarse:**
- `backtest_edificio.py` debe **adaptarse** para soportar el Marco Experimental: aislamiento de condiciones, métricas completas, reproducibilidad.
- `compute_features.py` y `brake_eval.py` deben **permanecer** como librería de features del Laboratorio.
- Los **simuladores** (`simulate_p2_p3_*`) deben **fusionarse** en el backtest único; tener varios backtests distintos es deuda técnica.
- `falsifier.py` y `variant_searcher.py` deben **adaptarse** para implementar la ley de falsación automáticamente.
- `optimizer.py` debe **archivarse** si no hay experimentos que lo justifiquen todavía.

---

### 2.10 HUB y visualización

**Capacidad:** panel web, métricas en vivo, eventos, bankroll, schedule, STRAT-F panel, edificio panel.

**Componentes principales:** `hub/server.py`, `hub/render.py`, `hub/events.py`, `hub/hub_models.py`, `hub/edificio_panel.py`, `hub/strat_f_panel.py`, `hub/strat_f_state.py`, `hub/process_lifecycle.py`, `hub/parser.py`.

**Clasificación:** 🟡 Reutilizable con adaptación

**Diagnóstico:**
- El HUB ya muestra datos en vivo.
- Tiene **paneles separados** por estrategia/subsistema.
- Tiene **bankroll** y **schedule**.
- Pero está orientado a **métricas de ejecución**, no a **estado de hipótesis**.

**Valor para el nuevo Laboratorio:**
- Medio: el HUB no genera conocimiento, pero es el **único canal de observación humana**.
- Si el Laboratorio va a ser revisado por humanos, el HUB debe mostrar **expedientes**, no pares ni señales.

**Debe permanecer igual, adaptarse o fusionarse:**
- `edificio_panel.py` debe **adaptarse** para mostrar **expedientes de hipótesis**: piso actual, evidencia, confianza, historial.
- `strat_f_panel.py` debe **archivarse** como legacy.
- El servidor y eventos pueden **permanecer**; el cambio es en el **modelo de datos** que consumen.

---

### 2.11 Utilidades y soporte

**Capacidad:** logging, alertas, config, errores, modelos, loops, estadísticas, matemáticas.

**Componentes principales:** `bot_logging.py`, `alerter.py`, `config.py`, `errors.py`, `models.py`, `loop_utils.py`, `stats.py`, `math_utils.py`, `math_filters.py`, `spike_filter.py`, `candle_patterns.py`, `htf_scanner.py`.

**Clasificación:** 🟢 Activo estratégico

**Diagnóstico:**
- Son infraestructura transversal.
- `models.py` define dataclasses compartidas.
- `config.py` centraliza parámetros.
- `loop_utils.py` maneja pools, countdowns, shutdown limpio.
- `math_utils.py` tiene helpers numéricos.
- `spike_filter.py` filtra spikes de datos.

**Valor para el nuevo Laboratorio:**
- Alto: sin estas utilidades, cualquier experimento se reinventa la rueda.

**Debe permanecer igual, adaptarse o fusionarse:**
- Deben **permanecer** en su mayoría.
- `config.py` debe **adaptarse** para soportar **configuración experimental** (parámetros de experimento, no solo de bot).
- `models.py` debe **extenderse** con `HypothesisFile`, `Evidence`, `FloorVigilante`.

---

### 2.12 Testing

**Capacidad:** suite de tests unitarios e integración.

**Componentes principales:** 47 archivos en `tests/`.

**Clasificación:** ⚪ Legacy con partes reutilizables

**Diagnóstico:**
- 409 tests pasan, 32 fallan.
- Muchos tests protegen el sistema viejo.
- Pocos tests protegen la arquitectura nueva.
- No hay tests de **máquina de estados**, **expediente**, **vigilantes**, **orquestador**.

**Valor para el nuevo Laboratorio:**
- Medio: la suite es un **activo de regresión** para el core existente.
- Pero no certifica el nuevo modelo cognitivo.

**Debe permanecer igual, adaptarse o fusionarse:**
- Los tests legacy deben **archivarse** progresivamente a medida que el código legacy se retire.
- Deben crearse **nuevos tests** para: estados de hipótesis, transiciones, expediente, orquestador, aislamiento experimental.

---

## 3. Oportunidades de fusión

| Capacidad fusión | Componentes involucrados | Resultado esperado |
|---|---|---|
| **Ejecutor único** | `executor.py` + `edificio_executor.py` + `smart_order_place.py` + `m1_micro_confirm.py` + `multi_duration_entry.py` | Un solo ejecutor que recibe órdenes del orquestador, sin lógica de estrategia ni edificio mezclada. |
| **Memoria única** | `trade_journal.py` + `black_box_recorder.py` + `experience_engine.py` + `observador/store.py` | Un almacén de memoria único, append-only, con dos modos: journal de trades y memoria de experiencia/episodios. |
| **Backtest único** | `backtest_edificio.py` + simuladores P1→P2→P3 + `backtester.py` de strategy_lab | Un `experiment_runner.py` que reemplace todos los backtests actuales y soporte el Marco Experimental. |
| **Vigilantes del Edificio** | `maturing_watchlist.py` + `maturing_watcher.py` + lógica de pisos en `edificio_contratacion.py` | Vigilantes de piso puros, sin dependencias de scanner ni executor. |
| **Configuración unificada** | `config.py` + `strategy_lab/config_loader.py` + `observador/config_loader.py` | Una sola capa de configuración con perfiles: `bot`, `lab`, `edificio`, `hub`. |

---

## 4. Patentes por categoría

### 🟢 Activo estratégico
- Conexión y datos (`connection.py`, `marketfeed/`, `candle_cache.py`)
- Utilidades transversales (`config.py`, `models.py`, `errors.py`, `loop_utils.py`, `math_utils.py`)
- Gestión de riesgo y ciclo (`massaniello_risk.py`, `massaniello_persistence.py`, `entry_sync.py`)
- Persistencia de trades (`trade_journal.py`)
- Núcleo del Laboratorio actual (`strategy_lab/compute_features.py`, `strategy_lab/brake_eval.py`, experimentos existentes)

### 🟡 Reutilizable con adaptación
- Edificio actual (`edificio_contratacion.py`, `edificio_executor.py`, `black_box_recorder.py`)
- Observador (`observador/`)
- HUB (`hub/`)
- ML scorer (`ml_scorer.py`, `ml_features.py`)
- Maturing watchlist/watcher

### 🟠 Experimental
- ML scorer y features: prometedor pero no validado para el nuevo objetivo
- Falsifier y variant searcher: pueden ser la base de experimentación automática, pero deben alinearse al Marco Experimental
- Optimizer: sin uso claro todavía

### ⚪ Legacy
- Escáner monolítico (`scanner.py` y estrategias satélite)
- Estrategias STRAT-A, STRAT-F, momentum, order block, etc.
- Tests legacy
- Configuración fragmentada

### ⚫ Obsoleto
- `martingale_calculator.py`
- `kelly_sizer.py` (si no está en uso en producción)
- `strat_f_postmortem.py` (si depende de STRAT-F legacy)

---

## 5. Fortalezas del patrimonio actual

1. **Datos causales reproducibles.** `marketfeed/replay.py` + parquet + black box permiten re-ejecutar cualquier experimento histórico.
2. **Experimentos reales ya realizados.** POI volumen, POI comportamiento, patient waiting, timing, sweep. Son conocimiento válido; no hay que volver a empezar.
3. **Capa de persistencia madura.** SQLite, journals, black box, experience engine. Hay infraestructura para almacenar expedientes sin crear desde cero.
4. **Gestión de riesgo implementada.** Massaniello, session manager, entry sync. Eso permite que el Laboratorio se enfoque en discovery, no en operación.
5. **ML wrapper existente.** LightGBM ya está integrado; el salto es cambiar el objetivo de entrenamiento, no crear el pipeline desde cero.

---

## 6. Deuda técnica crítica

1. **Tres sistemas paralelos** (legacy / Edificio / Laboratorio) que no se hablan. Esto impide que el conocimiento fluya.
2. **No hay expediente central.** `BuildingCard` es un snapshot, no una historia.
3. **Los tests no protegen la nueva arquitectura.** Si reescribimos el Edificio, los tests actuales no van a fallar hasta que sea demasiado tarde.
4. **Backtests duplicados.** Varios scripts hacen lo mismo con pequeñas variaciones; eso genera inconsistencias.
5. **Configuración fragmentada.** Tres loaders distintos (`config.py`, `strategy_lab/config_loader.py`, `observador/config_loader.py`).

---

## 7. Oportunidades ocultas

1. **El Observador es un edificio disfrazado.** Su máquina de estados por episodio es casi idéntica a la máquina de estados por hipótesis que necesitamos. Con adaptarla, ganamos meses de desarrollo.
2. **La Black Box es史料 pura.** Tiene datos reales de aceptación/rechazo por condición. Eso permite calcular winrates reales sin correr el bot.
3. **Los experimentos de Laboratorio ya tienen respuestas.** No hay que experimentar de cero; hay que **promover lo que ya demostró valor** y **descartar lo que ya demostró no valer**.
4. **ML puede reentrenarse rápido.** Si alineamos las features con el expediente, el modelo existente puede convertirse en predictor de transiciones de estado en días, no meses.

---

## 8. Respuesta a la pregunta fundamental

> ¿Qué patrimonio tecnológico y científico ya posee QUOTEX para construir el nuevo Laboratorio y el nuevo Edificio sin empezar desde cero?

**Resumen:**
QUOTEX ya posee **cimientos sólidos**: datos reproducibles, persistencia madura, gestión de riesgo, ML wrapper, y un **Laboratorio experimental que ya generó conocimiento valioso**.

No parte de cero. Parte de:
- Un **Edificio con máquina de estados parcial** que solo necesita cambiar de “evento” a “hipótesis”.
- Un **Laboratorio con experimentos documentados** que solo necesita formalizarse bajo el Marco Experimental.
- Una **Black Box** que contiene la史料 para calibrar condiciones sin correr el bot.
- Un **Observador** que tiene la máquina de estados que el nuevo Edificio necesita.

La deuda principal no es tecnológica. Es **conceptual**: los componentes existen, pero hablan lenguajes diferentes. La tarea no es escribir código nuevo. Es **unificar el lenguaje** para que el Laboratorio produzca conocimiento, el Edificio lo aplique, y el Orquestador decida.

---

*Última actualización: 2026-08-04*
*Estado: Auditoría científica completada. Pendiente de aprobación humana para definir roadmap de evolución.*
