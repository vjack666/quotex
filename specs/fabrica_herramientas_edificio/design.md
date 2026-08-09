# Design — Fabrica de Herramientas del Edificio

Subordinado a docs/LAB_CHARTER.md y docs/specs.md. Apoya el proceso SDD, no lo
reemplaza. La filosofia de "fabrica" ya esta viva en el Edificio; este design la
hace explicita y cierra dos gaps reales identificados en la sesion 2026-08-08/09.

## Estado actual (lo que YA existe, no se reescribe)
- `src/edificio_contratacion.py`: linea de produccion P1→P2→P3→CONTRATADO (maquina
  validada en exp_funnel_b; P2→P3 reparado para la válvula del motor real).
- Herramientas ya medidas como gates compuestos (sobre el embudo P1→P2→P3):
  - Arcoiris 7-EMA (EXP-EDF-04): WR 70.6% pooled, n=489, vence a baseline 18/19.
  - Válvula K/D motor (EXP-EDF-FINAL): WR 57.0% pooled, n=5.655, vence 19/19.
  - cruce_limpio+M5 (descartado): 48.4%, moneda.
- `src/edificio_executor` + Massaniello: GOBERNADOR hoy afuera del flujo de
  evidencia (lo traemos adentro como estacion explicita).

## Decisions técnicas
1. **Registro de herramientas** (`src/edificio_tools/registry.py` nuevo):
   dataclass `Tool` { name, exp_ref, wr_pooled, n, charter_verdict, domain,
   gate_fn }. Cargado por el Edificio en arranque. Cada herramienta implementa
   `evaluate(ctx) -> Evidence` (R2). NO importa ordenes.
2. **Contrato Evidence** (`src/edificio_tools/evidence.py` nuevo):
   `direction: Literal[LONG,SHORT,NONE]`, `strength: float`, `confidence: float`,
   `stage: str`. Sellado: ningun campo de orden.
3. **Ensamblador** (`src/edificio_tools/assembler.py` nuevo): toma lista de
   Evidence de herramientas activas + regla congelada (R4). v1 = "mayoria de
   direction con confidence>=umbral Y sin conflicto inspector". Devuelve
   `BUY|SELL|NO_TRADE`.
4. **Inspector** (`src/edificio_tools/inspector.py` nuevo): detecta direcciones
   opuestas confidence>=0.5 → CONFLICTO → fuerza NO_TRADE (R5).
5. **Gobernador** (decorar `edificio_executor`): recibe BUY/SELL, calcula lote
   Massaniello sobre *serie filtrada* (R6). Reusa logica existente; no duplica.
6. **Gap de produccion (R7)**: EXP-077 mide n combinado de arcoiris+valvula K/D
   como una sola hipotesis; el Ensamblador v1 NO asume suma de edges.
7. **Orquestador del ciclo** (`src/edificio_tools/cycle_orchestrator.py` nuevo,
   R0/R12/R14/R15/R16): planifica el lote (hipótesis principal + EXP-076..080),
   CONGELA parámetros/dataset/métrica/criterio de cada EXP antes de ejecutar, corre
   todos los EXP sin modificar reglas entre ellos, y produce la MATRIZ DE EVIDENCIA
   global al cierre (R13). NO adapta parámetros tras resultados parciales. La
   pausa de decisión humana ocurre SOLO al cierre del ciclo, no entre EXP.
   ADICIONAL: tras cada EXP el orquestador DEBE generar `EXP-NNN_reporte.md` en
   `reports/CICLO-XXX/EXP-NNN/` (evidencia primaria, R14) y hacer `git add` +
   `commit` + `push` con prefijo `EXP-NNN:` (R15). El ciclo NO se cierra (R13) si
   falta el reporte de algún EXP del lote salvo error explícitamente registrado
   (R16). El commit del ciclo usa prefijo `CYCLE-XXX:`.

## Alternativas descartadas
- **Rewrite del Edificio como scorer (+1/+2)**: descartado por riesgo de
  overfitting por combinatoria (2^10). El Ensamblador v1 usa regla de mayoria
  declarada, no score libre. Queda como evolucion futura tras EXP-077.
- **Promover arcoiris 71% por WR**: descartado por n=489 (fragil para Massaniello);
  la válvula K/D (n=5.655) es la candidata adoptable. R9/R10 lo exigen.

## Riesgos metodologicos (ver risks via Charter)
- Aproximacion de timing: todas las WR son i+1/i+2 close M15. EXP-076 obligatorio.
- Combinacion apilada puede matar frecuencia → romper Massaniello (R6/R10).
- EURUSD REAL ≠ OTC (Art. 10/13): promocion requiere validacion OTC.

## Trazabilidad esperada (hacia tests)
- R0→test_decision_unit_is_cycle_not_single_exp
- R1→test_registry_loads_tool_with_exp_ref
- R2→test_evidence_has_no_order_field
- R3→test_piso_requires_evidence_before_ascent
- R4→test_assembler_majority_rule
- R5→test_inspector_conflict_forces_no_trade
- R6→test_governor_vetoes_over_dd
- R7→test_composition_uses_combined_n (EXP-077)
- R8→test_contract_traceable_to_exps
- R9→test_no_otc_promotion_without_otc_evidence
- R10→test_no_promotion_on_wr_alone
- R11→test_exp076_exp077_declared_in_cycle
- R12→test_orchestrator_freezes_before_run_and_runs_full_lot
- R13→test_evidence_matrix_global_dictamen
- R14→test_individual_report_generated_per_exp
- R15→test_report_committed_and_pushed_to_remote
- R16→test_cycle_not_closed_without_all_reports
