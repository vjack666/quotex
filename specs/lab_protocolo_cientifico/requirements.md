# Requirements — lab_protocolo_cientifico

> Este SPEC cumple el Laboratory Charter (`docs/LAB_CHARTER.md`). No modifica
> ninguno de sus principios. Se apoya en la infraestructura ya existente
> (tribunal FDR/Bonferroni, `experiment_runner.py`, `LAB_MARCO_EXPERIMENTAL.md`,
> `LAB_EVIDENCIA_CIENTIFICA.md`) y la extiende sin duplicar.

## Contexto

El laboratorio ya posee: tribunal declarativo (`promotion_gate.py` +
`tribunal_v1.yaml`), corrección FDR/Bonferroni (`multiple_comparisons.py`),
runner de experimentos (`experiment_runner.py`), y los marcos de
`docs/LAB_MARCO_EXPERIMENTAL.md` y `docs/LAB_EVIDENCIA_CIENTIFICA.md`. Lo que
falta son las piezas de gobierno que vuelven reproducible y auditable la
búsqueda de configuración aceptable del Edificio (p.ej. la auditoría de
secuencia/funnel que diagnosticó el embudo P1→P2→P3→CONTRATADO).

## Fase 1 — Núcleo metodológico

### R1
CUANDO se cree un experimento EXP-XXX, el sistema DEBE incluir un
`hypothesis.md` estandarizado con: ID, H0, H1, métrica primaria, métricas
secundarias, nivel α, corrección (FDR-BH), poder esperado y n mínimo.

### R2
CUANDO se cree un experimento EXP-XXX, el sistema DEBE incluir un `risks.md`
que declare las amenazas del laboratorio (data leakage, look-ahead, data
snooping, comparaciones múltiples, survivorship bias, REAL≠OTC, muestra
pequeña, no independencia, cambios de régimen, overfitting).

### R3
CUANDO se analice un experimento EXP-XXX, el sistema DEBE producir un
`validation.md` con: dataset, n, Win Rate, IC95%, poder, FDR, Bonferroni,
bootstrap, permutación, robustez y un veredicto único
(PROMOVIDA | INCONCLUSIVE | REFUTADA).

### R4
EL sistema DEBE registrar toda decisión metodológica en `docs/decisions/`
como ADR-XXX (p.ej. ADR-001 uso de FDR, ADR-002 separación REAL/OTC).

### R5
EL rol Scientist DEBE ser responsable de diseñar H0/H1, fijar α/FDR/poder/n
mínimo y congelar el protocolo antes de ejecutar (ya definido en
`docs/specs.md`; R5 lo hace obligatorio para todo EXP).

## Fase 2 — Infraestructura

### R6
EL sistema DEBE versionar datasets en `datasets/dataset_vNNN/` con
`manifest.json` (origen, fechas, pares, velas, timezone, checksum) y el
hash debe declararse en el `hypothesis.md` del experimento que lo usa.

### R7
CUANDO un experimento inicie su fase Running, el sistema DEBE congelar el
protocolo (hipótesis, métricas, α, FDR, poder, n mínimo, dataset) y no
permitir su modificación retroactiva (Art. 6 del Charter).

### R8
CUANDO un experimento termine, el sistema DEBE generar evidencia inmutable en
`reports/EXP-XXX/` con `results.json`, `summary.md`, `seed.txt`,
`environment.txt` y `dataset_hash.txt`.

### R9
EL sistema DEBE ofrecer un CLI único `lab run EXP-XXX` que reproduzca
exactamente el resultado sin intervención manual.

### R10
EL pipeline de CI DEBE incluir, además de lint/tests/coverage, las etapas:
dataset_hash, reproducibilidad, FDR, bootstrap, permutaciones, poder y reporte.

### R11
EL ciclo de vida científico (Hypothesis → Designed → Protocol Frozen →
Running → Analyzed → Peer Reviewed → Archived, ya en `docs/specs.md`) DEBE
usarse para todo EXP-XXX.

## No duplicación

- R1–R3 extienden el "Contrato de experimento EXP-XXX" de
  `docs/LAB_CIENCIA_ROADMAP.md`, no crean un formato paralelo.
- R3 reutiliza el veredicto del tribunal existente
  (`promotion_gate.py`: PROMOVIDA/INCONCLUSIVE/REFUTADA).
- R6–R9 reutilizan `experiment_runner.py` y `compute_features.py` (SMC_ROOT).
- R4 referencia la sección "Reforma del Charter" para la creación de ADR.

## Trazabilidad

- R1 → T1, T2
- R2 → T3
- R3 → T4
- R4 → T5
- R5 → T6 (extiende specs.md existente)
- R6 → T7
- R7 → T8
- R8 → T9
- R9 → T10
- R10 → T11
- R11 → T12 (extiende specs.md existente)
