# Plan de reestructuración del repositorio

## Objetivo

Reducir complejidad accidental sin cambiar la lógica de trading de forma silenciosa. Cada movimiento debe preservar imports, tests y comportamiento operativo.

## Clasificación adoptada

- `src/decision/`: scoring final, vetos y política de aprobación.
- `src/strategies/`: lógica específica de estrategias; solo se moverá después de verificar referencias.
- `src/execution/`: broker, órdenes y lifecycle de trades.
- `src/risk/`: Massaniello, sizing y límites de exposición.
- `src/data/`: candles, conexión y caches de mercado.
- `src/lab/`: backtests, análisis y experimentos reproducibles.
- `tests/`: tests unitarios/integración.
- `docs/`: arquitectura, operación y auditorías.

## Reglas de seguridad

1. No eliminar un módulo solo porque parezca viejo.
2. Antes de mover un módulo: localizar imports/referencias.
3. Durante la transición, usar shims de compatibilidad cuando reduzcan riesgo.
4. No mezclar refactor estructural con cambios de estrategia.
5. No mover datos runtime, logs, sesiones ni caches al repositorio.
6. Cada lote de cambios debe poder revertirse mediante Git.

## Fase actual

### Completado

- Limpieza de perfiles/caches locales.
- `graphify-out/` retirado y bloqueado por `.gitignore`.
- Creado `src/decision/`.
- `entry_decision_engine.py` trasladado a `src/decision/entry_decision_engine.py`.
- `src/entry_decision_engine.py` convertido en shim de compatibilidad para no romper consumidores existentes.

### Siguiente lote

1. Mapear dependencias de `entry_scorer.py` y decidir si pertenece al mismo dominio `decision/`.
2. Auditar `scanner.py` como orquestador de señales y reducir responsabilidades sin cambiar comportamiento.
3. Separar módulos de ejecución, riesgo y datos solo cuando el grafo de imports lo permita.
4. Revisar estrategias duplicadas/antiguas y retirar únicamente código sin consumidores.
5. Revisar documentación duplicada (`Documentos/`, `docs/`, `progress/`, `agent/`) y conservar una única fuente de verdad por tema.
6. Ejecutar la batería de tests y corregir imports después de cada lote.

## Hallazgos importantes

`entry_scorer.py` calcula/modula el score, mientras `entry_decision_engine.py` aplica vetos y clasifica A/B/C/REJECT. Son responsabilidades distintas aunque comparten umbrales. Por eso se agrupan en el dominio `decision`, pero no se fusionan todavía.

`scanner.py` concentra demasiadas responsabilidades: prefetch, evaluación de estrategias, radar, STRAT-F, journal, Edificio y selección/ejecución. Es el principal candidato a una segunda refactorización, pero requiere análisis de dependencias antes de partirlo.

## Criterio de finalización

El repositorio estará ordenado cuando cada módulo tenga una responsabilidad principal clara, las dependencias fluyan hacia capas inferiores y no existan duplicados funcionales sin una razón explícita.
