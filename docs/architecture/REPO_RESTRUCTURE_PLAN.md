# Plan de reestructuración del repositorio

## Objetivo

Reducir complejidad accidental sin cambiar la lógica de trading de forma silenciosa. Cada movimiento debe preservar imports, tests y comportamiento operativo.

## Arquitectura objetivo

- `src/core/`: orquestación mínima y ciclo principal.
- `src/decision/`: scoring, vetos y política de aprobación.
- `src/strategies/`: lógica específica de estrategias.
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
7. Preferir cambios pequeños y verificables sobre una reescritura masiva.

## Trabajo aplicado

### Limpieza

- Perfiles y caches locales eliminados.
- `graphify-out/` bloqueado por `.gitignore`.
- Caché de skills y configuración local de VS Code eliminadas.

### Dominio decision

- Creado `src/decision/`.
- `entry_decision_engine.py` trasladado a `src/decision/entry_decision_engine.py`.
- `src/entry_decision_engine.py` convertido en shim de compatibilidad.
- `entry_scorer.py` permanece temporalmente en `src/` hasta completar el mapa de consumidores.

### Dominio risk

- Creado `src/risk/`.
- `massaniello_engine.py` trasladado a `src/risk/massaniello_engine.py`.
- `massaniello_risk.py` trasladado a `src/risk/massaniello_risk.py`.
- Ambos módulos originales conservan shims para evitar romper consumidores durante la migración.

## Auditoría de responsabilidades

### Scanner

`scanner.py` concentra actualmente demasiadas responsabilidades: prefetch, evaluación de estrategias, radar, STRAT-F, journal, Edificio, scoring y selección/ejecución. No se moverá como bloque. Se extraerán responsabilidades por dependencia y con compatibilidad temporal.

### Decision

`entry_scorer.py` calcula/modula el score, mientras `entry_decision_engine.py` aplica vetos y clasifica A/B/C/REJECT. Son responsabilidades distintas aunque comparten umbrales. Se agrupan en el mismo dominio, pero no se fusionan.

### Risk

`massaniello_engine.py` contiene el cálculo puro/simulador; `massaniello_risk.py` contiene el estado de sesión y la integración operativa. Son complementarios, no duplicados, y ahora viven juntos bajo `src/risk/`.

## Próximos lotes automáticos

1. Mover `entry_scorer.py` a `src/decision/` con shim, después de verificar consumidores.
2. Auditar y extraer de `scanner.py` únicamente prefetch/data y utilidades claramente independientes.
3. Agrupar módulos de ejecución bajo `src/execution/` sin alterar el API público interno.
4. Agrupar estrategias reales bajo `src/strategies/`, manteniendo shims mientras se actualizan consumidores.
5. Detectar scripts duplicados y módulos sin consumidores; eliminar solo los demostrablemente muertos.
6. Consolidar documentación duplicada entre `Documentos/`, `docs/`, `progress/` y `agent/`, conservando una fuente de verdad por tema.
7. Actualizar README, comandos de arranque y configuración de agentes cuando termine la nueva estructura.
8. Ejecutar tests/import checks después de cada lote.

## Criterio de finalización

El repositorio estará ordenado cuando cada módulo tenga una responsabilidad principal clara, las dependencias fluyan hacia capas inferiores, los imports legacy hayan desaparecido o estén explícitamente justificados y no existan duplicados funcionales sin una razón documentada.
