# Implementación — Experience Engine (Feature 27)

> Mapa de trazabilidad: cada requisito `R<n>` de
> `specs/experience_engine/requirements.md` → dónde se cumple en el código/test.
> Estado: **DONE** (2026-07-24, 73 tests passed).

---

## Arquitectura

```
Mercado → Observación (observation.py + hook en black_box_recorder)
        → ExperienceMemory (data/market_memory/*.jsonl, append-only)
        → ExperienceEngine (modo activo: distribuye a IAs)
        → IAs lectoras: F18 (Entry Intelligence Agent) + prototipo Zonas
```

Unidad de información: **arco de experiencia** (`MarketExperience`),
NO snapshot. Capturador escribe; IAs solo leen.

---

## Trazabilidad R → código/test

| Req | Qué exige | Dónde se cumple |
|-----|-----------|-----------------|
| R1  | Adquirir experiencia en cada cambio relevante | `observation.build_entry_experience` + hook `black_box_recorder._record_experience_arc` (detrás `OBSERVATION_ENABLED`) |
| R2  | Estructura del arco + reconstrucción íntegra | `experience_schema.MarketExperience` (`to_dict`/`from_dict`/`fingerprint`); test `test_experience_engine.py::test_experience_roundtrip` (T2) |
| R3  | Memoria única, sin silos | `experience_engine.ExperienceMemory` (append-only, particionado por mes); test `test_experience_engine.py::test_two_ias_read_only` (T5) |
| R4  | IAs solo leen | `query_similar` (solo lectura); test T5 verifica que dos IAs no escriben |
| R5  | Modo activo: distribuir a IAs | `entry_scorer._apply_experience_distrib` (lee memoria, empuja win-rate a F18); test `test_experience_distrib.py` (T8/T9) |
| R6  | F18 como primer lector | `train_lightgbm.load_experiences_as_rows` lee `ExperienceMemory`; test `test_train_from_memory.py` (T10/T11) |
| R7  | Observación sin juicio | `observation.py` guarda `contexto_previo`/`evento` TAL CUAL (sin etiqueta soporte/resistencia); verificado en `test_observation.py` |
| R8  | Reentrenar IAs desde memoria | `run_training` prioriza memoria única; test `test_train_from_memory.py` |
| R9  | Cero reglas de detección | `zone_memory.py` marcado OBSOLETO (docstring); prototipo Zonas usa clustering por proximidad, no "3 toques" |
| R10 | Ingesta post-trade (evolución+resultado+consecuencias) | hook `black_box_recorder._record_experience_arc` cierra el arco con `resultado`/`evolucion`/`consecuencias` |
| R11 | Tests de la memoria | suites: `test_experience_engine` (4), `test_observation` (5), `test_experience_distrib` (3), `test_train_from_memory` (4) + ML existente (61) |
| R12 | Sin tocar bot hasta aprobar | puerta SDD respetada; Observación detrás de `OBSERVATION_ENABLED` (demo segura) |

---

## Validación empírica (sin reglas)

Seed OFFLINE (`scripts/seed_experience_memory.py`) sembró **211 experiencias
reales** desde `data/db/*.db`. Win rate por contexto (sin reglas):
NEUTRO 47% / SOBREVENTA 51% / SOBRECOMPRA 37% → el contexto SÍ correlaciona
con outcome, lo descubre el agente, no el código.

IA de Zonas (prototipo, `scripts/zone_ia_prototype.py`) descubrió **33 zonas
de reacción en 25 assets** por clustering de proximidad de nivel, leyendo la
MISMA memoria que F18. Tesis validada: una memoria, múltiples IAs.

---

## Archivos

- `src/experience_schema.py` — arco de experiencia (sin I/O)
- `src/experience_engine.py` — memoria única + modo activo
- `src/observation.py` — capturador en vivo (T6/T7)
- `scripts/seed_experience_memory.py` — seed OFFLINE (T12/T13)
- `scripts/zone_ia_prototype.py` — IA de Zonas (prototipo, valida tesis)
- `src/entry_scorer.py` — `_apply_experience_distrib` (T8/T9)
- `scripts/train_lightgbm.py` — `load_experiences_as_rows` (T10/T11)
- `src/black_box_recorder.py` — hook post-trade (T6/T7)
- `data/market_memory/` — 211 experiencias reales (append-only)

## Pendiente (no bloquea)

- **Feature 28 — IA de Zonas real**: reemplaza `zone_memory.py` (STRAT-A
  veto wall + STRAT-F adj) leyendo la memoria única y emitiendo
  `zone_confidence`. Al implementarse, se BORRA `zone_memory.py`.
- `zone_memory.py` queda OBSOLETO hasta la Feature 28 (no borrar antes:
  STRAT-A/F dependen de él en el hot path).
