# Arquitectura — Qué significa "hacer un buen trabajo"

> Este documento define el estándar de calidad. Los agentes revisores
> evalúan código contra este archivo. Si no está aquí, no es un requisito.

## Principios

1. **Capas claras.** El proyecto tiene cuatro capas y solo cuatro:
   - **Conexión** (`connection.py`) — WebSocket con pyquotex, reconexión, heartbeat.
   - **Análisis** (`scanner.py`) — descarga y caché de velas, detección de zonas/patrones.
   - **Estrategias** (`strat_a.py`, `strat_b.py`, `strat_momentum.py`, ...) — lógica de señal pura, sin I/O.
   - **Ejecución** (`executor.py`) — scoring, selección, envío de órdenes, gestión de capital.
   No mezclar responsabilidades. Una función hace una cosa.

2. **Separación estrategia-ejecución.** Las estrategias NO llaman al broker.
   Devuelven `CandidateEntry` con score. El `executor` decide si opera.

3. **Dependencias externas mínimas.** Solo `pyquotex`, `python-dotenv`, `pandas`, `loguru`.
   Si una feature requiere una dependencia nueva, primero se discute (estado `blocked`).

4. **Errores explícitos.** Las funciones que pueden fallar lanzan excepciones nombradas,
   no devuelven `None` ni `False` silencioso.

5. **Estado en SQLite.** Todo estado transaccional (sesión Massaniello, ciclo, streak) se
   persiste en `trade_journal.db`. El bot debe poder reiniciarse sin pérdida.
   *(Persistencia Massaniello: feature #11 `massaniello_persistence`, pendiente.)*

6. **Tests sin broker.** Todo test usa datos grabados o sintéticos. Nunca depende de
   conexión real a Quotex.

## Flujo de datos HFT

```
Broker (Quotex WebSocket)
    │
    ▼
connection.py (keepalive, reconexión)
    │
    ▼
scanner.py (descarga paralela + caché)
    │
    ├──► strat_a.py     (consolidación)
    ├──► strat_b.py     (spring/upthrust)
    ├──► strat_momentum.py      [pendiente #6]
    ├──► strat_swing_reversal.py [pendiente #7]
    └──► strat_order_block.py   [pendiente #8]
    │
    ▼
entry_scorer.py (score 0-100 por candidato)
    │
    ▼
executor.py (selecciona mejor, gestiona capital, envía orden)
    │
    ├──► massaniello_risk.py  (gestión de riesgo activa — 5 ops / 3 ITM)
    ├──► kelly_sizer.py       (complemento opcional — pendiente #13)
    └──► diversifier.py       (límites por activo — pendiente #14)
    │
    ▼
trade_journal.py (SQLite: candidatos, outcomes, estado)
    │
    ▼
hub/ (monitoreo WebSocket en vivo — pendiente #12)
```

## Gestión de riesgo (estado actual)

| Componente | Rol | Estado |
|------------|-----|--------|
| `massaniello_engine.py` | Motor matemático (tabla de stakes) | ✅ activo |
| `massaniello_risk.py` | Gestor de sesión (ops, wins, timeout) | ✅ activo |
| `martingale_calculator.py` | Legacy — no usar en código nuevo | ⚠️ deprecado |

Parámetros de sesión (`config.py`):

- `MASSANIELLO_OPERATIONS = 5`
- `MASSANIELLO_EXPECTED_WINS = 3`
- `SESSION_MAX_MIN = 60`
- Cuenta forzada a `PRACTICE` en demo

## Módulos por capa (implementados)

| Capa | Módulos |
|------|---------|
| Facade | `consolidation_bot.py`, `main.py` |
| Conexión | `connection.py` |
| Análisis | `scanner.py`, `entry_scorer.py` |
| Estrategias | `strat_a.py`, `strat_b.py`, `strategy_spring_sweep.py`, `candle_patterns.py` |
| Ejecución | `executor.py`, `massaniello_engine.py`, `massaniello_risk.py` |
| Soporte | `config.py`, `models.py`, `errors.py`, `loop_utils.py`, `trade_journal.py` |

## Qué NO hacer

- No mezclar lógica de broker con lógica de estrategia.
- No usar `time.sleep()` en flujos asíncronos (usar `asyncio.sleep()`).
- No leer/escribir archivos en cada ciclo de escaneo.
- No depender de `consolidation_bot.log` para estado interno (usar BD).
- No añadir features sin spec aprobado.
- No usar `MartingaleCalculator` en código nuevo (usar `MassanielloRiskManager`).