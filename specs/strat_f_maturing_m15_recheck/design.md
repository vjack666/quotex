# Design — strat_f_maturing_m15_recheck

> Feature #16 (SDD). Decisiones técnicas ANTES de tocar código.

## Frontera con el código existente

La regla R1 de `evaluate_strat_f` (strat_fractal.py:274-277) YA es correcta y
se mantiene intacta. El bug está en la **promoción**, no en la evaluación. Por
eso el fix se hace en el punto donde `maturing_watchlist` suelta la entrada, no
en `evaluate_strat_f`.

## Archivos afectados

| Archivo | Cambio |
|---|---|
| `src/strat_fractal.py` | Nueva función pura `recheck_m15_alignment(candles_15m, direction) -> bool` (reusa `_m15_context`). Y helper `stoch_m5_exhausted(stoch_k, direction) -> bool` (umbrales 20/80). |
| `src/scanner.py` | En el bloque que agenda `("mark_promoted", (key, mode))` (líneas ~2399, ~2351), antes de agendar: re-evaluar `m15_context` actual del activo; si contra-tendencia, exigir stoch M5 en extremo. Si no hay confirmación → agendar `("drop", (key, reason))` en vez de `mark_promoted`. |
| `src/maturing_watchlist.py` | Sin cambio de firma. El handler `mark_promoted` (línea 2529) ya borra la entrada; el `drop` ya existe. Solo se decide EN EL SCANNER qué agendar. |
| `tests/test_strat_f_maturing_recheck.py` | Nuevo test (ver R1-R5). |

## Firmas nuevas (propuestas)

```python
# src/strat_fractal.py
def recheck_m15_alignment(candles_15m: List[Candle], direction: str) -> bool:
    """True si direction está ALINEADA con M15 actual (no contra-tendencia)."""

def stoch_m5_exhausted(stoch_k: Optional[float], direction: str) -> bool:
    """Confirmación de agotamiento: CALL contra-M15-bajista -> stoch<20;
    PUT contra-M15-alcista -> stoch>80. None/otro -> False."""
```

## Dónde se obtiene el stoch M5 actual

El log ya muestra `stoch_extreme_against` (modo hard) → el stoch M5 SE CALCULA
en el pipeline. Al promover, el scanner debe disponer de `stoch_m5` del activo
en ese ciclo. Si el `ScanCycleData` no lo trae hoy, se agrega el campo
`stoch_m5: dict[str, float]` al ciclo (prefetch ya baja M5; el stoch es
cálculo barato, sin I/O nueva). ESTO se confirma en fase de implementación
(lectura de `scanner.py` prefetch) antes de escribir el test.

## Alternativas descartadas

1. **Mover el re-chequeo a `evaluate_strat_f`**: descartado. La evaluación
   fresca ya filtra R1; el agujero es la promoción diferida, no la evaluación.
   Meter stoch ahí duplicaría lógica y no arreglaría las entradas maduradas.
2. **TTL más corto en maturing_watchlist**: descartado. Acorta la espera pero
   no garantiza que al soltar la entrada la tendencia no haya virato. No resuelve
   la raíz (contexto viejo).
3. **Eliminar la sala de espera (R3 young)**: descartado. La maduración de
   zonas jóvenes es útil; el problema es solo el re-chequeo al soltar.

## Riesgos

- **Stoch falso de agotamiento**: si el stoch da señal de extremo pero el
  contra-movimiento continuía, se entra tarde/contra. Mitigado porque solo se
  usa como CONFIRMACIÓN de una entrada ya contra-tendencia (no como disparador
  primario). R4 descarta si no hay confirmación.
- **Massaniello**: R7 garantiza que la espera no quema operaciones. El `buy()`
  real es el único que incrementa el conteo.
- **Complejidad de estado**: la watchlist YA existe y retiene; solo se agrega
  una rama de decisión al promover. No se crea un watcher nuevo (reusa el ciclo
  de scanner que ya re-evalúa la watchlist).
