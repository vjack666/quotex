# Primera Auditoría Científica del Laboratorio — Mapa de Capacidades

> **Objetivo:** descubrir qué patrimonio científico ya posee QUOTEX para construir el nuevo Laboratorio y el nuevo Edificio sin empezar desde cero.
>
> **Regla de oro:** durante esta auditoría está prohibido proponer refactorizaciones, mover carpetas, escribir código o eliminar módulos. La única misión es identificar conocimiento existente.

---

## Metodología

Para cada capacidad identificada se responde:

- ¿Qué conocimiento aporta?
- ¿Qué problema resuelve actualmente?
- ¿Ese conocimiento sigue siendo válido con el nuevo Marco Experimental?
- ¿Debe permanecer igual?
- ¿Debe adaptarse?
- ¿Debe fusionarse con otro módulo?
- ¿Debe archivarse?
- ¿Debe eliminarse?
- ¿Qué valor aporta al nuevo Laboratorio?
- **Activos ocultos:** ¿este conocimiento puede reutilizarse para algo distinto a su función original?

---

## 1. Datos de mercado reproducibles

**Componentes:** `connection.py`, `caffeine.py`, `candle_cache.py`, `parallel_fetch.py`, `marketfeed/`

### ¿Qué conocimiento aporta?
- Flujo de datos causal desde el broker hasta el almacenamiento local.
- Estrategias de reconexión, heartbeats y backpressure.
- Capacidad de grabar y reproducir sesiones de mercado sin modificar código de análisis.

### ¿Qué problema resuelve actualmente?
- Conectividad con Quotex, descarga paralela de velas, cache anti-duplicados, reproducción offline.

### ¿Sigue siendo válido?
Sí. El nuevo Laboratorio requiere datos causales reproducibles como condición de existencia. Sin esta capacidad, ningún experimento es reproducible.

### ¿Debe permanecer igual?
Sí. Es infraestructura de adquisición.

### ¿Debe adaptarse?
Solo para exponer interfaces estables al Laboratorio, no cambiar su funcionamiento interno.

### ¿Debe fusionarse?
No.

### ¿Debe archivarse?
No.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es el **cimiento**. Todo experimento depende de esta capacidad.

### Activos ocultos
- `marketfeed/replay.py` no es solo una herramienta de debugging. Es un **generador de experimentos controlados**: permite rerun exacto de cualquier hipótesis histórica con los mismos datos.
- `caffeine.py` no es solo un watchdog. Es **conocimiento sobre vida útil de sesiones WebSocket**, útil para diseñar experimentos de sesiones.

---

## 2. Backtest causal vela-por-vela

**Componentes:** `strategy_lab/backtester.py`, `strategy_lab/scripts/backtest_edificio.py`, simuladores `simulate_p2_p3_*`

### ¿Qué conocimiento aporta?
- Pipeline causal de expedientes viviendo en pisos, sin look-ahead.
- Generación de dataset features + label para ML.
- Medición de winrate baseline por par y condición.

### ¿Qué problema resuelve actualmente?
- Permite medir el Edificio offline sobre datos históricos sin tocar el bot en vivo.

### ¿Sigue siendo válido?
Sí. Es la **herramienta científica principal** del Laboratorio.

### ¿Debe permanecer igual?
No. Hoy está hardcodeado a una estrategia completa; el Marco Experimental requiere aislar condiciones.

### ¿Debe adaptarse?
Sí. Debe convertirse en el motor que ejecute `EXP-NNN` con aislamiento, métricas completas y reproducibilidad.

### ¿Debe fusionarse?
Sí. Los tres backtests/simuladores deben fusionarse en una sola capacidad: **ejecutor de experimentos**.

### ¿Debe archivarse?
Los scripts actuales pueden archivarse como versión histórica una vez que el nuevo ejecutor esté funcionando.

### ¿Debe eliminarse?
No. El conocimiento contenido en ellos es demasiado valioso.

### ¿Qué valor aporta al nuevo Laboratorio?
Es el **núcleo operativo**. Sin esta capacidad, el Laboratorio no puede funcionar.

### Activos ocultos
- `backtest_edificio.py` ya tiene **lógica de separación K/D, sticky cross, martillo y body_n**. Eso no es solo código de backtest; es **conocimiento experimental sobre condiciones individuales** que puede reempaquetarse como experimentos aislados.
- Los parámetros hardcodeados (`R`, `MAX_LOOKAHEAD`, `MIN_CROSS_SEPARATION`) son en realidad **hipótesis implícitas** que deben volver a medirse formalmente.

---

## 3. Features técnicas validadas

**Componentes:** `strategy_lab/compute_features.py`, `strategy_lab/brake_eval.py`, `strategy_lab/stochastic_m15.py`, `strategy_lab/stoch_cross_state.py`

### ¿Qué conocimiento aporta?
- Cálculo causal de features del expediente: body_n, brake_ratio, kd_dist, separación, cruce, sticky, martillo.
- Algoritmos de detección de brake, swing, POI.

### ¿Qué problema resuelve actualmente?
- Provee las métricas que el Edificio y el Laboratorio usan para evaluar hipótesis.

### ¿Sigue siendo válido?
Sí. Son las **mediciones básicas** del sistema.

### ¿Debe permanecer igual?
Sí, como librería de features.

### ¿Debe adaptarse?
Solo para exponer una API clara al futuro `experiment_runner.py`.

### ¿Debe fusionarse?
No.

### ¿Debe archivarse?
No.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es el **vocabulario de medición**. Sin estas features, no se puede formular ninguna hipótesis del Edificio.

### Activos ocultos
- `compute_features.py` tiene lógica de `align_htf` que resuelve un problema de **timezone mismatch** entre timeframes. Ese conocimiento puede reutilizarse para **experimentos multi-timeframe** no solo del Edificio, sino de cualquier condición HTF.
- `stoch_cross_state.py` no solo calcula cruces; tiene **estados de separación** que pueden convertirse en features de “paciencia” para ML.

---

## 4. Experimentos de Laboratorio con resultados

**Componentes:** `strategy_lab/scripts/run_poi_vol_sensitivity.py`, `strategy_lab/scripts/run_local_volume_sensor.py`, `strategy_lab/scripts/run_volume_profile_experiment.py`, `strategy_lab/scripts/run_poi_behavior_experiment.py`, `strategy_lab/scripts/analyze_patient_waiting.py`, `strategy_lab/scripts/simulate_p2_p3_timing.py`, `strategy_lab/scripts/simulate_p2_p3_sweep.py`, `strategy_lab/scripts/simulate_p2_promotion.py`, resultados CSV/MD asociados.

### ¿Qué conocimiento aporta?
- Evidencia experimental sobre POI volumen, POI comportamiento, timing de brake→cruce, sweep de parámetros, patient waiting.
- Documentación de experimentos fallidos y exitosos.

### ¿Qué problema resuelve actualmente?
- Permite tomar decisiones informadas sobre qué condiciones promover al Edificio.

### ¿Sigue siendo válido?
Sí. Son **datos científicos** del proyecto.

### ¿Debe permanecer igual?
No. Hoy están como scripts sueltos sin estructura de experimento formal.

### ¿Debe adaptarse?
Sí. Cada experimento debe reestructurarse como `EXP-NNN` siguiendo el Marco Experimental.

### ¿Debe fusionarse?
Sí. Todos los scripts deben fusionarse en una sola herramienta: **experiment runner**.

### ¿Debe archivarse?
Los scripts actuales pueden archivarse como **versión histórica** una vez promovidos a `EXP-NNN`.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es el **patrimonio científico ya generado**. No hay que volver a experimentar sobre POI volumen/comportamiento; ya hay respuestas.

### Activos ocultos
- `analyze_patient_waiting.py` no solo mide tiempos de espera. Tiene lógica de **trayectoria de separación K/D post-cruce** que puede reutilizarse para crear una feature de **“índice de paciencia”** en el expediente.
- `simulate_p2_p3_sweep.py` tiene un barrido de parámetros que puede convertirse en un **protocolo de falsación automática** para nuevas hipótesis.
- `poi_behavior.py` y `volume_profile.py` tienen código de detección de estructuras que puede reutilizarse para **experimentos geométricos** más allá del Edificio.

---

## 5. Máquina de estados de episodios

**Componentes:** `observador/state_machine.py`, `observador/observer.py`, `observador/pressure.py`, `observador/evolution.py`, `observador/store.py`, `observador/summary.py`

### ¿Qué conocimiento aporta?
- Máquina de estados real por activo: QUIET → PRESSURE → EXPANSION → RESOLUTION.
- Ventana rodante de contexto.
- Pressure points y resolución de episodios.

### ¿Qué problema resuelve actualmente?
- Clasifica el comportamiento de mercado en episodios con estado.

### ¿Sigue siendo válido?
Sí, pero **mal aplicado**. El conocimiento es correcto; el problema es que está orientado a “episodio de mercado”, no a “evolución de hipótesis”.

### ¿Debe permanecer igual?
No. Debe cambiar de dominio: de estructura de mercado a madurez de hipótesis.

### ¿Debe adaptarse?
Sí. Es el **patrón de implementación** para el nuevo Edificio.

### ¿Debe fusionarse?
Sí. Con `experience_engine.py` y el futuro expediente, debe convertirse en el **motor de estados de hipótesis**.

### ¿Debe archivarse?
Solo si se reemplaza completamente por la nueva máquina de estados de hipótesis. El conocimiento original debe preservarse.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es la **plantilla de implementación** del Edificio. Ya resuelve el problema de estados, ventanas y transiciones.

### Activos ocultos
- `pressure_point` no es solo un detector de presión. Es una **medida cuantitativa de convicción del mercado** que puede usarse como feature en experimentos de robustez.
- La **ventana rodante** (`ROLLING_WINDOW`) puede convertirse en la **ventana de evidencia acumulada** del expediente.

---

## 6. Persistencia y memoria append-only

**Componentes:** `experience_engine.py`, `experience_schema.py`, `trade_journal.py`, `black_box_recorder.py`

### ¿Qué conocimiento aporta?
- Memoria única de experiencias append-only.
- Journal de trades con resultados reales.
- Black box con escaneos completos, aceptaciones, rechazos, snapshots de velas.

### ¿Qué problema resuelve actualmente?
- Almacena historial para análisis posterior y entrenamiento de ML.

### ¿Sigue siendo válido?
Sí. La filosofía de memoria única es correcta.

### ¿Debe permanecer igual?
No. Hoy hay **tres silos** separados que deberían ser uno solo.

### ¿Debe adaptarse?
Sí. Deben fusionarse en un **Expediente Persistente** que almacene: historial de pisos, evidencia, decisiones, resultados.

### ¿Debe fusionarse?
Sí. `trade_journal` + `black_box` + `experience_engine` deben ser una sola capacidad.

### ¿Debe archivarse?
No.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es la **memoria histórica** sin la cual el Laboratorio no puede medir nada.

### Activos ocultos
- `black_box_recorder.py` tiene **snapshots de velas** en el momento de aceptación/rechazo. Eso no es solo logging; es **material para experimentos de causalidad** porque permite reconstruir el estado exacto del mercado en cada decisión.
- `experience_schema.py` define un esquema de experiencia que puede **extenderse** para convertirse en el esquema del expediente de hipótesis.

---

## 7. ML scorer existente

**Componentes:** `ml_scorer.py`, `ml_features.py`, `entry_intelligence.py`, `scripts/train_lightgbm.py`

### ¿Qué conocimiento aporta?
- Wrapper de LightGBM para predecir confianza 0-1.
- Pipeline de features y entrenamiento.

### ¿Qué problema resuelve actualmente?
- Asigna score a candidatos de entrada.

### ¿Sigue siendo válido?
Sí, pero **mal aplicado**. Hoy predice sobre snapshots de eventos, no sobre expedientes.

### ¿Debe permanecer igual?
No.

### ¿Debe adaptarse?
Sí. Debe cambiar de objetivo: de “clasificar señal” a **“predecir transición de estado / confianza de hipótesis”**.

### ¿Debe fusionarse?
Sí. Debe integrarse en el orquestador como capa de predicción sobre el expediente.

### ¿Debe archivarse?
El modelo actual puede archivarse como baseline histórico.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es la **base de ML** ya integrada. No hay que construir desde cero.

### Activos ocultos
- `ml_features.py` tiene **transformaciones de features** que pueden reutilizarse para calcular **tendencias de evidencia** en el expediente.
- El concepto de **confianza 0-1** puede reutilizarse como la **confianza dinámica de la hipótesis** del documento fundacional.

---

## 8. Gestión de riesgo y sesiones

**Componentes:** `massaniello_risk.py`, `massaniello_engine.py`, `massaniello_persistence.py`, `session_manager.py`, `entry_sync.py`, `diversification_enforcer.py`

### ¿Qué conocimiento aporta?
- Gestión de capital por sesión, límites de ops, recuperación, stop de sesión, sincronización de entrada, diversificación por activo.

### ¿Qué problema resuelve actualmente?
- Protege el capital y administra el ciclo de trading.

### ¿Sigue siendo válido?
Sí. El Laboratorio no reemplaza la gestión de riesgo; la complementa.

### ¿Debe permanecer igual?
Sí.

### ¿Debe adaptarse?
Solo para consumir `CONTRATAR` del orquestador, no eventos sueltos.

### ¿Debe fusionarse?
No.

### ¿Debe archivarse?
No.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es el **marco de seguridad** que permite experimentar sin riesgo real. Sin él, el Laboratorio no podría medir nada en vivo.

### Activos ocultos
- `massaniello_persistence.py` tiene conocimiento sobre **estado de sesión durable**. Eso puede reutilizarse para persistir el **estado del Laboratorio** entre sesiones de experimentación.
- `entry_sync.py` resuelve un problema de **timing de entrada** que también afecta a los experimentos: cuándo considerar que una condición está “lista” si hay lag de broker.

---

## 9. Filtros y condiciones de estrategias legacy

**Componentes:** `strat_a.py`, `strat_fractal.py`, `strat_momentum.py`, `strat_order_block.py`, `strat_reversal_swing.py`, `candle_patterns.py`, `entry_scorer.py`, `entry_decision_engine.py`

### ¿Qué conocimiento aporta?
- Reglas de consolidación, springs, fractales, momentum, order blocks, patrones de vela.
- Scoring de candidatos, alineación HTF, blacklist de patrones.

### ¿Qué problema resuelve actualmente?
- Genera candidatos de entrada para el bot legacy.

### ¿Sigue siendo válido?
No como estrategias completas. Pero **cada condición individual es una hipótesis experimental** que debe volver a medirse.

### ¿Debe permanecer igual?
No.

### ¿Debe adaptarse?
Sí. Cada condición debe aislarse y promoverse como experimento al Laboratorio.

### ¿Debe fusionarse?
Sí. En su conjunto, deben convertirse en el **catálogo de hipótesis del Laboratorio**.

### ¿Debe archivarse?
Como código de producción, sí. Como **patrimonio de hipótesis**, no.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es el **inventario de condiciones** que ya existen y que deben volver a medirse formalmente.

### Activos ocultos
- `strat_a.py` tiene lógica de **dynamic range** y **consolidación** que puede reutilizarse para definir **criterios de permanencia** en el Administrador del Edificio.
- `candle_patterns.py` tiene clasificación de formas de vela que puede reutilizarse para **validar vela confirmatoria** en Piso 6 sin hardcodear “martillo”.
- `entry_decision_engine.py` tiene lógica de **HTF alignment** que es un experimento en sí mismo: ¿la alineación HTF realmente aporta valor?

---

## 10. HUB y visualización

**Componentes:** `hub/server.py`, `hub/render.py`, `hub/events.py`, `hub/edificio_panel.py`, `hub/strat_f_panel.py`

### ¿Qué conocimiento aporta?
- Visualización en vivo de métricas, eventos, bankroll, estado de procesos.
- Paneles diferenciados por estrategia.

### ¿Qué problema resuelve actualmente?
- Monitoreo humano del bot en producción.

### ¿Sigue siendo válido?
Sí, pero **debe cambiar su modelo de datos**: de “pares/estrategias” a “expedientes/hipótesis”.

### ¿Debe permanecer igual?
No.

### ¿Debe adaptarse?
Sí. Debe mostrar **estado de hipótesis**, no señales.

### ¿Debe fusionarse?
No.

### ¿Debe archivarse?
El panel STRAT-F sí, como legacy. El resto debe adaptarse.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es el **canal de observación humana**. Sin visualización, el Laboratorio no puede ser revisado por el operador.

### Activos ocultos
- `hub/events.py` define un **modelo de eventos** que puede reutilizarse para definir los **eventos del expediente**: ingreso, cambio de piso, retroceso, contratación, archivo.
- `hub/render.py` tiene lógica de **agregación y filtrado** que puede reutilizarse para **priorizar expedientes** por `priority_score`.

---

## 11. Utilidades y soporte

**Componentes:** `config.py`, `models.py`, `errors.py`, `loop_utils.py`, `math_utils.py`, `math_filters.py`, `spike_filter.py`, `alerter.py`, `bot_logging.py`

### ¿Qué conocimiento aporta?
- Infraestructura transversal: configuración, modelos de datos, errores, loops, matemáticas, logging, alertas.

### ¿Qué problema resuelve actualmente?
- Sostiene todo el proyecto con código reutilizable.

### ¿Sigue siendo válido?
Sí.

### ¿Debe permanecer igual?
Sí.

### ¿Debe adaptarse?
Solo para soportar conceptos nuevos: `HypothesisFile`, `Evidence`, `ExperimentConfig`.

### ¿Debe fusionarse?
No.

### ¿Debe archivarse?
No.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es la **base sobre la cual se construye todo**.

### Activos ocultos
- `math_filters.py` tiene **filtros numéricos** que pueden reutilizarse para **limpiar señales de evidencia** en el expediente.
- `spike_filter.py` tiene conocimiento sobre **outliers de datos** que es crítico para experimentos de robustez.

---

## 12. Testing como baseline de regresión

**Componentes:** 47 archivos en `tests/`, 409 tests pasando, 32 fallando.

### ¿Qué conocimiento aporta?
- Comportamiento esperado del sistema legacy.
- Casos edge documentados.

### ¿Qué problema resuelve actualmente?
- Regresión continua del core existente.

### ¿Sigue siendo válido?
Solo parcialmente. Protege el sistema viejo, no el nuevo.

### ¿Debe permanecer igual?
No.

### ¿Debe adaptarse?
Sí. Deben crearse tests nuevos para: estados de hipótesis, transiciones, expediente, orquestador, aislamiento experimental.

### ¿Debe fusionarse?
No.

### ¿Debe archivarse?
Los tests legacy deben archivarse progresivamente.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es el **colchón de seguridad** para no romper el core mientras se implementa la nueva arquitectura.

### Activos ocultos
- Los tests de **black box** y **scanner** contienen **casos reales de aceptación/rechazo** que pueden reutilizarse como **dataset de validación** para experimentos del Laboratorio.

---

## 13. Herramientas de descubrimiento y minería

**Componentes:** `strategy_lab/falsifier.py`, `strategy_lab/variant_searcher.py`, `strategy_lab/optimizer.py`, `strategy_lab/law_engine.py`, `strategy_lab/laws_freno.py`, `strategy_lab/minar_leyes_freno.py`

### ¿Qué conocimiento aporta?
- Búsqueda de variantes, minería de leyes, optimización, falsación.

### ¿Qué problema resuelve actualmente?
- Exploración automática de combinaciones de condiciones.

### ¿Sigue siendo válido?
Sí, como **prototipos de experimentación automática**.

### ¿Debe permanecer igual?
No.

### ¿Debe adaptarse?
Sí. Deben alinearse al Marco Experimental: una pregunta por experimento, falsación, reproducibilidad.

### ¿Debe fusionarse?
Sí. Deben integrarse en el `experiment_runner.py`.

### ¿Debe archivarse?
Como código actual, sí. Como enfoque, no.

### ¿Debe eliminarse?
No.

### ¿Qué valor aporta al nuevo Laboratorio?
Es el **inicio de la automatización científica**. Ya hay código que busca, mide y evalúa; solo necesita formalizarse.

### Activos ocultos
- `falsifier.py` ya implementa la **ley de falsación** del Marco Experimental. Es un activo invaluable porque ya existe, solo hay que adaptarlo.
- `minar_leyes_freno.py` y `laws_freno.py` contienen **conocimiento minado** sobre frenos que puede promoverse directamente como experimentos validados.

---

## 14. Mapa de capacidades sintético

| Capacidad | Clasificación | Valor para el nuevo Laboratorio |
|---|---|---|
| Datos reproducibles | 🟢 Estratégica | Cimiento |
| Backtest causal | 🟢 Estratégica | Núcleo operativo |
| Features técnicas | 🟢 Estratégica | Vocabulario de medición |
| Experimentos con resultados | 🟢 Estratégica | Patrimonio científico |
| Máquina de estados | 🟡 Adaptable | Plantilla de implementación |
| Persistencia y memoria | 🟢 Estratégica | Memoria histórica |
| ML scorer | 🟠 Experimental | Base de predicción |
| Gestión de riesgo | 🟢 Estratégica | Marco de seguridad |
| Filtros legacy | 🟠 Experimental | Inventario de hipótesis |
| HUB | 🟡 Adaptable | Canal humano |
| Utilidades | 🟢 Estratégica | Infraestructura |
| Testing | ⚪ Legacy | Colchón de regresión |
| Herramientas de descubrimiento | 🟠 Experimental | Automatización científica |

---

## 15. Activos ocultos identificados

1. `marketfeed/replay.py` → generador de experimentos controlados.
2. `caffeine.py` → conocimiento sobre vida útil de sesiones WebSocket.
3. `backtest_edificio.py` → parámetros hardcodeados son hipótesis implícitas.
4. `analyze_patient_waiting.py` → trayectoria de separación K/D puede ser índice de paciencia.
5. `simulate_p2_p3_sweep.py` → protocolo de falsación automática.
6. `poi_behavior.py` / `volume_profile.py` → código de estructuras reutilizable para experimentos geométricos.
7. `observador/pressure_point` → medida cuantitativa de convicción del mercado.
8. `observador/ROLLING_WINDOW` → ventana de evidencia acumulada del expediente.
9. `black_box_recorder.py` → snapshots de velas para experimentos de causalidad.
10. `strat_a.py` → dynamic range y consolidación como criterios de permanencia.
11. `candle_patterns.py` → clasificación de velas para validación de confirmación.
12. `entry_decision_engine.py` → alineación HTF como hipótesis experimental.
13. `math_filters.py` → limpieza de señales de evidencia.
14. `spike_filter.py` → outliers para experimentos de robustez.
15. Tests de black box/scanner → dataset de validación para Laboratorio.
16. `falsifier.py` → implementación existente de falsación.
17. `minar_leyes_freno.py` / `laws_freno.py` → leyes minadas listas para promover.

---

## 16. Respuesta a la pregunta fundamental

> ¿Qué patrimonio tecnológico y científico ya posee QUOTEX para construir el nuevo Laboratorio y el nuevo Edificio sin empezar desde cero?

QUOTEX posee:

- **Datos reproducibles** y una **black box con史料 real**.
- **Experimentación ya realizada** con resultados documentados.
- **Máquina de estados** casi lista para adaptar.
- **Persistencia madura** y **gestión de riesgo funcionando**.
- **ML wrapper** integrado.
- **Herramientas de falsación y minería** prototipadas.

No parte de cero. Parte de un **ecosistema con conocimiento disperso pero valioso**. La tarea no es inventar, sino **unificar, formalizar y promover** lo que ya existe bajo el Marco Experimental.

---

---

# Segunda Auditoría — Epistemología del Proyecto QUOTEX

> **Objetivo:** descubrir qué sabe hacer cada capacidad del proyecto, tratándola como un investigador que trabajó durante años.
>
> **Pregunta central:** ¿Qué conocimiento genera, consume, preserva y puede reaprovechar para hipótesis futuras, vigilantes del Edificio y experimentos del Laboratorio?
>
> **Regla de oro:** solo descubrimiento intelectual. No se propone refactor, código ni eliminación.

---

## Metodología epistemológica

Para cada capacidad se responde:

- ¿Qué conocimiento genera?
- ¿Qué conocimiento consume?
- ¿Qué conocimiento deja disponible para otros módulos?
- ¿Qué hipótesis del Laboratorio podría alimentar?
- ¿Qué vigilante del Edificio podría beneficiarse?
- ¿Qué experimentos futuros podrían reutilizarlo?
- ¿Qué parte es conocimiento permanente y qué parte es implementación?
- ¿Existe duplicación de conocimiento con otro módulo?
- ¿Puede convertirse en un servicio científico reutilizable?

---

## 1. Datos de mercado reproducibles — epistemología

### ¿Qué conocimiento genera?
- **Procedimientos de conectividad causal:** cómo obtener velas sin fuga de datos.
- **Protocolos de paginación y deduplicación:** conocimiento sobre límites y huecos en la API de Quotex.
- **Estrategias de backpressure:** cuánto pedir, cuándo reintentar, cómo evitar saturar.

### ¿Qué conocimiento consume?
- Parámetros de conexión, tokens de sesión, timeouts, reglas del broker.

### ¿Qué conocimiento deja disponible para otros módulos?
- Datos históricos limpios y referenciables.
- Sesiones grabadas reproducibles (`marketfeed/replay.py`).
- Cache dedup de velas.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Todas. Sin datos causales reproducibles no existe hipótesis falsable.

### ¿Qué vigilante del Edificio podría beneficiarse?
Indirectamente, todos. Los pisos necesitan velas cerradas sin contaminación.

### ¿Qué experimentos futuros podrían reutilizarlo?
Cualquier `EXP-NNN` que requiera reruns exactos, experimentos controlados o validación offline.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** protocolos de paginación, deduplicación, causalidad.
- **Implementación:** `connection.py`, `parallel_fetch.py`, `caffeine.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
No. Es la única fuente de datos.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Debe exponerse como **servicio de adquisición causal** al cual el Laboratorio llama para cualquier experimento.

---

## 2. Backtest causal vela-por-vela — epistemología

### ¿Qué conocimiento genera?
- **Mediciones winrate/lossrate por condición aislada.**
- **Lógica de aislamiento causal:** cómo separar una condición sin look-ahead.
- **Protocolos de etiquetado:** qué significa “ganó” y “perdió” en cada par.

### ¿Qué conocimiento consume?
- Features técnicas, parámetros de backtest, definiciones de piso.

### ¿Qué conocimiento deja disponible para otros módulos?
- Dataset features+label para ML.
- Métricas baseline por par.
- Lógica reutilizable de `R` velas de resultado.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Todas las hipótesis del Edificio: POI, brake, martillo, cruce, separación, body_n, sticky cross.

### ¿Qué vigilante del Edificio podría beneficiarse?
Todos los vigilantes de Piso 2 a Piso 6. Cada uno necesita medir su contribución aislada.

### ¿Qué experimentos futuros podrían reutilizarlo?
Todos los `EXP-NNN`. Es el motor científico del Laboratorio.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** lógica de etiquetado causal, separación de condiciones, medición de winrate.
- **Implementación:** `backtest_edificio.py`, simuladores P2/P3, `backtester.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
Sí. Tres backtests hacen lo mismo con pequeñas variaciones. El conocimiento está duplicado; la implementación está fragmentada.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Debe convertirse en el **ejecutor universal de experimentos**: recibe una hipótesis, aísla la condición, devuelve métricas completas.

---

## 3. Features técnicas validadas — epistemología

### ¿Qué conocimiento genera?
- **Definiciones operativas de concepts:** qué es body_n, brake_ratio, kd_dist, separación, sticky cross, martillo.
- **Algoritmos de detección causal:** cómo calcular cada feature sin look-ahead.
- **Resolución de conflictos temporales:** alineación de timeframes, timezone handling.

### ¿Qué conocimiento consume?
- Velas raw, parámetros de detección, constantes de dominio.

### ¿Qué conocimiento deja disponible para otros módulos?
- Vocabulario común de medición.
- Features listas para usar en backtests, ML y HUB.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Todas. Sin features validadas no se puede formular una hipótesis medible.

### ¿Qué vigilante del Edificio podría beneficiarse?
Todos. Cada vigilante consume features para emitir SÍ/NO/SIGUE/RETROCEDE.

### ¿Qué experimentos futuros podrían reutilizarlo?
Todos. Es el vocabulario del Laboratorio.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** definiciones de features, algoritmos de detección, causalidad.
- **Implementación:** `compute_features.py`, `brake_eval.py`, `stochastic_m15.py`, `stoch_cross_state.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
No. Es la fuente única de features.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Debe exponerse como **librería de features** con API estable.

---

## 4. Experimentos de Laboratorio con resultados — epistemología

### ¿Qué conocimiento genera?
- **Evidencia experimental documentada:** POI volumen, POI comportamiento, patient waiting, timing, sweep.
- **Protocolos de ejecución:** comandos exactos, versiones de datos, parámetros.
- **Conocimiento negativo:** qué NO funciona.

### ¿Qué conocimiento consume?
- Datos históricos, features, hipótesis formuladas.

### ¿Qué conocimiento deja disponible para otros módulos?
- Resultados CSV/MD con métricas.
- Protocolos reproducibles.
- Criterios de aceptación/rechazo.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Directamente: POI como área, paciencia post-cruce, timing de brake→cruce, sweep de parámetros.

### ¿Qué vigilante del Edificio podría beneficiarse?
Piso 2 (EN_POI), Piso 3 (RESPEANDO_POI), Piso 4 (EN_CRUCE), Piso 5 (CONFIRMANDO_CRUCE).

### ¿Qué experimentos futuros podrían reutilizarlo?
Cualquier `EXP-NNN` sobre condiciones ya medidas. No hay que volver a hacer POI volumen/comportamiento.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** hipótesis, protocolos, resultados, lecciones aprendidas.
- **Implementación:** scripts de ejecución, CSV generados.

### ¿Existe duplicación de conocimiento con otro módulo?
Sí. Varios scripts hacen sweep/timing/backtest con lógica similar. El conocimiento está disperso.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Debe convertirse en el **catálogo de experimentos** del Laboratorio, con estado `vigente/reemplazado/refutado/histórico`.

---

## 5. Máquina de estados de episodios — epistemología

### ¿Qué conocimiento genera?
- **Patrón de estados por activo:** QUIET → PRESSURE → EXPANSION → RESOLUTION.
- **Reglas de transición:** cuándo cambiar de estado, con qué triggers.
- **Ventana rodante de contexto:** cuánta historia considerar.

### ¿Qué conocimiento consume?
- Flujo de velas, eventos de presión, configuración de ventana.

### ¿Qué conocimiento deja disponible para otros módulos?
- Máquina de estados reutilizable.
- Pressure points como medida cuantitativa.
- Episodios clasificados con evolución.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Hipótesis sobre madurez de estructuras de mercado, contexto HTF, régimen de precio.

### ¿Qué vigilante del Edificio podría beneficiarse?
Todos. La máquina de estados puede convertirse en el motor de transiciones de piso.

### ¿Qué experimentos futuros podrían reutilizarlo?
Experimentación sobre máquinas de estado, contextos de mercado, predictores de régimen.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** patrón de estados, triggers, ventana rodante.
- **Implementación:** `state_machine.py`, `observer.py`, `pressure.py`, `evolution.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
Sí. `edificio_contratacion.py` ya tiene una máquina de estados parcial por pisos. Hay dos implementaciones del mismo patrón.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Puede convertirse en el **motor de estados de hipótesis** del nuevo Edificio.

---

## 6. Persistencia y memoria append-only — epistemología

### ¿Qué conocimiento genera?
- **Historia de eventos:** qué pasó, cuándo, con qué resultado.
- **Procedimientos de deduplicación:** cómo evitar guardar duplicados.
- **Formatos de serialización:** cómo almacenar experiencias sin pérdida.

### ¿Qué conocimiento consume?
- Eventos generados por el bot, escaneos, resultados de trades.

### ¿Qué conocimiento deje disponible para otros módulos?
- Memoria histórica consultable.
- Snapshots de velas en momentos de decisión.
- Esquema de experiencia extensible.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Todas. Sin memoria histórica no hay validación estadística posible.

### ¿Qué vigilante del Edificio podría beneficiarse?
Indirectamente todos. El expediente del futuro Edificio se apoya en esta capacidad.

### ¿Qué experimentos futuros podrían reutilizarlo?
Cualquier experimento que necesite rerun, validación cruzada o análisis histórico.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** filosofía append-only, deduplicación, particionado temporal.
- **Implementación:** `trade_journal.py`, `black_box_recorder.py`, `experience_engine.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
Sí. Tres silos separados hacen lo mismo: guardar historia. El conocimiento está duplicado; los formatos son distintos.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Debe convertirse en el **Expediente Persistente** único del proyecto.

---

## 7. ML scorer existente — epistemología

### ¿Qué conocimiento genera?
- **Modelo predictivo de confianza:** cómo combinar features en una probabilidad 0-1.
- **Importancia de features:** qué variables pesan más.
- **Protocolo de entrenamiento/reeentrenamiento:** cómo actualizar el modelo sin fuga.

### ¿Qué conocimiento consume?
- Snapshots de candidatos, labels de win/loss, features engineered.

### ¿Qué conocimiento deja disponible para otros módulos?
- Score de confianza para candidatos.
- Pipeline de features listo.
- Modelo serializado.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Hipótesis sobre predictores de éxito, importancia de variables, optimización de features.

### ¿Qué vigilante del Edificio podría beneficiarse?
Indirectamente el Orquestador: puede usar el score como evidencia adicional.

### ¿Qué experimentos futuros podrían reutilizarlo?
Experimentación sobre ML, feature importance, modelos bayesianos, redes neuronales.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** concepto de scorer, feature importance, protocolo de entrenamiento.
- **Implementación:** `ml_scorer.py`, `ml_features.py`, `train_lightgbm.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
No. Es la única capa de ML.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Pero debe cambiar de objetivo: de “clasificar señal” a **“predecir transición de estado / confianza de hipótesis”**.

---

## 8. Gestión de riesgo y sesiones — epistemología

### ¿Qué conocimiento genera?
- **Reglas de protección de capital:** límites, recuperación, stop de sesión.
- **Protocolos de sincronización de entrada:** cómo resolver latencia.
- **Diversificación por activo:** cómo distribuir riesgo.

### ¿Qué conocimiento consume?
- Resultados de trades, estado de sesión, bankroll, configuración de riesgo.

### ¿Qué conocimiento deja disponible para otros módulos?
- Sesión con límites claros.
- Estado de bankroll.
- Sincronización de entrada lista.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Indirectamente: sin gestión de riesgo, no hay experimentación en vivo posible.

### ¿Qué vigilante del Edificio podría beneficiarse?
Indirectamente todos. El Orquestador necesita saber si hay cupo para operar.

### ¿Qué experimentos futuros podrían reutilizarlo?
Experimentación sobre gestión de capital, sesiones óptimas, recuperación.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** reglas de Massaniello, Kelly, sesiones, diversificación.
- **Implementación:** `massaniello_risk.py`, `session_manager.py`, `entry_sync.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
No.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Como **marco de seguridad experimental**: permite correr experimentos en vivo sin riesgo.

---

## 9. Filtros y condiciones legacy — epistemología

### ¿Qué conocimiento genera?
- **Reglas de filtrado:** consolidación, springs, fractales, momentum, order blocks.
- **Criterios de aceptación/rechazo:** scoring, blacklist de patrones.
- **Alineación HTF:** conocimiento sobre contexto de timeframe mayor.

### ¿Qué conocimiento consume?
- Velas, features, configuración de estrategia.

### ¿Qué conocimiento deja disponible para otros módulos?
- Condiciones individuales como hipótesis potenciales.
- Casos de aceptación/rechazo reales.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Todas las condiciones legacy deben volver a medirse: POI, martillo, cruce, separación, body_n, HTF alignment.

### ¿Qué vigilante del Edificio podría beneficiarse?
Todos los vigilantes de Piso 2 a Piso 6 pueden derivarse de estas condiciones.

### ¿Qué experimentos futuros podrían reutilizarlo?
EXP-001 en adelante. Cada condición es un experimento potencial.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** reglas de filtrado, criterios de aceptación, conocimiento sobre estructuras.
- **Implementación:** cada `strat_*.py`, `candle_patterns.py`, `entry_scorer.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
Sí. Varias estrategias comparten filtros similares (ej: alineación HTF, blacklist).

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Como **catálogo de hipótesis del Laboratorio**: cada condición es una pregunta experimental.

---

## 10. HUB y visualización — epistemología

### ¿Qué conocimiento genera?
- **Modelo de visualización humana:** cómo representar estados complejos en tiempo real.
- **Agregación y filtrado:** cómo priorizar información para el operador.

### ¿Qué conocimiento consume?
- Eventos del bot, métricas, estado de procesos.

### ¿Qué conocimiento deja disponible para otros módulos?
- Visualización en vivo.
- Modelo de eventos estructurado.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Indirectamente: el HUB es el canal de revisión humana de experimentos.

### ¿Qué vigilante del Edificio podría beneficiarse?
Indirectamente todos. El operador humano revisa el estado de las hipótesis.

### ¿Qué experimentos futuros podrían reutilizarlo?
Experimentación sobre visualización de estados, priorización de hipótesis.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** modelo de eventos, agregación, filtrado.
- **Implementación:** `hub/server.py`, `hub/render.py`, `hub/events.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
Parcial. `hub/events.py` y `black_box_recorder.py` ambos modelan eventos, pero con propósitos distintos.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Como **interfaz de revisión humana del Laboratorio**: muestra expedientes, hipótesis, experimentos.

---

## 11. Utilidades y soporte — epistemología

### ¿Qué conocimiento genera?
- **Infraestructura transversal:** configuración, modelos de datos, logging, errores.
- **Filtros numéricos:** limpieza de señales, detección de outliers.

### ¿Qué conocimiento consume?
- Parámetros de configuración, formatos de datos, convenciones del proyecto.

### ¿Qué conocimiento deja disponible para otros módulos?
- Herramientas reutilizables para todo el proyecto.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Indirectamente todas. Sin utilidades, cada experimento reinventa la rueda.

### ¿Qué vigilante del Edificio podría beneficiarse?
Indirectamente todos. Necesitan config, modelos, logging.

### ¿Qué experimentos futuros podrían reutilizarlo?
Todos.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** convenciones, formatos, filtros numéricos.
- **Implementación:** `config.py`, `models.py`, `math_filters.py`, `spike_filter.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
No.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Como **base de infraestructura científica**: configuración experimental, modelos de datos, logging estructurado.

---

## 12. Testing como baseline de regresión — epistemología

### ¿Qué conocimiento genera?
- **Comportamiento esperado documentado:** qué debe hacer cada módulo.
- **Casos edge:** situaciones límite ya identificadas.
- **Protocolos de verificación:** cómo saber si algo se rompió.

### ¿Qué conocimiento consume?
- Código existente, supuestos de comportamiento.

### ¿Qué conocimiento deja disponible para otros módulos?
- Colchón de seguridad para cambios.
- Dataset de casos edge.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Indirectamente: casos edge de black box/scanner pueden usarse como dataset de validación.

### ¿Qué vigilante del Edificio podría beneficiarse?
Indirectamente todos. Los tests certifican que los módulos no se rompen.

### ¿Qué experimentos futuros podrían reutilizarlo?
Experimentación sobre validación, falsación, regresión.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** casos edge, protocolos de verificación.
- **Implementación:** 47 archivos de tests.

### ¿Existe duplicación de conocimiento con otro módulo?
No.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Como **framework de validación experimental**: cada `EXP-NNN` debe tener tests de reproducibilidad.

---

## 13. Herramientas de descubrimiento y minería — epistemología

### ¿Qué conocimiento genera?
- **Protocolos de búsqueda automática:** cómo explorar combinaciones de condiciones.
- **Leyes minadas:** conocimiento extraído de datos históricos sobre frenos.
- **Estrategias de falsación:** cómo intentar romper hipótesis automáticamente.

### ¿Qué conocimiento consume?
- Features, condiciones, parámetros, datos históricos.

### ¿Qué conocimiento deja disponible para otros módulos?
- Leyes minadas sobre frenos.
- Protocolos de falsación automática.
- Variantes candidatas.

### ¿Qué hipótesis del Laboratorio podría alimentar?
Hipótesis sobre optimización de parámetros, minería de condiciones, falsación masiva.

### ¿Qué vigilante del Edificio podría beneficiarse?
Indirectamente todos. Las leyes minadas pueden convertirse en vigilantes.

### ¿Qué experimentos futuros podrían reutilizarlo?
Experimentación automática, falsación masiva, minería de condiciones.

### ¿Qué parte es conocimiento permanente y qué parte es implementación?
- **Permanente:** protocolos de minería, leyes minadas, estrategias de falsación.
- **Implementación:** `falsifier.py`, `variant_searcher.py`, `minar_leyes_freno.py`.

### ¿Existe duplicación de conocimiento con otro módulo?
Parcial. `variant_searcher.py` y `optimizer.py` ambos exploran combinaciones.

### ¿Puede convertirse en un servicio científico reutilizable?
Sí. Como **motor de experimentación automática**: busca, mide, falsa y reporta.

---

## 14. Mapa epistemológico sintético

| Capacidad | Genera conocimiento | Consume conocimiento | Deja disponible | Servicio científico |
|---|---|---|---|---|
| Datos reproducibles | Protocolos de conectividad causal | Parámetros de conexión | Datos limpios, replay | Adquisición causal |
| Backtest causal | Mediciones winrate/lossrate | Features, parámetros | Dataset, métricas | Ejecutor de experimentos |
| Features técnicas | Definiciones operativas, algoritmos | Velas raw | Vocabulario de medición | Librería de features |
| Experimentos con resultados | Evidencia documentada, protocolos | Datos históricos | Resultados, lecciones | Catálogo de experimentos |
| Máquina de estados | Patrón de estados, triggers | Flujo de velas | Estados, transitions | Motor de estados de hipótesis |
| Persistencia append-only | Historia, deduplicación | Eventos, trades | Memoria histórica | Expediente persistente |
| ML scorer | Modelo predictivo, feature importance | Snapshots, labels | Score, pipeline | Predictor de transiciones |
| Gestión de riesgo | Reglas de protección, sincronización | Resultados, bankroll | Sesión segura | Marco de seguridad experimental |
| Filtros legacy | Reglas de filtrado, criterios | Velas, features | Condiciones como hipótesis | Catálogo de hipótesis |
| HUB | Modelo de visualización, agregación | Eventos, métricas | Visualización en vivo | Interfaz de revisión humana |
| Utilidades | Infraestructura, filtros numéricos | Configuración, formatos | Herramientas transversales | Base de infraestructura |
| Testing | Casos edge, protocolos | Código, supuestos | Colchón de seguridad | Framework de validación |
| Herramientas de minería | Leyes minadas, falsación automática | Features, datos | Protocolos de búsqueda | Motor de experimentación automática |

---

## 15. Oportunidades de servicios científicos

1. **Servicio de adquisición causal** — `connection.py` + `marketfeed/replay.py`.
2. **Ejecutor universal de experimentos** — backtests actuales unificados.
3. **Librería de features** — `compute_features.py` + `brake_eval.py`.
4. **Catálogo de experimentos** — todos los experimentos existentes formalizados como `EXP-NNN`.
5. **Motor de estados de hipótesis** — `observador/state_machine.py` adaptado.
6. **Expediente persistente** — fusión de trade journal, black box, experience engine.
7. **Predictor de transiciones** — `ml_scorer.py` reorientado.
8. **Marco de seguridad experimental** — `massaniello_risk.py` + `session_manager.py`.
9. **Catálogo de hipótesis** — condiciones legacy formalizadas.
10. **Interfaz de revisión humana** — HUB adaptado a expedientes/hipótesis.
11. **Base de infraestructura** — utilidades y soporte.
12. **Framework de validación** — tests legacy + nuevos tests de arquitectura.
13. **Motor de experimentación automática** — `falsifier.py` + `variant_searcher.py`.

---

## 16. Respuesta a la pregunta epistemológica fundamental

> ¿Qué patrimonio intelectual acumulado posee QUOTEX?

QUOTEX posee **conocimiento distribuido en 13 capacidades distintas**. Ese conocimiento no es código. Es:

- **Procedimientos causales** para obtener datos reproducibles.
- **Mediciones validadas** de condiciones de trading.
- **Experimentos documentados** con resultados positivos y negativos.
- **Máquina de estados** casi lista para adaptar a hipótesis.
- **Memoria histórica** en tres formatos distintos.
- **ML wrapper** entrenable.
- **Herramientas de falsación y minería** prototipadas.

El proyecto no es un bot de trading. Es un **laboratorio científico con capacidades operativas**. Su mayor activo no es el código en vivo, sino el **conocimiento acumulado** que aún no está formalizado bajo el Marco Experimental.

La tarea siguiente no es escribir código. Es **convertir ese conocimiento disperso en un sistema unificado de descubrimiento científico**.

---

*Última actualización: 2026-08-04*
*Estado: Segunda auditoría epistemológica completada. Pendiente de aprobación humana.*
