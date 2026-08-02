# Auditoría EDIFICIO — Flujo ideal vs ejecución real

> Objetivo: comparar la arquitectura teórica documentada en `docs/EDIFICIO_CONTRATACION.md`
> contra la implementación real actual para deuda técnica.
>
> Regla: **no se modifica código aquí**, solo se registran desvíos como pendientes.

---

## 1. Resumen ejecutivo

| Capa | Ideal (documentado) | Real (implementado) | ¿Deuda? |
|------|---------------------|---------------------|---------|
| P1 — Recepción | Esperar payout ≥ umbral; si baja → fuera | Igual | No |
| P2 — Cerebro | 2 pruebas independientes (freno + extremo), puede esperar horas | Mismo scan: `if brake_ok and extreme_ok` → sube a P3 **en el mismo instante** | **Sí — sin espera post-freno** |
| P3 — Sala de espera | Esperar cruce limpio K/D; mientras espera, mantener condiciones vivas | Si `cross_ok or cross_sticky` → sube a P3; luego, con `body_5m>0.03`, contrata **en el mismo scan** | **Parcial** |
| Cross sticky | Si K/D muy pegadas → esperar a que se separen | Usa `is_sticky_cross()`; entra igual si sticky | **Sí** |
| Baja de piso | Si pierde condición → baja al piso anterior | No implementado como tal; si payout baja → expulsado; si no, se queda | **Sí** |
| POI tracker | Marcar paso por cada piso obligatoriamente | No hay tracker de POIs; sube si condiciones cumplidas sin marcas | **Sí** |
| Vigilante | Solo revisar piso actual por ronda | Scanner revisa todo cada 60s y deriva flags por asset | Parcial |
| Black box | Registrar filters_applied, rule_version, close data, loss_reason | Registra filters_applied y rule_version; **falta `loss_reason`** | **Sí** |

---

## 2. Auditoría piso por piso

### 2.1 P1 — Recepción

**Ideal:**
- Entrada solo si payout ≥ mínimo usuario.
- Si mientras espera baja el pago → fuera (Regla 1).
- No reevalúa pisos superiores si ya pasó.

**Real (`src/edificio_contratacion.py`):**
```python
# Línea ~244
if card.piso == PISO_FUERA:
    if payout_ok:
        card.piso = PISO_1
        ...
        return "subio"
```

**Diagnóstico:**
- Coincide con ideal.
- No hay evidencia en black box de entradas con payout < 80.
- **No aplica deuda.**

---

### 2.2 P2 — El cerebro (PRINCIPAL DESVÍO)

**Ideal documentado:**
- Prueba A: freno → "No ser quiquilloso. Si el freno está parcialmente confirmado, considerar que pasa."
- Prueba B: extremo (stoch ≤20 CALL, ≥80 PUT).
- Puede estar horas esperando hasta cumplir AMBAS.
- Cuando ambas OK → sube a P3.

**Real implementado:**
```python
# src/scanner.py:1510
_brake_ok = _prev_range > 0 and _last_range < _prev_range * 0.7

# src/edificio_contratacion.py:257
if brake_ok and extreme_ok:
    card.piso = PISO_2
    ...
    return "subio"
```

**Diagnóstico:**
- **Desvío 1 — Sin espera post-freno:** El sistema sube a P2 **en el mismo scan** en que detecta freno + extremo. No hay delay de "observar 1 vela cerrada" ni "esperar rebote".
- **Desvío 2 — Umbral rígido:** `_last_range < _prev_range * 0.7` exige 30% de reducción. En mercados laterales o con baja volatilidad, es demasiado estricto y filtra señales válidas.
- **Desvío 3 — No hay "parcialmente confirmado":** El código no implementa la regla práctica de "freno parcial cuenta". Es binario True/False.

**Evidencia black box (2026-08-01):**
- `brake_ok=True`: 24W/25L = **49% WR**
- `brake_ok=False`: 6W/4L = **60% WR**

Eso indica que el freno tal como está medido **no suma valor** hoy.

**Deuda técnica:**
1. Implementar espera post-freno: al menos 1 vela M15 cerrada después de `brake_ok=True` antes de evaluar extremo.
2. Hacer el freno gradual: `_brake_ok = _last_range < _prev_range * factor` con factor configurable, no hardcoded 0.7.
3. Implementar regla de freno parcial: si `_last_range < _prev_range * 0.85` → considerar "parcial", sumar puntos.

---

### 2.3 P3 — Sala de espera del cruce

**Ideal documentado:**
- Ya tiene brake + extremo.
- Espera **solo** el cruce limpio K/D.
- Mientras espera:
  1. ¿Sigue pagando? No → fuera.
  2. ¿Sigue frenado? No → vuelve a P2.
  3. ¿Sigue en extremo? No → vuelve a P2.
  4. ¿Ya hubo cruce limpio (no sticky)? Sí → CONTRATADO.

**Real implementado:**
```python
# src/edificio_contratacion.py:269
if cross_ok or cross_sticky:
    card.piso = PISO_3
    ...

# Línea 301-306
contract_now = (
    card.direction in {"CALL", "PUT"}
    and (cross_ok or cross_sticky)
    and extreme_ok
    and (candle_5m_body is None or candle_5m_body > 0.03)
)
```

**Diagnóstico:**
- **Desvío 1 — Entra con sticky:** El código usa `cross_sticky` como válido (`or cross_sticky`). El documento dice que sticky debe esperar a que se separe o ignorarse.
- **Desvío 2 — Sin mantenimiento de condiciones:** Una vez en P3, el sistema no reevalúa si `brake_ok` sigue vigente. Solo chequea payout, cross y body_5m.
- **Desvío 3 — Contratación inmediata:** Si en el MISMO scan llega `cross_ok` → contrata. No hay delay de "esperar apertura de próxima vela 15m" para ejecutar.

**Evidencia black box (2026-08-01):**
- `cross_ok=True`: 16W/12L = **57% WR**
- `cross_sticky=True`: 23W/24L = **49% WR**

El sticky está restando, pero el sistema lo permite entrar.

**Deuda técnica:**
1. Eliminar `cross_sticky` como entrada válida. Si sticky → volver a P2 hasta que se separe.
2. Agregar mantenimiento de condiciones en P3: si `brake_ok` se deshace → volver a P2.
3. Implementar delay de ejecución: entrada al **inicio de próxima vela 15m** después del cruce, no en el mismo scan.

---

### 2.4 Ejecución — `src/edificio_executor.py`

**Ideal:**
- Recibir evento CONTRATADO con todos los metadatos.
- Enviar orden al broker.
- Registrar en black box: order_id, rule_version, filters_applied, close data, loss_reason, result.
- Resolver WIN/LOSS robusto (doble path: ticket + order_id).

**Real implementado:**
- Envío por socket único: OK.
- Resolución doble (`check_win` + `get_result`): OK.
- Registro de `rule_version` y `filters_applied`: OK.
- **`loss_reason` nunca se setea.**

**Diagnóstico:**
- El resolvedor funciona (3 resoluciones exitosas post-fix).
- Pero sin `loss_reason` no podemos diagnosticar POR QUÉ perdió una entrada.

**Deuda técnica:**
1. En `resolve_one()` o en el flujo de post-ejecución, setear `loss_reason` según la fase en que falló:
   - `NO_PAYOUT` — payout < umbral en momento de entrada
   - `NO_BRAKE` — brake_ok se deshizo en P3
   - `NO_EXTREME` — stoch salió de extremo en P3
   - `NO_CROSS` — no hubo cruce limpio
   - `BODY_FILTER` — vela 5m chica bloqueó en P3
   - `STICKY_CROSS` — entró con sticky cuando no debía

---

### 2.5 Scanner — `src/scanner.py`

**Ideal:**
- Solo revisar el piso actual de cada asset.
- Orden: P3 → P2 → P1.
- No reevalúa todo desde cero.

**Real implementado:**
- Cada 60s calcula **todos los flags** (`brake_ok`, `extreme_ok`, `cross_ok`, `cross_sticky`, stoch, velas) para **todos los assets**.
- Luego llama a `_feed_edificio()`.

**Diagnóstico:**
- Es menos eficiente, pero no incorrecto.
- La carga computacional hoy no es el cuello de botella.

**Deuda técnica:**
1. Migrar a vigilante por piso: solo calcular flags necesarios para el piso actual.
2. Priorizar P3 (entrantes) antes que P1 (nuevos) para reducir latencia de entrada.

---

### 2.6 Black box — `src/black_box_recorder.py`

**Ideal:**
- Registrar TODO el contexto de la entrada y el cierre.
- `order_result`: WIN/LOSS/UNRESOLVED.
- `close_candle_5m/15m`, `close_stoch_m15`: forma del mercado en el cierre.
- `loss_reason`: por qué falló.
- `improvement_hint`: qué se puede corregir.

**Real:**
- `order_result`: parcial (18% NULL hoy, mejora desde 87%).
- `close_candle_5m/15m`, `close_stoch_m15`: 82-94% cobertura — **OK**.
- `loss_reason`: **0%** — nunca se setea.
- `improvement_hint`: **0%** — nunca se setea.

**Diagnóstico:**
- La telemetría básica está bien.
- Falta el diagnóstico de fallo.

**Deuda técnica:**
1. Poblar `loss_reason` en el flujo de resolución.
2. Poblar `improvement_hint` automáticamente (ej: "bajar umbral brake a 0.8", "ignorar cross_sticky").

---

## 3. Estado black box — 2026-08-01

### 3.1 Métricas globales (71 candidatos EDIFICIO)

| Métrica | Valor |
|---------|-------|
| Candidatos totales | 71 |
| order_result NULL | 13 (18%) |
| Wins | 30 |
| Losses | 28 |
| Fake IDs (OID-77/88) | 4 — irrecuperables |
| Real UUID IDs | 67 — recuperables |
| stoch_m15 completo (k!=None) | 67/71 (94%) — OK |
| close_candle_5m | 58/71 (82%) — OK |
| close_candle_15m | 57/71 (82%) — OK |
| close_stoch_m15 | 57/71 (82%) — OK |
| loss_reason | 0/71 (0%) — CRÍTICO |
| improvement_hint | 0/71 (0%) — CRÍTICO |

### 3.2 Clasificación de NULLs

| Tipo | Cantidad | Recuperable | Acción |
|------|----------|-------------|--------|
| FAKE_ID (OID-77/88) | 4 | No | Eliminar hardcodeo |
| STALE_NULL (pre-13:00) | 9 | Sí | Ejecutar resolvedor doble |
| Pendientes recientes | 0 | — | — |

### 3.3 Gaps de entrada

- Gap promedio: **7.9 min**
- Gap mínimo: **0s**
- Gap máximo: **67.7 min**

No es fallo del scanner: es el mercado el que no cumple las 3 pruebas seguidas (pago + freno + extremo).

---

## 4. Simulaciones Massaniello con datos reales (2026-08-01)

### 4.1 Configuración

- Depósito inicial: **$10**
- Payout promedio: **~92%**
- Trades resueltos disponibles: **59** (30W/28L, 51.7% WR real)
- Orden de ejecución: cronológico por `ts` de black box

### 4.2 Resultados

| Config | Trades | Resultado | Balance final | ¿Sobrevivió? |
|--------|--------|-----------|---------------|--------------|
| 7/4 | 7 | 3W/4L | $0.00 | **NO** |
| 10/6 | 10 | 5W/5L | $0.00 | **NO** |
| 10/6 + Gale 3 capas | 2-3 | 0W/8L | $0.00 | **NO** |

### 4.3 Conclusión Massaniello

Con depósito de $10 y payout ~92%, la gestión Massaniello **no salva el capital** con la muestra real de hoy.

**Razón:** la win rate real (51.7%) está por debajo de la esperada por Massaniello 7/4 (57% ITM) y 10/6 (60% ITM). El stake crece exponencialmente en rachas cortas de losses y liquida el capital antes de recuperar.

**No implementar gale simple ni modificar el sistema de stakes.** Con depósito chico, el gale 3 capas acelera la ruina.

---

## 5. Lista de deuda técnica priorizada

| # | Deuda | Piso afectado | Impacto estimado | Esfuerzo |
|---|-------|---------------|------------------|----------|
| 1 | **Espera post-freno** (mínimo 1 vela M15) | P2 → P3 | Alto — evita entradas inmediatas post-freno | Medio |
| 2 | **Eliminar cross_sticky como entrada válida** | P3 | Medio — sticky hoy da 49% WR vs 57% WR limpio | Bajo |
| 3 | **Mantenimiento de brake_ok en P3** | P3 | Medio — si el freno se deshace, no debería entrar | Medio |
| 4 | **Poblar loss_reason** | Executor | Alto — sin esto no sabemos por qué perdemos | Bajo |
| 5 | **Delay de ejecución** (inicio próxima vela 15m) | P3 → Broker | Medio — evita ejecución en medio de vela | Bajo |
| 6 | **Freno gradual** (factor configurable, regla parcial) | P2 | Medio — mejora detección en mercados laterales | Medio |
| 7 | **Scanner por piso** (solo flags necesarios) | Scanner | Bajo — eficiencia, no correctness | Alto |
| 8 | **POI tracker** (marcar paso por piso) | Todos | Bajo — audit trail, no afecta ejecución | Medio |

---

## 6. Comparación directa: documento vs código

### 6.1 Documento dice / Código hace

| Tema | Documento | Código |
|------|-----------|--------|
| **Freno como alerta** | "Esperar horas hasta cumplir pruebas" | Sube a P2 en mismo scan |
| **Freno parcial** | "No ser quiquilloso, parcial cuenta" | Binario True/False, sin grados |
| **Cross sticky** | "Esperar a que se separe o ignorar" | `cross_sticky=True` → entra igual |
| **Baja de piso** | "Si pierde condición → vuelve al piso anterior" | No implementado; solo expulsa por payout |
| **POI** | "Sin 3 POIs → no hay CONTRATADO" | No hay POI tracker |
| **Mantenimiento P3** | "Mientras espera, chequear 4 condiciones" | Solo chequea payout, cross, body_5m |
| **Loss reason** | No mencionado | No implementado |
| **Delay entrada** | "Entrada al inicio de próxima vela 15m" | No implementado; entra en mismo scan |

### 6.2 Flujo real actual (paso a paso)

```
Scan cada 60s:
1. Para cada asset OTC:
   - Calcular stoch_m15, velas M15/M5
   - Derivar: direction, brake_ok, extreme_ok, cross_ok, cross_sticky
   - Guardar snapshot en flags_by_asset

2. _feed_edificio(bot, assets, flags_by_asset):
   Para cada asset:
   a. Si P1: si payout_ok y brake_ok+extreme_ok → P2 (mismo scan)
   b. Si P2: si cross_ok o cross_sticky → P3 (mismo scan)
   c. Si P3: si body_5m>0.03 → CONTRATADO (mismo scan)

3. execute_contratados(bot):
   - Enviar orden al broker por socket único
   - Registrar en black box

4. resolve_contratados(bot):
   - Para cada orden pendiente:
     - check_win(ticket) → si WIN/LOSS, actualizar black box
     - get_result(order_id) → fallback si ticket=0
     - Si resolved=None/0 → marcar resolved=True, perder reintento
```

**Problema estructural:** el paso 2 es un pipeline secuencial dentro del mismo scan. No hay "tiempo real" entre pisos; todo se evalúa en el instante del scan.

---

## 7. Propuesta de flujo ideal (futuro)

```
Scan cada 60s:
1. Para cada asset en edificio:
   a. Si P1 y payout_ok:
      - Si brake_ok+extreme_ok → P2 (con marca de tiempo brake_at)
      - Si no → stay
   b. Si P2:
      - Si brake_at + MIN_BRAKE_WAIT < now:
        * Si extreme_ok → P3
        * Si no → stay
      - Si brake_ok se deshizo → volver a P1
   c. Si P3:
      - Si NO brake_ok → volver a P2
      - Si NO extreme_ok → volver a P2
      - Si cross_limpio (NO sticky) y body_5m>0.03:
        * Marcar entrada pendiente para próxima vela 15m
      - Si inicio de vela 15m y entrada_pendiente:
        * CONTRATAR
```

---

## 8. Próximos pasos recomendados

1. **Implementar espera post-freno** (Deuda #1): `MIN_BRAKE_WAIT = 1 vela M15 cerrada`.
2. **Eliminar cross_sticky** como entrada (Deuda #2): cambiar a `cross_ok=True` y `cross_sticky=False`.
3. **Poblar loss_reason** (Deuda #4): agregar en `resolve_one()` según fase de fallo.
4. **Implementar delay de ejecución** (Deuda #5): entrada al inicio de próxima vela 15m.
5. **Validar con black box** después de cada cambio: medir WR por condición.

---

## 9. Recomendaciones operativas inmediatas

| Tema | Recomendación | Razón |
|------|---------------|-------|
| **Gale** | NO implementar gale simple ni martingala | Con depósito $10 y payout ~92%, el gale 3 capas acelera la ruina |
| **Sticky threshold** | NO modificar `EDIFICIO_STICKY_THRESHOLD` | Muestra de 21 trades no muestra correlación entre separación K/D y win rate |
| **Filtro body_5m** | MANTENER | Mejoró WR de 41% a 59% post-actualización |
| **Resolvedor** | Ejecutar sobre 9 STALE_NULL | Mejora cobertura de black box de 82% a 100% |
| **loss_reason** | Implementar YA | Es la deuda de mayor impacto / menor esfuerzo |

---

*Creado: 2026-08-01*
*Estado: PENDIENTE — no se modificó código.*
