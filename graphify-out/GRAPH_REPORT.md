# Graph Report - .  (2026-07-14)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2544 nodes · 5091 edges · 164 communities (121 shown, 43 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 691 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9e818a62`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TradeExecutor
- strat_a.py
- evaluate_strat_f
- smc_analysis.py
- Connection
- _pre_validate_entry (gate de riesgo)
- test_scanner_strat_a.py
- TelegramAlerter
- consolidation_bot.py — Bot de consolidación (facade)
- SessionManager
- ScheduleController
- Implement Missing Modules — Design
- models.py
- datetime
- massaniello_engine.py
- GaleWatcher
- MassanielloPersistence
- entry_decision_engine.py
- BlackBoxRecorder
- Design hub_live_websocket
- DiversificationEnforcer
- MartingaleCalculator
- AssetScanner
- CandleCache
- BotRunner
- scan_prefetch.py
- ObservableCandleFetcher
- server.py
- config.py
- MassanielloRiskManager
- ConsolidationZone
- CandidateEntry
- .refresh_from_candidate
- test_stochastic_m15.py
- test_strat_reversal_swing.py
- scanner.py
- consolidation_bot.py
- test_backtester.py
- Candle
- BreakerOrderBlockDetector
- fetch_candles_with_retry
- zone_memory.py
- Journal
- bot_logging.py
- MassanielloRiskManager (src/massaniello_risk.py)
- ._scan_phase_evaluate_assets
- Common Scanner / Scoring Pipeline
- HTFScanner
- test_weight_calibrator.py
- WeightCalibrator
- test_htf_zone_wiring.py
- TestHelpers
- TestExportLoad
- __init__.py
- Backtester
- test_hub_bankroll_store.py
- connection.py
- load_schedule
- HubScanner
- FilterSellOTC
- test_consolidation_bot.py
- massaniello_is_terminal
- trade_journal.py
- Path
- stats.py
- Refactor Monolith (Feature #1)
- ._refresh_cycle
- StratFHubState
- TestReevaluate
- _now
- spike_filter.py
- app.py
- test_hub_strat_f.py
- STRAT-A OB Prefetch (Feature #21)
- STRAT-A Quality Filters Feature (id=19)
- journal_performance_report.py
- detect_momentum_1m
- HubEventBus
- CandidateData
- main.py
- massaniello_risk.py
- create_client
- .calibrate
- STRAT-A HTF Zone Wiring (Feature #20)
- test_strat_f_golive.py
- QualityAssetLibrary
- ._reevaluate_strat_a
- strat_f_postmortem.py
- test_fase4_postmortem.py
- black_box_recorder.py
- analyze_trades.py
- executor.py
- render.py
- trader_short.py
- htf_scanner.py
- ._ensure_schema_upgrades
- TestStratFRecognition
- test_strat_f_journal.py
- _WebLogHandler
- diag_strat_f_live.py
- .apply_weights
- test_fase3_scanner_blackbox.py
- test_fase5_stats.py
- lifespan
- update_config
- strat_support.py
- extract_modules.py
- loop_utils.py
- enviar_orden
- .query_strat_f
- ._row_to_trade
- TestNoBrokerIO
- TestIntegration
- bot_start
- parse_strat_a_session.py
- build_executor_scanner.py
- fix_indent.py
- .cache_age_sec
- ._resolve_assets
- .export_weights
- ws_logs
- engram
- deep_analysis.py
- reindent_class.py
- .conn
- bot_status
- bot_stop
- clear_blackbox_trades
- get_blackbox_session
- get_logs
- health
- massaniello_preview
- reset_session
- reject_cycle
- session_status
- count_trades.py
- trading_workflow.py
- conftest.py
- WebSocket
- skill-registry.md — Registry de skills (Gentle AI)
- Candle
- ConsolidationZone
- HubScanner
- Path
- progress/current.md — Plantilla sesión actual
- ScanCycleData
- Hub Live WebSocket — Placeholder
- Namespace
- Quotex
- Task
- Connection
- str
- Enum
- Any
- DataFrame
- Any
- DataFrame
- ArgumentParser

## God Nodes (most connected - your core abstractions)
1. `Candle` - 181 edges
2. `MassanielloRiskManager` - 68 edges
3. `AssetScanner` - 62 edges
4. `TradeExecutor` - 59 edges
5. `WeightCalibrator` - 44 edges
6. `ConsolidationZone` - 43 edges
7. `SessionManager` - 41 edges
8. `Backtester` - 40 edges
9. `ScheduleController` - 35 edges
10. `Journal` - 34 edges

## Surprising Connections (you probably didn't know these)
- `Capas del Quant Engine (6 capas)` --semantically_similar_to--> `Arquitectura de 4 capas (connection→scanner→strats→executor)`  [INFERRED] [semantically similar]
  Documentos/files/QUANT_ENGINE_ARQUITECTURA.md → agent/PROJECT_STATE.md
- `test_radar_watch_tick_no_crash()` --calls--> `AssetScanner`  [INFERRED]
  tests/test_strat_a_radar.py → src/scanner.py
- `Decisión: Massaniello activo (no martingala en runtime)` --semantically_similar_to--> `Martingala (legacy, superseded por Massaniello)`  [INFERRED] [semantically similar]
  CHECKPOINTS.md → MARTINGALE_SUMMARY.md
- `Motor Masaniello 5/2` --semantically_similar_to--> `MassanielloRiskManager (gestor de riesgo activo)`  [INFERRED] [semantically similar]
  Documentos/files/PLAN_MASANIELLO.md → agent/CONTEXT.md
- `Modo Conservador Post-Pérdida (Masaniello)` --semantically_similar_to--> `MassanielloRiskManager (gestor de riesgo activo)`  [INFERRED] [semantically similar]
  Documentos/files/PLAN_MASANIELLO.md → agent/CONTEXT.md

## Import Cycles
- None detected.

## Communities (164 total, 43 thin omitted)

### Community 0 - "TradeExecutor"
Cohesion: 0.05
Nodes (32): CandidateEntry, EntryTimingInfo, Any, ConsolidationZone, Delega sincronización y validación de timing al EntrySynchronizer., Consulta el resultado de una operación expirada al broker         y actualiza e, Crea un trade_client FRESCO antes de cada orden.          Fix definitivo: pyqu, Fallback liviano: limpia trades ya resueltos o dispara resolución si         la (+24 more)

### Community 1 - "strat_a.py"
Cohesion: 0.08
Nodes (70): CandleSignal, MAState, OrderBlock, avg_body(), _block_distance(), broke_above(), broke_below(), _clamp() (+62 more)

### Community 2 - "evaluate_strat_f"
Cohesion: 0.06
Nodes (68): _avg_ticks(), evaluate_strat_f(), _fractal_down(), _fractal_up(), _m15_context(), _m1_rejects_band(), _phase_a_from_ticks(), Estrategia F: Fractal / Wyckoff (marco M15/M5/M1).  Une los libros de boblioteca (+60 more)

### Community 3 - "smc_analysis.py"
Cohesion: 0.07
Nodes (52): Bias, _compute_bias(), detect_fvg(), detect_structure(), detect_swings(), _extract_zones(), FVG, _label_structure_events() (+44 more)

### Community 4 - "Connection"
Cohesion: 0.06
Nodes (44): KellySizer, Path, Cálculo de Kelly Criterion para sizing conservador del capital., Retorna payout promedio como ratio (85 % → 0.85)., Calcula el factor de Kelly fraccional.          Args:             fractional: Fr, Calcula el factor de Kelly fraccional desde datos históricos.      Fórmula compl, Busca el archivo trade_journal-*.db más reciente., Cierra la conexión a la BD si está abierta. (+36 more)

### Community 5 - "_pre_validate_entry (gate de riesgo)"
Cohesion: 0.06
Nodes (59): CHANGELOG (agent memory), CONTEXT (conocimiento técnico persistente), MassanielloRiskManager (gestor de riesgo activo), Strategy A — Consolidation (5m), Strategy B — Wyckoff Spring/Upthrust, Decisión: workflow autónomo /agent, Rationale: carpeta /agent para resumen cross-machine, Decisión: demo-only para fase Masaniello (+51 more)

### Community 6 - "test_scanner_strat_a.py"
Cohesion: 0.11
Nodes (47): PendingReversal, Datos prefetched para un ciclo de escaneo., ScanCycleData, _bearish_15m_candles(), _candle(), FakeBot, _FakeHTFScanner, _make_scanner_mocks() (+39 more)

### Community 7 - "TelegramAlerter"
Cohesion: 0.05
Nodes (46): Exception, Alertas a Telegram para eventos del bot vía Bot API., Alerta: conexión perdida con el broker (R6)., Alerta: stop-loss de sesión activado (R7)., Envía mensajes a un chat de Telegram vía Bot API.      Lee TELEGRAM_BOT_TOKEN y, Check cooldown for event_type. Updates timestamp if allowed., Send a raw text message to Telegram.          Args:             text: Message te, Alerta: sesión Massaniello cumplida (R4). (+38 more)

### Community 8 - "consolidation_bot.py — Bot de consolidación (facade)"
Cohesion: 0.08
Nodes (55): AGENTS.md — Mapa de navegación para agentes, alerter.py — Alertas Telegram, backtester.py — Motor de backtesting, candle_cache.py — Caché local de velas, CHECKPOINTS.md — Evaluación del estado final, CLAUDE.md — Instrucciones para Claude (rol leader), implementer.md — Agente Implementador, leader.md — Agente Líder (Orquestador) (+47 more)

### Community 9 - "SessionManager"
Cohesion: 0.06
Nodes (23): Enum, _get_event_bus(), Any, Session lifecycle manager for the Quotex trading bot.  Manages the state machine, Transition to STOPPED from any state., Transition from SCANNING to TRADING., Transition from TRADING back to SCANNING., Mark session as completed (meta ITM / failed / timeout / exhausted).          Em (+15 more)

### Community 10 - "ScheduleController"
Cohesion: 0.08
Nodes (26): ClockFn, SleepFn, Any, Schedule controller for manual / auto_full overnight data collection.  Phases: i, User pressed Detener — cancel timers and disarm., Massaniello cycle finished. Returns action: none | next_cycle | rest., Work/rest/consecutive-session scheduler for schedule_mode=auto_full., Prepare controller from config. Does not start a work block yet. (+18 more)

### Community 11 - "Implement Missing Modules — Design"
Cohesion: 0.06
Nodes (49): Backtesting Engine — Design, Backtester (src/backtester.py), Decision: pandas descartado en backtester, Performance Metrics (Sharpe, Drawdown, Win Rate), trade_journal.Journal (shared DB dependency), Backtesting Engine — Requirements, Backtesting Engine — Tasks, Candle Cache — Design (+41 more)

### Community 12 - "models.py"
Cohesion: 0.07
Nodes (39): EntrySynchronizer, Sincronización precisa de entradas con apertura de vela 1m., Telemetría por orden: time_since_open y secs_to_close., Calcula y valida timing de entrada respecto al open de vela 1m., Evalúa timing puro respecto a un open de vela conocido.          Args:, Espera al próximo open de vela 1m y valida que el envío no llegue tarde., EntryTimingInfo, MartinPending (+31 more)

### Community 13 - "datetime"
Cohesion: 0.09
Nodes (34): datetime, Popen, _count_outcomes(), _launch_main(), _load_state(), main(), Path, Autopilot STRAT-F: relanza main.py mientras el host mate el WebSocket, y cuenta (+26 more)

### Community 14 - "massaniello_engine.py"
Cohesion: 0.10
Nodes (39): Result, Settings, BetRow, calculate_balance_objective(), calculate_stake(), effective_profit(), _is_finished(), _multiplier_table() (+31 more)

### Community 15 - "GaleWatcher"
Cohesion: 0.08
Nodes (24): FetchPriceFn, GetBalanceFn, mg/ — Motor de Gale (Martingale Engine)  Módulo independiente que vigila opera, GaleWatcher, mg/mg_watcher.py — GaleWatcher  Vigila una operación binaria abierta de 5 minu, Información de la operación activa que el watcher vigila., True si el precio actual implica que la operación va perdiendo., Texto corto de P/L: dirección, variación de precio e implicancia. (+16 more)

### Community 16 - "MassanielloPersistence"
Cohesion: 0.07
Nodes (24): Journal, MassanielloPersistence, Valida tipos y rangos básicos. Retorna state limpio o None., Guarda y recupera el estado de MassanielloRiskManager en SQLite., INSERT del estado actual de *manager* en massaniello_state.          Devuelve, SELECT de la última fila de massaniello_state.          Retorna dict con la fi, Restaura campos de *manager* desde *state*.          No modifica si el estado, journal() (+16 more)

### Community 17 - "entry_decision_engine.py"
Cohesion: 0.08
Nodes (42): CandleSignal, apply_category_logic(), _check_candles_available(), _check_cycle_limit(), _check_htf_available_and_aligned(), _check_no_active_trade(), _check_pattern_confirmed(), _check_payout_minimum() (+34 more)

### Community 18 - "BlackBoxRecorder"
Cohesion: 0.07
Nodes (22): BlackBoxRecorder, Any, Registra TODA la actividad de las estrategias., Crea tablas si no existen., Elimina archivos DB y JSONL de caja negra con más de RETENTION_DAYS., Registra el inicio de un escaneo. Retorna scan_id., Registra un candidato escaneado y retorna su id., Actualiza un candidato existente con estado posterior al escaneo. (+14 more)

### Community 19 - "Design hub_live_websocket"
Cohesion: 0.07
Nodes (39): Arquitectura y estándar de calidad, Qué NO hacer (anti-patrones), Flujo de datos HFT, Cuatro capas (Conexión/Análisis/Estrategias/Ejecución), Gestión de riesgo (estado actual), Estado transaccional en SQLite, Separación estrategia-ejecución, Convenciones de código (+31 more)

### Community 20 - "DiversificationEnforcer"
Cohesion: 0.09
Nodes (33): DiversificationEnforcer, diversification_enforcer.py — Rechaza entradas que violan límites de diversifica, Valida que una nueva entrada no viole los límites de diversificación., Verifica si se permite una entrada para ``candidate_asset``.          Parameters, TradeState, _make_trade(), Tests de diversification_enforcer.py., Permite entrada en otro activo aunque el máximo por activo se alcanzó. (+25 more)

### Community 21 - "MartingaleCalculator"
Cohesion: 0.09
Nodes (19): MartingaleCalculator, Martingale Calculator para Opciones Binarias. Reemplica la lógica de la calcula, Calcula el objetivo de ciclo para un balance dado (sin mutar estado)., Redondea hacia arriba a centavos., Calcula el monto a invertir para alcanzar el objetivo.          Args:, Calcula inversión para un balance proyectado sin mutar el estado interno., Calculadora de Martingale para ciclos de trading con incremento fijo., Registra ganancia y cierra ciclo.         El saldo se ajusta EXACTAMENTE al obj (+11 more)

### Community 22 - "AssetScanner"
Cohesion: 0.11
Nodes (10): AssetScanner, Any, Path, Task, FASE 4/5 y 5/5 — pending reversals, selección y ejecución., Envía la orden para un candidato y devuelve True si el broker la aceptó., Escanea todos los activos, puntúa cada candidato con el sensor         matemáti, Re-evalúa activos en pending_reversals.         Devuelve candidatos listos para (+2 more)

### Community 23 - "CandleCache"
Cohesion: 0.10
Nodes (19): CacheKey, Lock, _CacheEntry, CandleCache, Any, Caché en memoria de velas con actualización incremental., Elimina entradas expiradas. Devuelve cantidad purgada., Caché asyncio-safe: clave (asset, tf_sec) → velas ordenadas por ts. (+11 more)

### Community 24 - "BotRunner"
Cohesion: 0.10
Nodes (13): BotRunner, Any, Gestiona el lifecycle del bot: start / stop / status.      Diseñado para ser l, Write inactive/clean Massaniello state using hub shape (ops/ITM/capital)., Push _config values into the config module so imports see updated values., Push config changes to the live bot instance (hot-reload)., User confirmed they want a new cycle., User declined new cycle. (+5 more)

### Community 25 - "scan_prefetch.py"
Cohesion: 0.12
Nodes (25): Semaphore, decrement_failed_assets(), _fetch_with_optional_stagger(), filter_scan_assets(), prefetch_primary_candles(), prefetch_strat_a_secondary(), Any, Orquestación de prefetch para ciclos de escaneo. (+17 more)

### Community 26 - "ObservableCandleFetcher"
Cohesion: 0.11
Nodes (15): CandleFetchResult, ConnectionState, FetchMetrics, ObservableCandleFetcher, Any, candle_fetcher_observable.py ============================  Capa de observabil, Obtiene estado actual de la conexión., Fetch con observabilidad + retry controlado para empty arrays. (+7 more)

### Community 27 - "server.py"
Cohesion: 0.12
Nodes (24): api_state(), api_strat_f(), _auto_open_dashboard(), _broadcast(), _build_snapshot(), _close_browser(), _enrich_with_bot(), _event_relay() (+16 more)

### Community 28 - "config.py"
Cohesion: 0.11
Nodes (19): main(), Comparar métodos de fetch de velas pyquotex., main(), Test new HistoryMixin candle APIs., main(), Poll candle count after get_candles request., main(), Prueba aislada: una sola vela fetch con delays. (+11 more)

### Community 29 - "MassanielloRiskManager"
Cohesion: 0.16
Nodes (12): MassanielloRiskManager, Any, Wrapper de sesión Massaniello (ops / ITM / límite temporal).      Ops/ITM se l, mgr(), Tests del wrapper MassanielloRiskManager., test_next_stake_ok(), test_register_win_logs_session_complete(), test_session_status_snapshot() (+4 more)

### Community 30 - "ConsolidationZone"
Cohesion: 0.12
Nodes (20): ConsolidationZone, _age_ratio_ok(), _clamp(), compute_readiness(), RadarWatchEntry, rank_and_trim(), STRAT-A hunter radar: watchlist de zonas casi listas (coarse → fine)., Puntuación 0–100: proximidad al extremo, madurez, compresión, payout. (+12 more)

### Community 31 - "CandidateEntry"
Cohesion: 0.15
Nodes (23): _age_adjustment(), _clamp(), detect_swing_levels(), _ema(), explain_score(), _normalize(), Componente REBOUND: mide calidad de mecha en el extremo y momentum de velas reci, Componente BREAKOUT: mide fuerza de la vela de ruptura vs historial.     Interp (+15 more)

### Community 32 - ".refresh_from_candidate"
Cohesion: 0.16
Nodes (14): Ventana VIP para candidatos casi listos para entrada., VipWindowData, _candles_tail(), _ema(), _ma_pair(), Any, vip_library.py ============== Biblioteca VIP de candidatos casi listos para en, Biblioteca de ventanas VIP, actualizada con cada candidato evaluado. (+6 more)

### Community 33 - "test_stochastic_m15.py"
Cohesion: 0.18
Nodes (22): _candles_to_ohlcv(), compute_stoch(), _detect_divergence(), Any, Estocástico M15 para STRAT-F — capa fina sobre pyquotex.  REUTILIZA la implement, Detecta divergencia precio vs %K en la ventana reciente.      bull: precio hace, Extrae close/high/low/open de una secuencia de Candle., Calcula el estocástico M15 (Slow/Full 14,3) + derivados.      Args:         cand (+14 more)

### Community 34 - "test_strat_reversal_swing.py"
Cohesion: 0.13
Nodes (22): detect_reversal_swing(), Estrategia reversal swing: reversión en niveles dinámicos de soporte/resistencia, Detecta reversión en niveles de soporte/resistencia dinámicos (swing highs/lows), _base_candles(), _candles_with_swing_high(), _candles_with_swing_low(), Tests de strat_reversal_swing.py., R2: vela toca swing low con mecha inferior → señal CALL. (+14 more)

### Community 35 - "scanner.py"
Cohesion: 0.15
Nodes (14): Lógica de estado del HUB STRAT-F.  Reemplaza hub_scanner.py viejo (orientado a, Panel STRAT-F del HUB (estado + registro).  Reemplaza la VISTA del dashboard: el, Modelo de datos del nuevo HUB STRAT-F.  Un solo estado: aceptadas vs rechazadas,, Señal STRAT-F que pasó todos los filtros., Activo STRAT-F descartado, con la razón legible., StratFReject, StratFRow, Descarga de velas y recolección de candidatos por activo. (+6 more)

### Community 36 - "consolidation_bot.py"
Cohesion: 0.14
Nodes (10): Namespace, Quotex, ConsolidationBot, _extract_candidates_for_hub(), main(), parse_args(), consolidation_bot.py — Facade del bot de consolidación Quotex., Convierte last_scan_candidates del bot a payloads para el hub. (+2 more)

### Community 37 - "test_backtester.py"
Cohesion: 0.13
Nodes (19): Backtester — offline strategy replay engine.  Re-evaluates historical signals, _create_db(), db_empty(), db_known_metrics(), db_mixed(), db_strat_f(), _momentum_candles(), Any (+11 more)

### Community 38 - "Candle"
Cohesion: 0.29
Nodes (18): _body(), _body_high_zone(), _body_low_zone(), _body_pct(), detect_reversal_pattern(), _engulfs(), explain_no_pattern_reason(), fetch_candles_1m() (+10 more)

### Community 39 - "BreakerOrderBlockDetector"
Cohesion: 0.22
Nodes (8): BoBPhase, BoBResult, BoBSetup, BoBState, BreakerOrderBlockDetector, Enum, str, Detector BoB por fases: setup -> retest -> confirmation.      Este detector NO

### Community 40 - "fetch_candles_with_retry"
Cohesion: 0.16
Nodes (18): _candles_from_raw(), fetch_candles(), fetch_candles_with_retry(), looks_like_connection_issue(), _min_expected_candles(), raw_to_candle(), Tests de connection.py con mocks (sin broker real)., test_fetch_candles_fallback_to_historical() (+10 more)

### Community 41 - "zone_memory.py"
Cohesion: 0.14
Nodes (17): EntryContext, Contexto opcional para evaluación de entrada., _classify_role(), _decay(), HistoricalZone, Path, query_nearby_zones(), zone_memory.py ============== Módulo de memoria de zonas históricas de consoli (+9 more)

### Community 42 - "Journal"
Cohesion: 0.11
Nodes (9): Journal, Connection, Muestra los últimos N candidatos rechazados con detalle., Interfaz principal del módulo de aprendizaje., Actualiza auditoría de timing para un candidato ya registrado., Registra una zona que fue descartada.          expiry_reason: TIME_LIMIT | BRO, Muestra las últimas N zonas expiradas con diagnóstico., Actualiza trazabilidad de ticket para una fila de candidato. (+1 more)

### Community 43 - "bot_logging.py"
Cohesion: 0.14
Nodes (15): Counter, Logger, asset_detail(), format_reject_summary(), is_verbose(), Any, Logging helpers — keep console signal-to-noise high.  Normal mode (default): cyc, Per-asset chatter: INFO only when verbose, else DEBUG. (+7 more)

### Community 44 - "MassanielloRiskManager (src/massaniello_risk.py)"
Cohesion: 0.14
Nodes (17): Kelly integration in consolidation_bot.py, Discarded: per-asset Kelly, Kelly Criterion Sizing (Feature), KellySizer (src/kelly_sizer.py), Kelly x Massaniello _initial_capital, Kelly reads candidates table, Discarded: JSON file persistence, Persistence save in executor.py (+9 more)

### Community 45 - "._scan_phase_evaluate_assets"
Cohesion: 0.18
Nodes (6): PendingReversalHint, RadarWatchEntry, FASE 3/5 — MOMENTUM y STRAT-A sin I/O de red., Tick 1m sobre pares en watchlist. Devuelve True si se intentó entrada., Veto HTF 15m y muro zone_memory antes de crear candidato STRAT-A.          Ret, StratAEvaluation

### Community 46 - "Common Scanner / Scoring Pipeline"
Cohesion: 0.18
Nodes (18): Common Scanner / Scoring Pipeline, Momentum 1m — Design, Momentum 1m — Requirements, Momentum 1m — Tasks, Order Block — Design, Order Block — Requirements, Order Block — Tasks, Reversal Swing — Design (+10 more)

### Community 47 - "HTFScanner"
Cohesion: 0.11
Nodes (10): HTFScanner, Devuelve {asset: n_candles} para diagnóstico., TTL del cache HTF en segundos., Cantidad de activos actualmente presentes en la biblioteca HTF., Devuelve la última lista elegible (asset, payout) del scanner HTF.         Si e, Pausa el refresco (libera el WebSocket para orders/open)., Reanuda el refresco en la próxima ronda., Cache de velas 15m mantenida en background.      Parámetros     ---------- (+2 more)

### Community 48 - "test_weight_calibrator.py"
Cohesion: 0.16
Nodes (16): weight_calibrator.py — Calibración dinámica de pesos del entry_scorer. =========, calibrator_empty(), calibrator_minimal(), calibrator_with_trades(), _candles_with_volatility(), _create_in_memory_db(), _populate_db(), Any (+8 more)

### Community 49 - "WeightCalibrator"
Cohesion: 0.18
Nodes (5): Connection, Calibra pesos del entry_scorer usando datos históricos de trades.      Proceso:, WeightCalibrator, TestCalibrate, TestLoadTrades

### Community 50 - "test_htf_zone_wiring.py"
Cohesion: 0.27
Nodes (15): FakeHTFScanner, _make_scanner(), Path, Unit tests — HTF 15m cache wiring y zone_memory en STRAT-A., R15: trend usa candles_15m (>=25) en lugar de velas 5m del candidato., _seed_expired_zone(), test_htf_pass_aligned_call(), test_htf_veto_misaligned_put() (+7 more)

### Community 51 - "TestHelpers"
Cohesion: 0.18
Nodes (3): Mapea hora (0-23) a bucket: night/morning/afternoon/evening., Calcula Sharpe ratio de una lista de profits.          Retorna -999 si hay menos, TestHelpers

### Community 52 - "TestExportLoad"
Cohesion: 0.18
Nodes (7): Carga pesos calibrados desde un archivo JSON.          Args:             path: R, Selecciona los pesos correspondientes a un grupo (hora + vol).          Args:, Path, Cuando el grupo exacto no existe, usa default., Cuando el grupo existe, retorna sus pesos., Ciclo completo: load → calibrate → export → load → select., TestExportLoad

### Community 53 - "__init__.py"
Cohesion: 0.17
Nodes (14): CandleSnapshot, GaleState, HubScanSnapshot, HubState, MasanielloState, Modelos del HUB para datos reales de STRAT-A., Resultado de un ciclo completo de escaneo., [DEPRECATED] Estado anterior del GaleWatcher. Use MasanielloState en su lugar. (+6 more)

### Community 54 - "Backtester"
Cohesion: 0.17
Nodes (6): Backtester, Path, Compare historical decision vs reevaluated signal.          Returns a dict wit, Generate a performance metrics report.          Only considers candidates with, Offline backtesting engine that replays strategies on historical data.      Us, TestLoadFromDB

### Community 55 - "test_hub_bankroll_store.py"
Cohesion: 0.18
Nodes (14): _hydrate_bankroll_from_web(), Fill bankroll unknowns from data/hub_bankroll.json (written by the hub)., apply_bankroll_shape_to_manager(), load_bankroll(), Any, Path, Persist hub bankroll settings across process restarts.  The bankroll fields in c, Push live config module ops/ITM onto manager when safe (no progress). (+6 more)

### Community 56 - "connection.py"
Cohesion: 0.18
Nodes (12): ConnectionManager, create_trading_client(), force_reconnect(), _force_reconnect_locked(), _handle_order_result(), place_order(), Quotex, WebSocket Quotex: conexión, velas y envío de órdenes. (+4 more)

### Community 57 - "load_schedule"
Cohesion: 0.20
Nodes (13): duration_min_to_sec(), load_schedule(), Any, Path, Persist hub schedule / auto-full settings across process restarts.  Schedule fie, Map user-facing minutes to order duration seconds (floor 60s)., save_schedule(), Path (+5 more)

### Community 58 - "HubScanner"
Cohesion: 0.13
Nodes (5): HubScanner, Any, Gestor de ciclos de escaneo y estado visible del HUB STRAT-F., Registra el resultado de un ciclo STRAT-F.          El bot (scanner.py) o el d, Devuelve el estado actual del HUB (lo usa server.py).

### Community 59 - "FilterSellOTC"
Cohesion: 0.21
Nodes (9): FilterSellOTC, OrderAck, Quotex, Filtro de activos OTC por payout y venta PUT en el mejor candidato., Tests de filter_and_sell_otc.py con mocks (sin broker)., test_list_candidates_filters_via_connection(), test_run_once_default_dry_run(), test_run_once_empty_candidates_returns_empty() (+1 more)

### Community 60 - "test_consolidation_bot.py"
Cohesion: 0.15
Nodes (7): ArgumentParser, _parser_option_strings(), Tests del facade consolidation_bot., HTF scanner follows hub min_payout (same floor as bankroll card)., R14: parse_args() declara y acepta --live, --real, --loop, --greylist., test_consolidation_bot_htf_scanner_uses_min_payout(), test_parse_args_legacy_cli_flags()

### Community 61 - "massaniello_is_terminal"
Cohesion: 0.21
Nodes (8): Protocol, massaniello_has_progress(), massaniello_is_terminal(), _MassanielloLike, Transition from STOPPED to SCANNING., Activate scanning when the user presses Iniciar / the process starts.          R, True when Massaniello no longer admits new entries for this cycle., True when the current cycle already recorded entries/results.

### Community 62 - "trade_journal.py"
Cohesion: 0.25
Nodes (11): build_calibration(), classify_skip(), print_calibration(), Reporte de calibracion STRAT-F.  Lee las decisiones STRAT-F del diario (trade_jo, trade_journal.py — Módulo de aprendizaje y registro histórico de trades =======, _feed(), Tests para calibration_report.py (reporte de calibracion STRAT-F)., test_build_calibration_groups_and_suggests() (+3 more)

### Community 63 - "Path"
Cohesion: 0.21
Nodes (6): Path, 3 WIN + 1 LOSS → win rate = 75%., 0.80 - 1.00 + 0.75 + 0.85 = $1.40., No resolved trades → friendly message., TestCompare, TestReport

### Community 64 - "stats.py"
Cohesion: 0.24
Nodes (12): api_blackbox(), Reporte de la caja negra STRAT-F (win_rate, ranking pérdidas, A/B estocástico)., build_stats(), main(), _parse_stoch(), Any, Estadísticas de la caja negra STRAT-F (Fase 5).  Lee scan_candidates de la caja, Formatea el dict a texto legible (consola / log). (+4 more)

### Community 65 - "Refactor Monolith (Feature #1)"
Cohesion: 0.29
Nodes (13): src/config.py (constants), src/connection.py (broker I/O), Discarded: subfolder monolith, src/executor.py (TradeExecutor), consolidation_bot.py facade, Refactor Monolith (Feature #1), main.py entrypoint, MartingaleCalculator (legacy) (+5 more)

### Community 66 - "._refresh_cycle"
Cohesion: 0.15
Nodes (7): get_black_box(), Obtiene instancia singleton del recorder., Loop principal del scanner HTF.         Diseñado para correr como asyncio.creat, Una ronda completa: recorre todos los activos y refresca si es necesario., True si el cache está vacío o venció el TTL., Fetch con timeout y semáforo propio. Devuelve [] en caso de fallo., Notifica refresh de un activo para telemetría externa (HUB).

### Community 67 - "StratFHubState"
Cohesion: 0.21
Nodes (7): Capa visible del HUB centrada en STRAT-F., Registra el resultado de un ciclo STRAT-F., Devuelve el estado STRAT-F actual (lo usa server.py / main.py)., StratFPanel, Estado completo del panel HUB STRAT-F para un ciclo., StratFHubState, test_state_defaults_empty()

### Community 68 - "TestReevaluate"
Cohesion: 0.17
Nodes (7): LogCaptureFixture, Momentum candles should produce a 'call' signal., Swing candles with upper wick should signal 'put'., Random small-body candles should NOT produce a reversal signal., Running reevaluate() without filter processes all strategies., Unknown strategy origins should be logged as warnings., TestReevaluate

### Community 69 - "_now"
Cohesion: 0.17
Nodes (5): _now(), Crea un registro de sesión y devuelve su id., Registra un candidato evaluado.          decision debe ser uno de:, Actualiza el resultado de una orden ya registrada.          outcome: "WIN" | ", Igual que update_outcome pero usando la clave primaria (id) de la fila.

### Community 70 - "spike_filter.py"
Cohesion: 0.23
Nodes (11): detect_spike_anomaly(), spike_filter.py =============== Filtro anti-spike para velas OTC con saltos an, Elimina velas anómalas de una serie OHLC manteniendo el orden temporal.      E, Diagnóstico de una vela anómala., Resultado del chequeo anti-spike., Estadísticas de saneamiento de una serie de velas., Detecta si hay vela anómala en las últimas N velas.      Reglas:     1) Gap r, sanitize_spike_candles() (+3 more)

### Community 71 - "app.py"
Cohesion: 0.18
Nodes (9): get_blackbox_trades(), _load_dotenv(), new_cycle(), QUOTEX Web App — FastAPI entry point.  Usage:     python app.py, Stop bot + close browser + kill server., Load .env before importing modules (config reads EMAIL at import time)., Get trade history from black box., Confirm and start a new trading cycle. (+1 more)

### Community 72 - "test_hub_strat_f.py"
Cohesion: 0.35
Nodes (9): HubLogParser, Parser del panel HUB para STRAT-F.  Lee la salida de ``progress/diag_strat_f_liv, Parsea lineas de log del diagnóstico STRAT-F al estado del panel., Tests para el nuevo HUB STRAT-F (modelo + parser + render).  Reemplaza tests/hub, _sample_log(), test_parser_reject_fields(), test_parser_separates_signals_and_skips(), test_parser_signal_fields() (+1 more)

### Community 73 - "STRAT-A OB Prefetch (Feature #21)"
Cohesion: 0.24
Nodes (11): CANDLE_FETCH_CONCURRENCY, Parallel Asset Scan (Feature #3), fetch_candles_parallel (src/parallel_fetch.py), scanner.py prefetch changes, STRAT-A OB Prefetch — Requirements, STRAT-A OB Prefetch — Tasks, ScanCycleData.blocks_by_symbol, candle_cache.py OB cache (+3 more)

### Community 74 - "STRAT-A Quality Filters Feature (id=19)"
Cohesion: 0.29
Nodes (11): STRAT-A Quality Filters — Design, STRAT-A Quality Filters — Requirements, STRAT-A Quality Filters — Tasks, STRAT-A Test Suite — Design, STRAT-A Test Suite — Requirements, STRAT-A Test Suite — Tasks, STRAT-A Evaluate (Feature #17), STRAT-A Quality Constants (MIN_PAYOUT/SCORE/ZONE_AGE) (+3 more)

### Community 75 - "journal_performance_report.py"
Cohesion: 0.36
Nodes (10): fetch_rows(), latest_journal_db(), main(), outcome_counts(), Any, Connection, Path, Row (+2 more)

### Community 76 - "detect_momentum_1m"
Cohesion: 0.33
Nodes (9): detect_momentum_1m(), Estrategia momentum 1m: cuerpo grande + cierre en tercio extremo., Detecta momentum en la última vela 1m.      Returns:         (direction, strengt, _base_candles(), Tests de strat_momentum.py., test_momentum_detect_bearish(), test_momentum_detect_bullish(), test_momentum_detect_no_signal_small_body() (+1 more)

### Community 77 - "HubEventBus"
Cohesion: 0.24
Nodes (4): HubEventBus, Event bus for real-time hub updates., In-process pub/sub. Safe to call from sync or async code., Queue

### Community 78 - "CandidateData"
Cohesion: 0.20
Nodes (7): CandidateData, _normalize_direction(), Any, Candidato normalizado para renderizar en el HUB., Valor único para ordenar candidatos en el HUB., Construye candidato STRAT-A desde payload real del bot., _utc_now()

### Community 79 - "main.py"
Cohesion: 0.29
Nodes (9): _apply_runtime_config(), _build_parser(), _load_dotenv(), ArgumentParser, Namespace, Parsea el log y dibuja el panel HUB STRAT-F en la terminal.      El panel nuev, Carga .env antes de importar módulos src (config lee EMAIL al importar)., _render_hub_once() (+1 more)

### Community 80 - "massaniello_risk.py"
Cohesion: 0.20
Nodes (5): Persistencia de sesión Massaniello en SQLite., Gestión de sesión Massaniello para el bot Quotex., Ops/ITM from hub config must drive real MassanielloRiskManager stakes., test_manager_reads_live_config_not_import_defaults(), test_manager_stake_changes_when_ops_itm_change()

### Community 81 - "create_client"
Cohesion: 0.31
Nodes (9): create_client(), get_practice_balance(), load_credentials_from_env(), Path, Quotex, QuotexCredentials, Load QUOTEX_EMAIL/QUOTEX_PASSWORD from .env or process environment., Create Quotex client using credentials loaded from .env. (+1 more)

### Community 82 - ".calibrate"
Cohesion: 0.27
Nodes (5): Any, Calcula thresholds de volatilidad (percentiles 33 y 66)., Recomputa el score total con nuevos pesos., Grid search sobre combinaciones de pesos.          Varía cada componente en [-ST, Ejecuta la calibración completa sobre self.trades.          Agrupa por (hour_buc

### Community 83 - "STRAT-A HTF Zone Wiring (Feature #20)"
Cohesion: 0.24
Nodes (10): evaluate_strat_a(), PendingReversalHint (no mutation), Scanner delegates to evaluate_strat_a, StratAEvaluation dataclass, entry_scorer trend 15m, STRAT-A HTF Zone Wiring (Feature #20), Scanner HTF + zone_memory gates, HTFScanner 15m background (+2 more)

### Community 84 - "test_strat_f_golive.py"
Cohesion: 0.29
Nodes (9): _fake_candidate(), _make_scanner_with_batch(), Tests de go-live STRAT-F: GAP G1 (panel en vivo) + GAP G2 (STRAT_F_ONLY).  Verif, Armado minimo de AssetScanner solo para ejercitar _flush_strat_f_panel., scan_all con STRAT_F_ONLY=True solo opera STRAT-F (no STRAT-A)., test_flush_fills_bot_panel(), test_flush_no_batch_is_noop(), test_scan_all_respects_strat_f_only() (+1 more)

### Community 85 - "QualityAssetLibrary"
Cohesion: 0.25
Nodes (3): QualityAssetLibrary, Biblioteca dinámica de activos elegibles por payout., Lista de activos en biblioteca, ordenados por payout desc.

### Community 86 - "._reevaluate_strat_a"
Cohesion: 0.25
Nodes (5): Any, Replay strategies on every loaded candidate.          If *strategies* is given, Marca un candidato STRAT-F como re-evaluado.          STRAT-F necesita 3 tempo, Re-evaluate a STRAT-A candidate.          Attempts to reconstruct ``Consolidat, Load candidates from ``candidates`` table within the given day range.

### Community 87 - "strat_f_postmortem.py"
Cohesion: 0.36
Nodes (8): analyze_postmortem(), _as_candles(), _best_reversal_in_window(), Any, Post-mortem automático STRAT-F (Fase 4).  Dado el snapshot ANTES (velas 1m al en, Busca el patrón de reversión más fuerte en la ventana post-cierre., Devuelve (loss_reason, improvement_hint).      Para WIN/UNRESOLVED: loss_reason, _to_candle()

### Community 88 - "test_fase4_postmortem.py"
Cohesion: 0.36
Nodes (7): _c1m(), Tests de Fase 4 — post-mortem STRAT-F + cierre de candidato en caja negra.  Veri, test_loss_with_opposite_reversal_gives_direccion_equivocada(), test_loss_with_same_direction_reversal_gives_entro_temprano(), test_loss_without_reversal_gives_rango_sin_reversion(), test_recorder_resolve_by_id_exact(), test_recorder_resolve_pending_candidate()

### Community 89 - "black_box_recorder.py"
Cohesion: 0.25
Nodes (4): BLACK BOX RECORDER - Captura completa de estrategias A, B, C ==================, Tests de la caja negra STRAT-F (Fase 1): esquema extendido + grabación.  Usa una, Correr _init_db dos veces no rompe ni duplica columnas., test_migration_idempotent_on_existing_db()

### Community 91 - "executor.py"
Cohesion: 0.29
Nodes (4): Connection, main(), Diag STRAT-F: mide el SCORE FINAL que usa el bot (score_candidate) con datos rea, Ejecución de órdenes, martingala y gestión de ciclo.

### Community 92 - "render.py"
Cohesion: 0.57
Nodes (6): _bar(), _plain(), Renderer del panel HUB para STRAT-F.  Dibuja el resultado de un ciclo: aceptadas, render_dashboard(), _rich(), _shorten()

### Community 93 - "trader_short.py"
Cohesion: 0.43
Nodes (6): _build_candidate(), _eval_one(), main(), Trader corto STRAT-F (sortea el host-kill del sandbox).  Hace UN ciclo compacto, Marca WIN/LOSS de las PENDING de hoy consultando get_result., _reconcile()

### Community 94 - "htf_scanner.py"
Cohesion: 0.29
Nodes (4): AssetBook, asset_library.py ================ Biblioteca de activos de calidad ("libros"), Refresca la biblioteca desde la foto actual de activos elegibles.          Par, htf_scanner.py ============== Scanner de temporalidad alta (15 minutos) que co

### Community 95 - "._ensure_schema_upgrades"
Cohesion: 0.29
Nodes (3): Path, Exporta la tabla candidates a CSV para análisis externo., Aplica migraciones suaves para bases existentes.

### Community 96 - "TestStratFRecognition"
Cohesion: 0.29
Nodes (4): R7 — el backtester reconoce STRAT-F (rama dedicada)., R7 — reevaluate procesa STRAT-F usando strategy_json., R8 — el reporte incluye las metricas de las señales STRAT-F resueltas., TestStratFRecognition

### Community 97 - "test_strat_f_journal.py"
Cohesion: 0.57
Nodes (6): Tests para el diario/calibracion STRAT-F en trade_journal.py.  Cubre: grabacion, _strat_f_entry(), test_log_candidate_strat_f_accepted(), test_log_candidate_strat_f_rejected_with_zone_none(), test_query_and_report_strat_f(), _tmp_journal()

### Community 98 - "_WebLogHandler"
Cohesion: 0.33
Nodes (5): Captures log records into ring buffer + pushes to WebSocket subscribers., Add web log handler to consolidation_bot + black_box_recorder loggers., _setup_web_logging(), _WebLogHandler, LogRecord

### Community 99 - "diag_strat_f_live.py"
Cohesion: 0.40
Nodes (5): _feed_journal(), main(), Diagnóstico STRAT-F en vivo (solo lectura).  Conecta a demo, baja 15m/5m/1m de u, Graba una decision STRAT-F en el diario (trade_journal.db)., get_journal()

### Community 100 - ".apply_weights"
Cohesion: 0.40
Nodes (3): Sobrescribe los pesos globales en entry_scorer.          Llámese al inicio del b, Después de aplicar, los dicts tienen las mismas keys., TestApplyWeights

### Community 101 - "test_fase3_scanner_blackbox.py"
Cohesion: 0.53
Nodes (5): _fake_eval(), _make_cycle(), _make_self(), Test de Fase 3 — cableado STRAT-F -> caja negra en scanner.py.  Verifica que, en, test_scan_records_accepted_and_rejected_in_black_box()

### Community 102 - "test_fase5_stats.py"
Cohesion: 0.47
Nodes (4): Tests de Fase 5 — stats.py lee la caja negra y calcula métricas.  Usa una DB tem, _seed(), test_build_stats_aggregates_correctly(), test_render_report_includes_sections()

### Community 103 - "lifespan"
Cohesion: 0.40
Nodes (5): _event_relay(), lifespan(), Poll bot state and push to WebSocket clients every 0.8s., Relay hub events to WebSocket clients., _state_poller()

### Community 104 - "update_config"
Cohesion: 0.40
Nodes (5): get_config(), Any, Get current bot configuration., Update bot configuration (only when bot is stopped)., update_config()

### Community 105 - "strat_support.py"
Cohesion: 0.40
Nodes (4): DataFrame, candles_to_dataframe(), find_strong_support_2m(), Utilidades compartidas de análisis de velas (soporte fuerte 2m, conversión a Dat

### Community 107 - "loop_utils.py"
Cohesion: 0.40
Nodes (3): Utilidades de temporización del loop principal., Sleep with countdown. Returns True if aborted early via should_abort()., sleep_with_inline_countdown()

### Community 108 - "enviar_orden"
Cohesion: 0.40
Nodes (4): enviar_orden(), Any, Envío simple y robusto de órdenes OTC a QUOTEX.  Extrae la lógica que ya comprob, Envía UNA orden OTC y devuelve (ok, info).      `direction` debe ser "call" (com

### Community 109 - ".query_strat_f"
Cohesion: 0.40
Nodes (3): Row, Devuelve los candidatos con strategy_origin='STRAT-F'., Imprime diario + métricas de calibración de STRAT-F.

### Community 110 - "._row_to_trade"
Cohesion: 0.40
Nodes (3): Row, Carga trades históricos con outcome WIN/LOSS desde la BD.          Retorna la ca, Convierte una fila de la BD a un dict interno para calibración.

### Community 111 - "TestNoBrokerIO"
Cohesion: 0.40
Nodes (3): The full load → reevaluate → compare → report cycle runs         without network, backtester must not import pyquotex or similar broker libs., TestNoBrokerIO

### Community 112 - "TestIntegration"
Cohesion: 0.40
Nodes (3): Todos los pesos en default y by_group suman 100., weight_calibrator must not import pyquotex or broker libs., TestIntegration

### Community 113 - "bot_start"
Cohesion: 0.50
Nodes (4): bot_start(), _connect_hub_after_start(), Start the trading bot., Wait for bot to be running, then connect hub scanner.

### Community 115 - "parse_strat_a_session.py"
Cohesion: 0.67
Nodes (3): load_session(), main(), Parse STRAT-A live validation session from consolidation_bot.log.

### Community 117 - "fix_indent.py"
Cohesion: 0.50
Nodes (3): fix_module(), Path, Corrige indentación de métodos sueltos en executor.py y scanner.py.

### Community 122 - "ws_logs"
Cohesion: 0.67
Nodes (3): WebSocket endpoint for real-time log streaming., ws_logs(), WebSocket

## Knowledge Gaps
- **48 isolated node(s):** `engram`, `CLAUDE.md — Instrucciones para Claude (rol leader)`, `skill-registry.md — Registry de skills (Gentle AI)`, `hub/static/index.html — Dashboard HUB (frontend)`, `progress/current.md — Plantilla sesión actual` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **43 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Candle` connect `Candle` to `evaluate_strat_f`, `smc_analysis.py`, `test_scanner_strat_a.py`, `models.py`, `entry_decision_engine.py`, `AssetScanner`, `CandleCache`, `scan_prefetch.py`, `ConsolidationZone`, `CandidateEntry`, `.refresh_from_candidate`, `test_stochastic_m15.py`, `test_strat_reversal_swing.py`, `scanner.py`, `BreakerOrderBlockDetector`, `fetch_candles_with_retry`, `zone_memory.py`, `._scan_phase_evaluate_assets`, `test_htf_zone_wiring.py`, `Backtester`, `connection.py`, `Path`, `TestReevaluate`, `spike_filter.py`, `detect_momentum_1m`, `._reevaluate_strat_a`, `strat_f_postmortem.py`, `TestStratFRecognition`, `strat_support.py`, `TestNoBrokerIO`?**
  _High betweenness centrality (0.148) - this node is a cross-community bridge._
- **Why does `TradeExecutor` connect `TradeExecutor` to `scanner.py`, `consolidation_bot.py`, `SessionManager`, `AssetScanner`, `BotRunner`, `executor.py`, `MassanielloRiskManager`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `AssetScanner` connect `AssetScanner` to `TradeExecutor`, `scanner.py`, `test_scanner_strat_a.py`, `Candle`, `models.py`, `._scan_phase_evaluate_assets`, `test_htf_zone_wiring.py`, `ConsolidationZone`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 60 inferred relationships involving `Candle` (e.g. with `Backtester` and `.load_from_db()`) actually correct?**
  _`Candle` has 60 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `MassanielloRiskManager` (e.g. with `reset_session()` and `_WebLogHandler`) actually correct?**
  _`MassanielloRiskManager` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `AssetScanner` (e.g. with `StratFReject` and `StratFRow`) actually correct?**
  _`AssetScanner` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `TradeExecutor` (e.g. with `BotRunner` and `ConsolidationBot`) actually correct?**
  _`TradeExecutor` has 15 INFERRED edges - model-reasoned connections that need verification._