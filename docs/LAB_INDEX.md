# LAB_INDEX — Índice de documentos científicos

Mapa de la jerarquía documental del laboratorio. No duplica contenido:
cada entrada enlaza al documento real.

## Pirámide de gobierno

```
LAB_CHARTER.md          (Nivel 1 — Constitución: principios inquebrantables)
      │
      ▼
docs/specs.md           (Nivel 2 — Manual operativo SDD, subordinado al Charter)
      │
      ▼
specs/<feature>/        (Nivel 3 — SPEC de cada feature)
      │
      ▼
EXP-XXX                 (Nivel 4 — experimentos)
```

## Documentos por nivel

### Nivel 1 — Constitución
- `docs/LAB_CHARTER.md` — Artículos inquebrantables + cláusula de prevalencia + reforma.

### Nivel 2 — Manual operativo (SDD)
- `docs/specs.md` — Flujo SDD, participación del Trader-Humano, rol Scientist,
  ciclo de vida científico, declaración de cumplimiento del Charter.

### Fundamentos científicos (referenciados, no subordinados)
- `docs/LAB_MARCO_EXPERIMENTAL.md` — Filosofía y leyes del Laboratorio.
- `docs/LAB_EVIDENCIA_CIENTIFICA.md` — Tribunal de evidencia (jerarquía Observacional→Demostrada).
- `docs/LAB_CIENCIA_ROADMAP.md` — Hoja de ruta y decisiones de arquitectura.
- `docs/AUDITORIA_CIENTIFICA_LABORATORIO.md` — Auditoría epistemológica del laboratorio.
- `docs/AUDITORIA_CIENTIFICA_QUOTEX.md` — Auditoría del bot Quotex.

### Infraestructura de validación (ya existente, reutilizada)
- `src/strategy_lab/multiple_comparisons.py` — FDR/Bonferroni.
- `src/strategy_lab/promotion_gate.py` + `config/tribunal_v1.yaml` — Tribunal declarativo (PROMOVIDA/INCONCLUSIVE/REFUTADA).
- `src/strategy_lab/experiment_runner.py` — Runner de experimentos.

### Registro de decisiones
- `docs/decisions/` — ADR-XXX (por crear según Fase 2 del spec `lab_protocolo_cientifico`).
