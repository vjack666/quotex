# Tasks — lab_protocolo_cientifico

> Este SPEC cumple el Laboratory Charter (`docs/LAB_CHARTER.md`). No modifica
> ninguno de sus principios.

## Fase 1 — Núcleo metodológico

- [ ] T1 — Crear `docs/lab_templates/hypothesis.md` con plantilla H0/H1/α/FDR/poder/n mínimo. Cubre: R1.
- [ ] T2 — Validar que un EXP de ejemplo (p.ej. re-análisis del embudo P1→P2→P3→CONTRATADO de EXP-039) usa la plantilla. Cubre: R1.
- [ ] T3 — Crear `docs/lab_templates/risks.md` con las 11 amenazas del laboratorio. Cubre: R2.
- [ ] T4 — Crear `docs/lab_templates/validation.md` con IC95/poder/FDR/Bonferroni/bootstrap/permutación/robustez y veredicto único (reusa tribunal). Cubre: R3.
- [ ] T5 — Crear `docs/decisions/ADR-001.md` (uso de FDR) y `ADR-002.md` (separación REAL/OTC). Cubre: R4.
- [ ] T6 — Confirmar en `docs/specs.md` que el rol Scientist es obligatorio en EXP (ya presente; añadir checklist de congelamiento). Cubre: R5.

## Fase 2 — Infraestructura

- [ ] T7 — Crear `datasets/dataset_v001/manifest.json` referenciando SMC_ROOT (sin copiar velas) + checksum. Cubre: R6.
- [ ] T8 — Extender `experiment_runner.py` para escribir `protocol_frozen.json` al entrar en Running. Cubre: R7.
- [ ] T9 — Extender `experiment_runner.py` para escribir `reports/EXP-XXX/` con `seed.txt`, `environment.txt`, `dataset_hash.txt`, `lifecycle.json`. Cubre: R8, R11.
- [ ] T10 — Crear `scripts/lab_run.py` como wrapper CLI único `lab run EXP-XXX`. Cubre: R9.
- [ ] T11 — Crear job `lab-ci` (lint+tests+coverage+dataset_hash+reproducibilidad+FDR+bootstrap+permutaciones+poder+reporte) reusando `multiple_comparisons.py`/`evidence.py`. Cubre: R10.
- [ ] T12 — Documentar el uso del ciclo de vida científico en el README del lab y ejemplo de transición. Cubre: R11.

## Verificación

- [ ] T13 — `pytest tests/` en verde para cualquier código nuevo (T8, T10, T11). Cubre: R9, R10.
- [ ] T14 — Reproducibilidad: `lab run EXP-039-reanalysis` produce `reports/EXP-XXX/results.json` idéntico en dos corridas (mismo seed/dataset_hash). Cubre: R9, R8.

## Notas

- Ningún task crea documento redundante: todos extienden/referencian
  tribunal, marco, evidencia y runner existentes.
- El Scientist (rol de `docs/specs.md`) firma T1–T5 y T7–T11 antes de Archived.
