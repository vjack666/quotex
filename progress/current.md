# Progress — 2026-08-03

## ⭐ Estado de estrategias (DEUDA SALDADA)

- **STRAT-A**: primer paso hacia el Edificio — etapa **conclusa**, misión cumplida.
- **STRAT-F y todas las demás estrategias**: archivadas / etapa concluida.
- **Edificio de Contratación** (`src/edificio_contratacion.py`): **ÚNICA estrategia activa** y **FINAL para operar en REAL**.
- NO reactivar estrategias archivadas sin pedido explícito del usuario.

## Active task

**T4 — Clasificación de cruces K/D del estocástico (FASE 2 del edificio)** — EN CURSO.
El freno fue verificado (fase 1, ver Status): existe y filtra; sin muestra real para calibrar (la DB estaba contaminada por tests).

## Status

- ✅ Auditoría completa entregada (2026-08-03): plan fiel en esqueleto; deudas 08-01 pagadas.
- ✅ TODOs T1-T11 ejecutados y verificados (4 commits: 3c1c473, ac0b5e8, 127d6f1, ddd36c4) + `e15c1c4` (estado de estrategias) + `9510e70` (tanda T2 + archivo plan completado).
- ✅ Freno (fase 1) verificado contra log real 03-08 (11:22–13:39): 17+ CANCELLED por pérdida de brake/extremo. **El freno es una ALERTA de preparación, no genera entrada** — comportamiento correcto: solo espera el cruce.
- ✅ **Orden correcto documentado** (corrección 03-08): freno = alerta (prepara al par para esperar el cruce K/D) → cruce K/D = otra condición (tampoco es señal) → señal final = cruce de velas + separación de líneas, con estrategia completa. **El WR se evalúa cuando TODA la estrategia esté completa, no por piezas.** Ver `docs/EDIFICIO_CONTRATACION.md` ⚠ El orden correcto.
- ✅ **Freno = tarjeta de acceso a P2** (corrección 03-08): el motor ya no exige `brake_ok AND extreme_ok` para arrancar el candidato en P1 — ahora SOLO el freno (`if brake_ok:`) arranca la candidatura y el CONFIRMED con vela M15 cerrada sube a P2. La estadía en P2 se sostiene con la tarjeta (freno CONFIRMED) + extremo vigente; el `brake_ok` instantáneo (vela en formación, ruidoso) NO revoca la tarjeta. Si se pierde el extremo → baja a P1. Hub: badge `freno ✓ ratio` en toda card CONFIRMED + `p2Lights` con la nueva semántica. `EDIFICIO_RULE_VERSION` → `2026-08-03a`. Suite EDIFICIO: **53/53** verde (51 + 2 tests nuevos). Docs actualizados: `EDIFICIO_CONTRATACION.md` (PISO 2, flujo, comparativa), `progress/current.md`.
- ✅ **Auditoría P3 + documentación escrita** (03-08): `progress/auditoria_piso3_y_docs_2026-08-03.md` — P1 OK, P2 OK, P3 con 1 brecha (entrada no re-exige `not cross_sticky`), laboratorio F27-F29 completo y coherente, 2 docs de auditoría 01-08 DESACTUALIZADOS (describen motor viejo). Esperando aprobación humana para ejecutar.
- ⚠️ **Descubrimiento crítico**: los tests de executor/contratación escriben en la DB real de la caja negra (`get_black_box` sin mockear) → 68 filas EDIFICIO con fixtures (ratio=0.5 exacto, witness=2.0). Deuda **D1** de la tanda T4: aislar con tmp_path (patrón CSV ya resuelto).
- ⚠️ Fase A de T2 (direction_source) implementada por la otra ventana **SIN COMMITEAR** (5 src + 2 tests, suite 51/51 verde). Deuda **D2**: revisar bug menor (direction_source="M15" sin dirección), validar, commitear.
- ✅ Suite EDIFICIO + black box: **53/53** verde (51 + 2 tests de la tarjeta de acceso / estadía en P2).
- ⚠️ Suite completa: 32 fallos preexistentes (STRAT-A, session_lifecycle, smart_order_place) — NO crecieron. No arreglarlos sin pedido.
- ✅ **Documento teórico del POI como ÁREA** (03-08): `docs/TEORIA_POI.md` — teoría viva: el POI es una zona de precio (no línea), el descarte del freno no debe ser "a la primera" sino al SOBREPASAR la zona (cierre M15 fuera de la banda por el lado del impulso), y cómo medir el grosor del área en OTC sin volumen (proxies: ticks de Quotex / toques / dispersión / clustering 0.15%). Hallazgo: el proyecto YA captura `Candle.ticks` (models.py:20, connection.py:88/:142) y `zone_strength.py:201` ya lo usa como order-flow; NO existe Volume Profile (suma de ticks por nivel) — construirlo es agregación pura. NO implementado: es teoría para guiar la implementación.
- ✅ **Experimento LAB diseñado: POI de VOLUMEN en el eje Y** (03-08): `src/strategy_lab/EXPERIMENTO_POI_VOLUMEN.md` — hipótesis: la franja de mayor acumulación de volumen (M15, ticks) contiene el nivel donde el precio reacciona más que el POI actual. Universo: **62 pares en P1** (snapshot del log 16:53, bot en vivo, 0 CONFIRMED). Protocolo: descarga M15 paginación profunda (offset=3600, step=2940, index 12 dígitos, `message["data"]`), medir tiempo por target 2/7/30 días; franja = POC ± celdas ≥60%, banda 0.15% (ZONE_BAND_PCT); comparar tasa de rebote/WR implícito/retensión vs POI actual. SIN código aún — pendiente aprobación para ejecutar.

## Next

1. **Aprobación humana pendiente** (⏸ 03-08): auditoría `progress/auditoria_piso3_y_docs_2026-08-03.md` — ver §6 Orden de ejecución (fix P3 sticky → D1 → D2 → A1-A6 → docs 01-08 → B1 usuario).
2. **T4 — cruces K/D** (EN CURSO): lista `progress/todos_cruce_lineas_2026-08-03.md`. Orden: D1 (aislar DB de tests) → D2 (commitear Fase A direction_source) → A1-A6 (telemetría de evaluación por ciclo + clasificación sticky/limpio/separación) → B1 (usuario: ≥1h demo) → C1-C3 (veredicto → ⏸ usuario).
3. **T2 — dirección M1 vs M15**: Fase A lista (falta D2); la decisión por WR se evalúa cuando la estrategia esté completa.
4. **T3 — post-freno** (referenciado, después de T2/T4).
5. **Señal final de compra/venta**: NO existe por diseño — freno = alerta (fase 1), cruce = condición (fase 2), señal = estrategia completa. Tema con el usuario cuando T4 cierre.
6. Esperar feedback del usuario sobre comportamiento del Edificio en demo.

## Referencia

- Nueva tanda activa: `progress/todos_cruce_lineas_2026-08-03.md` (T4).
- Tanda T2 (direction_source): `progress/todos_direction_source_2026-08-03.md` (Fase A hecha, falta D2).
- Tanda cerrada (archivada): `progress/plan_completado/todos_auditoria_edificio_2026-08-03.md`.
- Plan ideal: `docs/EDIFICIO_CONTRATACION.md`.
- Auditorías: `docs/EDIFICIO_AUDIT_FLOW_2026-08-01.md`, `docs/EDIFICIO_RULES_AUDIT_2026-08-01.md`.
- Evidencia freno: `data/logs/runtime/consolidation_bot.log` (03-08), `data/db/black_box_strat_2026-08-0X.db`.
