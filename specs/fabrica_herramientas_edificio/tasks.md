# Tasks — Fabrica de Herramientas del Edificio

Checklist ejecutable para el `implementer`. Cada task referencia al menos un R<n>.
NO se toca codigo del Edificio hasta que el spec este APROBADO por el trader-humano
y por el humano (puerta SDD).

PRINCIPIO DE CICLO (revisión trader-humano 2026-08-09): la unidad de decisión
humana es el CICLO EXPERIMENTAL, no el experimento aislado. Los EXP-076..080 se
ejecutan COMO UN LOTE congelado; la pausa de decisión humana ocurre SOLO al
cierre del ciclo, tras la síntesis conjunta (R0/R12/R13). El trader-humano no
decide entre experimentos individuales salvo condición de seguridad previamente
congelada. CADA EXP deja reporte individual en su carpeta + commit/push (R14/R15);
el ciclo no cierra sin todos los reportes (R16).

## Fase A — Registro y contrato (cubre R1, R2)
- [ ] T1 — Crear `src/edificio_tools/evidence.py` con dataclass `Evidence`
      (direction/strength/confidence/stage, sin campo de orden). Cubre: R2.
- [ ] T2 — Crear `src/edificio_tools/registry.py` con dataclass `Tool`
      (name, exp_ref, wr_pooled, n, charter_verdict, domain, gate_fn) y loader.
      Cubre: R1.
- [ ] T3 — Registrar las herramientas ya medidas: arcoiris (EXP-EDF-04),
      valvula_kd (EXP-EDF-FINAL), cruce_limpio (descartado). Cubre: R1, R9.

## Fase B — Ensamblador e Inspector (cubre R3, R4, R5)
- [ ] T4 — Crear `src/edificio_tools/assembler.py`: regla de mayoria congelada,
      devuelve BUY/SELL/NO_TRADE. Cubre: R3, R4.
- [ ] T5 — Crear `src/edificio_tools/inspector.py`: detecta direccion opuesta
      confidence>=0.5 → CONFLICTO → NO_TRADE. Cubre: R5.
- [ ] T6 — Cablear pisos P1→P2→P3 para emitir Evidence antes del ascenso.
      Cubre: R3.

## Fase C — Gobernador (cubre R6)
- [ ] T7 — Decorar `edificio_executor` para calcular lote Massaniello sobre la
      SERIE FILTRADA (frecuencia/racha de la composicion), con veto por DD.
      Cubre: R6.

## Fase D — Trazabilidad y dominio (cubre R8, R9, R10)
- [ ] T8 — Registrar en cada BUY/SELL/NO_TRADE el conjunto de herramientas y sus
      EXP-XXX + WR/n individuales y combinados en reporte inmutable. Cubre: R8.
- [ ] T9 — Bloquear promocion a OTC sin evidencia OTC; bloquear promocion por WR
      aislada (exigir n + holdout + n combinado). Cubre: R9, R10.

## Fase E — Orquestador del ciclo + reportes + Git (cubre R0,R11,R12,R14,R15,R16)
- [ ] T10 — Crear `src/edificio_tools/cycle_orchestrator.py`: planifica el lote
       (hipótesis principal + EXP-076..080), CONGELA parámetros/dataset/métrica/
       criterio de cada EXP ANTES de ejecutar, corre el lote completo SIN modificar
       reglas entre EXP, y prohíbe re-ajuste adaptativo. Cubre: R0,R11,R12.
- [ ] T11 — Ejecutar el LOTE COMPLETO (no experimento aislado): EXP-076 timing
       broker, EXP-077 composicion arcoiris+valvula K/D (n combinado), EXP-078 OOS
       externo, EXP-079 frecuencia/DD/racha sobre serie filtrada, EXP-080 estabilidad.
       TRAS CADA EXP: generar `reports/CICLO-XXX/EXP-NNN/EXP-NNN_reporte.md`
       (evidencia primaria: hipótesis, config congelada, dataset, n, WR, OOS, timing,
       anomalías, conclusión del EXP) y `git add`+`commit`+`push` con prefijo
       `EXP-NNN:`. Cubre: R11,R12,R14,R15.
- [ ] T12 — Producir MATRIZ DE EVIDENCIA global (solo si T11 dejó reporte de TODOS
       los EXP; si falta alguno sin error registrado, NO cerrar ciclo): por-EXP
       (resultado+peso), composicion agregada (WR/n/OOS/timing), riesgo
       (frecuencia/DD/racha) y DICTAMEN GLOBAL (PROMOVER|CONTINUAR|REFORMULAR|
       ARCHIVAR). `git add`+`commit`+`push` con prefijo `CYCLE-XXX:`. Cubre: R13,R15,R16.

## Fase F — Tests y cierre (cubre R0..R16)
- [ ] T13 — `tests/` para R1..R16 (ver design.md trazabilidad). Cubre: todos.
- [ ] T14 — `pytest tests/` en verde en entorno limpio. Cubre: cierre SDD.

## Pausa de decisión humana (R0)
- El trader-humano y el humano reciben la MATRIZ DE EVIDENCIA (T12) y emiten UNA
  decisión de dirección (PROMOVER | CONTINUAR | REFORMULAR | ARCHIVAR) para TODO el
  ciclo. NO hay pausa entre EXP-076..080. Los reportes individuales ya están en Git
  para revisión externa (GitHub/ChatGPT) sin esperar la decisión del director.

## Notas
- El Edificio NO se reescribe: se anaden estaciones (Ensamblador/Inspector/
  Gobernador/Orquestador) y se hace explicito el registro de herramientas.
- Hasta que corra el lote (T11) y cierre el ciclo (T12), las herramientas estan
  registradas como CANDIDATAS, no activas. La promocion a REAL requiere ademas
  validacion OTC (Charter Art. 10/13).
- Niveles documentales: (1) reporte individual EXP = evidencia PRIMARIA;
  (2) matriz global = síntesis SECUNDARIA; (3) decisión humana = TERCIARIA.
