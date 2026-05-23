# QUANT ENGINE - Arquitectura Operativa

## Capas del sistema

1. Data Layer
- Fuente de velas y precios dentro de `scan_all`.
- Cache por simbolo para 1m/5m y telemetria de calidad de datos.

2. Strategy Layer
- STRAT-B (Spring/Wyckoff) en `src/consolidation_bot.py`.
- BoB (Breaker Order Block) en `src/breaker_order_block.py`.
- Estrategias desacopladas: cada una produce su propia semantica.

3. Signal Layer
- Modelo unificado de señal en `src/quant_engine/models.py`.
- Router multi-estrategia con deduplicacion por simbolo en `src/quant_engine/signal_router.py`.

4. Risk Layer
- Gate unificado de riesgo via `_pre_validate_entry(...)`.
- Todas las señales confirmadas pasan por validacion antes de ejecutar.

5. Execution Layer
- Entrada unificada via `_enter(...)` con `strategy_origin`.
- Broker queda desacoplado del detector de estrategias.

6. Monitoring Layer
- Estado por ciclo en terminal con `render_control_center(...)`.
- Dashboard textual de señales, fases y top-signal del router.

## Flujo operativo

1. Data snapshot por simbolo.
2. Estrategias generan señales tipadas.
3. Signal Router prioriza y deduplica.
4. Risk valida cada señal confirmada.
5. Execution procesa solo señales aprobadas.
6. Monitoring publica estado del ciclo.

## Reglas de diseño

- No mezclar logica de estrategias.
- No ejecutar desde detectores.
- Ejecutar solo desde capa de router + riesgo.
- Persistir evidencias en journal para auditoria.
- Sistema extensible: agregar estrategia = emitir `StrategySignal`.
