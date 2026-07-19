# Reporte de Auditoría — Datos Black Box STRAT-F

> Fecha: 2026-07-15
> Fuente: 7 black box DBs (2026-07-02 a 2026-07-15)
> Script: `scripts/audit_blackbox.py` + `scripts/deep_audit.py`

---

## 1. Resumen de datos recolectados

| Métrica | Valor |
|---------|-------|
| **Total STRAT-F trades con resultado** | **28** |
| WIN | 14 (50.0%) |
| LOSS | 14 (50.0%) |
| **Baseline win rate** | **50.0%** |
| Activos únicos | 20 |
| Score (todos 70.0) | fijo — no hay variación |
| DBs con stoch_m15 | 4 de 7 (07-13, 07-14, 07-15 + parciales) |
| DBs sin stoch_m15 | 3 (07-02, 07-03, 07-11, 07-12 — schema viejo) |

### Distribución por DB

| DB | Candidatos STRAT-F | Resueltos | Pendientes |
|----|-------------------|-----------|------------|
| 07-13 | 850 | 0 | 850 |
| 07-14 | 1961 | 19 | 1941 |
| 07-15 | 160 | 9 | 151 |
| **Total** | **2971** | **28** | **2942** |

---

## 2. Evaluación de completitud

### 2.1 stoch_m15

| Campo | Estado | Detalle |
|-------|--------|---------|
| **Presencia** | ✅ 100% | Los 28 trades resueltos tienen `stoch_m15` válido |
| **k** | ✅ Completo | Valores numéricos presentes en todos |
| **d** | ✅ Completo | Valores numéricos presentes en todos |
| **estado** | ✅ Completo | SOBRECOMPRA/NEUTRO/SOBREVENTA |
| **cruce** | ⚠️ Parcial | 12 de 28 tienen cruce (43%), 16 son `null` |
| **divergencia** | ⚠️ Parcial | Solo 3 de 28 tienen divergencia detectada (11%) |
| **contradicts** | ✅ Completo | Todos tienen el campo (todos = 0) |

### 2.2 candles_15m

| Métrica | Valor |
|---------|-------|
| **Presencia** | ✅ 100% (28/28) |
| **Suficientes para divergencia (>=15)** | ✅ 100% (28/28) |
| **Count fijo** | ⚠️ Siempre 20 velas — no varía |

### 2.3 Otros campos

| Campo | Estado |
|-------|--------|
| `direction` | ✅ CALL/PUT presentes |
| `order_result` | ✅ WIN/LOSS |
| `score` | ⚠️ **Siempre 70.0** — no hay variación de score |
| `asset` | ✅ 20 activos únicos |
| `ts` | ✅ Timestamps presentes |
| `stoch_contradicts` | ✅ Todos = 0 (ninguna contradicción detectada) |

---

## 3. Distribuciones observadas

### Estado estocástico

| Estado | Trades | % |
|--------|--------|---|
| NEUTRO | 16 | 57% |
| SOBREVENTA | 8 | 29% |
| SOBRECOMPRA | 4 | 14% |

### Win rate por estado

| Estado | WIN/Total | Win Rate |
|--------|-----------|----------|
| NEUTRO | 11/16 | 68.8% |
| SOBRECOMPRA | 2/4 | 50.0% |
| SOBREVENTA | 1/8 | 12.5% |

### Win rate por dirección + estado

| Dirección + Estado | WIN/Total | Win Rate |
|-------------------|-----------|----------|
| PUT + NEUTRO | 5/6 | 83.3% |
| CALL + NEUTRO | 6/10 | 60.0% |
| CALL + SOBRECOMPRA | 2/3 | 66.7% |
| PUT + SOBREVENTA | 1/3 | 33.3% |
| CALL + SOBREVENTA | 0/6 | **0.0%** |
| PUT + SOBRECOMPRA | 0/1 | 0.0% |

### Divergencias detectadas

| Tipo | Count | Win Rate |
|------|-------|----------|
| Ninguna | 25 | 56.0% |
| bull | 2 | 0.0% |
| bear | 1 | 0.0% |

---

## 4. Problemas identificados

### P1 — Volumen insuficiente (CRÍTICO)

**Solo 28 trades resueltos** de ~3000 candidatos. El 99% están pendientes.

Esto indica que el bot escanea mucho pero entra poco, o que los trades no se están resolviendo correctamente en la caja negra.

**Impacto:** 28 trades es insuficiente para cualquier análisis estadístico serio. El mínimo recomendado en `07_analisis_divergencias_blackbox.md` es 100 trades, con al menos 30 por categoría.

### P2 — Score siempre fijo en 70.0

Todos los 28 trades tienen `score = 70.0`. Esto sugiere que:
- El adaptive threshold no está variando, o
- Solo entran trades con score exacto del threshold

**Impacto:** No se puede analizar si el score correlaciona con win rate.

### P3 — stoch_contradicts siempre = 0

Ningún trade tiene contradicción detectada. Esto es sospechoso porque:
- 4 trades tienen SOBRECOMPRA + CALL (debería contradecir)
- 8 trades tienen SOBREVENTA + PUT (debería contradecir)

**Posible causa:** La lógica de `contradicts` en `stochastic_m15.py` es:
```python
if direction == "call" and estado == "SOBRECOMPRA": contradicts = 1
elif direction == "put" and estado == "SOBREVENTA": contradicts = 1
```
Pero los datos muestran CALL+SOBRECOMPRA con contradicts=0. Esto indica que el campo se graba **antes** de que se calcule la contradicción, o que la dirección que se pasa a `compute_stoch()` no coincide con la dirección final del trade.

### P4 — Divergencias con 0% win rate

Las 3 divergencias detectadas (2 bull, 1 bear) perdieron todas. Con n=3 no es estadísticamente significativo, pero es una señal a monitorear.

### P5 — Cruce null en 57% de los trades

16 de 28 trades no tienen cruce detectado. Esto es esperable (el cruce solo ocurre cuando K cruza D), pero limita el análisis de "cruce en zona extrema".

### P6 — candles_15m siempre = 20

Todas las entradas tienen exactamente 20 velas 15m. Esto es suficiente para el estocástico (14 período + buffer), pero **insuficiente para detectar divergencias regulares/ocultas** que necesitan ver 2 swings de precio, lo cual típicamente requiere 25-40 velas.

---

## 5. Hallazgos interesantes (preliminares)

### CALL + SOBREVENTA = 0% win rate (0/6)

Esto es contraintuitivo. La teoría dice que CALL en sobreventa debería ser bueno (rebote desde piso). Los datos muestran lo opuesto. **Pero con n=6 no es concluyente.**

### PUT + NEUTRO = 83.3% win rate (5/6)

PUT en estado neutro tiene el mejor win rate observado. Podría ser que STRAT-F ya filtra bien las señales PUT y el estocástico neutro no interfiere.

### NEUTRO domina (57% de trades)

La mayoría de las señales ocurren en zona neutra del estocástico, lo que sugiere que STRAT-F opera independientemente del estado estocástico.

---

## 6. Recomendación

### ¿Se puede empezar el análisis de divergencias?

**NO todavía.** Razones:

| Criterio (de 07_analisis) | Estado | Cumple? |
|---------------------------|--------|---------|
| Mínimo 50 trades STRAT-F | 28 | ❌ |
| Mínimo 30 trades con stoch completo | 28 | ❌ |
| Mínimo 30 trades por categoría | Máx 16 (NEUTRO) | ❌ |
| Mínimo 20 trades con divergencia | 3 | ❌ |
| Mínimo 15 trades con contradicción | 0 | ❌ |

### Acciones requeridas

1. **URGENTE: Investigar por qué 2942 de 2971 candidatos están pendientes.**
   - ¿El bot no está resolviendo trades?
   - ¿La caja negra no está actualizando `order_result`?
   - Esto es un bug de recording, no de volumen.

2. **Investigar por qué `stoch_contradicts` siempre es 0.**
   - Verificar que la dirección que se pasa a `compute_stoch()` coincide con la dirección del trade.
   - Revisar `scanner.py` línea ~1252 donde se llama `compute_stoch(candles_15m, direction=f_eval.direction)`.

3. **Seguir operando en Continuous Mode** hasta tener al menos 100 trades resueltos.
   - Con el ritmo actual (~28 trades en varios días), esto tomará ~2-3 semanas más.

4. **NO cambiar nada en la lógica de entrada** hasta tener datos suficientes.
   - Cualquier cambio ahora sería basado en ruido, no señal.

### Timeline estimado

| Hito | Trades necesarios | Tiempo estimado |
|------|-------------------|-----------------|
| Análisis descriptivo básico (Fase B) | 100 | ~2-3 semanas |
| Re-detección de divergencias (Fase C) | 150 | ~4 semanas |
| Análisis multivariable (Fase D) | 200+ | ~6 semanas |

---

## 7. Scripts de auditoría

Los scripts usados para este reporte están en:
- `scripts/audit_blackbox.py` — auditoría general de todos los DBs
- `scripts/deep_audit.py` — análisis detallado por DB

Ambos son read-only y no modifican datos.
