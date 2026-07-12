# Graph Report - C:\Users\v_jac\Desktop\QUOTEX  (2026-07-11)

## Corpus Check
- Large corpus: 229 files · ~606,451 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 1989 nodes · 4154 edges · 95 communities (82 shown, 13 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 637 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Breaker Order Block Detector
- Entry Timing Sync (EntrySynchronizer)
- SMC Analysis Core (FVG/Swings/Bias)
- Kelly Criterion Sizing
- Parallel Asset Scan / Candle Fetch
- Agent Memory & Strategy Decisions
- Repo Map & Agent Roles (AGENTS/CLAUDE)
- Telegram Alerts & Risk Events
- Order Block Scan Prefetch
- Candidate Scoring & Selection
- Backtesting Engine
- Architecture & Conventions
- Martingale (Gale) Engine/Watcher
- Strategy B — Wyckoff Spring
- Trade Journal (SQLite)
- Martingale Calculator
- Diversification Enforcer
- Strategy A Consolidation Logic
- Black Box Recorder
- Masaniello Engine
- Consolidation Bot Main
- Observable Candle Fetcher
- Masaniello Stake/Table Logic
- Strategy A Radar (HTF zones)
- Hub State & Scanner
- HTF Scanner (15m)
- Candle Cache
- Masaniello Risk Manager
- VIP Window Library
- Strategy A Entry Gates
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 74
- Community 75
- Community 76
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 89
- Community 92

## God Nodes (most connected - your core abstractions)
1. `Candle` - 192 edges
2. `AssetScanner` - 61 edges
3. `TradeExecutor` - 54 edges
4. `ConsolidationZone` - 52 edges
5. `MassanielloRiskManager` - 46 edges
6. `WeightCalibrator` - 45 edges
7. `Backtester` - 37 edges
8. `CandleSignal` - 34 edges
9. `evaluate_strat_a()` - 33 edges
10. `HubScanner` - 30 edges

## Surprising Connections (you probably didn't know these)
- `Capas del Quant Engine (6 capas)` --semantically_similar_to--> `Arquitectura de 4 capas (connection→scanner→strats→executor)`  [INFERRED] [semantically similar]
  Documentos/files/QUANT_ENGINE_ARQUITECTURA.md → agent/PROJECT_STATE.md
- `test_radar_watch_tick_no_crash()` --calls--> `AssetScanner`  [INFERRED]
  tests/test_strat_a_radar.py → src/scanner.py
- `test_price_at_ceiling_within_tolerance()` --calls--> `price_at_ceiling()`  [INFERRED]
  tests/test_strat_a.py → src/strat_a.py
- `Decisión: Massaniello activo (no martingala en runtime)` --semantically_similar_to--> `Martingala (legacy, superseded por Massaniello)`  [INFERRED] [semantically similar]
  CHECKPOINTS.md → MARTINGALE_SUMMARY.md
- `Motor Masaniello 5/2` --semantically_similar_to--> `MassanielloRiskManager (gestor de riesgo activo)`  [INFERRED] [semantically similar]
  Documentos/files/PLAN_MASANIELLO.md → agent/CONTEXT.md

## Import Cycles
- None detected.

## Communities (95 total, 13 thin omitted)

### Community 0 - "Breaker Order Block Detector"
Cohesion: 0.05
Nodes (84): BoBPhase, BoBResult, BoBSetup, BoBState, BreakerOrderBlockDetector, Enum, str, Detector BoB por fases: setup -> retest -> confirmation.      Este detector NO (+76 more)

### Community 1 - "Entry Timing Sync (EntrySynchronizer)"
Cohesion: 0.05
Nodes (33): EntrySynchronizer, Telemetría por orden: time_since_open y secs_to_close., Calcula y valida timing de entrada respecto al open de vela 1m., Evalúa timing puro respecto a un open de vela conocido.          Args:, Espera al próximo open de vela 1m y valida que el envío no llegue tarde., Any, Task, Calcula monto de entrada usando MassanielloRiskManager.         Retorna (monto, (+25 more)

### Community 2 - "SMC Analysis Core (FVG/Swings/Bias)"
Cohesion: 0.07
Nodes (52): Bias, _compute_bias(), detect_fvg(), detect_structure(), detect_swings(), _extract_zones(), FVG, _label_structure_events() (+44 more)

### Community 3 - "Kelly Criterion Sizing"
Cohesion: 0.05
Nodes (45): KellySizer, Connection, Path, Cálculo de Kelly Criterion para sizing conservador del capital., Retorna payout promedio como ratio (85 % → 0.85)., Calcula el factor de Kelly fraccional.          Args:             fractional: Fr, Calcula el factor de Kelly fraccional desde datos históricos.      Fórmula compl, Busca el archivo trade_journal-*.db más reciente. (+37 more)

### Community 4 - "Parallel Asset Scan / Candle Fetch"
Cohesion: 0.06
Nodes (63): CANDLE_FETCH_CONCURRENCY, Parallel Asset Scan (Feature #3), fetch_candles_parallel (src/parallel_fetch.py), scanner.py prefetch changes, src/config.py (constants), src/connection.py (broker I/O), Discarded: subfolder monolith, src/executor.py (TradeExecutor) (+55 more)

### Community 5 - "Agent Memory & Strategy Decisions"
Cohesion: 0.06
Nodes (59): CHANGELOG (agent memory), CONTEXT (conocimiento técnico persistente), MassanielloRiskManager (gestor de riesgo activo), Strategy A — Consolidation (5m), Strategy B — Wyckoff Spring/Upthrust, Decisión: workflow autónomo /agent, Rationale: carpeta /agent para resumen cross-machine, Decisión: demo-only para fase Masaniello (+51 more)

### Community 6 - "Repo Map & Agent Roles (AGENTS/CLAUDE)"
Cohesion: 0.08
Nodes (55): AGENTS.md — Mapa de navegación para agentes, alerter.py — Alertas Telegram, backtester.py — Motor de backtesting, candle_cache.py — Caché local de velas, CHECKPOINTS.md — Evaluación del estado final, CLAUDE.md — Instrucciones para Claude (rol leader), implementer.md — Agente Implementador, leader.md — Agente Líder (Orquestador) (+47 more)

### Community 7 - "Telegram Alerts & Risk Events"
Cohesion: 0.05
Nodes (45): Exception, Alerta: conexión perdida con el broker (R6)., Alerta: stop-loss de sesión activado (R7)., Envía mensajes a un chat de Telegram vía Bot API.      Lee TELEGRAM_BOT_TOKEN y, Check cooldown for event_type. Updates timestamp if allowed., Send a raw text message to Telegram.          Args:             text: Message te, Alerta: sesión Massaniello cumplida (R4)., Alerta: racha de pérdidas / sesión fallida (R5). (+37 more)

### Community 8 - "Order Block Scan Prefetch"
Cohesion: 0.07
Nodes (47): Semaphore, OrderBlock, decrement_failed_assets(), _fetch_with_optional_stagger(), filter_scan_assets(), prefetch_primary_candles(), prefetch_strat_a_secondary(), Any (+39 more)

### Community 9 - "Candidate Scoring & Selection"
Cohesion: 0.09
Nodes (20): explain_score(), select_best(), sleep_with_inline_countdown(), CandidateEntry, AssetScanner, Any, Path, FASE 3/5 — STRAT-B, MOMENTUM y STRAT-A sin I/O de red. (+12 more)

### Community 10 - "Backtesting Engine"
Cohesion: 0.06
Nodes (49): Backtesting Engine — Design, Backtester (src/backtester.py), Decision: pandas descartado en backtester, Performance Metrics (Sharpe, Drawdown, Win Rate), trade_journal.Journal (shared DB dependency), Backtesting Engine — Requirements, Backtesting Engine — Tasks, Candle Cache — Design (+41 more)

### Community 11 - "Architecture & Conventions"
Cohesion: 0.06
Nodes (45): Arquitectura y estándar de calidad, Qué NO hacer (anti-patrones), Flujo de datos HFT, Cuatro capas (Conexión/Análisis/Estrategias/Ejecución), Gestión de riesgo (estado actual), Estado transaccional en SQLite, Separación estrategia-ejecución, Convenciones de código (+37 more)

### Community 12 - "Martingale (Gale) Engine/Watcher"
Cohesion: 0.08
Nodes (24): FetchPriceFn, GetBalanceFn, mg/ — Motor de Gale (Martingale Engine)  Módulo independiente que vigila opera, GaleWatcher, mg/mg_watcher.py — GaleWatcher  Vigila una operación binaria abierta de 5 minu, Información de la operación activa que el watcher vigila., True si el precio actual implica que la operación va perdiendo., Texto corto de P/L: dirección, variación de precio e implicancia. (+16 more)

### Community 13 - "Strategy B — Wyckoff Spring"
Cohesion: 0.09
Nodes (38): candles_to_dataframe(), evaluate_strat_b(), find_strong_support_2m(), Any, DataFrame, Estrategia B: Spring / Upthrust (Wyckoff) en 1m., _clamp(), _confidence_from_metrics() (+30 more)

### Community 14 - "Trade Journal (SQLite)"
Cohesion: 0.07
Nodes (17): Journal, _now(), Connection, Path, Muestra los últimos N candidatos rechazados con detalle., Exporta la tabla candidates a CSV para análisis externo., Interfaz principal del módulo de aprendizaje., Aplica migraciones suaves para bases existentes. (+9 more)

### Community 15 - "Martingale Calculator"
Cohesion: 0.09
Nodes (19): MartingaleCalculator, Martingale Calculator para Opciones Binarias. Reemplica la lógica de la calcula, Calcula el objetivo de ciclo para un balance dado (sin mutar estado)., Redondea hacia arriba a centavos., Calcula el monto a invertir para alcanzar el objetivo.          Args:, Calcula inversión para un balance proyectado sin mutar el estado interno., Calculadora de Martingale para ciclos de trading con incremento fijo., Registra ganancia y cierra ciclo.         El saldo se ajusta EXACTAMENTE al obj (+11 more)

### Community 16 - "Diversification Enforcer"
Cohesion: 0.10
Nodes (32): DiversificationEnforcer, diversification_enforcer.py — Rechaza entradas que violan límites de diversifica, Valida que una nueva entrada no viole los límites de diversificación., Verifica si se permite una entrada para ``candidate_asset``.          Parameters, _make_trade(), Tests de diversification_enforcer.py., Permite entrada en otro activo aunque el máximo por activo se alcanzó., El mensaje de rechazo incluye activo y límite violado. (+24 more)

### Community 17 - "Strategy A Consolidation Logic"
Cohesion: 0.27
Nodes (31): Datos prefetched para un ciclo de escaneo., ScanCycleData, _base_consolidation_body(), _candle(), _consolidation_candles_5m_at_ceiling(), _consolidation_candles_5m_breakout(), _invalid_put_rejection_1m(), _make_strat_a_scanner() (+23 more)

### Community 18 - "Black Box Recorder"
Cohesion: 0.09
Nodes (17): BlackBoxRecorder, get_black_box(), Any, BLACK BOX RECORDER - Captura completa de estrategias A, B, C ==================, Registra TODA la actividad de las estrategias., Crea tablas si no existen., Registra el inicio de un escaneo. Retorna scan_id., Registra un candidato escaneado y retorna su id. (+9 more)

### Community 19 - "Masaniello Engine"
Cohesion: 0.09
Nodes (17): MasanielloConfig, MasanielloEngine, MasanielloState, Replica la fórmula de inversión de la columna C del Excel Masaniello., Escribe W/L en Excel para comparación manual con la plantilla original., Construye la tabla equivalente al bloque N:DJ del Excel Masaniello., Calcula primera inversión con la misma lógica base del Excel Masaniello., Calcula el monto de la siguiente operación.                  FÓRMULA MASANIELL (+9 more)

### Community 20 - "Consolidation Bot Main"
Cohesion: 0.12
Nodes (16): datetime, Alertas a Telegram para eventos del bot vía Bot API., Backtester — offline strategy replay engine.  Re-evaluates historical signals fr, Constantes operativas del bot de consolidación Quotex., parse_args(), Namespace, consolidation_bot.py — Facade del bot de consolidación Quotex., Sincronización precisa de entradas con apertura de vela 1m. (+8 more)

### Community 21 - "Observable Candle Fetcher"
Cohesion: 0.11
Nodes (15): CandleFetchResult, ConnectionState, FetchMetrics, ObservableCandleFetcher, Any, candle_fetcher_observable.py ============================  Capa de observabil, Obtiene estado actual de la conexión., Fetch con observabilidad + retry controlado para empty arrays. (+7 more)

### Community 22 - "Masaniello Stake/Table Logic"
Cohesion: 0.19
Nodes (24): Result, BetRow, calculate_balance_objective(), calculate_stake(), effective_profit(), _is_finished(), _multiplier_table(), normalize_history() (+16 more)

### Community 23 - "Strategy A Radar (HTF zones)"
Cohesion: 0.13
Nodes (21): ConsolidationZone, _age_ratio_ok(), _clamp(), compute_readiness(), _price_at_extreme(), RadarWatchEntry, rank_and_trim(), STRAT-A hunter radar: watchlist de zonas casi listas (coarse → fine). (+13 more)

### Community 24 - "Hub State & Scanner"
Cohesion: 0.08
Nodes (15): HubState, Estado global del HUB en ejecución., HubScanner, Registra que se abrió una entrada., Actualiza temporizador y telemetría de la entrada activa., Guarda el resultado del último trade para mostrarlo en el HUB., Gestor de ciclos de escaneo y estado visible del HUB., Cierra la entrada activa (limpia campos de trade en curso). (+7 more)

### Community 25 - "HTF Scanner (15m)"
Cohesion: 0.09
Nodes (15): HTFScanner, TTL del cache HTF en segundos., Cantidad de activos actualmente presentes en la biblioteca HTF., Devuelve la última lista elegible (asset, payout) del scanner HTF.         Si e, Loop principal del scanner HTF.         Diseñado para correr como asyncio.creat, Una ronda completa: recorre todos los activos y refresca si es necesario., Resuelve la lista de activos a escanear usando callback externo o fallback inter, Escaneo interno de activos OTC abiertos con payout > min_payout. (+7 more)

### Community 26 - "Candle Cache"
Cohesion: 0.13
Nodes (15): CacheKey, Lock, _CacheEntry, CandleCache, Any, Caché en memoria de velas con actualización incremental., Elimina entradas expiradas. Devuelve cantidad purgada., Caché asyncio-safe: clave (asset, tf_sec) → velas ordenadas por ts. (+7 more)

### Community 27 - "Masaniello Risk Manager"
Cohesion: 0.16
Nodes (12): MassanielloRiskManager, Any, Wrapper de sesión: 5 ops / 3 ITM / límite temporal., mgr(), Tests del wrapper MassanielloRiskManager., test_next_stake_ok(), test_register_win_logs_session_complete(), test_session_status_snapshot() (+4 more)

### Community 28 - "VIP Window Library"
Cohesion: 0.15
Nodes (14): Ventana VIP para candidatos casi listos para entrada., VipWindowData, _candles_tail(), _ema(), _ma_pair(), Any, vip_library.py ============== Biblioteca VIP de candidatos casi listos para en, Biblioteca de ventanas VIP, actualizada con cada candidato evaluado. (+6 more)

### Community 29 - "Strategy A Entry Gates"
Cohesion: 0.11
Nodes (25): _check_candles_available(), _check_cycle_limit(), _check_htf_available_and_aligned(), _check_no_active_trade(), _check_pattern_confirmed(), _check_payout_minimum(), _check_score_minimum(), _check_spike_1m() (+17 more)

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (22): MAState, Re-evalúa activos en pending_reversals.         Devuelve candidatos listos para, avg_body(), _block_distance(), broke_below(), _clamp(), compute_atr(), compute_dynamic_range() (+14 more)

### Community 31 - "Community 31"
Cohesion: 0.12
Nodes (14): CandidateData, _normalize_direction(), Any, Construye candidato STRAT-B desde señal real del bot., Candidato normalizado para renderizar en el HUB., Valor único para ordenar candidatos en el HUB., Construye candidato STRAT-A desde payload real del bot., _utc_now() (+6 more)

### Community 32 - "Community 32"
Cohesion: 0.11
Nodes (16): main(), Comparar métodos de fetch de velas pyquotex., main(), Test new HistoryMixin candle APIs., main(), Poll candle count after get_candles request., main(), Prueba aislada: una sola vela fetch con delays. (+8 more)

### Community 33 - "Community 33"
Cohesion: 0.17
Nodes (20): _candles_from_raw(), fetch_candles(), fetch_candles_with_retry(), force_reconnect(), looks_like_connection_issue(), _min_expected_candles(), place_order(), Quotex (+12 more)

### Community 34 - "Community 34"
Cohesion: 0.18
Nodes (20): _age_adjustment(), _clamp(), detect_swing_levels(), _ema(), _normalize(), Componente REBOUND: mide calidad de mecha en el extremo y momentum de velas reci, Componente BREAKOUT: mide fuerza de la vela de ruptura vs historial.     Interp, Ajuste por antigüedad de zona. Negativo penaliza, positivo bonifica. (+12 more)

### Community 35 - "Community 35"
Cohesion: 0.14
Nodes (10): MassanielloPersistence, Guarda y recupera el estado de MassanielloRiskManager en SQLite., INSERT del estado actual de *manager* en massaniello_state.          Devuelve, SELECT de la última fila de massaniello_state.          Retorna dict con la fi, R3 + R4 — Restauración y validación., R1 + R5 — Guardado exitoso., R2 — Recuperación exitosa., TestApply (+2 more)

### Community 36 - "Community 36"
Cohesion: 0.15
Nodes (9): ConnectionManager, ConsolidationBot, _extract_candidates_for_hub(), main(), Any, Quotex, Convierte last_scan_candidates del bot a payloads para el hub., Orquestador: compone conexión, scanner y executor. (+1 more)

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (16): api_state(), _auto_open_dashboard(), _broadcast(), _build_snapshot(), _event_relay(), _open_browser(), FastAPI + WebSocket server for the live hub dashboard., Return `requested` if free, otherwise find a random free port. (+8 more)

### Community 38 - "Community 38"
Cohesion: 0.14
Nodes (17): EntryContext, Contexto opcional para evaluación de entrada., _classify_role(), _decay(), HistoricalZone, Path, query_nearby_zones(), zone_memory.py ============== Módulo de memoria de zonas históricas de consoli (+9 more)

### Community 39 - "Community 39"
Cohesion: 0.33
Nodes (12): Enum, str, RoutedSignal, RouterSnapshot, SignalPhase, StrategyName, StrategySignal, render_control_center() (+4 more)

### Community 40 - "Community 40"
Cohesion: 0.14
Nodes (17): Kelly integration in consolidation_bot.py, Discarded: per-asset Kelly, Kelly Criterion Sizing (Feature), KellySizer (src/kelly_sizer.py), Kelly x Massaniello _initial_capital, Kelly reads candidates table, Discarded: JSON file persistence, Persistence save in executor.py (+9 more)

### Community 41 - "Community 41"
Cohesion: 0.18
Nodes (5): Connection, Calibra pesos del entry_scorer usando datos históricos de trades.      Proceso:, WeightCalibrator, TestCalibrate, TestLoadTrades

### Community 42 - "Community 42"
Cohesion: 0.27
Nodes (15): FakeHTFScanner, _make_scanner(), Path, Unit tests — HTF 15m cache wiring y zone_memory en STRAT-A., R15: trend usa candles_15m (>=25) en lugar de velas 5m del candidato., _seed_expired_zone(), test_htf_pass_aligned_call(), test_htf_veto_misaligned_put() (+7 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (12): _bearish_15m_candles(), _candle(), FakeBot, _FakeHTFScanner, _make_scanner_mocks(), Tests de scanner.py con activos/velas sintéticas., Regression: confirmed pending reversal must not crash on strat_a helpers., test_process_pending_reversals_confirmed_pattern_no_attribute_error() (+4 more)

### Community 44 - "Community 44"
Cohesion: 0.13
Nodes (7): AssetBook, QualityAssetLibrary, asset_library.py ================ Biblioteca de activos de calidad ("libros"), Biblioteca dinámica de activos elegibles por payout., Refresca la biblioteca desde la foto actual de activos elegibles.          Par, Lista de activos en biblioteca, ordenados por payout desc., htf_scanner.py ============== Scanner de temporalidad alta (15 minutos) que co

### Community 45 - "Community 45"
Cohesion: 0.18
Nodes (3): Mapea hora (0-23) a bucket: night/morning/afternoon/evening., Calcula Sharpe ratio de una lista de profits.          Retorna -999 si hay menos, TestHelpers

### Community 46 - "Community 46"
Cohesion: 0.18
Nodes (7): Carga pesos calibrados desde un archivo JSON.          Args:             path: R, Selecciona los pesos correspondientes a un grupo (hora + vol).          Args:, Path, Cuando el grupo exacto no existe, usa default., Cuando el grupo existe, retorna sus pesos., Ciclo completo: load → calibrate → export → load → select., TestExportLoad

### Community 47 - "Community 47"
Cohesion: 0.17
Nodes (16): _create_db(), db_empty(), db_known_metrics(), db_mixed(), _momentum_candles(), Any, Tests for src/backtester.py.  Uses an in-memory SQLite database injected via ``t, Populate a SQLite DB at *path* with the given candidate rows. (+8 more)

### Community 48 - "Community 48"
Cohesion: 0.19
Nodes (13): CandleSnapshot, GaleState, HubScanSnapshot, MasanielloState, Modelos del HUB para datos reales de STRAT-A y STRAT-B., Resultado de un ciclo completo de escaneo., [DEPRECATED] Estado anterior del GaleWatcher. Use MasanielloState en su lugar., Estado en tiempo real del motor Masaniello (gestión dinámica de riesgo). (+5 more)

### Community 49 - "Community 49"
Cohesion: 0.17
Nodes (6): Backtester, Path, Compare historical decision vs reevaluated signal.          Returns a dict with, Generate a performance metrics report.          Only considers candidates with `, Offline backtesting engine that replays strategies on historical data.      Usag, TestLoadFromDB

### Community 50 - "Community 50"
Cohesion: 0.16
Nodes (11): journal(), manager(), manager_no_balance(), persistence(), Tests de persistencia Massaniello — R6., R4 — Datos corruptos o inválidos., Corrupción a nivel BD — load() no debe lanzar excepción., Filas con valores fuera de rango: load() devuelve el dict, apply() lo valida. (+3 more)

### Community 51 - "Community 51"
Cohesion: 0.19
Nodes (15): calibrator_empty(), calibrator_minimal(), calibrator_with_trades(), _candles_with_volatility(), _create_in_memory_db(), _populate_db(), Any, Connection (+7 more)

### Community 52 - "Community 52"
Cohesion: 0.17
Nodes (14): fetch_candles_1m(), _check_spike_5m(), Veto 6: ¿Sin spike en 5m?, detect_spike_anomaly(), spike_filter.py =============== Filtro anti-spike para velas OTC con saltos an, Elimina velas anómalas de una serie OHLC manteniendo el orden temporal.      E, Diagnóstico de una vela anómala., Resultado del chequeo anti-spike. (+6 more)

### Community 53 - "Community 53"
Cohesion: 0.21
Nodes (13): init(), Any, Task, start(), _apply_runtime_config(), _build_parser(), _load_dotenv(), ArgumentParser (+5 more)

### Community 54 - "Community 54"
Cohesion: 0.22
Nodes (9): FilterSellOTC, OrderAck, Quotex, Filtro de activos OTC por payout y venta PUT en el mejor candidato., Tests de filter_and_sell_otc.py con mocks (sin broker)., test_list_candidates_filters_via_connection(), test_run_once_default_dry_run(), test_run_once_empty_candidates_returns_empty() (+1 more)

### Community 55 - "Community 55"
Cohesion: 0.18
Nodes (9): PendingReversal, Enum, Estructuras de datos compartidas entre módulos., SignalMode, ScanResult, PendingReversalHint, Pista para que scanner encole espera activa; sin mutación en strat_a., FakeBot (+1 more)

### Community 56 - "Community 56"
Cohesion: 0.21
Nodes (6): Path, 3 WIN + 1 LOSS → win rate = 75%., 0.80 - 1.00 + 0.75 + 0.85 = $1.40., No resolved trades → friendly message., TestCompare, TestReport

### Community 57 - "Community 57"
Cohesion: 0.17
Nodes (5): _parser_option_strings(), ArgumentParser, Tests del facade consolidation_bot., R14: parse_args() declara y acepta --live, --real, --loop, --greylist., test_parse_args_legacy_cli_flags()

### Community 58 - "Community 58"
Cohesion: 0.17
Nodes (7): LogCaptureFixture, Momentum candles should produce a 'call' signal., Swing candles with upper wick should signal 'put'., Random small-body candles should NOT produce a reversal signal., Running reevaluate() without filter processes all strategies., Unknown strategy origins should be logged as warnings., TestReevaluate

### Community 59 - "Community 59"
Cohesion: 0.25
Nodes (10): apply_category_logic(), classify_candidate(), EntryCategory, Enum, entry_decision_engine.py — Motor de decisión de entrada modular e independiente., Clasifica candidato en categoría A/B/C basada en métricas.          CATEGORÍA, Categoría de setup probabilístico., Aplica lógica de ejecución según categoría y estado del ciclo.          CATEGO (+2 more)

### Community 60 - "Community 60"
Cohesion: 0.36
Nodes (10): fetch_rows(), latest_journal_db(), main(), outcome_counts(), Any, Connection, Path, Row (+2 more)

### Community 61 - "Community 61"
Cohesion: 0.24
Nodes (4): HubEventBus, Event bus for real-time hub updates., In-process pub/sub. Safe to call from sync or async code., Queue

### Community 62 - "Community 62"
Cohesion: 0.31
Nodes (9): create_client(), get_practice_balance(), load_credentials_from_env(), Path, Quotex, QuotexCredentials, Load QUOTEX_EMAIL/QUOTEX_PASSWORD from .env or process environment., Create Quotex client using credentials loaded from .env. (+1 more)

### Community 63 - "Community 63"
Cohesion: 0.27
Nodes (5): Any, Calcula thresholds de volatilidad (percentiles 33 y 66)., Recomputa el score total con nuevos pesos., Grid search sobre combinaciones de pesos.          Varía cada componente en [-ST, Ejecuta la calibración completa sobre self.trades.          Agrupa por (hour_buc

### Community 64 - "Community 64"
Cohesion: 0.25
Nodes (5): Any, Replay strategies on every loaded candidate.          If *strategies* is given (, Re-evaluate a STRAT-A candidate.          Attempts to reconstruct ``Consolidatio, Re-evaluate a STRAT-B candidate., Load candidates from ``candidates`` table within the given day range.          F

### Community 65 - "Community 65"
Cohesion: 0.25
Nodes (5): PipelineMetrics, instrumentation_layer.py — Capa de logging para auditoría de pipeline =========, Acumulador de métricas por ciclo de escaneo., Reinicia contadores para un nuevo ciclo., Emite resumen en formato parseble.

### Community 66 - "Community 66"
Cohesion: 0.39
Nodes (7): _build_query(), _export_csv(), main(), _print_table(), Path, review_expired_zones.py ======================= Script de diagnóstico para rev, _require_sqlite()

### Community 67 - "Community 67"
Cohesion: 0.40
Nodes (3): Sobrescribe los pesos globales en entry_scorer.          Llámese al inicio del b, Después de aplicar, los dicts tienen las mismas keys., TestApplyWeights

### Community 69 - "Community 69"
Cohesion: 0.40
Nodes (4): fetch_candles_parallel(), Any, Descarga paralela de velas con límite de concurrencia., Descarga velas para varios símbolos en paralelo con semáforo compartido.

### Community 70 - "Community 70"
Cohesion: 0.40
Nodes (3): Row, Carga trades históricos con outcome WIN/LOSS desde la BD.          Retorna la ca, Convierte una fila de la BD a un dict interno para calibración.

### Community 71 - "Community 71"
Cohesion: 0.40
Nodes (3): The full load → reevaluate → compare → report cycle runs         without network, backtester must not import pyquotex or similar broker libs., TestNoBrokerIO

### Community 72 - "Community 72"
Cohesion: 0.40
Nodes (3): Todos los pesos en default y by_group suman 100., weight_calibrator must not import pyquotex or broker libs., TestIntegration

### Community 74 - "Community 74"
Cohesion: 0.67
Nodes (3): load_session(), main(), Parse STRAT-A live validation session from consolidation_bot.log.

### Community 76 - "Community 76"
Cohesion: 0.50
Nodes (3): fix_module(), Path, Corrige indentación de métodos sueltos en executor.py y scanner.py.

### Community 78 - "Community 78"
Cohesion: 0.50
Nodes (4): EntryDecision, explain_decision(), Devuelve explicación en lenguaje natural de la decisión., Decisión final de entrada estructurada.

## Knowledge Gaps
- **49 isolated node(s):** `engram`, `CLAUDE.md — Instrucciones para Claude (rol leader)`, `skill-registry.md — Registry de skills (Gentle AI)`, `hub/static/index.html — Dashboard HUB (frontend)`, `progress/current.md — Plantilla sesión actual` (+44 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Candle` connect `Breaker Order Block Detector` to `SMC Analysis Core (FVG/Swings/Bias)`, `Order Block Scan Prefetch`, `Candidate Scoring & Selection`, `Strategy B — Wyckoff Spring`, `Strategy A Consolidation Logic`, `Strategy A Radar (HTF zones)`, `Candle Cache`, `VIP Window Library`, `Strategy A Entry Gates`, `Community 30`, `Community 33`, `Community 34`, `Community 36`, `Community 38`, `Community 42`, `Community 43`, `Community 49`, `Community 52`, `Community 55`, `Community 56`, `Community 58`, `Community 59`, `Community 64`, `Community 69`, `Community 71`, `Community 78`?**
  _High betweenness centrality (0.206) - this node is a cross-community bridge._
- **Why does `ConsolidationBot` connect `Community 36` to `Entry Timing Sync (EntrySynchronizer)`, `Kelly Criterion Sizing`, `Community 35`, `Telegram Alerts & Risk Events`, `Candidate Scoring & Selection`, `Community 41`, `Diversification Enforcer`, `Consolidation Bot Main`, `Community 55`, `Strategy A Radar (HTF zones)`, `HTF Scanner (15m)`, `Candle Cache`, `Masaniello Risk Manager`?**
  _High betweenness centrality (0.129) - this node is a cross-community bridge._
- **Why does `WeightCalibrator` connect `Community 41` to `Community 67`, `Community 36`, `Community 70`, `Community 72`, `Community 45`, `Community 46`, `Community 81`, `Community 51`, `Consolidation Bot Main`, `Community 63`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 57 inferred relationships involving `Candle` (e.g. with `Backtester` and `.load_from_db()`) actually correct?**
  _`Candle` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `AssetScanner` (e.g. with `ConsolidationBot` and `.__init__()`) actually correct?**
  _`AssetScanner` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `TradeExecutor` (e.g. with `ConsolidationBot` and `.__init__()`) actually correct?**
  _`TradeExecutor` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `ConsolidationZone` (e.g. with `._reevaluate_strat_a()` and `ConsolidationBot`) actually correct?**
  _`ConsolidationZone` has 24 INFERRED edges - model-reasoned connections that need verification._