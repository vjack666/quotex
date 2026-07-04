# Diseño: STRAT-A Radar de caza (coarse → fine)

> Inspiración industria: escaneo amplio + watchlist estrecha + alertas en tiempo real
> (QuantConnect universes, Trade Ideas/Scanz screeners, stage-analysis screeners).

## Problema actual

- Cada ciclo descarga **todos** los activos (5m+1m+OB+H1) → ~2–3 min/ciclo.
- Zonas **jóvenes** (<20 min) consumen CPU sin estar listas para trade.
- `pending_reversals` ya espera patrón, pero no hay **lista priorizada** visible ni polling 1m dedicado entre ciclos completos.
- `watched_candidates` solo se usa cuando hay trade abierto (límite concurrente).

## Modelo radar (2 fases)

```
┌─────────────────────────────────────────────────────────────┐
│  FASE A — Radar amplio (cada 3–5 min o cuando watch vacía) │
│  Prefetch 5m+1m → detectar zonas → filtrar "casi listas"    │
└──────────────────────────┬──────────────────────────────────┘
                           │ top-N por readiness_score
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  FASE B — Watchlist cazador (cada 60s, solo pares lista)   │
│  Fetch 1m (+5m ligero si falta) → patrón + rechazo + entry │
└─────────────────────────────────────────────────────────────┘
```

## Criterio "casi lista" (readiness)

Un par entra al watchlist solo si:

| Condición | Rebote | Breakout |
|-----------|--------|----------|
| Zona válida | sí | sí |
| Precio en extremo (techo/piso) | sí | ruptura iniciada |
| Edad zona | ≥ 75% de `ZONE_AGE_REBOUND_MIN` (15 min) | ≥ `ZONE_AGE_BREAKOUT_MIN` (8 min) |
| Payout | ≥ `MIN_PAYOUT` | igual |
| Patrón 1m | pendiente OK (no obligatorio aún) | volumen/ruptura OK |

**readiness_score** (0–100): mezcla de proximidad al extremo, madurez de zona, compresión, payout, bonus si ya está en `pending_reversals`.

Solo pares con `readiness >= STRAT_A_RADAR_MIN_READINESS` (default 70).

## Watchlist

- Máximo `STRAT_A_RADAR_MAX_WATCH` pares (default 5).
- Log cada actualización:
  ```
  [RADAR] Watchlist (3): USDEGP_otc PUT techo readiness=82 | USDZAR_otc PUT techo readiness=78 | ...
  ```
- Si un par deja de estar en extremo o zona expira → se elimina.

## Tick minuto a minuto

Entre escaneos completos, cada `STRAT_A_RADAR_TICK_SEC` (60s):

1. Para cada par en watchlist: fetch 1m (36 velas), precio actual.
2. Re-evaluar `evaluate_strat_a` o `_process_pending_reversals` según estado.
3. Si reglas cumplidas → candidato → `select_best` → ejecutar (misma ruta FASE 5).

Si watchlist vacía → siguiente ciclo es radar amplio inmediato.

## Config propuesta (`config.py`)

```python
STRAT_A_RADAR_ENABLED = True          # activo con STRAT_A_ONLY
STRAT_A_RADAR_MAX_WATCH = 5
STRAT_A_RADAR_MIN_READINESS = 70.0
STRAT_A_RADAR_MIN_AGE_RATIO = 0.75    # 15 min de 20
STRAT_A_RADAR_TICK_SEC = 60
STRAT_A_RADAR_FULL_SCAN_MIN_SEC = 180 # mínimo entre sweeps amplios si hay watchlist
```

## Archivos

| Archivo | Rol |
|---------|-----|
| `src/strat_a_radar.py` | `RadarWatchEntry`, `compute_readiness`, `rank_watchlist` |
| `src/scanner.py` | Actualizar watchlist post-eval; `radar_watch_tick()` |
| `src/consolidation_bot.py` | Estado `radar_watchlist`; loop con ticks 1m |
| `tests/test_strat_a_radar.py` | Unitarios readiness + tick |

## Trazabilidad #22

Evidencia en log: líneas `[RADAR]` + entradas desde watchlist (`_from_radar=True`).