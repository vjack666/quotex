# Auditoría Científica de QUOTEX — Reporte Formal

**Proyecto:** QUOTEX — Edificio de Contratación + Laboratorio Experimental  
**Documento base:** `docs/AUDITORIA_CIENTIFICA_QUOTEX.md`  
**Tipo:** Auditoría de patrimonio tecnológico y científico  
**Alcance:** motor en vivo, Laboratorio, Edificio, documentación, HUB, IA, utilidades y tests  
**Fecha:** 2026-08-04  
**Estado:** Completada. Pendiente de aprobación humana.  
**Auditor:** Hermes Agent (modo científico, sin propuestas de código ni refactor)

---

## Resumen ejecutivo

QUOTEX no parte de cero.

Posee:
- **Datos reproducibles** y una **black box con史料 real** de aceptación/rechazo.
- **Experimentación ya realizada** con resultados documentados.
- **Máquina de estados** casi lista para adaptar a hipótesis.
- **Persistencia madura** y **gestión de riesgo funcionando**.
- **ML wrapper** integrado.
- **Herramientas de falsación y minería** prototipadas.

La deuda principal no es tecnológica. Es **conceptual**: los componentes existen, pero hablan lenguajes diferentes. La tarea no es inventar, sino **unificar, formalizar y promover** lo que ya existe bajo el Marco Experimental.

---

## Metodología

Se analizó todo el repositorio desde la perspectiva del **Marco Experimental Fundacional** (`docs/LAB_MARCO_EXPERIMENTAL.md`).

Para cada capacidad se evaluó:
- ¿Qué conocimiento aporta?
- ¿Qué problema resuelve actualmente?
- ¿Ese conocimiento sigue siendo válido con el nuevo Marco Experimental?
- ¿Debe permanecer igual / adaptarse / fusionarse / archivarse / eliminarse?
- ¿Qué valor aporta al nuevo Laboratorio?
- **Activos ocultos:** ¿este conocimiento puede reutilizarse para algo distinto a su función original?

**Regla de oro:** durante esta auditoría está prohibido proponer refactorizaciones, mover carpetas, escribir código o eliminar módulos. La única misión es identificar conocimiento existente.

---

## Mapa de capacidades

### 1. Datos de mercado reproducibles

**Componentes:** `connection.py`, `caffeine.py`, `candle_cache.py`, `parallel_fetch.py`, `marketfeed/`

**Clasificación:** 🟢 Activo estratégico

**Conocimiento aportado:**
- Flujo de datos causal desde el broker hasta el almacenamiento local.
- Estrategias de reconexión, heartbeats y backpressure.
- Capacidad de grabar y reproducir sesiones de mercado sin modificar código de análisis.

**Diagnóstico:** Es el cimiento de todo. Sin datos causales, el Laboratorio no existe.

**Valor para el nuevo Laboratorio:** Provee datos causales para experimentos. `marketfeed/replay.py` permite reproducibilidad offline.

**Activos ocultos:**
- `marketfeed/replay.py` es un generador de experimentos controlados.
- `caffeine.py` contiene conocimiento sobre vida útil de sesiones WebSocket.

---

### 2. Backtest causal vela-por-vela

**Componentes:** `strategy_lab/backtester.py`, `strategy_lab/scripts/backtest_edificio.py`, simuladores `simulate_p2_p3_*`

**Clasificación:** 🟢 Activo estratégico (núcleo del Laboratorio)

**Conocimiento aportado:**
- Pipeline causal de expedientes viviendo en pisos, sin look-ahead.
- Generación de dataset features + label para ML.
- Medición de winrate baseline por par y condición.

**Diagnóstico:** Es la herramienta científica principal del Laboratorio, pero está hardcodeada a una estrategia completa.

**Valor para el nuevo Laboratorio:** Es el núcleo operativo. Debe convertirse en el motor que ejecute `EXP-NNN` con aislamiento, métricas completas y reproducibilidad.

**Activos ocultos:**
- `backtest_edificio.py` tiene lógica de separación K/D, sticky cross, martillo y body_n. Es conocimiento experimental sobre condiciones individuales.
- Los parámetros hardcodeados (`R`, `MAX_LOOKAHEAD`, `MIN_CROSS_SEPARATION`) son hipótesis implícitas que deben volver a medirse formalmente.

---

### 3. Features técnicas validadas

**Componentes:** `strategy_lab/compute_features.py`, `strategy_lab/brake_eval.py`, `strategy_lab/stochastic_m15.py`, `strategy_lab/stoch_cross_state.py`

**Clasificación:** 🟢 Activo estratégico

**Conocimiento aportado:**
- Cálculo causal de features del expediente: body_n, brake_ratio, kd_dist, separación, cruce, sticky, martillo.
- Algoritmos de detección de brake, swing, POI.

**Diagnóstico:** Son las mediciones básicas del sistema. Sin ellas no se puede formular ninguna hipótesis medible.

**Valor para el nuevo Laboratorio:** Es el vocabulario de medición.

**Activos ocultos:**
- `compute_features.py` tiene lógica de `align_htf` que resuelve timezone mismatch entre timeframes. Puede reutilizarse para experimentos multi-timeframe.
- `stoch_cross_state.py` tiene estados de separación que pueden convertirse en features de “paciencia” para ML.

---

### 4. Experimentos de Laboratorio con resultados

**Componentes:** scripts y resultados de POI volumen, POI comportamiento, patient waiting, timing, sweep.

**Clasificación:** 🟢 Activo estratégico (patrimonio científico)

**Conocimiento aportado:**
- Evidencia experimental documentada sobre POI volumen/comportamiento, timing de brake→cruce, sweep de parámetros, patient waiting.
- Documentación de experimentos fallidos y exitosos.

**Diagnóstico:** Son datos científicos del proyecto. No hay que volver a experimentar sobre estas condiciones desde cero.

**Valor para el nuevo Laboratorio:** Es el patrimonio científico ya generado.

**Activos ocultos:**
- `analyze_patient_waiting.py` tiene lógica de trayectoria de separación K/D post-cruce que puede reutilizarse como feature de “índice de paciencia”.
- `simulate_p2_p3_sweep.py` tiene un barrido de parámetros que puede convertirse en protocolo de falsación automática.

---

### 5. Máquina de estados de episodios

**Componentes:** `observador/state_machine.py`, `observador/observer.py`, `observador/pressure.py`, `observador/evolution.py`, `observador/store.py`, `observador/summary.py`

**Clasificación:** 🟡 Reutilizable con adaptación

**Conocimiento aportado:**
- Máquina de estados real por activo: QUIET → PRESSURE → EXPANSION → RESOLUTION.
- Ventana rodante de contexto.
- Pressure points y resolución de episodios.

**Diagnóstico:** Tiene la máquina de estados que el nuevo Edificio necesita, pero orientada a “episodio de mercado”, no a “evolución de hipótesis”.

**Valor para el nuevo Laboratorio:** Es la plantilla de implementación del Edificio.

**Activos ocultos:**
- `pressure_point` es una medida cuantitativa de convicción del mercado útil para experimentos de robustez.
- `ROLLING_WINDOW` puede convertirse en la ventana de evidencia acumulada del expediente.

---

### 6. Persistencia y memoria append-only

**Componentes:** `experience_engine.py`, `experience_schema.py`, `trade_journal.py`, `black_box_recorder.py`

**Clasificación:** 🟢 Activo estratégico

**Conocimiento aportado:**
- Memoria única de experiencias append-only.
- Journal de trades con resultados reales.
- Black box con escaneos completos, aceptaciones, rechazos, snapshots de velas.

**Diagnóstico:** Hay tres silos separados que deberían ser uno solo.

**Valor para el nuevo Laboratorio:** Es la memoria histórica sin la cual no se puede medir nada.

**Activos ocultos:**
- `black_box_recorder.py` tiene snapshots de velas en momentos de decisión → material para experimentos de causalidad.
- `experience_schema.py` puede extenderse para convertirse en el esquema del expediente de hipótesis.

---

### 7. ML scorer existente

**Componentes:** `ml_scorer.py`, `ml_features.py`, `entry_intelligence.py`, `scripts/train_lightgbm.py`

**Clasificación:** 🟠 Experimental

**Conocimiento aportado:**
- Wrapper de LightGBM para predecir confianza 0-1.
- Pipeline de features y entrenamiento.

**Diagnóstico:** Hoy predice sobre snapshots de eventos, no sobre expedientes. No hay evidencia de que mejore el winrate actual.

**Valor para el nuevo Laboratorio:** Es la base de ML ya integrada. El salto es cambiar el objetivo de entrenamiento, no crear el pipeline desde cero.

**Activos ocultos:**
- `ml_features.py` tiene transformaciones que pueden reutilizarse para calcular tendencias de evidencia en el expediente.
- El concepto de confianza 0-1 puede reutilizarse como confianza dinámica de la hipótesis.

---

### 8. Gestión de riesgo y sesiones

**Componentes:** `massaniello_risk.py`, `massaniello_engine.py`, `massaniello_persistence.py`, `session_manager.py`, `entry_sync.py`, `diversification_enforcer.py`

**Clasificación:** 🟢 Activo estratégico (con deuda técnica)

**Conocimiento aportado:**
- Gestión de capital por sesión, límites de ops, recuperación, stop de sesión, sincronización de entrada, diversificación por activo.

**Diagnóstico:** Es la capa más madura del proyecto. Sin ella no hay experimentación en vivo posible.

**Valor para el nuevo Laboratorio:** Es el marco de seguridad que permite experimentar sin riesgo real.

**Activos ocultos:**
- `massaniello_persistence.py` tiene conocimiento sobre estado de sesión durable → puede persistir el estado del Laboratorio.
- `entry_sync.py` resuelve timing de entrada → afecta también a los experimentos.

---

### 9. Filtros y condiciones legacy

**Componentes:** `strat_a.py`, `strat_fractal.py`, `strat_momentum.py`, `strat_order_block.py`, `strat_reversal_swing.py`, `candle_patterns.py`, `entry_scorer.py`, `entry_decision_engine.py`

**Clasificación:** ⚪ Legacy con piezas reutilizables

**Conocimiento aportado:**
- Reglas de consolidación, springs, fractales, momentum, order blocks, patrones de vela.
- Scoring de candidatos, alineación HTF, blacklist de patrones.

**Diagnóstico:** Cada estrategia es una condición experimental que puede aislarse y medirse. El scoring da un baseline numérico.

**Valor para el nuevo Laboratorio:** Es el inventario de condiciones que deben volver a medirse formalmente.

**Activos ocultos:**
- `strat_a.py` tiene dynamic range y consolidación → criterios de permanencia del Administrador del Edificio.
- `candle_patterns.py` tiene clasificación de velas → validación de vela confirmatoria sin hardcodear “martillo”.
- `entry_decision_engine.py` tiene alineación HTF → hipótesis experimental en sí misma.

---

### 10. HUB y visualización

**Componentes:** `hub/server.py`, `hub/render.py`, `hub/events.py`, `hub/edificio_panel.py`, `hub/strat_f_panel.py`

**Clasificación:** 🟡 Reutilizable con adaptación

**Conocimiento aportado:**
- Visualización en vivo de métricas, eventos, bankroll, estado de procesos.
- Paneles diferenciados por estrategia.

**Diagnóstico:** Debe cambiar su modelo de datos: de “pares/estrategias” a “expedientes/hipótesis”.

**Valor para el nuevo Laboratorio:** Es el canal de observación humana.

**Activos ocultos:**
- `hub/events.py` define un modelo de eventos que puede reutilizarse para eventos del expediente.
- `hub/render.py` tiene agregación y filtrado → priorizar expedientes por `priority_score`.

---

### 11. Utilidades y soporte

**Componentes:** `config.py`, `models.py`, `errors.py`, `loop_utils.py`, `math_utils.py`, `math_filters.py`, `spike_filter.py`, `alerter.py`, `bot_logging.py`

**Clasificación:** 🟢 Activo estratégico

**Conocimiento aportado:**
- Infraestructura transversal: configuración, modelos de datos, errores, loops, matemáticas, logging, alertas.

**Diagnóstico:** Sin estas utilidades, cualquier experimento se reinventa la rueda.

**Valor para el nuevo Laboratorio:** Es la base sobre la cual se construye todo.

**Activos ocultos:**
- `math_filters.py` tiene filtros numéricos → limpiar señales de evidencia en el expediente.
- `spike_filter.py` tiene conocimiento sobre outliers → crítico para experimentos de robustez.

---

### 12. Testing como baseline de regresión

**Componentes:** 47 archivos en `tests/`, 409 tests pasando, 32 fallando.

**Clasificación:** ⚪ Legacy con partes reutilizables

**Conocimiento aportado:**
- Comportamiento esperado del sistema legacy.
- Casos edge documentados.

**Diagnóstico:** Protege el sistema viejo, no el nuevo modelo cognitivo.

**Valor para el nuevo Laboratorio:** Es el colchón de seguridad para no romper el core mientras se implementa la nueva arquitectura.

**Activos ocultos:**
- Tests de black box/scanner contienen casos reales de aceptación/rechazo → dataset de validación para experimentos.

---

### 13. Herramientas de descubrimiento y minería

**Componentes:** `strategy_lab/falsifier.py`, `strategy_lab/variant_searcher.py`, `strategy_lab/optimizer.py`, `strategy_lab/law_engine.py`, `strategy_lab/laws_freno.py`, `strategy_lab/minar_leyes_freno.py`

**Clasificación:** 🟠 Experimental

**Conocimiento aportado:**
- Búsqueda de variantes, minería de leyes, optimización, falsación.

**Diagnóstico:** Son prototipos de experimentación automática. Ya hay código que busca, mide y evalúa; solo necesita formalizarse.

**Valor para el nuevo Laboratorio:** Es el inicio de la automatización científica.

**Activos ocultos:**
- `falsifier.py` ya implementa la ley de falsación del Marco Experimental.
- `minar_leyes_freno.py` y `laws_freno.py` contienen leyes minadas listas para promover.

---

## Oportunidades de fusión

| Capacidad fusión | Componentes involucrados | Resultado esperado |
|---|---|---|
| **Ejecutor único** | `executor.py` + `edificio_executor.py` + `smart_order_place.py` + `m1_micro_confirm.py` + `multi_duration_entry.py` | Un solo ejecutor que recibe órdenes del orquestador, sin lógica de estrategia ni edificio mezclada. |
| **Memoria única** | `trade_journal.py` + `black_box_recorder.py` + `experience_engine.py` + `observador/store.py` | Un almacén de memoria único, append-only, con dos modos: journal de trades y memoria de experiencia/episodios. |
| **Backtest único** | `backtest_edificio.py` + simuladores P1→P2→P3 + `backtester.py` de strategy_lab | Un `experiment_runner.py` que reemplace todos los backtests actuales y soporte el Marco Experimental. |
| **Vigilantes del Edificio** | `maturing_watchlist.py` + `maturing_watcher.py` + lógica de pisos en `edificio_contratacion.py` | Vigilantes de piso puros, sin dependencias de scanner ni executor. |
| **Configuración unificada** | `config.py` + `strategy_lab/config_loader.py` + `observador/config_loader.py` | Una sola capa de configuración con perfiles: `bot`, `lab`, `edificio`, `hub`. |

---

## Clasificación por categorías

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
- Falsifier y variant searcher: pueden ser la base de experimentación automática
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

## Fortalezas del patrimonio actual

1. **Datos causales reproducibles.** `marketfeed/replay.py` + parquet + black box permiten re-ejecutar cualquier experimento histórico.
2. **Experimentos reales ya realizados.** POI volumen/comportamiento, patient waiting, timing, sweep. Son conocimiento válido; no hay que volver a empezar.
3. **Capa de persistencia madura.** SQLite, journals, black box, experience engine. Hay infraestructura para almacenar expedientes sin crear desde cero.
4. **Gestión de riesgo implementada.** Massaniello, session manager, entry sync. Eso permite que el Laboratorio se enfoque en discovery, no en operación.
5. **ML wrapper existente.** LightGBM ya está integrado; el salto es cambiar el objetivo de entrenamiento, no crear el pipeline desde cero.

---

## Deuda técnica crítica

1. **Tres sistemas paralelos** (legacy / Edificio / Laboratorio) que no se hablan. Esto impide que el conocimiento fluya.
2. **No hay expediente central.** `BuildingCard` es un snapshot, no una historia.
3. **Los tests no protegen la nueva arquitectura.** Si reescribimos el Edificio, los tests actuales no van a fallar hasta que sea demasiado tarde.
4. **Backtests duplicados.** Varios scripts hacen lo mismo con pequeñas variaciones; eso genera inconsistencias.
5. **Configuración fragmentada.** Tres loaders distintos (`config.py`, `strategy_lab/config_loader.py`, `observador/config_loader.py`).

---

## Oportunidades ocultas

1. **El Observador es un edificio disfrazado.** Su máquina de estados por episodio es casi idéntica a la máquina de estados por hipótesis que necesitamos. Con adaptarla, ganamos meses de desarrollo.
2. **La Black Box es史料 pura.** Tiene datos reales de aceptación/rechazo por condición. Eso permite calcular winrates reales sin correr el bot.
3. **Los experimentos de Laboratorio ya tienen respuestas.** No hay que experimentar de cero; hay que **promover lo que ya demostró valor** y **descartar lo que ya demostró no valer**.
4. **ML puede reentrenarse rápido.** Si alineamos las features con el expediente, el modelo existente puede convertirse en predictor de transiciones de estado en días, no meses.

---

## Respuesta a la pregunta fundamental

> ¿Qué patrimonio tecnológico y científico ya posee QUOTEX para construir el nuevo Laboratorio y el nuevo Edificio sin empezar desde cero?

QUOTEX ya posee **cimientos sólidos**: datos reproducibles, persistencia madura, gestión de riesgo, ML wrapper, y un **Laboratorio experimental que ya generó conocimiento valioso**.

No parte de cero. Parte de:
- Un **Edificio con máquina de estados parcial** que solo necesita cambiar de “evento” a “hipótesis”.
- Un **Laboratorio con experimentos documentados** que solo necesita formalizarse bajo el Marco Experimental.
- Una **Black Box** que contiene la史料 para calibrar condiciones sin correr el bot.
- Un **Observador** que tiene la máquina de estados que el nuevo Edificio necesita.

La deuda principal no es tecnológica. Es **conceptual**: los componentes existen, pero hablan lenguajes diferentes. La tarea no es escribir código nuevo. Es **unificar el lenguaje** para que el Laboratorio produzca conocimiento, el Edificio lo aplique, y el Orquestador decida.

---

## Aprobación humana

- [ ] Aprobado para definir roadmap de evolución
- [ ] Aprobado con observaciones
- [ ] Rechazado; requiere revisión

**Observaciones:**

---

*Documento generado por Hermes Agent*  
*Última actualización: 2026-08-04*  
*Estado: Completado. Pendiente de aprobación humana.*
