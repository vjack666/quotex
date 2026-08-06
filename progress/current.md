# Progress — 2026-08-06

## ⭐ Sesión actual: Laboratorio Científico Reproducible

**Feature 38 `lab_protocolo_cientifico` = DONE y pusheada (commit `dc53c97`).**

### Qué se hizo
- Charter científico (`docs/LAB_CHARTER.md`, Art.1–12): FDR (Art.9), Dominio
  REAL≠OTC (Art.10), Parsimonia (Art.11), Muerte definitiva (Art.12).
- Manual SDD (`docs/specs.md`): ciclo de vida científico + checklist
  Art.6/10/11/12 + Trader-Humano en SDD.
- SPEC feature 38 aprobado (Trader-Humano + Aprobación Final) con 5 observaciones
  incorporadas: Dominio, Effect Size (R12), Costo operacional (R13), Muerte
  definitiva, Parsimonia.
- Plantillas `docs/lab_templates/{hypothesis,risks,validation}.md`.
- ADR `docs/decisions/ADR-001..004`.
- Dataset versionado `datasets/dataset_v001/manifest.json` (ref SMC_ROOT, sin copiar).
- `scripts/lab_run.py` (CLI `lab run EXP-XXX`) + `scripts/lab_ci.py` (CI) +
  `.github/workflows/lab-ci.yml`.
- `src/strategy_lab/experiment_runner.py` extendido con reports inmutables
  (seed.txt, environment.txt, dataset_hash.txt, protocol_frozen.json, lifecycle.json).
- Protocolo de cierre `agent/CLOSE.md` cableado en AGENTS.md (trigger "listo
  por hoy" / "voy a apagar").

### Verificación
- pytest test_experiment_runner + test_promotion_gate + test_registry = 19 passed.
- `lab run EXP-CLI-TEST` → rc=0, reports inmutables generados.
- `lab ci` → VERDICT GREEN (hash / FDR / reproducibilidad / reporte PASS).

### Decisión
- Force-push autorizado para limpiar commit vago `226bc44` → `dc53c97` (solo
  feature 38). Origin/main limpio.

### Próximo paso sugerido
- Aplicar el laboratorio al embudo roto del Edificio (EXP-039: 40→2→0→0; cuello
  = FRENO, solo 2/40 pasan). El lab (secuencia_libre.py + optimizer.py) debe
  encontrar config aceptable vía secuencias, no ajuste manual.

### Notas
- Las 3 recomendaciones futuras del Trader-Humano (edad de hipótesis, Confidence
  Score, registro de descartadas) quedaron ancladas en
  `specs/lab_protocolo_cientifico/trader_humano_review.md` (evolución, no bloquean).
- NO operar REAL sin OK. Bot corre PRACTICE por defecto.
