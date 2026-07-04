# Design — strategy_order_block

## Módulo

`src/strat_order_block.py` — función principal:

```python
def detect_order_block_entry(
    candles_1m: list[Candle],
    blocks: list[OrderBlock] | None = None,
    tolerance: float = 0.05,
) -> Optional[tuple[str, float]]:
```

## Reglas de detección de OB

1. **OB alcista**: vela roja (`close < open`) con cuerpo >= 1.5× promedio,
   seguida de 2+ velas verdes con cuerpos fuertes. Rango del OB: `[low, high]`
   de la vela base.
2. **OB bajista**: vela verde (`close > open`) con cuerpo >= 1.5× promedio,
   seguida de 2+ velas rojas con cuerpos fuertes. Rango del OB: `[low, high]`
   de la vela base.

## Mitigación

Un OB se mitiga CUANDO una vela cierra completamente fuera del rango del OB
por el lado opuesto a la dirección esperada (bullish OB → precio cierra bajo
`low`; bearish OB → precio cierra sobre `high`). Los OBs mitigados NO generan
señal.

## Entry trigger

El precio debe _revisitar_ el rango del OB: la mecha de una vela debe tocar
dentro del `[price_start, price_end]` con tolerancia configurable (default
5%). No se requiere cierre dentro del rango — en binary options el entry es
inmediato.

## Reuso de detect_order_blocks existente

`detect_order_blocks` en `src/scan_prefetch.py` ya implementa la detección
base. `detect_order_block_entry` acepta `blocks: list[OrderBlock] | None`:
- Si se proveen → evalúa entry sobre esos bloques (modo pipeline)
- Si `None` → llama a `detect_order_blocks(candles_1m)` internamente

## Integración scanner

En `scanner.py`, nuevo bloque después de reversal-swing (si existe) y antes de
STRAT-A:

```python
if not _runtime_config.STRAT_A_ONLY and STRAT_ORDER_BLOCK_ENABLED:
    ob_hit = detect_order_block_entry(candles_1m)
    if ob_hit:
        direction, strength = ob_hit
        pseudo_zone = ConsolidationZone(
            top=max(ob.price_start, ob.price_end),
            bottom=min(ob.price_start, ob.price_end),
            mode=SignalMode.REBOUND,
        )
        entry = CandidateEntry(
            asset=asset, payout=..., zone=pseudo_zone,
            direction=direction, candles=candles_1m,
            score=strength,
            score_breakdown={'ob_strength': strength},
            reversal_pattern='order_block',
            reversal_strength=strength,
            mode=SignalMode.REBOUND,
            _strategy_origin='STRAT-ORDER-BLOCK',
        )
```

## Constantes en config.py

```python
STRAT_ORDER_BLOCK_ENABLED = True
STRAT_ORDER_BLOCK_MIN_STRENGTH = 30  # score mínimo 0-100
```

## Scoring

- `strength` se normaliza en `[0, 1]` basado en relación cuerpo/avg_body del
  OB y distancia del retroceso al rango
- Score final = `strength * 100` (mismo escalado que momentum)
- Se reusan pesos REBOUND en el scoring pipeline

## Alternativas consideradas

| Alternativa | Descartada por |
|---|---|
| Usar solo OBs en 5m | Entradas más lentas; binary options necesita frames cortos |
| Confirmación volumétrica | Sin datos de volumen confiables en OTC |
| Multi-timeframe confluence | Complejidad extra sin beneficio claro en 1m |

## Fuera de alcance

- Multi-timeframe OB confluence
- Volume-based OB confirmation
- Auto-trade independiente (entra al pipeline de scoring común como REBOUND)
