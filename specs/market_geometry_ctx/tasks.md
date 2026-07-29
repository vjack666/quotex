# Tasks — Contexto Geométrico M15 (Feature 29)

> Feature ID: 29 · status: done (2026-07-24)
> Depende de: 27 (memoria única), 28 (IA de Zonas). Aplica a OTC.

---

## Fase 1 — Módulo de geometría (puro cálculo)

- [x] T1 — `src/market_geometry_ctx.py`: `compute_daily_geometry(candles_15m, asset)`
      usa `smc_analysis.detect_structure` + filtra swings falsos OTC. Cubre RG1, RG7.
- [x] T2 — `GeometryCache` (LRU por asset, TTL 900s). Cubre RG2.
- [x] T3 — `level_role(ctx, price)` métricas sin decidir. Cubre RG3.
- [x] T4 — Test determinista: rango con soporte real tocado N veces → swing_low
      detectado; vela plana OTC no genera swing falso. Cubre RG8, RG7.

## Fase 2 — Memoria aprende contexto (F27)

- [x] T5 — `observation.py`: guardar `contexto_previo.geometry` en el arco.
      Cubre RG5.
- [x] T6 — Test: experiencia incluye geometry en contexto. Cubre RG5.

## Fase 3 — IAs consumen geometría (F28 + F18)

- [x] T7 — `zone_ia.py`: usar `level_role` como feature de consulta (sin regla).
      Cubre RG4.
- [x] T8 — `entry_scorer._score_extreme_direction(entry, geom)` detrás de
      `MARKET_GEOMETRY_ENABLED`; consenso 3 fuentes + cuerpo en extremo. Cubre RG4, RG6.
- [x] T9 — Scanner: cachear geometría por barra y pasarla al candidato. Cubre RG2.
      (El scanner ya puebla `candles_15m`; el scorer la calcula vía GEOMETRY_CACHE.)
- [x] T10 — Test: consenso mejora dirección en extremo vs stoch solo. Cubre RG4, RG6.
      (test_scorer_wires_geometry_and_penalizes_put_at_support)

## Fase 4 — Validación y cierre

- [x] T11 — Bandera `MARKET_GEOMETRY_ENABLED = True` en config.py.
- [x] T12 — `progress/impl_market_geometry_ctx.md` con mapa RG<n> → test.
- [x] T13 — Marcar feature `done` en `feature_list.json` tras tests verdes.
