# Tasks — Experience Engine (Market Memory)

> Feature ID: 27 · status: done (aprobada y verificada 2026-07-24)
> Cada task referencia al menos un `R<n>` de requirements.md.
> Verificación: 73 tests passed (engine + observación + ML + distribución);
> seed OFFLINE = 211 experiencias reales en data/market_memory/.

---

## Fase 1 — Definición del arco (sin I/O)

- [x] T1 — Crear `src/experience_schema.py` con dataclass `MarketExperience`
      (contexto_previo, evento, evolucion, resultado, consecuencias, ts, asset,
      tf). Cubre: R2.
- [x] T2 — Validar que el arco se reconstruye íntegro (test de round-trip en
      memoria). Cubre: R2.

## Fase 2 — Memoria única (almacenamiento append-only)

- [x] T3 — Crear `src/experience_engine.py` con `ExperienceMemory` (append-only,
      particionado por mes en `data/market_memory/`). Cubre: R3.
- [x] T4 — API de escritura `record(experience)` y lectura `query_similar(profile)`
      (sin reglas, por perfil de contexto/evento). Cubre: R3, R5.
- [x] T5 — Test: dos IAs distintas leen la MISMA memoria; ninguna escribe. Cubre: R3, R4.

## Fase 3 — Observación sin juicio

- [x] T6 — Hook de Observación que, en cada cambio relevante del mercado, captura
      contexto_previo + evento TAL CUAL (sin etiquetar soporte/resistencia/fvg).
      Cubre: R1, R7, R9. (En `src/observation.py` + hook en `black_box_recorder`.)
- [x] T7 — Hook post-trade que completa el arco con evolución + resultado +
      consecuencias (pips, estructura rota, tiempo a invalidación, WIN/LOSS).
      Cubre: R10. (Detrás de OBSERVATION_ENABLED.)

## Fase 4 — Modo activo (distribución)

- [x] T8 — `entry_scorer._apply_experience_distrib` busca arcos similares y los
      empuja a la IA de Entradas al evaluar (solo LECTURA, win rate observado).
      Cubre: R5.
- [x] T9 — Test: inyectar experiencia similar dispara distribución (test
      test_experience_distrib). Cubre: R5.

## Fase 5 — F18 como primer lector

- [x] T10 — F18 se re-entrena desde la memoria única (`train_lightgbm.py`
      `load_experiences_as_rows`). Cubre: R6, R8.
- [x] T11 — Test: F18 se re-entrena desde la memoria sin cambiar su contrato de
      Confidence Score (test_train_from_memory, 4 tests). Cubre: R6, R11.

## Fase 6 — Seed OFFLINE + validación (sin tocar el bot)

- [x] T12 — Script `scripts/seed_experience_memory.py` que RE-LEE `scan_candidates`
      y siembra arcos de experiencia (OFFLINE). Cubre: R1, R10.
- [x] T13 — Validar empíricamente que el contexto correlaciona con win rate
      (NEUTRO 47% / SOBREVENTA 51% / SOBRECOMPRA 37%). Cubre: R6, R8.
- [x] T14 — Marcar `src/zone_memory.py` como OBSOLETO en docstring (anti-patrón R9).
      Cubre: R9. (No se borra: STRAT-A/F dependen de él; lo reemplaza Feature 28.)

## Fase 7 — Trazabilidad y cierre

- [x] T15 — `progress/impl_experience_engine.md` con mapa R<n> → test. Cubre: R11.
- [x] T16 — NO modificar el bot en vivo hasta aprobar implementación. Cubre: R12.
      (Observación detrás de OBSERVATION_ENABLED; demo corre segura.)
