# 07 — Análisis de divergencias estocásticas desde la caja negra

> **Marco de análisis** para evaluar el poder predictivo de las divergencias
> del estocástico M15 sobre los trades STRAT-F.
> **Fase:** medición y análisis (pre-SDD). No toca código de entrada.
> Última actualización: 2026-07-15

---

## 1. Propósito y alcance

### 1.1 Qué es este documento

Un **framework de análisis** para responder, con datos reales de la caja negra,
cuánto poder predictivo tienen las divergencias del estocástico M15 sobre el
resultado de las señales STRAT-F.

### 1.2 Qué NO es

- No es un spec de implementación.
- No define reglas de entrada finales.
- No modifica `scanner.py`, `stochastic_m15.py`, `black_box_recorder.py` ni
  ningún archivo bajo `src/`.

### 1.3 Principio rector

> **"Medir primero, promover después."**
> Ninguna divergencia se convierte en filtro, veto o boost de score sin
> evidencia estadística de la caja negra (mínimo 100 trades por categoría).

---

## 2. Contexto actual

### 2.1 Qué ya se graba

La tabla `scan_candidates` de la caja negra ya persiste por trade:

| Campo | Tipo | Contenido |
|-------|------|-----------|
| `stoch_m15` | JSON | `{k, d, estado, cruce, divergencia, contradicts}` |
| `stoch_contradicts` | INT 0/1 | Flag rápido: estocástico va contra la dirección |
| `candles_15m` | JSON | Snapshot de velas M15 pre-entrada |
| `candles_5m` | JSON | Snapshot de velas M5 pre-entrada |
| `candles_1m` | JSON | Snapshot de velas M1 pre-entrada |
| `candles_post` | JSON | 3-5 velas M1 post-expiry |
| `direction` | TEXT | `call` / `put` |
| `order_result` | TEXT | `WIN` / `LOSS` / `PENDING` |
| `profit` | REAL | Ganancia/pérdida neta |
| `entry_price` | REAL | Precio de entrada (open 1m) |
| `exit_price` | REAL | Precio al expiry |
| `score` | REAL | Score del candidato (0-100) |
| `payout` | INT | Payout % del broker |
| `asset` | TEXT | Par operado |
| `ts` | REAL | Timestamp UTC de la señal |

### 2.2 Qué calcula `compute_stoch()` hoy

```
stoch_m15 = {
    "k": float,              # %K actual (último valor)
    "d": float,              # %D actual (SMA 3 de %K)
    "estado": str,           # "SOBRECOMPRA" | "SOBREVENTA" | "NEUTRO"
    "cruce": str|None,       # "alcista" | "bajista" | None
    "divergencia": str|None, # "bull" | "bear" | None
    "contradicts": int,      # 0 | 1
}
```

La divergencia actual (`_detect_divergence`) usa una ventana fija de 5 velas
y compara el último cierre contra el mínimo/máximo del resto. Es una **primera
aproximación**, suficiente para medición inicial pero insuficiente para
análisis fino de swings.

---

## 3. Taxonomía de divergencias para STRAT-F

### 3.1 Divergencia regular (reversión de tendencia)

| Tipo | Patrón de precio | Patrón de %K | Dirección STRAT-F esperada |
|------|-----------------|--------------|---------------------------|
| **Regular alcista (RB)** | Mínimo más bajo (LL) | Mínimo más alto (HL) | CALL |
| **Regular bajista (RB)** | Máximo más alto (HH) | Máximo más bajo (LH) | PUT |

**Interpretación:** el momentum (%K) se agota antes que el precio. Señal de
reversión. En STRAT-F, refuerza el rebote en banda Wyckoff.

### 3.2 Divergencia oculta (continuación de tendencia)

| Tipo | Patrón de precio | Patrón de %K | Dirección STRAT-F esperada |
|------|-----------------|--------------|---------------------------|
| **Oculta alcista (HB)** | Mínimo más alto (HL) | Mínimo más bajo (LL) | CALL |
| **Oculta bajista (HB)** | Máximo más bajo (LH) | Máximo más alto (HH) | PUT |

**Interpretación:** el precio retrocede menos que el momentum → la tendencia
subyacente sigue fuerte. En STRAT-F, puede indicar que el fractal M5 es parte
de una continuación, no un rebote de rango.

### 3.3 Extremos sin divergencia

| Estado | Condición | Lectura en contexto STRAT-F |
|--------|-----------|----------------------------|
| **SC puro** | `k >= 80`, sin divergencia | Rango recalentado arriba; PUT en banda superior tiene contexto favorable |
| **SV puro** | `k <= 20`, sin divergencia | Rango congelado abajo; CALL en banda inferior tiene contexto favorable |
| **SC sostenida** | `k >= 80` por ≥3 velas M15 | Posible tendencia alcista fuerte; PUT contra tendencia = riesgo |
| **SV sostenida** | `k <= 20` por ≥3 velas M15 | Posible tendencia bajista fuerte; CALL contra tendencia = riesgo |

### 3.4 Cruces %K/%D en contexto

| Cruce | Zona | Lectura |
|-------|------|---------|
| **Alcista** (K cruza D hacia arriba) | Sobreventa (≤20) | Refuerzo CALL — momentum gira al alza desde extremo |
| **Alcista** | Neutro (20-80) | Señal débil por sí sola; necesita fractal M5 |
| **Bajista** (K cruza D hacia abajo) | Sobrecompra (≥80) | Refuerzo PUT — momentum gira a la baja desde extremo |
| **Bajista** | Neutro (20-80) | Señal débil por sí sola; necesita fractal M5 |

### 3.5 Contradicción estocástica

Ya implementada como `stoch_contradicts`:

- `direction=call` + `estado=SOBRECOMPRA` → contradicts=1
- `direction=put` + `estado=SOBREVENTA` → contradicts=1

**Hipótesis a validar:** los trades con `contradicts=1` tienen win_rate
significativamente menor que el baseline STRAT-F.

---

## 4. Detección desde los datos de la caja negra

### 4.1 Datos disponibles hoy

Con `candles_15m` (JSON de velas OHLC) + `stoch_m15` (JSON con k, d) se puede
reconstruir el contexto necesario para detectar divergencias **post-hoc** en
scripts de análisis (`analyze_trades.py`, `deep_analysis.py`).

### 4.2 Pseudocode: divergencia regular (bull)

```python
def detect_regular_bull_divergence(candles_15m: list[dict], k_vals: list[float],
                                    lookback: int = 20) -> bool:
    """
    Divergencia regular alcista:
      - Precio hace LL (lower low) en la ventana
      - %K hace HL (higher low) en la misma ventana

    candles_15m: lista de dicts con {open, high, low, close, timestamp}
    k_vals: serie completa de %K (no solo el último valor)
    """
    lows = [c["low"] for c in candles_15m[-lookback:]]
    k_window = k_vals[-lookback:]

    # Encontrar los dos últimos mínimos de precio
    price_minima = find_local_minima(lows, order=2)
    if len(price_minima) < 2:
        return False

    last_min = price_minima[-1]
    prev_min = price_minima[-2]

    # LL: el último mínimo es más bajo que el anterior
    if lows[last_min] >= lows[prev_min]:
        return False

    # HL: el %K en el último mínimo es más alto que en el anterior
    k_at_last = k_window[last_min]
    k_at_prev = k_window[prev_min]

    return k_at_last > k_at_prev


def find_local_minima(series: list[float], order: int = 2) -> list[int]:
    """Encuentra índices de mínimos locales (order = barras a cada lado)."""
    minima = []
    for i in range(order, len(series) - order):
        if all(series[i] < series[i - j] for j in range(1, order + 1)) and \
           all(series[i] < series[i + j] for j in range(1, order + 1)):
            minima.append(i)
    return minima
```

### 4.3 Pseudocode: divergencia regular (bear)

```python
def detect_regular_bear_divergence(candles_15m: list[dict], k_vals: list[float],
                                    lookback: int = 20) -> bool:
    """
    Divergencia regular bajista:
      - Precio hace HH (higher high)
      - %K hace LH (lower high)
    """
    highs = [c["high"] for c in candles_15m[-lookback:]]
    k_window = k_vals[-lookback:]

    price_maxima = find_local_maxima(highs, order=2)
    if len(price_maxima) < 2:
        return False

    last_max = price_maxima[-1]
    prev_max = price_maxima[-2]

    # HH: el último máximo es más alto
    if highs[last_max] <= highs[prev_max]:
        return False

    # LH: el %K en el último máximo es más bajo
    k_at_last = k_window[last_max]
    k_at_prev = k_window[prev_max]

    return k_at_last < k_at_prev
```

### 4.4 Pseudocode: divergencia oculta

```python
def detect_hidden_bull_divergence(candles_15m: list[dict], k_vals: list[float],
                                   lookback: int = 20) -> bool:
    """
    Oculta alcista (continuación):
      - Precio hace HL (mínimo más alto) → tendencia alcista intacta
      - %K hace LL (mínimo más bajo) → pullback de momentum
    """
    lows = [c["low"] for c in candles_15m[-lookback:]]
    k_window = k_vals[-lookback:]

    price_minima = find_local_minima(lows, order=2)
    if len(price_minima) < 2:
        return False

    last_min = price_minima[-1]
    prev_min = price_minima[-2]

    # HL en precio
    if lows[last_min] <= lows[prev_min]:
        return False

    # LL en %K
    return k_window[last_min] < k_window[prev_min]


def detect_hidden_bear_divergence(candles_15m: list[dict], k_vals: list[float],
                                   lookback: int = 20) -> bool:
    """
    Oculta bajista (continuación):
      - Precio hace LH (máximo más bajo)
      - %K hace HH (máximo más alto)
    """
    highs = [c["high"] for c in candles_15m[-lookback:]]
    k_window = k_vals[-lookback:]

    price_maxima = find_local_maxima(highs, order=2)
    if len(price_maxima) < 2:
        return False

    last_max = price_maxima[-1]
    prev_max = price_maxima[-2]

    # LH en precio
    if highs[last_max] >= highs[prev_max]:
        return False

    # HH en %K
    return k_window[last_max] > k_window[prev_max]
```

### 4.5 Detección de extremos sostenidos

```python
def is_sustained_extreme(k_vals: list[float], threshold: float,
                          min_bars: int = 3, lookback: int = 10) -> bool:
    """
    ¿El estocástico estuvo en el extremo (SC o SV) por al menos min_bars
    consecutivas dentro de la ventana lookback?
    """
    window = k_vals[-lookback:]
    consecutive = 0
    for k in reversed(window):
        if (threshold >= 80 and k >= threshold) or \
           (threshold <= 20 and k <= threshold):
            consecutive += 1
            if consecutive >= min_bars:
                return True
        else:
            consecutive = 0
    return False
```

---

## 5. Campos adicionales recomendados para la caja negra

### 5.1 Evaluación de campos actuales

| Campo actual | ¿Suficiente? | Nota |
|-------------|-------------|------|
| `stoch_m15.k` | ⚠️ Parcial | Solo el último valor. Para detectar divergencias se necesita la **serie completa** de %K en la ventana de lookback |
| `stoch_m15.d` | ⚠️ Parcial | Igual que k |
| `stoch_m15.divergencia` | ⚠️ Parcial | Usa ventana fija de 5 velas; no distingue regular vs oculta |
| `stoch_m15.cruce` | ✅ OK | Suficiente para análisis de cruces |
| `stoch_m15.estado` | ✅ OK | SC/SV/NEUTRO está bien |
| `stoch_m15.contradicts` | ✅ OK | Flag binario funcional |
| `candles_15m` | ✅ OK | Con OHLC se reconstruyen los swings de precio |

### 5.2 Campos propuestos (solo si justificados por el análisis)

> **No agregar ahora.** Estos campos se agregan solo cuando el análisis
> inicial demuestra que la serie histórica de %K/%D aporta poder predictivo
> adicional sobre el snapshot actual.

| Campo propuesto | Tipo | Justificación |
|----------------|------|--------------|
| `stoch_k_series` | JSON array | Serie completa de %K (últimas 20 velas M15). Necesaria para detectar swings y divergencias post-hoc sin recalcular |
| `stoch_d_series` | JSON array | Serie completa de %D (últimas 20 velas M15). Complemento de k_series |
| `stoch_div_type` | TEXT | Tipo de divergencia detectada: `regular_bull`, `regular_bear`, `hidden_bull`, `hidden_bear`, `none`. Reemplaza el booleano simple actual |
| `stoch_sustained_bars` | INT | Cuántas velas consecutivas estuvo en extremo (0 si no hay sostenimiento). Útil para filtrar "SC sostenida en tendencia" |

### 5.3 Criterio para agregar campos

Agregar un campo nuevo **solo si** se cumple:

1. El análisis con datos existentes muestra que la métrica derivada de ese
   campo correlaciona con win_rate (|correlation| > 0.15).
2. El campo no se puede derivar eficientemente de `candles_15m` + `stoch_m15`
   en el script de análisis.
3. El costo de almacenamiento es marginal (< 500 bytes por trade).

---

## 6. Métricas de evaluación

### 6.1 Métricas primarias

| Métrica | Fórmula | Umbral de interés |
|---------|---------|-------------------|
| **Win rate por tipo** | `wins / total` dentro de cada categoría de divergencia | > baseline STRAT-F + 5pp |
| **Expectancy por tipo** | `(win_rate * avg_profit_win) - ((1 - win_rate) * avg_profit_loss)` | > 0 (positiva) |
| **Contradiction rate** | `trades con contradicts=1 / total trades` | Contexto: qué % de señales van contra el estocástico |
| **Contradiction penalty** | `win_rate(contradicts=1) - win_rate(contradicts=0)` | < -10pp = candidato a veto |

### 6.2 Métricas secundarias

| Métrica | Qué mide |
|---------|----------|
| **Win rate por estado** | SC vs SV vs NEUTRO (sin considerar divergencia) |
| **Win rate por cruce + zona** | Cruce alcista en SV vs cruce alcista en neutro |
| **Win rate por payout + estado** | ¿El estocástico importa más con payout bajo? |
| **Win rate por asset + estado** | ¿Hay pares donde el estocástico funciona mejor? |
| **Tasa de falsas divergencias** | Divergencia detectada pero trade LOSS |
| **Recency effect** | ¿Las divergencias funcionan mejor en las primeras/últimas horas de sesión? |

### 6.3 Baseline de referencia

Todo análisis se compara contra el **baseline STRAT-F sin filtro estocástico**:

```
baseline_wr = win_rate global de STRAT-F (todos los trades, sin segmentar)
baseline_expectancy = expectancy global de STRAT-F
```

Una categoría de divergencia es **interesante** si:
- `wr_categoria >= baseline_wr + 5` puntos porcentuales, **o**
- `expectancy_categoria > baseline_expectancy * 1.2`

Una categoría es **dañina** si:
- `wr_categoria <= baseline_wr - 10` puntos porcentuales, **o**
- `expectancy_categoria < 0` (negativa)

---

## 7. Plan de análisis paso a paso

### Fase A — Auditoría de datos (semana 1)

**Objetivo:** saber qué tenemos y cuánto falta.

```sql
-- 1. Total de trades STRAT-F cerrados
SELECT COUNT(*) as total_trades
FROM scan_candidates
WHERE strategy = 'STRAT-F' AND order_result IN ('WIN', 'LOSS');

-- 2. Distribución por estado estocástico
SELECT
    json_extract(stoch_m15, '$.estado') as estado,
    COUNT(*) as total,
    SUM(CASE WHEN order_result = 'WIN' THEN 1 ELSE 0 END) as wins,
    ROUND(100.0 * SUM(CASE WHEN order_result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
FROM scan_candidates
WHERE strategy = 'STRAT-F' AND order_result IN ('WIN', 'LOSS')
    AND stoch_m15 IS NOT NULL
GROUP BY estado;

-- 3. Tasa de contradicción
SELECT
    stoch_contradicts,
    COUNT(*) as total,
    ROUND(100.0 * SUM(CASE WHEN order_result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
FROM scan_candidates
WHERE strategy = 'STRAT-F' AND order_result IN ('WIN', 'LOSS')
    AND stoch_m15 IS NOT NULL
GROUP BY stoch_contradicts;

-- 4. Distribución por cruce
SELECT
    json_extract(stoch_m15, '$.cruce') as cruce,
    COUNT(*) as total,
    ROUND(100.0 * SUM(CASE WHEN order_result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
FROM scan_candidates
WHERE strategy = 'STRAT-F' AND order_result IN ('WIN', 'LOSS')
    AND stoch_m15 IS NOT NULL
GROUP BY cruce;

-- 5. Divergencias detectadas (versión actual)
SELECT
    json_extract(stoch_m15, '$.divergencia') as divergencia,
    COUNT(*) as total,
    ROUND(100.0 * SUM(CASE WHEN order_result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
FROM scan_candidates
WHERE strategy = 'STRAT-F' AND order_result IN ('WIN', 'LOSS')
    AND stoch_m15 IS NOT NULL
GROUP BY divergencia;
```

**Criterio de salida:** tener al menos **50 trades STRAT-F** con `stoch_m15`
poblado y resultado cerrado. Ideal: 100+.

### Fase B — Análisis descriptivo (semana 2)

**Objetivo:** tablas de win_rate y expectancy por categoría.

1. Ejecutar las queries de Fase A.
2. Generar tabla resumen:

| Categoría | Trades | Wins | Win Rate | Avg Profit | Expectancy | vs Baseline |
|-----------|--------|------|----------|------------|------------|-------------|
| Baseline (todos) | N | W | X% | $Y | $Z | — |
| SC + PUT | | | | | | |
| SV + CALL | | | | | | |
| NEUTRO | | | | | | |
| Cruce alcista en SV | | | | | | |
| Cruce bajista en SC | | | | | | |
| Contradicts=1 | | | | | | |
| Contradicts=0 | | | | | | |
| Divergencia bull | | | | | | |
| Divergencia bear | | | | | | |

3. Identificar categorías con desviación significativa del baseline.

### Fase C — Re-detección de divergencias (semana 3)

**Objetivo:** detectar divergencias regular/oculta con el algoritmo de §4
sobre los `candles_15m` almacenados.

1. Extraer todos los trades con `candles_15m` poblado (mínimo 15 velas).
2. Para cada trade, reconstruir la serie de %K usando las velas 15m
   (mismo algoritmo que `compute_stoch`, con k_period=14, d_period=3).
3. Aplicar los 4 detectores (§4.2–§4.5) y clasificar cada trade en:
   - `regular_bull`, `regular_bear`, `hidden_bull`, `hidden_bear`, `none`
4. Cruzar con `order_result` y recalcular win_rate por tipo.

### Fase D — Análisis multivariable (semana 4)

**Objetivo:** entender interacciones entre factores.

1. **Estado × Dirección:** ¿SC favorece PUT más de lo que SV favorece CALL?
2. **Cruce × Estado:** ¿Un cruce alcista en SV es mejor que en neutro?
3. **Divergencia × Fuerza STRAT-F:** ¿La divergencia importa más cuando
   `strength` del fractal es marginal?
4. **Payout × Estado:** ¿El estocástico compensa payouts bajos?
5. **Asset × Estado:** ¿Hay pares donde el estocástico es más predictivo?

### Fase E — Propuesta de reglas (solo si la evidencia lo justifica)

**Objetivo:** traducir hallazgos en reglas candidatas para SDD.

Para cada regla candidata, documentar:

| Campo | Contenido |
|-------|-----------|
| **Regla** | Descripción concisa (ej: "Hard veto si contradicts=1 + SC sostenida ≥3 barras") |
| **Evidencia** | Win rate, expectancy, n de trades, intervalo de confianza |
| **Tipo** | `hard_veto` / `soft_veto` / `score_boost` / `score_penalty` |
| **Impacto estimado** | Cuántas señales filtraría, cuánto subiría el win_rate global |
| **Riesgo** | Falsos positivos (señales buenas que se perderían) |

---

## 8. Hipótesis a validar

| # | Hipótesis | Métrica de validación | Mínimo de trades |
|---|-----------|----------------------|------------------|
| H1 | `contradicts=1` reduce win_rate ≥ 10pp vs baseline | Win rate comparativo | 30 trades con contradicts=1 |
| H2 | SC + PUT tiene win_rate > baseline | Win rate por estado+dirección | 30 trades SC+PUT |
| H3 | SV + CALL tiene win_rate > baseline | Win rate por estado+dirección | 30 trades SV+CALL |
| H4 | Divergencia regular alineada con dirección sube win_rate ≥ 5pp | Win rate por tipo de divergencia | 20 trades con divergencia |
| H5 | Cruce alcista en zona SV refuerza CALL | Win rate cruce+zona | 20 trades |
| H6 | SC sostenida (≥3 barras) + PUT contra tendencia = LOSS frecuente | Win rate SC sostenida | 15 trades |
| H7 | Divergencia oculta indica continuación → fractal en contra es falso | Win rate cuando hidden contradice fractal | 15 trades |

---

## 9. Qué NO hacer en esta fase

### 9.1 Prohibiciones explícitas

| ❌ No hacer | Por qué |
|------------|---------|
| Agregar lógica de veto/boost en `scanner.py` o `entry_scorer.py` | Sin datos, es fe hardcodeada |
| Cambiar los umbrales 80/20 sin evidencia | Son los del libro de Lane; cambiarlos sin A/B es arbitrario |
| Usar divergencias de `stoch_m15.divergencia` como verdad absoluta | La detección actual (ventana de 5) es aproximada; re-detectar con §4 |
| Mezclar datos de diferentes estrategias | Solo trades STRAT-F; otras strats tienen dinámicas distintas |
| Sacar conclusiones con < 30 trades por categoría | Muestra insuficiente; alta varianza |
| Modificar `black_box_recorder.py` para agregar campos "por las dudas" | Violación del principio "medir primero"; agregar solo si §5.3 lo justifica |
| Tocar `feature_list.json` | Este documento es análisis, no una feature |

### 9.2 Anti-patrones a evitar

- **Cherry-picking:** no seleccionar solo los trades que confirman la hipótesis.
- **Overfitting retrospectivo:** no ajustar reglas para que funcionen perfecto
  sobre los datos pasados. Las reglas deben ser simples y generalizables.
- **Ignorar el payout:** un win_rate alto con payout 70% puede tener expectancy
  negativa. Siempre mirar expectancy, no solo win_rate.
- **Confundir correlación con causalidad:** que SC coincida con WIN no significa
  que SC cause WIN. Puede ser que STRAT-F ya filtre bien y el estocástico sea
  redundante.

---

## 10. Referencias cruzadas

| Archivo | Relación |
|---------|----------|
| `boblioteca/estocastico/01_historia_y_que_es.md` | Fórmula y origen del estocástico |
| `boblioteca/estocastico/02_cuando_usarlo.md` | Mercados donde funciona (rango vs tendencia) |
| `boblioteca/estocastico/03_senales_reales.md` | Señales clásicas de Lane (divergencias, cruces) |
| `boblioteca/estocastico/04_por_que_sirve_strat_f.md` | Justificación del estocástico M15 en STRAT-F |
| `boblioteca/estocastico/05_ejemplos_aplicados_binarias.md` | Ejemplos prácticos y esquema de caja negra |
| `boblioteca/estocastico/06_papel_en_escanner.md` | Rol como filtro de temporalidad mayor |
| `src/stochastic_m15.py` | Implementación actual de `compute_stoch()` |
| `src/black_box_recorder.py` | Schema de `scan_candidates` y métodos de persistencia |
| `src/scanner.py` | Donde se llama `compute_stoch()` y se graba en caja negra |
| `agent/HANDOFF.md` | Estado actual: stoch en modo medición, no decisión |
| `agent/TASKS.md` | P0: recolectar datos → análisis → SDD |
| `docs/ROADMAP.md` | Fase 6: datos → análisis → estocástico en entrada |

---

## 11. Glosario

| Término | Definición |
|---------|-----------|
| **%K** | Línea principal del estocástico: `(close - min_low) / (max_high - min_low) * 100` |
| **%D** | SMA de 3 períodos de %K (línea de señal) |
| **SC** | Sobrecompra: %K ≥ 80 |
| **SV** | Sobreventa: %K ≤ 20 |
| **HH** | Higher High: máximo más alto que el anterior |
| **LL** | Lower Low: mínimo más bajo que el anterior |
| **HL** | Higher Low: mínimo más alto que el anterior |
| **LH** | Lower High: máximo más bajo que el anterior |
| **pp** | Puntos porcentuales (diferencia absoluta entre win rates) |
| **Expectancy** | Ganancia esperada por trade: `(wr * avg_win) - ((1-wr) * avg_loss)` |
| **Baseline** | Win rate y expectancy global de STRAT-F sin filtro estocástico |
