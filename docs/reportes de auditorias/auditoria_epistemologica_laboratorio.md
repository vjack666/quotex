# Auditoría Epistemológica del Laboratorio — Reporte Formal

**Proyecto:** QUOTEX — Laboratorio Experimental  
**Documento base:** `docs/AUDITORIA_CIENTIFICA_LABORATORIO.md`  
**Tipo:** Auditoría de patrimonio intelectual acumulado  
**Alcance:** motor, laboratorio, edificio, documentación, HUB, experimentos, ML y tests  
**Fecha:** 2026-08-04  
**Estado:** Completada. Pendiente de aprobación humana.  
**Auditor:** Hermes Agent (modo científico, sin propuestas de código ni refactor)

---

## Resumen ejecutivo

QUOTEX no es un bot de trading. Es un **laboratorio científico con capacidades operativas**.

Su mayor activo no es el código en vivo, sino el **conocimiento acumulado** que aún no está formalizado bajo el Marco Experimental.

Este documento responde la pregunta:

> ¿Qué patrimonio intelectual acumulado posee QUOTEX?

**Respuesta corta:** conocimiento distribuido en **13 capacidades distintas**, cada una con su propio flujo de generación, consumo y preservación de conocimiento.

---

## Metodología

Se aplicó la **metodología epistemológica** a cada capacidad del proyecto.

Para cada capacidad se respondió:

- ¿Qué conocimiento genera?
- ¿Qué conocimiento consume?
- ¿Qué conocimiento deja disponible para otros módulos?
- ¿Qué hipótesis del Laboratorio podría alimentar?
- ¿Qué vigilante del Edificio podría beneficiarse?
- ¿Qué experimentos futuros podrían reutilizarlo?
- ¿Qué parte es conocimiento permanente y qué parte es implementación?
- ¿Existe duplicación de conocimiento con otro módulo?
- ¿Puede convertirse en un servicio científico reutilizable?

**Regla de oro:** solo descubrimiento intelectual. No se propone refactor, código ni eliminación.

---

## 1. Datos de mercado reproducibles

**Componentes:** `connection.py`, `caffeine.py`, `candle_cache.py`, `parallel_fetch.py`, `marketfeed/`

### ¿Qué conocimiento genera?
- Procedimientos de conectividad causal: cómo obtener velas sin fuga de datos.
- Protocolos de paginación y deduplicación: conocimiento sobre límites y huecos en la API de Quotex.
- Estrategias de backpressure: cuánto pedir, cuándo reintentar, cómo evitar saturar.

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

## 2. Backtest causal vela-por-vela

**Componentes:** `strategy_lab/backtester.py`, `strategy_lab/scripts/backtest_edificio.py`, simuladores `simulate_p2_p3_*`

### ¿Qué conocimiento genera?
- Mediciones winrate/lossrate por condición aislada.
- Lógica de aislamiento causal: cómo separar una condición sin look-ahead.
- Protocolos de etiquetado: qué significa “ganó” y “perdió” en cada par.

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

## 3. Features técnicas validadas

**Componentes:** `strategy_lab/compute_features.py`, `strategy_lab/brake_eval.py`, `strategy_lab/stochastic_m15.py`, `strategy_lab/stoch_cross_state.py`

### ¿Qué conocimiento genera?
- Definiciones operativas de concepts: qué es body_n, brake_ratio, kd_dist, separación, sticky cross, martillo.
- Algoritmos de detección causal: cómo calcular cada feature sin look-ahead.
- Resolución de conflictos temporales: alineación de timeframes, timezone handling.

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

## 4. Experimentos de Laboratorio con resultados

**Componentes:** `strategy_lab/scripts/run_poi_vol_sensitivity.py`, `strategy_lab/scripts/run_local_volume_sensor.py`, `strategy_lab/scripts/run_volume_profile_experiment.py`, `strategy_lab/scripts/run_poi_behavior_experiment.py`, `strategy_lab/scripts/analyze_patient_waiting.py`, `strategy_lab/scripts/simulate_p2_p3_timing.py`, `strategy_lab/scripts/simulate_p2_p3_sweep.py`, `strategy_lab/scripts/simulate_p2_promotion.py`, resultados CSV/MD asociados.

### ¿Qué conocimiento genera?
- Evidencia experimental documentada: POI volumen, POI comportamiento, patient waiting, timing, sweep.
- Protocolos de ejecución: comandos exactos, versiones de datos, parámetros.
- Conocimiento negativo: qué NO funciona.

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

## 5. Máquina de estados de episodios

**Componentes:** `observador/state_machine.py`, `observador/observer.py`, `observador/pressure.py`, `observador/evolution.py`, `observador/store.py`, `observador/summary.py`

### ¿Qué conocimiento genera?
- Patrón de estados por activo: QUIET → PRESSURE → EXPANSION → RESOLUTION.
- Reglas de transición: cuándo cambiar de estado, con qué triggers.
- Ventana rodante de contexto: cuánta historia considerar.

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

## 6. Persistencia y memoria append-only

**Componentes:** `experience_engine.py`, `experience_schema.py`, `trade_journal.py`, `black_box_recorder.py`

### ¿Qué conocimiento genera?
- Historia de eventos: qué pasó, cuándo, con qué resultado.
- Procedimientos de deduplicación: cómo evitar guardar duplicados.
- Formatos de serialización: cómo almacenar experiencias sin pérdida.

### ¿Qué conocimiento consume?
- Eventos generados por el bot, escaneos, resultados de trades.

### ¿Qué conocimiento deja disponible para otros módulos?
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

## 7. ML scorer existente

**Componentes:** `ml_scorer.py`, `ml_features.py`, `entry_intelligence.py`, `scripts/train_lightgbm.py`

### ¿Qué conocimiento genera?
- Modelo predictivo de confianza: cómo combinar features en una probabilidad 0-1.
- Importancia de features: qué variables pesan más.
- Protocolo de entrenamiento/reeentrenamiento: cómo actualizar el modelo sin fuga.

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

## 8. Gestión de riesgo y sesiones

**Componentes:** `massaniello_risk.py`, `massaniello_engine.py`, `massaniello_persistence.py`, `session_manager.py`, `entry_sync.py`, `diversification_enforcer.py`

### ¿Qué conocimiento genera?
- Reglas de protección de capital: límites, recuperación, stop de sesión.
- Protocolos de sincronización de entrada: cómo resolver latencia.
- Diversificación por activo: cómo distribuir riesgo.

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

## 9. Filtros y condiciones legacy

**Componentes:** `strat_a.py`, `strat_fractal.py`, `strat_momentum.py`, `strat_order_block.py`, `strat_reversal_swing.py`, `candle_patterns.py`, `entry_scorer.py`, `entry_decision_engine.py`

### ¿Qué conocimiento genera?
- Reglas de filtrado: consolidación, springs, fractales, momentum, order blocks.
- Criterios de aceptación/rechazo: scoring, blacklist de patrones.
- Alineación HTF: conocimiento sobre contexto de timeframe mayor.

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

## 10. HUB y visualización

**Componentes:** `hub/server.py`, `hub/render.py`, `hub/events.py`, `hub/edificio_panel.py`, `hub/strat_f_panel.py`

### ¿Qué conocimiento genera?
- Modelo de visualización humana: cómo representar estados complejos en tiempo real.
- Agregación y filtrado: cómo priorizar información para el operador.

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

## 11. Utilidades y soporte

**Componentes:** `config.py`, `models.py`, `errors.py`, `loop_utils.py`, `math_utils.py`, `math_filters.py`, `spike_filter.py`, `alerter.py`, `bot_logging.py`

### ¿Qué conocimiento genera?
- Infraestructura transversal: configuración, modelos de datos, logging, errores.
- Filtros numéricos: limpieza de señales, detección de outliers.

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

## 12. Testing como baseline de regresión

**Componentes:** 47 archivos en `tests/`, 409 tests pasando, 32 fallando.

### ¿Qué conocimiento genera?
- Comportamiento esperado documentado: qué debe hacer cada módulo.
- Casos edge: situaciones límite ya identificadas.
- Protocolos de verificación: cómo saber si algo se rompió.

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

## 13. Herramientas de descubrimiento y minería

**Componentes:** `strategy_lab/falsifier.py`, `strategy_lab/variant_searcher.py`, `strategy_lab/optimizer.py`, `strategy_lab/law_engine.py`, `strategy_lab/laws_freno.py`, `strategy_lab/minar_leyes_freno.py`

### ¿Qué conocimiento genera?
- Protocolos de búsqueda automática: cómo explorar combinaciones de condiciones.
- Leyes minadas: conocimiento extraído de datos históricos sobre frenos.
- Estrategias de falsación: cómo intentar romper hipótesis automáticamente.

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

## Mapa epistemológico sintético

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

## Oportunidades de servicios científicos

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

## Preguntas sin respuesta — backlog del Laboratorio

Estas son cosas que **creemos saber pero nunca hemos demostrado estadísticamente**. Constituyen el backlog prioritario de experimentos:

1. ¿Realmente esperar dos velas mejora el win rate?
2. ¿El martillo aporta valor o solo coincide con otras condiciones?
3. ¿El umbral del estocástico es el óptimo o fue elegido por intuición?
4. ¿El body_n actual tiene evidencia o es un valor heredado?
5. ¿Qué filtros del Edificio existen por tradición y cuáles por evidencia?
6. ¿La separación K/D > 5 es el umbral óptimo?
7. ¿El sticky cross realmente empeora los resultados, o es ruido?
8. ¿La alineación HTF realmente aporta valor?
9. ¿Cuántas velas puede permanecer un POI antes de degradarse?
10. ¿El brake ratio máximo óptimo es 1.0 o un valor menor?

---

## Respuesta a la pregunta epistemológica fundamental

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

## Aprobación humana

- [ ] Aprobado para definir roadmap de evolución
- [ ] Aprobado con observaciones
- [ ] Rechazado; requiere revisión

**Observaciones:**

---

*Documento generado por Hermes Agent*  
*Última actualización: 2026-08-04*  
*Estado: Completado. Pendiente de aprobación humana.*
