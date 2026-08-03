# Progress — 2026-08-03

## ⭐ Estado de estrategias (DEUDA SALDADA)

- **STRAT-A**: primer paso hacia el Edificio — etapa **conclusa**, misión cumplida.
- **STRAT-F y todas las demás estrategias**: archivadas / etapa concluida.
- **Edificio de Contratación** (`src/edificio_contratacion.py`): **ÚNICA estrategia activa** y **FINAL para operar en REAL**.
- NO reactivar estrategias archivadas sin pedido explícito del usuario.

## Active task

Auditoría del Edificio de Contratación (plan ideal vs código) — CERRADA.

## Status

- ✅ Auditoría completa entregada (2026-08-03): plan fiel en esqueleto; deudas 08-01 pagadas (freno vela M15 cerrada, sticky fuera, mantenimiento P3, delay 300s, loss_reason real).
- ✅ TODOs T1-T11 ejecutados y verificados: fix CSV auditoría (loss_reason real + test), scanner con umbral de freno unificado, resets de entrada, P2→P1, fetch fuera del loop, docs flow/rules actualizados, limpieza git. 4 commits (3c1c473, ac0b5e8, 127d6f1, ddd36c4).
- ✅ Suite EDIFICIO: **47/47** verde.
- ⚠️ Suite completa: 32 fallos preexistentes en módulos de estrategias archivadas (STRAT-A, session_lifecycle, smart_order_place) — **NO crecieron** (402 passed). No son responsabilidad del trabajo actual; no arreglarlos sin pedido.
- ✅ `init.ps1` verificado: entorno OK, FAIL solo por los 32 fallos preexistentes.

## Next

1. **T2 — dirección M1 vs M15** (EN CURSO, nueva tanda): instrumentar `direction_source` en caja negra (Fase A, telemetría sin tocar la decisión), juntar muestra en demo, y con los datos decidir si M15 es el juez (plan) o si M1 se mantiene. Lista: `progress/todos_direction_source_2026-08-03.md`.
2. **T3 — cierre del experimento post-freno** (referenciado, después de T2): contar muestra `post_brake_body_ratio` por bucket y WR; fijar criterio de corte (n>=30/bucket) y fecha. Si `0.0` es óptimo → cerrar como documentación; si hay sesgo → code-change con aprobación.
3. Esperar feedback del usuario sobre comportamiento del Edificio en demo.

## Referencia

- Nueva tanda activa: `progress/todos_direction_source_2026-08-03.md` (T2, Fase A telemetría).
- Tanda cerrada (archivada): `progress/plan_completado/todos_auditoria_edificio_2026-08-03.md`.
- Plan ideal: `docs/EDIFICIO_CONTRATACION.md`.
- Auditorías: `docs/EDIFICIO_AUDIT_FLOW_2026-08-01.md`, `docs/EDIFICIO_RULES_AUDIT_2026-08-01.md`.
