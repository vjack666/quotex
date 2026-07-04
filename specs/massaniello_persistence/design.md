# Design — massaniello_persistence

## Tabla SQLite

Nueva tabla `massaniello_state` en `trade_journal.db`:

```sql
CREATE TABLE IF NOT EXISTS massaniello_state (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    saved_at         TEXT NOT NULL,          -- ISO UTC del momento del guardado
    operations       INTEGER NOT NULL,
    expected_wins    INTEGER NOT NULL,
    session_max_min  INTEGER NOT NULL,
    session_start_time REAL,                 -- float timestamp (time.time())
    entries          INTEGER NOT NULL DEFAULT 0,
    wins             INTEGER NOT NULL DEFAULT 0,
    losses           INTEGER NOT NULL DEFAULT 0,
    current_balance  REAL,
    initial_capital  REAL,
    session_active   INTEGER NOT NULL DEFAULT 1  -- bool: 1 = sesión vigente
);
```

Se añade vía `Journal._ensure_schema_upgrades()` o por migración suave en el módulo de persistencia.

## Módulo / clase

`MassanielloPersistence` en `src/massaniello_persistence.py` (nuevo módulo):

| Método | Firma | Qué hace |
|--------|-------|----------|
| `save` | `(manager: MassanielloRiskManager) -> int` | INSERT del estado actual, devuelve row_id |
| `load` | `() -> dict \| None` | SELECT última fila ORDER BY id DESC |
| `apply` | `(manager: MassanielloRiskManager, state: dict) -> None` | Restaura campos en el manager |

### `save(manager)`

- Toma todos los campos de `MassanielloRiskManager` (operations, expected_wins, session_max_min, session_start_time, entries, wins, losses, current_balance, _initial_capital)
- Calcula `session_active` según `manager.can_enter()`
- Inserta nueva fila en `massaniello_state`
- Usa conexión de `get_journal()` (misma BD)

### `load()`

- `SELECT * FROM massaniello_state ORDER BY id DESC LIMIT 1`
- Retorna `dict` con row si existe, `None` si no hay filas
- Si hay excepción de integridad/corrupción → log warning + retorna `None`

### `apply(manager, state)`

- Asigna `manager.operations`, `manager.expected_wins`, `manager.session_max_min`
- Asigna `manager.session_start_time`, `manager.entries`, `manager.wins`, `manager.losses`
- Asigna `manager.current_balance`, `manager._initial_capital`
- No modifica si el estado es inválido (valores negativos, tipos incorrectos)

## Integración executor

### Post-operación (save)

En `executor.py`, dentro de `_resolve_trade`, después de llamar a `mgr.register_win()` o `mgr.register_loss()`:

```
MassanielloPersistence.save(bot.massaniello)
```

Se ejecuta tras cada WIN/LOSS confirmado.

### Inicio del bot (load)

En el arranque del bot (ej. `consolidation_bot.py` o `main.py`), antes del primer ciclo de escaneo:

```
state = MassanielloPersistence.load()
if state:
    MassanielloPersistence.apply(bot.massaniello, state)
else:
    # valores por defecto ya están por el constructor
    log.info("Sin estado Massaniello previo — arrancando con defaults")
```

## Alternativa descartada

**JSON file**: se descartó porque la BD ya es la fuente de verdad para el journal de trades. Usar SQLite evita tener dos sistemas de persistencia y permite consultar histórico de sesiones desde la misma BD.
