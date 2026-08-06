# Design — lab_protocolo_cientifico

> Este SPEC cumple el Laboratory Charter (`docs/LAB_CHARTER.md`). No modifica
> ninguno de sus principios.

## Decisiones técnicas

### D1 — Plantillas como archivos de ejemplo, no código
`hypothesis.md`, `risks.md`, `validation.md` se entregan como PLANTILLAS
estándar (una carpeta `specs/_templates/` o `docs/lab_templates/`) que todo
EXP-XXX copia. No es código: es formato obligatorio. Esto satisface R1–R3 sin
crear lógica nueva.

### D2 — ADR como archivos markdown planos
`docs/decisions/ADR-NNN.md` con frontmatter mínimo (título, fecha, estado).
Reutiliza la convención ya existente en `docs/LAB_CIENCIA_ROADMAP.md`
("decisiones de arquitectura"). R4.

### D3 — Versionado de datasets reutiliza SMC_ROOT
`compute_features.py` ya lee parquet desde `SMC_ROOT/{ASSET}_M15.parquet`.
El versionado (R6) añade `datasets/dataset_vNNN/` con `manifest.json` que
apunta a los parquet inmutables. NO se copian datos: el manifest referencia
las fuentes y declara el checksum. Evita duplicar velas en disco.

### D4 — Congelamiento = snapshot del protocolo
R7: al pasar a Protocol Frozen, el runner escribe
`reports/EXP-XXX/protocol_frozen.json` con los parámetros congelados. Cualquier
re-ejecución que difiera del snapshot se marca como violación de Charter
(Art. 6) y el experimento se considera inválido.

### D5 — Evidencia inmutable reutiliza experiment_runner
R8: `experiment_runner.run_experiment()` ya devuelve artifacts. Se extiende
para que SIEMPRE escriba `seed.txt` (semilla RNG), `environment.txt`
(versions de python/paquetes) y `dataset_hash.txt` (hash del manifest).
Esto no toca la lógica de cómputo, solo el reporteo.

### D6 — CLI `lab run` como wrapper del runner
R9: `scripts/lab_run.py` (o entrypoint en `pyproject`) parsea `EXP-XXX`,
localiza `specs/lab_protocolo_cientifico` o `src/strategy_lab/scripts/run_experiment_expNNN.py`
y lo ejecuta con los insumos declarados en el manifest. No reemplaza los
scripts existentes: los orquesta.

### D7 — CI científico como etapas adicionales
R10: el CI existente (pytest) se extiende con un job `lab-ci` que corre
dataset_hash check + un experimento de referencia (reproducibilidad) + FDR +
bootstrap + permutaciones + poder sobre un EXP canario. Reutiliza
`multiple_comparisons.py` y `evidence.py` ya existentes.

### D8 — Ciclo de vida científico ya documentado
R11: el ciclo (Hypothesis→…→Archived) ya está en `docs/specs.md`. El design
solo lo hace operativo: cada transición se registra en
`reports/EXP-XXX/lifecycle.json`.

## Alternativas descartadas

- **Crear un nuevo tribunal**: descartado. `promotion_gate.py` ya emite
  PROMOVIDA/INCONCLUSIVE/REFUTADA. `validation.md` lo consume.
- **Nuevo framework de experimentos**: descartado. `experiment_runner.py` ya
  existe; se extiende, no se reescribe.
- **Charter con procedimientos**: descartado explícitamente por el usuario.
  El Charter solo tiene principios (Art. 1–9).

## Archivos a crear / modificar

| Archivo | Acción | Cubre |
|---|---|---|
| `docs/lab_templates/hypothesis.md` | crear | R1 |
| `docs/lab_templates/risks.md` | crear | R2 |
| `docs/lab_templates/validation.md` | crear | R3 |
| `docs/decisions/ADR-001.md` | crear | R4 |
| `datasets/dataset_v001/manifest.json` | crear (referencia a SMC_ROOT) | R6 |
| `scripts/lab_run.py` | crear | R9 |
| `src/strategy_lab/experiment_runner.py` | modificar (seed/env/dataset_hash) | R8, R7 |
| `.github/workflows/lab-ci.yml` (o equivalente) | crear | R10 |
| `reports/EXP-XXX/` | generado por runner | R8, R11 |
| `docs/specs.md` | ya tiene Scientist + ciclo de vida | R5, R11 |

## Riesgos de implementación

- Los datos reales son grandes: el manifest DEBE referenciar, no copiar (D3).
- `lab run` debe fallar si el manifest o el seed no son reproducibles (D4/D5).
