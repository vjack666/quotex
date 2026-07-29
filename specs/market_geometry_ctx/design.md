# Design — Contexto Geométrico M15 (Feature 29)

## Principio

El mercado se EXPERIMENTA, no se memoriza. La geometría es contexto que la
memoria única (F27) y las IAs lectoras (F18 Entry Intelligence, F28 IA de Zonas)
consumen. CERO reglas de detección hardcoded.

## Componentes

### 1. `src/market_geometry_ctx.py` (nuevo, puro cálculo)
- `compute_daily_geometry(candles_15m: List[Candle], asset) -> MarketGeometry`
  - Usa `smc_analysis.detect_structure` (ya existe) sobre ~96 velas M15.
  - Extrae: swing_highs, swing_lows, bias, zonas S/R del día.
  - Filtra swings falsos OTC (cuerpo mínimo, nº de toques).
  - Devuelve estructura libre (dict), no etiqueta "compra/venta".
- `GeometryCache` (LRU por asset, TTL = 1 barra M15 = 900s): evita recalcular
  por candidato. `get(asset, candles_15m) -> MarketGeometry`.
- `level_role(ctx, price) -> {"distance_to_nearest_swing", "is_support",
  "is_resistance", "touches"}` — solo métricas, sin decidir.

### 2. `observation.py` (F27, extiende capturador)
- En el arco de experiencia, guarda en `contexto_previo`:
  `geometry = {swing_lows, swing_highs, bias, level_role_del_nivel}`.
- Así la memoria aprende "PUT en swing low diario → LOSS" (como EURJPY).

### 3. `zone_ia.py` (F28, lectora)
- `_zone_confidence_for_level` ya clustering por nivel. Se le suma el
  `level_role` del contexto geométrico como FEATURE de consulta (no regla):
  experiencias en nivel que es swing low → peso en WR. Sin cambiar la lógica.

### 4. `entry_scorer.py` (dirección en extremo, RG6)
- Nuevo `_score_extreme_direction(entry, geom)` (detrás de
  `MARKET_GEOMETRY_ENABLED`): si el nivel está en un extremo (swing o piso/techo
  de zona) y la vela de entrada NO tiene cuerpo a favor → penaliza la dirección
  (o sugiere inversión). Aditivo leve, no veto duro.
- Consenso (RG4): `direction_score = w1*zone_confidence + w2*geom_role +
  w3*body_confirm`. Sin una sola fuente como veto.

### 5. Scanner / cache de velas
- El scanner YA trae `candles_15m` (tf_sec=900) por asset. Se cachea la
  geometría una vez por barra (RG2). Se pasa al candidato como
  `entry.geometry = MarketGeometry`.

## Flujo

```
candles_15m (OTC, tf=900) ──► GeometryCache ──► MarketGeometry
                                            │
        observation (captura) ──┐            │
                                ▼            ▼
                        memoria única ◄── zona_ia (zone_confidence)
                                            │
                            entry_scorer (consenso + cuerpo en extremo)
```

## Costo / rendimiento
- 1 cálculo `detect_structure` por asset por 900s. Con ~20-40 assets activos =
  ~1-3 calculos/min. Despreciable.
- Sin LLM en hot path (determinista).

## Riesgos
- Ruido OTC → swings falsos. Mitigado por filtro de cuerpo mínimo + nº toques.
- Cache stale → TTL 900s con revalidación por timestamp de última vela.
