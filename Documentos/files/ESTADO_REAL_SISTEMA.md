# ESTADO REAL DEL SISTEMA
*Fuente única de estado operativo validado contra código y runtime*

Última actualización: 2026-05-22

---

## Alcance
Este documento consolida el estado real del proyecto comparando:
- documentación
- código fuente actual
- scripts de observación
- artefactos runtime/export
- tablas reales en SQLite

No define arquitectura nueva y no modifica lógica live.

---

## 1) Matriz de Estado Real

| Módulo / Área | Documentado | Implementado | Validado runtime | Validado estadísticamente | Estado real |
|---|---|---|---|---|---|
| Fase 2 vetos OLD | Sí | Sí (`_pre_validate_entry`) | Sí (rechazos en journal) | Parcial (sin desglose robusto por filtro+resultado) | Completado operativo |
| Fase 3 timing+maduración VIP | Sí | Sí (`_pre_validate_entry` + `_update_vip_library`) | Sí (gates de `vip_maturity` y `candle_timing`) | Pendiente (sin serie cerrada por filtro) | Completado operativo |
| Autoridad OLD | Sí | Sí | Sí | No aplica | Autoridad única vigente |
| Motor NEW (`entry_decision_engine`) | Sí | Sí | Parcial (solo vía shadow) | No | Experimental observador |
| Shadow context/hash/persist | Sí | Sí | Parcial (tabla existe, cobertura insuficiente) | No | Experimental no validado |
| Shadow runtime métricas en logs | Sí | Sí | Parcial (instrumentado, sin evidencia útil sostenida) | No | Instrumentado, sin muestra concluyente |
| Link outcome->shadow por candidate_id | Sí | Sí | Parcial | No | Funciona en código, sin dataset suficiente |
| Parser/reconcile/overhead scripts | Sí | Sí | Sí (CLI funcional) | No | Operativos |
| Framework GO/NO-GO formal | Sí | Sí (pack) | No | No | Definido pero no ejecutado con muestra válida |
| Validación estadística NEW vs OLD | Sí | Parcial (queries base) | No | No | Pendiente crítica |

---

## 2) Mapa de Flujo Real (Código)

Flujo principal:

1. CANDIDATE
   - STRAT-A candidato: `consolidation_bot.py` (`CandidateEntry` en scan)
   - STRAT-B candidato: `consolidation_bot.py` (bloque STRAT-B)

2. OLD
   - `_pre_validate_entry(...)` ejecuta vetos binarios y decide autorización real

3. SHADOW
   - `_build_shadow_context(...)`
   - `_run_shadow_observation(...)` llama `evaluate_entry(...)` y `explain_decision(...)`

4. JOURNAL
   - `log_candidate(...)` para ACCEPTED/REJECTED
   - `log_shadow_decision(...)` en `shadow_decision_audit`

5. ENTER
   - `_enter(...)` aplica lock de entrada, timing, payout check y `place_order(...)`

6. RESOLVE
   - `_resolve_trade(...)` actualiza outcome/profit y ciclo

7. OUTCOME LINK
   - `update_shadow_outcome_by_candidate(candidate_id=journal_id, ...)`

### Paths alternos
- STRAT-B live path existe, pero `main.py` fuerza `STRAT_B_CAN_TRADE = False` por diseño operativo actual.
- Martin/gale usan `_enter(..., stage="martin")` y pasan por lock/timing.
- Reconnect path: `ensure_connection()` -> `reconnect_client(...)` con lock de conexión.
- Legacy path: código LEGACY-RJ sigue presente, flags operativos deshabilitados.

### Riesgos de trazabilidad
- `candidate_id` puede quedar nulo en shadow cuando no hay `journal_cid` en ciertas rutas.
- `update_shadow_outcome_by_candidate` actualiza por `candidate_id`; si hubiese duplicados de `candidate_id` en shadow, impacta múltiples filas.
- Outcomes `UNRESOLVED` en candidates degradan calidad de muestra estadística cerrada.

---

## 3) Estado Real de Shadow

### Confirmaciones
- OLD sigue siendo autoridad única de ejecución.
- NEW solo observa (no autoriza órdenes).
- Shadow está desacoplado del broker/live execution.

### Cobertura actual
- Tabla `shadow_decision_audit` existe en DB reciente.
- Cobertura de filas aún insuficiente para validación formal NEW vs OLD.

### Riesgos abiertos
- Cobertura incompleta por path (especialmente rutas no frecuentes o con `candidate_id` ausente).
- Linkage no evaluable estadísticamente sin volumen de rows con `trade_outcome` final enlazado.
- Riesgo de divergencia no cuantificable todavía por falta de muestra.

---

## 4) Contradicciones detectadas (Docs vs código)

1. README desactualizado en umbrales y operación STRAT-B. Estado: corregido en esta sincronización.
2. README referenciaba carpeta `documentacion/` cuando la base actual está en `Documentos/`. Estado: corregido en esta sincronización.
3. Roadmap marcaba fase 2.5 como planificación pura, pero ya existe implementación parcial (motor NEW + hooks shadow). Estado: corregido en esta sincronización.
4. Métricas semanales documentadas sin script consolidado equivalente en runtime actual. Estado: pendiente (se mantiene paquete SQL + scripts shadow como vía operativa actual).

---

## 5) Framework GO / NO-GO actualizado

### Etapa A: Observación
- GO si:
  - logs incluyen `SHADOW-RUNTIME` y `SHADOW-DATA`
  - se generan artifacts parser/reconcile/overhead por sesión
  - no hay errores persist/eval

### Etapa B: Validación estadística formal
- GO si:
  - tamaño de muestra mínimo por categoría utilizable
  - divergencia OLD vs NEW medible
  - linkage outcome >= umbral definido
  - drift contexto/hashes dentro de tolerancia

### Etapa C: Paper trading comparativo
- GO si:
  - etapa B aprobada
  - degradación runtime dentro de tolerancia
  - rollback criteria definido y probado

### Etapa D: Live parcial
- GO si:
  - estabilidad operacional sostenida
  - métricas NEW superiores/no inferiores con significancia mínima

### Etapa E: Live authority NEW
- GO si:
  - evidencia estadística concluyente
  - riesgo runtime y trazabilidad controlados

Regla global: si falta evidencia suficiente, decisión automática = NO-GO.

---

## 6) Validación Estadística requerida (pendiente)

Comparativas requeridas:
- divergence OLD vs NEW
- WR, PF, expectancy
- métricas por asset
- métricas por horario
- métricas por strategy_origin
- métricas por veto_count
- métricas por HTF alignment
- impacto sobre ciclos Masaniello

Estado actual: no hay evidencia suficiente para dictamen estadístico concluyente NEW vs OLD.

---

## 7) Prioridad actual (sin cambios live)

1. Asegurar cobertura de shadow_decision_audit en sesiones controladas.
2. Ejecutar paquete SQL+scripts por sesión y preservar evidencia.
3. Cerrar brechas de integridad del dataset antes de cualquier promoción del motor NEW.

---

## 7.1) Limpieza y orden de repositorio (2026-05-22)

- Se mantiene el principio operativo: plan en curso, sin promoción de NEW y sin cambios de autoridad live.
- Se depuró la raíz del proyecto quitando scripts ad-hoc de diagnóstico puntual y artefactos de logs históricos.
- Se centralizó material de auditoría manual en carpetas dedicadas para evitar ruido en ejecución diaria.
- Se sincronizó documentación de arquitectura/CLI con el estado real de `main.py`.

Resultado: menor deuda operativa y menos riesgo de confundir scripts experimentales con runtime productivo.

---

## 8) Logros verificados (corrida PV real 2026-05-12)

Se registran logros concretos obtenidos en validación transaccional end-to-end usando
`PIPELINE_VALIDATOR=true`, sin declarar mejora estadística de edge.

### Logro L-01: ciclo completo de ejecución validado en real

Evidencia en `pv_run_fix_20260512_165132.log`:

- `[PV-ORDER-SENT]`
- `[PV-BUY-CONNECTION-CHECK]` y `[PV-BUY-READY]`
- `[PV-BUY-RAW-RESULT]` con respuesta broker tipo tuple `(True, {...})`
- `[PV-ORDER-OPEN]`
- `[PV-WATCHER-OPEN]` -> `[PV-WATCHER-POLL]` -> `[PV-WATCHER-RESULT]`
- `[PV-WATCHER-CLOSED]`
- `[PV-RESULT-WIN]` + `[PV-PIPELINE-COMPLETE]`
- `[PV-CLEANUP-START]` + `[PV-CLEANUP-END]`

Resultado: validación positiva del flujo completo
`SCAN -> CANDIDATO -> ORDER OPEN -> RESULT -> CLEANUP`.

### Logro L-02: mitigación del bloqueo en ruta `place_order()`

Se confirmó en runtime la mitigación del cuello previo de `buy()` (conexión cerrada/intermitente)
mediante endurecimiento de la ruta de orden:

- pre-check de conexión y readiness antes de `buy()`
- timeout duro local de compra
- retry controlado (una vez) en errores de conexión/timeouts
- trazabilidad raw de respuesta broker (`[PV-BUY-RAW-RESULT]`)

Impacto observado: la orden abrió y cerró correctamente en la corrida PV validada.

### Logro L-03: cleanup operativo post-resolución con estado explícito

Evidencia de cleanup posterior a resultado con estado final explícito en log:

- `active_trades=0`
- `cooldown_assets=0`
- `lock=False`

Esto confirma cierre operativo del ciclo validado sin operación activa residual.

### Alcance y límites

- Este logro valida completitud operativa del pipeline transaccional en modo PV.
- No sustituye la validación estadística formal NEW vs OLD ni la evaluación de edge.
- El objetivo de esta evidencia es resiliencia/observabilidad de ejecución, no rentabilidad.
