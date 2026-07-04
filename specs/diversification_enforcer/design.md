# Design — diversification_enforcer

## Clase: `DiversificationEnforcer`

Archivo: `src/diversification_enforcer.py`

### Constructor
```
__init__(max_simultaneous_trades: int, min_asset_spread: int, max_entries_per_asset: int)
```

### Método público
```
check(open_trades: dict[str, TradeState], candidate_asset: str) -> tuple[bool, str]
```
- `open_trades`: `bot.trades` (dict con activo → TradeState)
- `candidate_asset`: símbolo del activo que se quiere entrar
- Retorna `(True, "")` si permite, `(False, "razón")` si rechaza

### Lógica de check
1. Si `len(open_trades) >= max_simultaneous_trades` → rechazar
2. Si `len(open_trades) > 0` y `unique_assets < min_asset_spread` → rechazar
3. Si `count_entries_for_asset >= max_entries_per_asset` → rechazar
4. Si pasa todo → permitir

## Integración en scanner

Se inyecta desde `ConsolidationBot` al scanner vía `self.bot.diversification_enforcer`.

Dos puntos de guardia:
1. **`_scan_phase_evaluate_assets`** — antes de `enter_trade` de STRAT-B (línea ~1172)
2. **`_scan_phase_select_execute`** — antes de cada `enter_trade` para winners seleccionados (línea ~1894)

Martingala (`stage="martin"`) queda EXENTA de la verificación de diversificación
para no romper la recuperación de ciclo.

## Constantes en config.py

```python
MAX_SIMULTANEOUS_TRADES = 3
MIN_ASSET_SPREAD = 2
MAX_ENTRIES_PER_ASSET = 1
```

## Alternativa descartada

Centralizar la verificación exclusivamente en `TradeExecutor.enter_trade()`.
Motivo: es más encapsulado, pero introduce un side effect silencioso en un método
que el resto del sistema usa como "pasa orden al broker". Preferimos guardia
explícita en el scanner antes de la llamada para mantener logging claro.

## Trazabilidad tests

| Test | R cubierto |
|------|-----------|
| `test_rejects_exceeding_max_simultaneous` | R1 |
| `test_allows_below_max_simultaneous` | R1 |
| `test_rejects_low_asset_spread` | R2 |
| `test_rejects_exceeding_max_per_asset` | R3 |
| `test_logs_rejection_reason` | R4 |
| `test_allows_when_zero_trades` | R5 |
| `test_allows_martin_exempt` | R1, R5 |
