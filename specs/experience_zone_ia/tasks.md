# Tasks — IA de Zonas (Feature 28)

> Feature ID: 28 · status: done (2026-07-24)
> Reemplaza `zone_memory.py`. Depende de Feature 27 (memoria única).

---

## Fase 1 — Módulo Zone IA (lector de memoria)

- [x] T1 — Crear `src/zone_ia.py` con `ZoneIA.score(candidate, similars)` que
      descubre zonas por clustering de proximidad de `evento.nivel` y emite
      `zone_confidence` ∈ [0,1]. Cubre: RZ1, RZ3, RZ6.
- [x] T2 — Test: con memoria real, la IA descubre zonas sin reglas y emite
      confidence coherente (zona WR alto → confidence alto). Cubre: RZ8a, RZ8b.

## Fase 2 — Modo activo (reusa engine F27)

- [x] T3 — Cablear `ZoneIA` en `entry_scorer._finalize_scoring` vía
      `ExperienceEngine` (reutiliza `query_similar` + agregación).
      Cubre: RZ5, RZ7.
- [x] T4 — Test: inyectar experiencias de zona similares dispara `zone_confidence`.
      Cubre: RZ8d (solo lectura: memoria no crece).

## Fase 3 — Reemplazo en STRAT-A / STRAT-F

- [x] T5 — `entry_scorer._score_zone_memory_adj` → `_score_zone_ia` (detrás
      `ZONE_IA_ENABLED`). Cubre: RZ4a, RZ9.
- [x] T6 — Veto "zone_memory wall" en scanner/decision_engine → umbral de
      `zone_confidence`. Cubre: RZ4b.
- [x] T7 — ELIMINAR `src/zone_memory.py`; retirar imports en scanner,
      entry_scorer, entry_decision_engine, models. Cubre: RZ4, RZ6.
- [x] T8 — Test: bot arranca sin imports de `zone_memory`; `test_htf_zone_wiring`
      migrado a `zone_confidence`. Cubre: RZ8c.

## Fase 4 — Validación y cierre

- [x] T9 — Seed/validación: WR por zona desde memoria real reproducible.
      Cubre: RZ2.
- [x] T10 — `progress/impl_experience_zone_ia.md` con mapa RZ<n> → test.
      Cubre: RZ8.
- [x] T11 — Marcar feature `done` en `feature_list.json` tras tests verdes.
