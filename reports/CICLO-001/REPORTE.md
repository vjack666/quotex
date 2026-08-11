# CICLO-001 — Verificación de la teoría del 74.6% (EXP-076) con redes neuronales + evaluación del POI

**Fecha:** 2026-08-09 · **Datos:** EURUSD OTC 60s, 76.835 velas (2026-06-13 → 2026-08-05)
**Timing (protocolo R12):** señal al cierre de vela → entry = open de la vela 60s que contiene t+300s (i+6) → exit = close de la vela que contiene t+1200s (i+21). CALL gana si close[exit] > open[entry].

---

## 0. Pregunta del cliente

> "2 experimentos con redes neuronales para verificar la teoría del 74.6% + evaluar el POI de la estrategia + una gráfica paso a paso de la estrategia con una foto en cada paso."

El EXP-076 reportó (rama OTC 60s puro): **CALL 74.6% (n=1962) | PUT 67.0% (n=1695)** con el gate compuesto arcoíris 7-EMA + válvula K/D.

---

## 1. Reconstrucción del gate (paso previo obligatorio)

Repliqué el gate del EXP-077/076 con fidelidad al código auditado (`audit_exp_edf.py`, `audit_edificio_funnel.py`):
- Estocástico FULL 14,3,3 (Lane) — idéntico al bot.
- Dirección: k≤20 y d≤20 → CALL; k≥80 y d≥80 → PUT (`derive_direction`).
- Válvula: K sale del extremo + |K-D| ≥ 5 + separación creciente en ventana.
- Arcoíris: 7 EMAs [5,10,20,40,80,160,320] estrictamente apilados a favor.
- Flujo real (del audit): señal por extremo → búsqueda de la vela de confirmación compuesta en (i, i+MAX_HOLD] → trade.

### ⚠️ Hallazgo de reproducibilidad — el 74.6% NO se reproduce

| Variante | CALL n | CALL WR | PUT n | PUT WR |
|---|---|---|---|---|
| Dirección extrema K/D sola | 13.950 | 49.4% | 14.104 | 48.5% |
| Dirección + arcoíris (misma vela) | 3 | 0-33% | 0 | — |
| Gate compuesto (dir → confirmación en ventana, MAX_HOLD 10-30) | 222-530 | 37.9-42.1% | 200-456 | 51.8-56.3% |
| **Objetivo EXP-076** | **1.962** | **74.6%** | **1.695** | **67.0%** |

**Ninguna combinación de parámetros (MAX_HOLD 10/15/20/30 × EVOLVE 3/5 × señal al open/cierre) reproduce las 1.962+1.695 señales al 74.6%/67.0%.** El arcoíris de 7 EMAs estrictamente apilado es extremadamente raro sobre velas 60s. **Conclusión honesta: el número del EXP-076 no es reproducible con el código actual** (el script original `hermes-verify-exp076.py` fue eliminado del disco). Lo documentado en `progress/history.md` es la única evidencia restante. No se declara el 74.6% como verificado.

---

## 2. EXP-NN-1 — La red neuronal a ciegas (¿el edge está en los datos crudos?)

- Features crudas (sin gate): retornos 1/5/20, body/range, ATR, ticks, stoch K/D crudo.
- Target: CALL gana (close[i+21] > open[i+6]).
- Split temporal estricto 70/15/15 cronológico (train 53.770 / val 11.522 / test 11.523).
- Modelos: MLP (64,32) + LightGBM. Umbral de decisión fijo 0.55.
- Base rate test: 49.03% · Breakeven (payout 92%): 54%.

| Modelo | Target | ops test | WR | p vs 54% | Veredicto |
|---|---|---|---|---|---|
| MLP | CALL | 186 | 58.1% | 0.135 | no significativo |
| LGBM | CALL | 398 | 55.3% | 0.300 | no significativo |
| MLP | PUT | 103 | 56.3% | 0.340 | no significativo |
| LGBM | PUT | 334 | 56.6% | 0.192 | no significativo |

**Veredicto:** la red a ciegas **no encuentra edge significativo** sobre el breakeven con features crudas. Los WR (55-58%) superan el base rate (49%) pero ningún p-valor alcanza significancia. **El 74.6% no es recuperable trivialmente solo con velas crudas.**

---

## 3. EXP-NN-2 — El juez del gate (¿el gate codifica el edge mejor que la red?)

- Features del gate: 7 EMAs, K, D, |K-D|, distancias close→EMA, distancia K al extremo, body/range/ticks ratios, retornos.
- Mismo target y split temporal estricto.

| Modelo | ops test | WR | p vs 54% | Top 10% confianza |
|---|---|---|---|---|
| MLP | 3.036 | 46.9% | 1.000 | 46.7% |
| LGBM | 4.357 | 46.7% | 1.000 | 45.2% |

**Veredicto:** con las features del gate, la red predice **PEOR que el azar** (46-47%, p=1.0), incluso en los top deciles de confianza. **No hay información predictiva explotable a +900s en las features del gate.**

### Conclusión conjunta de los dos experimentos NN
La teoría del 74.6% del EXP-076 **no se sostiene bajo aprendizaje automático**:
1. El gate reconstruido no reproduce las cifras (problema de reproducibilidad).
2. Ninguna red (cruda o con features del gate) supera el breakeven de forma significativa.
3. La red con features del gate rinde por debajo del azar → el gate no codifica un edge persistente en el período test.

---

## 4. EXP-POI — Evaluación del POI de la estrategia

POI = bandas de swing causales (`swing_levels_causal`, min_touches=2, tol=5 pips, lookback=100 — mismos defaults del módulo). Se midió el WR de las señales que entran **dentro** de una zona POI vs **fuera**.

| Universo | Dentro n | Dentro WR | Fuera n | Fuera WR | p (dentro>fuera) |
|---|---|---|---|---|---|
| Dirección extrema K/D (28.067 eventos) | 1.018 | 50.0% | 27.036 | 48.9% | 0.256 (ns) |
| **Gate compuesto (570 eventos)** | **38** | **71.1%** | 532 | 47.2% | **0.0025** |

Sensibilidad de parámetros POI sobre el gate compuesto:

| Configuración | Dentro n | Dentro WR | Fuera WR | p_diff |
|---|---|---|---|---|
| tol=3 pips | 38 | **84.2%** | 46.2% | <0.0001 |
| min_touches=3 | 33 | **81.8%** | 46.7% | <0.0001 |
| lookback=200 | 38 | 71.1% | 47.2% | 0.0025 |

**Hallazgo consistente y estadísticamente significativo:** la interacción **gate×POI es real**. El POI solo no aporta (50.0% vs 48.9%), pero cuando el gate compuesto entra **dentro** de una zona POI activa, el WR salta a 71-84% (vs 46-47% fuera), con p≤0.0025, estable en 3 configuraciones.

**Cautela obligatoria:** n=33-38 es pequeño (IC95% ~±12-15%). Es una pista fuerte, no una prueba. Siguiente paso natural: validar fuera de muestra con más datos (el CSV solo cubre 53 días) o con los otros 7 pares OTC si existen.

---

## 5. VISUAL-ESTRATEGIA — Gráfica paso a paso (7 PNG)

Se buscó la primera señal real del gate compuesto dentro de POI y se graficó la secuencia completa de la estrategia sobre esa señal (CALL, vela señal 986, gate 990, entry 996 [t+300], exit 1011 [t+1200], WIN):

| # | Archivo | Paso |
|---|---|---|
| 1 | `paso_1_01_estocastico_extremo.png` | Estocástico FULL 14,3,3 → zona de extremo (dirección) |
| 2 | `paso_2_02_kd_separacion.png` | Separación K-D ≥ 5 y creciente (presión) |
| 3 | `paso_3_03_valvula_sale.png` | Válvula: K sale del extremo |
| 4 | `paso_4_04_arcoiris_alineado.png` | Arcoíris 7-EMA alineado a favor |
| 5 | `paso_5_05_senal_gate.png` | Gate compuesto completo → SEÑAL |
| 6 | `paso_6_06_timing_broker.png` | Timing: entry open[t+300] → exit close[t+1200] |
| 7 | `paso_7_07_resultado_poi.png` | Resultado WIN + banda POI en contexto |

Cada PNG tiene 2 paneles: precio + EMAs + banda POI (arriba) y estocástico K/D (abajo). Ruta: `reports/CICLO-001/VISUAL-ESTRATEGIA/`.

---

## 6. Resumen ejecutivo

1. **El 74.6% del EXP-076 no se reproduce** con el gate reconstruido fielmente (la evidencia restante es solo el reporte histórico; el script fue eliminado).
2. **Las NN no encuentran edge**: ni a ciegas (EXP-NN-1) ni con features del gate (EXP-NN-2, que rinde bajo el azar).
3. **El POI sí muestra interacción real con el gate**: dentro de POI 71-84% vs 47% fuera (p≤0.0025), consistente — aunque con n pequeño.
4. La estrategia paso a paso quedó documentada en 7 imágenes.

**Recomendación:** 1) no operar en real con la configuración del EXP-076 tal cual; 2) el hallazgo gate×POI merece una validación OOS con más pares/datos antes de cualquier decisión; 3) considerar recuperar el script original del EXP-076 desde el historial git si existe.

## 7. Artefactos generados

```
reports/CICLO-001/
├── exp_common.py                      # módulo común (indicadores + gate + POI + timing)
├── EXP-NN-1/
│   ├── gate_verify.py                 # verificación de reproducibilidad del gate
│   ├── exp_nn1_red_ciega.py           # EXP-NN-1
│   ├── dataset_features.parquet       # dataset con features + targets
│   └── resultados_nn1.npz             # resultados EXP-NN-1
├── EXP-NN-2/
│   ├── exp_nn2.py                     # EXP-NN-2 (juez del gate)
│   └── resultados_nn2.npz             # resultados EXP-NN-2
├── EXP-POI/
│   └── exp_poi.py                     # EXP-POI (evaluación del POI)
└── VISUAL-ESTRATEGIA/
    └── paso_1..7_*.png                # 7 imágenes paso a paso
```
