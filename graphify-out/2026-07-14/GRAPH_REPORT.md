# Graph Report - .  (2026-07-14)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2434 nodes · 4949 edges · 152 communities (114 shown, 38 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 710 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a654fc01`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- StratFHubState
- test_scanner_strat_a.py
- evaluate_strat_f
- smc_analysis.py
- Connection
- _pre_validate_entry (gate de riesgo)
- TelegramAlerter
- consolidation_bot.py — Bot de consolidación (facade)
- Implement Missing Modules — Design
- massaniello_engine.py
- MassanielloPersistence
- GaleWatcher
- SessionManager
- BlackBoxRecorder
- Design hub_live_websocket
- entry_decision_engine.py
- MartingaleCalculator
- app.py
- DiversificationEnforcer
- AssetScanner
- MassanielloRiskManager
- CandleCache
- strat_a.py
- ConsolidationBot
- config.py
- scan_prefetch.py
- ObservableCandleFetcher
- CandidateEntry
- evaluate_strat_a
- __init__.py
- server.py
- Candle
- BotRunner
- .refresh_from_candidate
- test_stochastic_m15.py
- test_strat_reversal_swing.py
- EntrySynchronizer
- OrderBlock
- ConsolidationZone
- strat_a_radar.py
- test_backtester.py
- TradeExecutor
- BreakerOrderBlockDetector
- fetch_candles_with_retry
- zone_memory.py
- __init__.py
- Journal
- bot_logging.py
- MassanielloRiskManager (src/massaniello_risk.py)
- session_manager.py
- Common Scanner / Scoring Pipeline
- test_weight_calibrator.py
- WeightCalibrator
- test_htf_zone_wiring.py
- TestHelpers
- TestExportLoad
- Backtester
- ._resolve_trade
- HTFScanner
- FilterSellOTC
- test_consolidation_bot.py
- trade_journal.py
- Path
- stats.py
- Refactor Monolith (Feature #1)
- .enter_trade
- TestReevaluate
- connection.py
- _now
- spike_filter.py
- scanner.py
- STRAT-A OB Prefetch (Feature #21)
- STRAT-A Quality Filters Feature (id=19)
- ._interpret_broker_result
- ._refresh_cycle
- journal_performance_report.py
- detect_momentum_1m
- HubEventBus
- autopilot.py
- create_client
- .calibrate
- STRAT-A HTF Zone Wiring (Feature #20)
- QualityAssetLibrary
- ._reevaluate_strat_a
- get_black_box
- review_expired_zones.py
- FakeBot
- analyze_trades.py
- trader_short.py
- htf_scanner.py
- PipelineMetrics
- ._ensure_schema_upgrades
- TestStratFRecognition
- test_strat_f_journal.py
- _WebLogHandler
- diag_strat_f_live.py
- .apply_weights
- test_black_box_stratf.py
- test_fase3_scanner_blackbox.py
- test_fase5_stats.py
- test_session_lifecycle.py
- update_config
- strat_support.py
- extract_modules.py
- enviar_orden
- .query_strat_f
- ._row_to_trade
- TestNoBrokerIO
- TestIntegration
- parse_strat_a_session.py
- build_executor_scanner.py
- fix_indent.py
- ._track_task
- .cache_age_sec
- ._resolve_assets
- .export_weights
- engram
- deep_analysis.py
- reindent_class.py
- .conn
- count_trades.py
- EntryCategory
- EntryDecision
- .pause
- trading_workflow.py
- conftest.py
- skill-registry.md — Registry de skills (Gentle AI)
- CandidateEntry
- Candle
- ConsolidationZone
- HubScanner
- Path
- progress/current.md — Plantilla sesión actual
- Quotex
- ScanCycleData
- Hub Live WebSocket — Placeholder
- Namespace
- Connection
- str
- Any
- DataFrame
- Any
- DataFrame
- Task
- ArgumentParser
- WebSocket

## God Nodes (most connected - your core abstractions)
1. `Candle` - 217 edges
2. `MassanielloRiskManager` - 65 edges
3. `AssetScanner` - 65 edges
4. `TradeExecutor` - 62 edges
5. `ConsolidationZone` - 55 edges
6. `WeightCalibrator` - 44 edges
7. `Backtester` - 40 edges
8. `SessionManager` - 40 edges
9. `CandidateEntry` - 36 edges
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

## Communities (152 total, 38 thin omitted)

### Community 0 - "StratFHubState"
Cohesion: 0.05
Nodes (56): HubScanner, Any, Lógica de estado del HUB STRAT-F.  Reemplaza hub_scanner.py viejo (orientado a, Gestor de ciclos de escaneo y estado visible del HUB STRAT-F., Registra el resultado de un ciclo STRAT-F.          El bot (scanner.py) o el d, Devuelve el estado actual del HUB (lo usa server.py)., HubLogParser, Parser del panel HUB para STRAT-F.  Lee la salida de ``progress/diag_strat_f_liv (+48 more)

### Community 1 - "test_scanner_strat_a.py"
Cohesion: 0.08
Nodes (64): CandleSignal, PendingReversal, Datos prefetched para un ciclo de escaneo., ScanCycleData, ScanResult, analyze_postmortem(), _as_candles(), _best_reversal_in_window() (+56 more)

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

### Community 6 - "TelegramAlerter"
Cohesion: 0.05
Nodes (46): Exception, Alertas a Telegram para eventos del bot vía Bot API., Alerta: conexión perdida con el broker (R6)., Alerta: stop-loss de sesión activado (R7)., Envía mensajes a un chat de Telegram vía Bot API.      Lee TELEGRAM_BOT_TOKEN y, Check cooldown for event_type. Updates timestamp if allowed., Send a raw text message to Telegram.          Args:             text: Message te, Alerta: sesión Massaniello cumplida (R4). (+38 more)

### Community 7 - "consolidation_bot.py — Bot de consolidación (facade)"
Cohesion: 0.08
Nodes (55): AGENTS.md — Mapa de navegación para agentes, alerter.py — Alertas Telegram, backtester.py — Motor de backtesting, candle_cache.py — Caché local de velas, CHECKPOINTS.md — Evaluación del estado final, CLAUDE.md — Instrucciones para Claude (rol leader), implementer.md — Agente Implementador, leader.md — Agente Líder (Orquestador) (+47 more)

### Community 8 - "Implement Missing Modules — Design"
Cohesion: 0.06
Nodes (49): Backtesting Engine — Design, Backtester (src/backtester.py), Decision: pandas descartado en backtester, Performance Metrics (Sharpe, Drawdown, Win Rate), trade_journal.Journal (shared DB dependency), Backtesting Engine — Requirements, Backtesting Engine — Tasks, Candle Cache — Design (+41 more)

### Community 9 - "massaniello_engine.py"
Cohesion: 0.09
Nodes (41): massaniello_preview(), Next-stake preview using the same Massaniello formula as the bot.      Query o, Result, Settings, BetRow, calculate_balance_objective(), calculate_stake(), effective_profit() (+33 more)

### Community 10 - "MassanielloPersistence"
Cohesion: 0.07
Nodes (25): Journal, MassanielloPersistence, Persistencia de sesión Massaniello en SQLite., Valida tipos y rangos básicos. Retorna state limpio o None., Guarda y recupera el estado de MassanielloRiskManager en SQLite., INSERT del estado actual de *manager* en massaniello_state.          Devuelve, SELECT de la última fila de massaniello_state.          Retorna dict con la fi, Restaura campos de *manager* desde *state*.          No modifica si el estado (+17 more)

### Community 11 - "GaleWatcher"
Cohesion: 0.08
Nodes (24): FetchPriceFn, GetBalanceFn, mg/ — Motor de Gale (Martingale Engine)  Módulo independiente que vigila opera, GaleWatcher, mg/mg_watcher.py — GaleWatcher  Vigila una operación binaria abierta de 5 minu, Información de la operación activa que el watcher vigila., True si el precio actual implica que la operación va perdiendo., Texto corto de P/L: dirección, variación de precio e implicancia. (+16 more)

### Community 12 - "SessionManager"
Cohesion: 0.07
Nodes (17): _get_event_bus(), Any, Transition from STOPPED to SCANNING., Transition to STOPPED from any state., Transition from SCANNING to TRADING., Transition from TRADING back to SCANNING., Mark session as completed (meta ITM / failed / timeout / exhausted).          Em, User confirmed they want a new cycle.          Transitions: COMPLETED → RESETTIN (+9 more)

### Community 13 - "BlackBoxRecorder"
Cohesion: 0.07
Nodes (22): BlackBoxRecorder, Any, Registra TODA la actividad de las estrategias., Crea tablas si no existen., Elimina archivos DB y JSONL de caja negra con más de RETENTION_DAYS., Registra el inicio de un escaneo. Retorna scan_id., Registra un candidato escaneado y retorna su id., Actualiza un candidato existente con estado posterior al escaneo. (+14 more)

### Community 14 - "Design hub_live_websocket"
Cohesion: 0.07
Nodes (39): Arquitectura y estándar de calidad, Qué NO hacer (anti-patrones), Flujo de datos HFT, Cuatro capas (Conexión/Análisis/Estrategias/Ejecución), Gestión de riesgo (estado actual), Estado transaccional en SQLite, Separación estrategia-ejecución, Convenciones de código (+31 more)

### Community 15 - "entry_decision_engine.py"
Cohesion: 0.09
Nodes (37): apply_category_logic(), _check_candles_available(), _check_cycle_limit(), _check_htf_available_and_aligned(), _check_no_active_trade(), _check_pattern_confirmed(), _check_payout_minimum(), _check_score_minimum() (+29 more)

### Community 16 - "MartingaleCalculator"
Cohesion: 0.09
Nodes (19): MartingaleCalculator, Martingale Calculator para Opciones Binarias. Reemplica la lógica de la calcula, Calcula el objetivo de ciclo para un balance dado (sin mutar estado)., Redondea hacia arriba a centavos., Calcula el monto a invertir para alcanzar el objetivo.          Args:, Calcula inversión para un balance proyectado sin mutar el estado interno., Calculadora de Martingale para ciclos de trading con incremento fijo., Registra ganancia y cierra ciclo.         El saldo se ajusta EXACTAMENTE al obj (+11 more)

### Community 17 - "app.py"
Cohesion: 0.06
Nodes (34): bot_start(), bot_status(), bot_stop(), _connect_hub_after_start(), _event_relay(), get_logs(), health(), lifespan() (+26 more)

### Community 18 - "DiversificationEnforcer"
Cohesion: 0.10
Nodes (32): DiversificationEnforcer, diversification_enforcer.py — Rechaza entradas que violan límites de diversifica, Valida que una nueva entrada no viole los límites de diversificación., Verifica si se permite una entrada para ``candidate_asset``.          Parameters, _make_trade(), Tests de diversification_enforcer.py., Permite entrada en otro activo aunque el máximo por activo se alcanzó., El mensaje de rechazo incluye activo y límite violado. (+24 more)

### Community 19 - "AssetScanner"
Cohesion: 0.11
Nodes (11): AssetScanner, Any, Path, Task, Vuelca el batch STRAT-F al panel del HUB (go-live G1).          Mapea las deci, FASE 4/5 y 5/5 — pending reversals, selección y ejecución., Envía la orden para un candidato y devuelve True si el broker la aceptó., Escanea todos los activos, puntúa cada candidato con el sensor         matemáti (+3 more)

### Community 20 - "MassanielloRiskManager"
Cohesion: 0.11
Nodes (17): _get_event_bus(), MassanielloRiskManager, Any, Gestión de sesión Massaniello para el bot Quotex., Wrapper de sesión Massaniello (ops / ITM / límite temporal).      Ops/ITM se l, Ops/ITM from hub config must drive real MassanielloRiskManager stakes., test_manager_reads_live_config_not_import_defaults(), test_manager_stake_changes_when_ops_itm_change() (+9 more)

### Community 21 - "CandleCache"
Cohesion: 0.10
Nodes (19): CacheKey, Lock, _CacheEntry, CandleCache, Any, Caché en memoria de velas con actualización incremental., Elimina entradas expiradas. Devuelve cantidad purgada., Caché asyncio-safe: clave (asset, tf_sec) → velas ordenadas por ts. (+11 more)

### Community 22 - "strat_a.py"
Cohesion: 0.11
Nodes (30): MAState, avg_body(), _block_distance(), broke_above(), broke_below(), _clamp(), compute_atr(), compute_dynamic_range() (+22 more)

### Community 23 - "ConsolidationBot"
Cohesion: 0.10
Nodes (15): Namespace, ConnectionManager, ConsolidationBot, _extract_candidates_for_hub(), main(), parse_args(), Quotex, consolidation_bot.py — Facade del bot de consolidación Quotex. (+7 more)

### Community 24 - "config.py"
Cohesion: 0.10
Nodes (21): main(), Comparar métodos de fetch de velas pyquotex., main(), Test new HistoryMixin candle APIs., main(), Poll candle count after get_candles request., main(), Prueba aislada: una sola vela fetch con delays. (+13 more)

### Community 25 - "scan_prefetch.py"
Cohesion: 0.12
Nodes (25): Semaphore, decrement_failed_assets(), _fetch_with_optional_stagger(), filter_scan_assets(), prefetch_primary_candles(), prefetch_strat_a_secondary(), Any, Orquestación de prefetch para ciclos de escaneo. (+17 more)

### Community 26 - "ObservableCandleFetcher"
Cohesion: 0.11
Nodes (15): CandleFetchResult, ConnectionState, FetchMetrics, ObservableCandleFetcher, Any, candle_fetcher_observable.py ============================  Capa de observabil, Obtiene estado actual de la conexión., Fetch con observabilidad + retry controlado para empty arrays. (+7 more)

### Community 27 - "CandidateEntry"
Cohesion: 0.13
Nodes (26): _age_adjustment(), _clamp(), detect_swing_levels(), _ema(), explain_score(), _normalize(), Componente REBOUND: mide calidad de mecha en el extremo y momentum de velas reci, Componente BREAKOUT: mide fuerza de la vela de ruptura vs historial.     Interp (+18 more)

### Community 28 - "evaluate_strat_a"
Cohesion: 0.25
Nodes (25): CandleSignal, evaluate_strat_a(), Evalúa señal STRAT-A sin I/O., validate_rejection_candle(), _base_5m_history(), Tests unitarios de strat_a (lógica pura)., R3: evaluate_strat_a sin I/O de red ni archivos., test_evaluate_strat_a_breakout_above_with_volume() (+17 more)

### Community 29 - "__init__.py"
Cohesion: 0.10
Nodes (21): CandidateData, CandleSnapshot, GaleState, HubScanSnapshot, HubState, MasanielloState, _normalize_direction(), Any (+13 more)

### Community 30 - "server.py"
Cohesion: 0.13
Nodes (23): api_state(), api_strat_f(), _auto_open_dashboard(), _broadcast(), _build_snapshot(), _close_browser(), _enrich_with_bot(), _event_relay() (+15 more)

### Community 31 - "Candle"
Cohesion: 0.22
Nodes (22): _body(), _body_high_zone(), _body_low_zone(), _body_pct(), detect_reversal_pattern(), _engulfs(), explain_no_pattern_reason(), fetch_candles_1m() (+14 more)

### Community 32 - "BotRunner"
Cohesion: 0.12
Nodes (10): BotRunner, Any, Gestiona el lifecycle del bot: start / stop / status.      Diseñado para ser l, Push _config values into the config module so imports see updated values., Push config changes to the live bot instance (hot-reload)., User confirmed they want a new cycle., User declined new cycle., Get current session status. (+2 more)

### Community 33 - ".refresh_from_candidate"
Cohesion: 0.16
Nodes (14): Ventana VIP para candidatos casi listos para entrada., VipWindowData, _candles_tail(), _ema(), _ma_pair(), Any, vip_library.py ============== Biblioteca VIP de candidatos casi listos para en, Biblioteca de ventanas VIP, actualizada con cada candidato evaluado. (+6 more)

### Community 34 - "test_stochastic_m15.py"
Cohesion: 0.18
Nodes (22): _candles_to_ohlcv(), compute_stoch(), _detect_divergence(), Any, Estocástico M15 para STRAT-F — capa fina sobre pyquotex.  REUTILIZA la implement, Detecta divergencia precio vs %K en la ventana reciente.      bull: precio hace, Extrae close/high/low/open de una secuencia de Candle., Calcula el estocástico M15 (Slow/Full 14,3) + derivados.      Args:         cand (+14 more)

### Community 35 - "test_strat_reversal_swing.py"
Cohesion: 0.13
Nodes (22): detect_reversal_swing(), Estrategia reversal swing: reversión en niveles dinámicos de soporte/resistencia, Detecta reversión en niveles de soporte/resistencia dinámicos (swing highs/lows), _base_candles(), _candles_with_swing_high(), _candles_with_swing_low(), Tests de strat_reversal_swing.py., R2: vela toca swing low con mecha inferior → señal CALL. (+14 more)

### Community 36 - "EntrySynchronizer"
Cohesion: 0.13
Nodes (15): EntrySynchronizer, Sincronización precisa de entradas con apertura de vela 1m., Telemetría por orden: time_since_open y secs_to_close., Calcula y valida timing de entrada respecto al open de vela 1m., Evalúa timing puro respecto a un open de vela conocido.          Args:, Espera al próximo open de vela 1m y valida que el envío no llegue tarde., Delega sincronización y validación de timing al EntrySynchronizer., EntryTimingInfo (+7 more)

### Community 37 - "OrderBlock"
Cohesion: 0.16
Nodes (21): OrderBlock, detect_order_blocks(), _calc_strength(), detect_order_block_entry(), _is_mitigated_design(), _price_revisits(), Estrategia Order Block 1m: detección de OBs y entry por revisita al rango., Calcula fuerza normalizada de la señal OB en [0, 1].      Usa el cuerpo de la ve (+13 more)

### Community 38 - "ConsolidationZone"
Cohesion: 0.16
Nodes (7): PendingReversalHint, RadarWatchEntry, ConsolidationZone, FASE 3/5 — MOMENTUM y STRAT-A sin I/O de red., Tick 1m sobre pares en watchlist. Devuelve True si se intentó entrada., Veto HTF 15m y muro zone_memory antes de crear candidato STRAT-A.          Ret, StratAEvaluation

### Community 39 - "strat_a_radar.py"
Cohesion: 0.13
Nodes (19): _age_ratio_ok(), _clamp(), compute_readiness(), RadarWatchEntry, rank_and_trim(), STRAT-A hunter radar: watchlist de zonas casi listas (coarse → fine)., Puntuación 0–100: proximidad al extremo, madurez, compresión, payout., Ordena por readiness y conserva solo top-N por encima del umbral. (+11 more)

### Community 40 - "test_backtester.py"
Cohesion: 0.13
Nodes (19): Backtester — offline strategy replay engine.  Re-evaluates historical signals, _create_db(), db_empty(), db_known_metrics(), db_mixed(), db_strat_f(), _momentum_candles(), Any (+11 more)

### Community 41 - "TradeExecutor"
Cohesion: 0.11
Nodes (5): Crea un trade_client FRESCO antes de cada orden.          Fix definitivo: pyqu, Fallback liviano: limpia trades ya resueltos o dispara resolución si         la, Limita la sobre-repetición del mismo activo.         Nota: martingala queda exe, Snapshot de parámetros activos para auditoría de caja negra., TradeExecutor

### Community 42 - "BreakerOrderBlockDetector"
Cohesion: 0.22
Nodes (8): BoBPhase, BoBResult, BoBSetup, BoBState, BreakerOrderBlockDetector, Enum, str, Detector BoB por fases: setup -> retest -> confirmation.      Este detector NO

### Community 43 - "fetch_candles_with_retry"
Cohesion: 0.16
Nodes (18): _candles_from_raw(), fetch_candles(), fetch_candles_with_retry(), looks_like_connection_issue(), _min_expected_candles(), raw_to_candle(), Tests de connection.py con mocks (sin broker real)., test_fetch_candles_fallback_to_historical() (+10 more)

### Community 44 - "zone_memory.py"
Cohesion: 0.14
Nodes (17): EntryContext, Contexto opcional para evaluación de entrada., _classify_role(), _decay(), HistoricalZone, Path, query_nearby_zones(), zone_memory.py ============== Módulo de memoria de zonas históricas de consoli (+9 more)

### Community 45 - "__init__.py"
Cohesion: 0.33
Nodes (12): Enum, RoutedSignal, RouterSnapshot, SignalPhase, StrategyName, StrategySignal, render_control_center(), _default_config() (+4 more)

### Community 46 - "Journal"
Cohesion: 0.11
Nodes (9): Journal, Connection, Muestra los últimos N candidatos rechazados con detalle., Interfaz principal del módulo de aprendizaje., Actualiza auditoría de timing para un candidato ya registrado., Registra una zona que fue descartada.          expiry_reason: TIME_LIMIT | BRO, Muestra las últimas N zonas expiradas con diagnóstico., Actualiza trazabilidad de ticket para una fila de candidato. (+1 more)

### Community 47 - "bot_logging.py"
Cohesion: 0.14
Nodes (15): Counter, Logger, asset_detail(), format_reject_summary(), is_verbose(), Any, Logging helpers — keep console signal-to-noise high.  Normal mode (default): cyc, Per-asset chatter: INFO only when verbose, else DEBUG. (+7 more)

### Community 48 - "MassanielloRiskManager (src/massaniello_risk.py)"
Cohesion: 0.14
Nodes (17): Kelly integration in consolidation_bot.py, Discarded: per-asset Kelly, Kelly Criterion Sizing (Feature), KellySizer (src/kelly_sizer.py), Kelly x Massaniello _initial_capital, Kelly reads candidates table, Discarded: JSON file persistence, Persistence save in executor.py (+9 more)

### Community 49 - "session_manager.py"
Cohesion: 0.18
Nodes (10): Protocol, massaniello_has_progress(), massaniello_is_terminal(), _MassanielloLike, Enum, Session lifecycle manager for the Quotex trading bot.  Manages the state machine, Activate scanning when the user presses Iniciar / the process starts.          R, True when Massaniello no longer admits new entries for this cycle. (+2 more)

### Community 50 - "Common Scanner / Scoring Pipeline"
Cohesion: 0.18
Nodes (18): Common Scanner / Scoring Pipeline, Momentum 1m — Design, Momentum 1m — Requirements, Momentum 1m — Tasks, Order Block — Design, Order Block — Requirements, Order Block — Tasks, Reversal Swing — Design (+10 more)

### Community 51 - "test_weight_calibrator.py"
Cohesion: 0.16
Nodes (16): weight_calibrator.py — Calibración dinámica de pesos del entry_scorer. =========, calibrator_empty(), calibrator_minimal(), calibrator_with_trades(), _candles_with_volatility(), _create_in_memory_db(), _populate_db(), Any (+8 more)

### Community 52 - "WeightCalibrator"
Cohesion: 0.18
Nodes (5): Connection, Calibra pesos del entry_scorer usando datos históricos de trades.      Proceso:, WeightCalibrator, TestCalibrate, TestLoadTrades

### Community 53 - "test_htf_zone_wiring.py"
Cohesion: 0.27
Nodes (15): FakeHTFScanner, _make_scanner(), Path, Unit tests — HTF 15m cache wiring y zone_memory en STRAT-A., R15: trend usa candles_15m (>=25) en lugar de velas 5m del candidato., _seed_expired_zone(), test_htf_pass_aligned_call(), test_htf_veto_misaligned_put() (+7 more)

### Community 54 - "TestHelpers"
Cohesion: 0.18
Nodes (3): Mapea hora (0-23) a bucket: night/morning/afternoon/evening., Calcula Sharpe ratio de una lista de profits.          Retorna -999 si hay menos, TestHelpers

### Community 55 - "TestExportLoad"
Cohesion: 0.18
Nodes (7): Carga pesos calibrados desde un archivo JSON.          Args:             path: R, Selecciona los pesos correspondientes a un grupo (hora + vol).          Args:, Path, Cuando el grupo exacto no existe, usa default., Cuando el grupo existe, retorna sus pesos., Ciclo completo: load → calibrate → export → load → select., TestExportLoad

### Community 56 - "Backtester"
Cohesion: 0.17
Nodes (6): Backtester, Path, Compare historical decision vs reevaluated signal.          Returns a dict wit, Generate a performance metrics report.          Only considers candidates with, Offline backtesting engine that replays strategies on historical data.      Us, TestLoadFromDB

### Community 57 - "._resolve_trade"
Cohesion: 0.21
Nodes (6): Capital virtual de referencia para Massaniello (demo). None si desactivado., Calcula monto de entrada usando MassanielloRiskManager.         Retorna (monto,, Calcula monto de compensación (gale legacy).         Con Massaniello activo del, Actualiza balance y aplica stop-loss de sesión., Consulta el resultado de una operación expirada al broker         y actualiza e, MartinPending

### Community 58 - "HTFScanner"
Cohesion: 0.12
Nodes (9): HTFScanner, Devuelve {asset: n_candles} para diagnóstico., TTL del cache HTF en segundos., Cantidad de activos actualmente presentes en la biblioteca HTF., Devuelve la última lista elegible (asset, payout) del scanner HTF.         Si e, Reanuda el refresco en la próxima ronda., Cache de velas 15m mantenida en background.      Parámetros     ----------, Devuelve la lista de velas 15m cacheadas para el activo.         Nunca bloquea (+1 more)

### Community 59 - "FilterSellOTC"
Cohesion: 0.21
Nodes (9): FilterSellOTC, OrderAck, Quotex, Filtro de activos OTC por payout y venta PUT en el mejor candidato., Tests de filter_and_sell_otc.py con mocks (sin broker)., test_list_candidates_filters_via_connection(), test_run_once_default_dry_run(), test_run_once_empty_candidates_returns_empty() (+1 more)

### Community 60 - "test_consolidation_bot.py"
Cohesion: 0.15
Nodes (7): ArgumentParser, _parser_option_strings(), Tests del facade consolidation_bot., HTF scanner follows hub min_payout (same floor as bankroll card)., R14: parse_args() declara y acepta --live, --real, --loop, --greylist., test_consolidation_bot_htf_scanner_uses_min_payout(), test_parse_args_legacy_cli_flags()

### Community 61 - "trade_journal.py"
Cohesion: 0.25
Nodes (11): build_calibration(), classify_skip(), print_calibration(), Reporte de calibracion STRAT-F.  Lee las decisiones STRAT-F del diario (trade_jo, trade_journal.py — Módulo de aprendizaje y registro histórico de trades =======, _feed(), Tests para calibration_report.py (reporte de calibracion STRAT-F)., test_build_calibration_groups_and_suggests() (+3 more)

### Community 62 - "Path"
Cohesion: 0.21
Nodes (6): Path, 3 WIN + 1 LOSS → win rate = 75%., 0.80 - 1.00 + 0.75 + 0.85 = $1.40., No resolved trades → friendly message., TestCompare, TestReport

### Community 63 - "stats.py"
Cohesion: 0.24
Nodes (12): api_blackbox(), Reporte de la caja negra STRAT-F (win_rate, ranking pérdidas, A/B estocástico)., build_stats(), main(), _parse_stoch(), Any, Estadísticas de la caja negra STRAT-F (Fase 5).  Lee scan_candidates de la caja, Formatea el dict a texto legible (consola / log). (+4 more)

### Community 64 - "Refactor Monolith (Feature #1)"
Cohesion: 0.29
Nodes (13): src/config.py (constants), src/connection.py (broker I/O), Discarded: subfolder monolith, src/executor.py (TradeExecutor), consolidation_bot.py facade, Refactor Monolith (Feature #1), main.py entrypoint, MartingaleCalculator (legacy) (+5 more)

### Community 66 - "TestReevaluate"
Cohesion: 0.17
Nodes (7): LogCaptureFixture, Momentum candles should produce a 'call' signal., Swing candles with upper wick should signal 'put'., Random small-body candles should NOT produce a reversal signal., Running reevaluate() without filter processes all strategies., Unknown strategy origins should be logged as warnings., TestReevaluate

### Community 67 - "connection.py"
Cohesion: 0.24
Nodes (11): create_trading_client(), force_reconnect(), _force_reconnect_locked(), _handle_order_result(), place_order(), Quotex, WebSocket Quotex: conexión, velas y envío de órdenes., Envía la orden y espera la confirmación del broker.      Usa client.buy() de A (+3 more)

### Community 68 - "_now"
Cohesion: 0.17
Nodes (5): _now(), Crea un registro de sesión y devuelve su id., Registra un candidato evaluado.          decision debe ser uno de:, Actualiza el resultado de una orden ya registrada.          outcome: "WIN" | ", Igual que update_outcome pero usando la clave primaria (id) de la fila.

### Community 69 - "spike_filter.py"
Cohesion: 0.23
Nodes (11): detect_spike_anomaly(), spike_filter.py =============== Filtro anti-spike para velas OTC con saltos an, Elimina velas anómalas de una serie OHLC manteniendo el orden temporal.      E, Diagnóstico de una vela anómala., Resultado del chequeo anti-spike., Estadísticas de saneamiento de una serie de velas., Detecta si hay vela anómala en las últimas N velas.      Reglas:     1) Gap r, sanitize_spike_candles() (+3 more)

### Community 70 - "scanner.py"
Cohesion: 0.25
Nodes (6): Connection, datetime, BLACK BOX RECORDER - Captura completa de estrategias A, B, C ==================, Ejecución de órdenes, martingala y gestión de ciclo., instrumentation_layer.py — Capa de logging para auditoría de pipeline =========, Descarga de velas y recolección de candidatos por activo.

### Community 71 - "STRAT-A OB Prefetch (Feature #21)"
Cohesion: 0.24
Nodes (11): CANDLE_FETCH_CONCURRENCY, Parallel Asset Scan (Feature #3), fetch_candles_parallel (src/parallel_fetch.py), scanner.py prefetch changes, STRAT-A OB Prefetch — Requirements, STRAT-A OB Prefetch — Tasks, ScanCycleData.blocks_by_symbol, candle_cache.py OB cache (+3 more)

### Community 72 - "STRAT-A Quality Filters Feature (id=19)"
Cohesion: 0.29
Nodes (11): STRAT-A Quality Filters — Design, STRAT-A Quality Filters — Requirements, STRAT-A Quality Filters — Tasks, STRAT-A Test Suite — Design, STRAT-A Test Suite — Requirements, STRAT-A Test Suite — Tasks, STRAT-A Evaluate (Feature #17), STRAT-A Quality Constants (MIN_PAYOUT/SCORE/ZONE_AGE) (+3 more)

### Community 73 - "._interpret_broker_result"
Cohesion: 0.25
Nodes (8): Map broker payload to (WIN|LOSS, profit) or None if not settled yet., Reconciliar ACCEPTED/PENDING al arrancar para no contaminar métricas.         S, Broker lag: never treat profitAmount==0 as LOSS., test_bool_check_win(), test_missing_history_is_pending(), test_negative_profit_is_loss(), test_positive_profit_is_win(), test_profit_zero_is_not_loss()

### Community 74 - "._refresh_cycle"
Cohesion: 0.18
Nodes (5): Loop principal del scanner HTF.         Diseñado para correr como asyncio.creat, Una ronda completa: recorre todos los activos y refresca si es necesario., True si el cache está vacío o venció el TTL., Fetch con timeout y semáforo propio. Devuelve [] en caso de fallo., Notifica refresh de un activo para telemetría externa (HUB).

### Community 75 - "journal_performance_report.py"
Cohesion: 0.36
Nodes (10): fetch_rows(), latest_journal_db(), main(), outcome_counts(), Any, Connection, Path, Row (+2 more)

### Community 76 - "detect_momentum_1m"
Cohesion: 0.33
Nodes (9): detect_momentum_1m(), Estrategia momentum 1m: cuerpo grande + cierre en tercio extremo., Detecta momentum en la última vela 1m.      Returns:         (direction, strengt, _base_candles(), Tests de strat_momentum.py., test_momentum_detect_bearish(), test_momentum_detect_bullish(), test_momentum_detect_no_signal_small_body() (+1 more)

### Community 77 - "HubEventBus"
Cohesion: 0.24
Nodes (4): HubEventBus, Event bus for real-time hub updates., In-process pub/sub. Safe to call from sync or async code., Queue

### Community 78 - "autopilot.py"
Cohesion: 0.33
Nodes (9): Popen, _count_outcomes(), _launch_main(), _load_state(), main(), Path, Autopilot STRAT-F: relanza main.py mientras el host mate el WebSocket, y cuenta, _save_state() (+1 more)

### Community 79 - "create_client"
Cohesion: 0.31
Nodes (9): create_client(), get_practice_balance(), load_credentials_from_env(), Path, Quotex, QuotexCredentials, Load QUOTEX_EMAIL/QUOTEX_PASSWORD from .env or process environment., Create Quotex client using credentials loaded from .env. (+1 more)

### Community 80 - ".calibrate"
Cohesion: 0.27
Nodes (5): Any, Calcula thresholds de volatilidad (percentiles 33 y 66)., Recomputa el score total con nuevos pesos., Grid search sobre combinaciones de pesos.          Varía cada componente en [-ST, Ejecuta la calibración completa sobre self.trades.          Agrupa por (hour_buc

### Community 81 - "STRAT-A HTF Zone Wiring (Feature #20)"
Cohesion: 0.24
Nodes (10): evaluate_strat_a(), PendingReversalHint (no mutation), Scanner delegates to evaluate_strat_a, StratAEvaluation dataclass, entry_scorer trend 15m, STRAT-A HTF Zone Wiring (Feature #20), Scanner HTF + zone_memory gates, HTFScanner 15m background (+2 more)

### Community 82 - "QualityAssetLibrary"
Cohesion: 0.25
Nodes (3): QualityAssetLibrary, Biblioteca dinámica de activos elegibles por payout., Lista de activos en biblioteca, ordenados por payout desc.

### Community 83 - "._reevaluate_strat_a"
Cohesion: 0.25
Nodes (5): Any, Replay strategies on every loaded candidate.          If *strategies* is given, Marca un candidato STRAT-F como re-evaluado.          STRAT-F necesita 3 tempo, Re-evaluate a STRAT-A candidate.          Attempts to reconstruct ``Consolidat, Load candidates from ``candidates`` table within the given day range.

### Community 84 - "get_black_box"
Cohesion: 0.25
Nodes (8): clear_blackbox_trades(), get_blackbox_session(), get_blackbox_trades(), Get trade history from black box., Clear trade history from black box (JSONL files preserved)., Get current session summary from black box., get_black_box(), Obtiene instancia singleton del recorder.

### Community 85 - "review_expired_zones.py"
Cohesion: 0.39
Nodes (7): _build_query(), _export_csv(), main(), _print_table(), Path, review_expired_zones.py ======================= Script de diagnóstico para rev, _require_sqlite()

### Community 86 - "FakeBot"
Cohesion: 0.39
Nodes (6): FakeBot, Tests de executor.py con mocks., test_executor_cycle_reset_on_target(), test_executor_dry_run_order(), test_executor_enter_trade_strat_a_breakout_no_monitor(), test_executor_enter_trade_strat_a_initial_sets_origin_and_monitor()

### Community 88 - "trader_short.py"
Cohesion: 0.43
Nodes (6): _build_candidate(), _eval_one(), main(), Trader corto STRAT-F (sortea el host-kill del sandbox).  Hace UN ciclo compacto, Marca WIN/LOSS de las PENDING de hoy consultando get_result., _reconcile()

### Community 89 - "htf_scanner.py"
Cohesion: 0.29
Nodes (4): AssetBook, asset_library.py ================ Biblioteca de activos de calidad ("libros"), Refresca la biblioteca desde la foto actual de activos elegibles.          Par, htf_scanner.py ============== Scanner de temporalidad alta (15 minutos) que co

### Community 90 - "PipelineMetrics"
Cohesion: 0.33
Nodes (4): PipelineMetrics, Acumulador de métricas por ciclo de escaneo., Reinicia contadores para un nuevo ciclo., Emite resumen en formato parseble.

### Community 91 - "._ensure_schema_upgrades"
Cohesion: 0.29
Nodes (3): Path, Exporta la tabla candidates a CSV para análisis externo., Aplica migraciones suaves para bases existentes.

### Community 92 - "TestStratFRecognition"
Cohesion: 0.29
Nodes (4): R7 — el backtester reconoce STRAT-F (rama dedicada)., R7 — reevaluate procesa STRAT-F usando strategy_json., R8 — el reporte incluye las metricas de las señales STRAT-F resueltas., TestStratFRecognition

### Community 93 - "test_strat_f_journal.py"
Cohesion: 0.57
Nodes (6): Tests para el diario/calibracion STRAT-F en trade_journal.py.  Cubre: grabacion, _strat_f_entry(), test_log_candidate_strat_f_accepted(), test_log_candidate_strat_f_rejected_with_zone_none(), test_query_and_report_strat_f(), _tmp_journal()

### Community 94 - "_WebLogHandler"
Cohesion: 0.33
Nodes (5): Captures log records into ring buffer + pushes to WebSocket subscribers., Add web log handler to consolidation_bot + black_box_recorder loggers., _setup_web_logging(), _WebLogHandler, LogRecord

### Community 95 - "diag_strat_f_live.py"
Cohesion: 0.40
Nodes (5): _feed_journal(), main(), Diagnóstico STRAT-F en vivo (solo lectura).  Conecta a demo, baja 15m/5m/1m de u, Graba una decision STRAT-F en el diario (trade_journal.db)., get_journal()

### Community 96 - ".apply_weights"
Cohesion: 0.40
Nodes (3): Sobrescribe los pesos globales en entry_scorer.          Llámese al inicio del b, Después de aplicar, los dicts tienen las mismas keys., TestApplyWeights

### Community 97 - "test_black_box_stratf.py"
Cohesion: 0.33
Nodes (3): Tests de la caja negra STRAT-F (Fase 1): esquema extendido + grabación.  Usa una, Correr _init_db dos veces no rompe ni duplica columnas., test_migration_idempotent_on_existing_db()

### Community 98 - "test_fase3_scanner_blackbox.py"
Cohesion: 0.53
Nodes (5): _fake_eval(), _make_cycle(), _make_self(), Test de Fase 3 — cableado STRAT-F -> caja negra en scanner.py.  Verifica que, en, test_scan_records_accepted_and_rejected_in_black_box()

### Community 99 - "test_fase5_stats.py"
Cohesion: 0.47
Nodes (4): Tests de Fase 5 — stats.py lee la caja negra y calcula métricas.  Usa una DB tem, _seed(), test_build_stats_aggregates_correctly(), test_render_report_includes_sections()

### Community 100 - "test_session_lifecycle.py"
Cohesion: 0.33
Nodes (4): mgr(), Smart session lifecycle: Iniciar / resume incomplete / stop on meta., Executor must mark COMPLETED before resetting Massaniello., TestExecutorNotifiesSessionManager

### Community 101 - "update_config"
Cohesion: 0.40
Nodes (5): get_config(), Any, Get current bot configuration., Update bot configuration (only when bot is stopped)., update_config()

### Community 102 - "strat_support.py"
Cohesion: 0.40
Nodes (4): DataFrame, candles_to_dataframe(), find_strong_support_2m(), Utilidades compartidas de análisis de velas (soporte fuerte 2m, conversión a Dat

### Community 104 - "enviar_orden"
Cohesion: 0.40
Nodes (4): enviar_orden(), Any, Envío simple y robusto de órdenes OTC a QUOTEX.  Extrae la lógica que ya comprob, Envía UNA orden OTC y devuelve (ok, info).      `direction` debe ser "call" (com

### Community 105 - ".query_strat_f"
Cohesion: 0.40
Nodes (3): Row, Devuelve los candidatos con strategy_origin='STRAT-F'., Imprime diario + métricas de calibración de STRAT-F.

### Community 106 - "._row_to_trade"
Cohesion: 0.40
Nodes (3): Row, Carga trades históricos con outcome WIN/LOSS desde la BD.          Retorna la ca, Convierte una fila de la BD a un dict interno para calibración.

### Community 107 - "TestNoBrokerIO"
Cohesion: 0.40
Nodes (3): The full load → reevaluate → compare → report cycle runs         without network, backtester must not import pyquotex or similar broker libs., TestNoBrokerIO

### Community 108 - "TestIntegration"
Cohesion: 0.40
Nodes (3): Todos los pesos en default y by_group suman 100., weight_calibrator must not import pyquotex or broker libs., TestIntegration

### Community 110 - "parse_strat_a_session.py"
Cohesion: 0.67
Nodes (3): load_session(), main(), Parse STRAT-A live validation session from consolidation_bot.log.

### Community 112 - "fix_indent.py"
Cohesion: 0.50
Nodes (3): fix_module(), Path, Corrige indentación de métodos sueltos en executor.py y scanner.py.

## Knowledge Gaps
- **46 isolated node(s):** `engram`, `CLAUDE.md — Instrucciones para Claude (rol leader)`, `skill-registry.md — Registry de skills (Gentle AI)`, `hub/static/index.html — Dashboard HUB (frontend)`, `progress/current.md — Plantilla sesión actual` (+41 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **38 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Candle` connect `Candle` to `test_scanner_strat_a.py`, `evaluate_strat_f`, `smc_analysis.py`, `entry_decision_engine.py`, `AssetScanner`, `CandleCache`, `strat_a.py`, `ConsolidationBot`, `scan_prefetch.py`, `CandidateEntry`, `evaluate_strat_a`, `.refresh_from_candidate`, `test_stochastic_m15.py`, `test_strat_reversal_swing.py`, `OrderBlock`, `ConsolidationZone`, `strat_a_radar.py`, `BreakerOrderBlockDetector`, `fetch_candles_with_retry`, `zone_memory.py`, `test_htf_zone_wiring.py`, `Backtester`, `Path`, `TestReevaluate`, `spike_filter.py`, `detect_momentum_1m`, `._reevaluate_strat_a`, `TestStratFRecognition`, `strat_support.py`, `TestNoBrokerIO`, `EntryCategory`, `EntryDecision`?**
  _High betweenness centrality (0.216) - this node is a cross-community bridge._
- **Why does `AssetScanner` connect `AssetScanner` to `BotRunner`, `StratFHubState`, `test_scanner_strat_a.py`, `scanner.py`, `ConsolidationZone`, `strat_a_radar.py`, `TradeExecutor`, `test_htf_zone_wiring.py`, `ConsolidationBot`, `CandidateEntry`, `Candle`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `BotRunner` connect `BotRunner` to `test_scanner_strat_a.py`, `.enter_trade`, `Connection`, `ConsolidationZone`, `massaniello_engine.py`, `TradeExecutor`, `MassanielloPersistence`, `SessionManager`, `session_manager.py`, `AssetScanner`, `MassanielloRiskManager`, `ConsolidationBot`, `HTFScanner`, `CandidateEntry`, `_WebLogHandler`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 63 inferred relationships involving `Candle` (e.g. with `Backtester` and `.load_from_db()`) actually correct?**
  _`Candle` has 63 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `MassanielloRiskManager` (e.g. with `reset_session()` and `_WebLogHandler`) actually correct?**
  _`MassanielloRiskManager` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `AssetScanner` (e.g. with `BotRunner` and `ConsolidationBot`) actually correct?**
  _`AssetScanner` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `TradeExecutor` (e.g. with `BotRunner` and `ConsolidationBot`) actually correct?**
  _`TradeExecutor` has 19 INFERRED edges - model-reasoned connections that need verification._