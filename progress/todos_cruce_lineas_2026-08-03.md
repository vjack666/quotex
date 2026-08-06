# TODOS — T4: Clasificación de cruces de líneas en el estocástico (P3) — 2026-08-03

> Lista de trabajo preparada por la ventana principal para **verificar que los
> cruces de líneas K/D del estocástico M15 se clasifican bien** en el Edificio
> de Contratación, y **saldar deudas** que impiden medir con datos confiables.
> - Contexto del usuario (2026-08-03): el **freno es solo la FASE 1** de la
>   estrategia — NO genera entrada. La fase siguiente es el **cruce de líneas**.
> - **OJO — el cruce TAMPOCO envía señal de compra/venta**: es OTRA condición
>   (esperar cruce de velas + detectar separación entre líneas). Solo se
>   estudia si la clasificación es correcta. La señal final es tema posterior.
> - **El freno es una ALERTA, no un disparador**: indica que el par está
>   preparado para ESPERAR el cruce de líneas K/D del estocástico. NO genera
>   entrada ni se evalúa WR en esta etapa. El WR se mide cuando TODA la
>   estrategia esté completa, no durante la implementación.
> - Destinada a **Hermes (otra ventana)**. Tanda anterior (T2 direction_source)
>   quedó implementada SIN COMMITEAR por la otra ventana (ver D2).

---

## Auditoría — lo que tenemos HOY vs lo ideal en el motor

| Ítem | Plan ideal (`docs/EDIFICIO_CONTRATACION.md`) | Motor HOY | Brecha |
|---|---|---|---|
| P1 recepción | Filtro de pago >= lo pedido | `payout_ok` en `evaluate()` | ✅ OK |
| P2 Prueba A (freno) | Brake M15 como **ALERTA**: el par está listo para esperar el cruce. NO es entrada | `brake_ok` = `last_range < prev_range * 0.7` (scanner.py:1515) + confirmación con vela M15 cerrada (`_brake_confirm`, edificio:659) | ⚠️ Estructural OK. En 2.5h de demo: 17+ CANCELLED, 0 CONFIRMED reales = comportamiento de alerta correcto (no deja pasar entradas). NO se evalúa WR ahora. |
| P2 Prueba B (extremo) | Stoch M15 en sobrecompra (≥80 PUT) / sobreventa (≤20 CALL) | `_extreme_ok` (scanner.py:1506) | ✅ OK |
| P3 sala de espera | Esperar **cruce limpio K/D (no sticky)** + separación K/D | `_cross_ok` (scanner.py:1502-1504) + `is_sticky_cross` (|K-D|<3.0) + `cross_separation_since` + 60s (`EDIFICIO_SEPARATION_WAIT_SEC`) | ⚠️ Verificar que el cruce se detecta sobre velas CERRADAS y que sticky/separación clasifican bien (esta tanda). El cruce TAMPOCO es señal: es otra condición. |
| P3 → CONTRATADO | Cruce dispara entrada | P3 exige cross_ok de nuevo + gate vela 5m + delay 300s | ⚠️ El cruce se exige para SUBIR a P3 y se vuelve a exigir DENTRO de P3. Verificar si la sala de espera real es P2 (conceptual, no urgente). Mientras la estrategia no esté completa NO debe llegar a orden. |
| Telemetría | Toda condición auditable | `direction_source` (sin commitear), brake_*, kd_distance, cross_limpieza_ok | ⚠️ **No hay telemetría por ciclo de evaluación del edificio**: `scan_candidates` solo se registra al enviar orden (executor). Para clasificar cruces se necesita registrar cada evaluación. |

**Deudas de infraestructura que bloquean TODA medición** (resolver primero):

- [ ] **D1. Los tests ensucian la DB real de la caja negra** (CRÍTICO).
  `get_black_box` NO está mockeado en `tests/test_edificio_executor.py` ni
  `tests/test_edificio_contratacion.py` → escriben en
  `data/db/black_box_strat_<hoy>.db` (producción). Evidencia 03-08: 68 filas
  EDIFICIO en la DB con `brake_ratio=0.5` EXACTO y `brake_witness_ts=2.0`
  (patrón de fixture) y assets `NZCADC_otc`/`TESTDS_otc`/`DIAG_otc`.
  **Fix**: mismo patrón que `_aislar_csv_auditoria` (fixture autouse con
  `tmp_path` + `monkeypatch.setattr("black_box_recorder.BLACK_BOX_DB", ...)`),
  replicado en ambos archivos. Misma regla: `tests/test_black_box_stoch.py`
  ya lo hace bien (test `test_record_candidate_persists_direction_source`).
  **Done**: suite verde + `data/db/` sin filas nuevas de fixtures tras correr tests.

- [ ] **D2. Fase A (direction_source) implementada SIN COMMITEAR** por la otra ventana.
  Diff pendiente: `src/scanner.py`, `src/black_box_recorder.py`,
  `src/edificio_contratacion.py` (BuildingCard), `src/edificio_executor.py`,
  `tests/test_black_box_stoch.py`, `tests/test_edificio_contratacion.py`.
  - Revisar el bug menor: scanner.py:1501 setea `_direction_source = "M15"`
    SIEMPRE que entra al fallback M15, incluso cuando el fallback NO define
    dirección (queda `direction=""` con `direction_source="M15"`).
    → `direction_source` debe ser `""` si no hay dirección.
  - Correr A5 (validación): suite edificio verde + `.\init.ps1` sin crecer los
    32 fallos preexistentes.
  - Commitear (A6): `feat(edificio): telemetria direction_source en caja negra`.
  - Actualizar `progress/todos_direction_source_2026-08-03.md` marcando Fase A
    completa. **NO bumpear rule_version, NO tocar la decisión**.
  **Done**: commit + árbol limpio + lista T2 actualizada.

---

## Tanda T4 — Verificar la clasificación de cruces K/D (FASE 2 del edificio)

Reglas duras (heredadas de la tanda anterior):

- **Una tarea a la vez.** Tests verdes con cada cambio de código.
- Suite del edificio: `python -m pytest tests/test_edificio_contratacion.py tests/test_edificio_executor.py tests/test_edificio_trazabilidad.py tests/test_black_box_stoch.py` (51 tests hoy).
- Los 32 fallos preexistentes (STRAT-A, session_lifecycle, smart_order_place) NO son responsabilidad: no deben crecer, pero no los arregles.
- **NO tocar la decisión de entrada** — esta tanda SOLO observa y registra. La decisión se toma después, con datos y aprobación del usuario.
- **El freno es ALERTA de preparación, no entrada**: un CONFIRMED no debe llegar a orden hasta que TODA la estrategia (freno → cruce → condiciones finales) esté completa. NO se evalúa WR en esta etapa.
- **NO bumpear `EDIFICIO_RULE_VERSION`** (no cambia reglas de decisión, solo telemetría).
- Commits convencionales, mensajes claros. Sin atribución de IA.
- **La DB/CSV de producción NO se contamina con fixtures** (tmp_path/monkeypatch).
- Una tarea NO está done sin el test que la prueba, verificado contra el código real (no contra claims).

### Fase A — Telemetría del cruce por evaluación (code-change, NO toca la decisión)

- [ ] **A1. Registrar cada evaluación del edificio en la caja negra**
  Hoy `scan_candidates` solo tiene filas EDIFICIO cuando se envía orden
  (`_record_sent_to_black_box`, edificio_executor.py:347). Para clasificar
  cruces se necesita una fila por evaluación (o un evento) con:
  - `piso` (P1/P2/P3/FUERA), `brake_ok`, `extreme_ok`, `cross_ok`, `cross_sticky`
  - `stoch_k`, `stoch_d`, `kd_distance` (= |K-D|), `direction`, `direction_source`
  - ts del scan y asset.
  **Cómo**: evaluar en `_feed_edificio` (scanner.py:3020) un `record_edificio_eval`
  nuevo en la caja negra, o reutilizar `record_candidate` con estrategia
  `EDIFICIO_EVAL`. Elegir el camino que NO duplique el registro de órdenes.
  **Done**: un ciclo de evaluación produce filas con piso y condiciones.

- [ ] **A2. Clasificación correcta de los cruces (el corazón de la tanda)**
  Verificar contra el código real que:
  - `_cross_up` / `_cross_down` (scanner.py:1502-1503) usan velas M15
    **CERRADAS** (el cache `candles_15m_by_asset` debe contener solo velas
    cerradas; verificar en el fetch) — un cruce NO puede dispararse con la
    vela en formación.
  - `is_sticky_cross` (|K-D| < 3.0, edificio_executor.py:44) clasifica bien:
    probar con K,D pegadas (sticky) vs separadas (limpio).
  - La separación K/D (`cross_separation_since` + `EDIFICIO_SEPARATION_WAIT_SEC`)
    se mantiene solo con cruce limpio sostenido.
  - El cruce se exige para subir a P3 y se vuelve a exigir dentro de P3:
    documentar el flujo real y si la "sala de espera" del plan es P2 de facto.
  **Cómo**: tests unitarios contra `is_sticky_cross` + tests de integración de
  `_feed_edificio` con velas fabricadas (cerradas) + revisión del fetch.
  **Done**: tests verdes + hallazgos documentados en este doc.

- [ ] **A3. Columna `piso` / `condiciones` persistidas y leídas**
  Patrón `direction_source` (columna TEXT + parse + INSERT). Verificar lectura
  con query real contra DB de tests (no mocks).
  **Done**: query real devuelve piso y condiciones por evaluación.

- [ ] **A4. Tests**
  - Clasificación sticky/limpio/separación con casos límite (K=D exacto, |K-D|=2.9 vs 3.1).
  - Evaluación registrada por ciclo (1 scan → N filas, una por activo evaluado).
  - Sin contaminar la DB real (fixture tmp_path).
  **Done**: suite edificio verde (51 + nuevos) + DB real sin filas nuevas.

- [ ] **A5. Validación**
  1. Suite edificio verde.
  2. `.\init.ps1` → los 32 fallos preexistentes NO crecen.
  **Done**: evidencia escrita en este doc.

- [ ] **A6. Commit**
  - `feat(edificio): telemetria de evaluacion para clasificar cruces K/D` (o similar).
  - NO bumpear rule_version. NO tocar la decisión.
  **Done**: commit + `git status` limpio.

### Fase B — Recolección en demo (próxima hora de ejecución; NO es tarea de Hermes; es del usuario)

- [ ] **B1.** Correr el bot en PRACTICE durante **≥1 hora** con la telemetría
  activa. Objetivo: **n≥30 evaluaciones con cruce** (entre limpio, sticky y sin
  cruce) en activos reales, registradas en la caja negra.
  - Registrar fecha/hora de inicio y fin; ventana completa en la Fase C.
  - NO se envían órdenes por esto (el cruce no dispara entrada).

### Fase C — Análisis y veredicto (read-only → aprobación del usuario)

- [ ] **C1.** Con la muestra B1: query a la caja negra y clasificar los cruces
  por `cross_kind` (up/down/none) y por sticky/limpio. Comparar contra el
  estocástico que muestra la plataforma (screenshot/referencia si aplica).
- [ ] **C2.** Veredicto: ¿la clasificación del motor coincide con la realidad?
  - ¿El cruce se detectó sobre velas cerradas?
  - ¿El filtro sticky y la separación filtraron lo esperado?
  - ¿El flujo P2→P3 respeta la sala de espera del plan?
- [ ] **C3.** Recomendación escrita → **ESPERAR al usuario**. NO convertir en
  código sin aprobación explícita.

---

## Pendiente referenciado (NO mezclar con esta tanda)

- **T2 (direction_source)**: Fase C de decisión M1 vs M15 — recién después de
  juntar su propia muestra. Fase A ya implementada (falta D2: revisar+commitear).
- **T3 (post-freno)**: cierre del experimento `EDIFICIO_POST_BRAKE_MIN_RATIO`.
- **Señal final de compra/venta**: NO existe aún por diseño (freno = fase 1,
  cruce = condición posterior). Tema a definir con el usuario cuando estas
  verificaciones cierren.

---

## Orden de ejecución
D1 → D2 → A1 → A2 → A3 → A4 → A5 → A6 → (B1 = usuario deja correr demo ≥1h) → C1 → C2 → C3 → ⏸ usuario.
