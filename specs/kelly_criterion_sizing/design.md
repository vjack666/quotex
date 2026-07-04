# Design — kelly_criterion_sizing

## Módulo nuevo

`src/kelly_sizer.py` — clase `KellySizer`:

| Método | Firma | Qué hace |
|--------|-------|----------|
| `calculate` | `(asset=None, strategy=None, fractional=0.25) -> float` | Calcula factor Kelly fraccional |
| `close` | `() -> None` | Cierra conexión BD |

### `calculate()`

1. Obtiene win rate desde `candidates` table
2. Obtiene payout promedio desde la misma tabla
3. Aplica Kelly completo: `full = (p * (b + 1) - 1) / b`
4. Acota a [0.0, 1.0]
5. Aplica fracción: `result = full * fractional`
6. Retorna `max(0.0, min(1.0, result))`

### Conexión BD

- Usa el mismo directorio `data/db/` que `trade_journal.py`
- Elige el archivo `trade_journal-*.db` más reciente por mtime
- Usa `sqlite3.Row` para acceso por nombre de columna
- WAL mode permite lecturas concurrentes con el Journal

### Win rate

```sql
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) AS wins
FROM candidates
WHERE decision = 'ACCEPTED'
  AND outcome IN ('WIN', 'LOSS')
```

Si hay menos de `MIN_TRADES` (10) filas, retorna 0.0.

### Payout promedio

```sql
SELECT AVG(payout) AS avg_payout
FROM candidates
WHERE decision = 'ACCEPTED'
  AND outcome IN ('WIN', 'LOSS')
  AND payout IS NOT NULL
```

Se convierte a ratio (85 → 0.85).

## Integración en consolidation_bot.py

Inserto el siguiente código después del bloque de carga de pesos calibrados
(línea ~303) y antes del inicio del HTF scanner:

```python
# ── Kelly Criterion Sizing ──────────────────────────────────────────────
try:
    from kelly_sizer import KellySizer
    _kelly = KellySizer()
    _kelly_factor = _kelly.calculate()
    if _kelly_factor > 0.0:
        if bot.massaniello._initial_capital is not None:
            _old = bot.massaniello._initial_capital
            bot.massaniello._initial_capital *= _kelly_factor
            log.info(
                "✅ Kelly sizing: capital %.2f → %.2f (factor=%.4f)",
                _old, bot.massaniello._initial_capital, _kelly_factor,
            )
    else:
        log.info("⏸️ Kelly factor %.4f — sin ajuste", _kelly_factor)
    _kelly.close()
except Exception as exc:
    log.warning("⚠️ Kelly sizing no disponible: %s", exc)
```

## Alternativa descartada

**Kelly por activo/estrategia**: se descartó para la primera versión porque
la mayoría de activos tienen menos de 10 trades. Se implementa con filtro
global. Los parámetros `asset` y `strategy` quedan en la firma para uso
futuro.

**Sobrescribir balance completo**: se descartó modificar `current_balance`
porque Massaniello usa `_initial_capital` como base de la tabla de
multiplicadores. Modificar `current_balance` rompería el seguimiento de
pérdidas/ganancias de la sesión.
