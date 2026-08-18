# Plan de reestructuración del repositorio

## Objetivo
Reducir complejidad accidental sin cambiar la lógica de trading de forma silenciosa. Cada movimiento debe preservar imports, tests y comportamiento operativo.

## Clasificación adoptada
- `src/core/`: orquestación mínima y ciclo principal.
- `src/decision/`: scoring, vetos, clasificación y política de aprobación.
- `src/strategies/`: lógica específica de estrategias.
- `src/execution/`: broker, órdenes y lifecycle de trades.
- `src/risk/`: Massaniello, sizing y límites de exposición.
- `src/data/`: candles, conexión y caches de mercado.
- `src/ml/`: modelos, features y memoria/experiencia cuando proceda.
- `src/lab/`: backtests, análisis y experimentos reproducibles.
- `tests/`: tests unitarios/integración.
- `docs/`: arquitectura, operación y auditorías.

## Reglas de seguridad
1. No eliminar un módulo solo porque parezca viejo.
2. Antes de mover un módulo: localizar imports/referencias.
3. Durante la transición, usar shims de compatibilidad cuando reduzcan riesgo.
4. No mezclar refactor estructural con cambios de estrategia.
5. No mover datos runtime, logs, sesiones ni caches al repositorio.
6. Cada lote debe poder revertirse mediante Git.
7. No borrar un shim hasta comprobar que no quedan consumidores del path antiguo.

## Completado
- Limpieza de perfiles/caches locales.
- `graphify-out/` retirado y bloqueado por `.gitignore`.
- `src/decision/` creado.
- `entry_decision_engine.py` trasladado a `src/decision/entry_decision_engine.py` con shim.
- `src/risk/` creado.
- `massaniello_engine.py` y `massaniello_risk.py` trasladados al dominio `risk` con shims.
- `src/data/` creado.
- `candle_cache.py` trasladado al dominio `data` con shim.
- `entry_scorer.py` ya tiene facade `src/decision/entry_scorer.py`; la implementación original permanece hasta migrar consumidores.

## Próximo lote automático
1. Auditar consumidores de `entry_scorer` y migrarlos a `decision.entry_scorer`.
2. Auditar `scanner.py` y extraer primero piezas puras/aisladas.
3. Mover módulos de conexión/candles al dominio `data` solo cuando el grafo de imports lo permita.
4. Separar ejecución y riesgo restantes.
5. Clasificar estrategias y retirar únicamente módulos sin consumidores.
6. Revisar documentación duplicada (`Documentos/`, `docs/`, `progress/`, `agent/`) y conservar una única fuente de verdad por tema.
7. Añadir/fortalecer CI para imports y tests antes de eliminar shims.

## Criterio de finalización
Cada módulo debe tener una responsabilidad principal clara, las dependencias deben fluir hacia capas inferiores y no deben existir duplicados funcionales sin una razón explícita.
