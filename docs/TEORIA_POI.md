# Teoría del POI como Área — Documento Vivo

> Documento teórico vivo — 2026-08-03.
> El POI como ÁREA **no está implementado** en el edificio de contratación hoy.
> Este documento define la teoría que debe guiar su implementación.
> Evoluciona con la evidencia; no se congela.

---

## 1. Qué es un POI

Un POI (Point of Interest) es una **zona de precio donde el mercado ya reaccionó antes**:
un nivel de swing (high/low) que fue tocado ≥ N veces dentro de una ventana de observación.

La hipótesis de negocio es la transición de presión (Principio 1 de FILOSOFIA.md):
un impulso que pierde energía al llegar a una zona de atención produce un rebote
técnico explotable (~15 minutos). El POI es la materialización de esa "zona de atención".

### 1.1 El POI es un ÁREA, no una línea

El mercado no reacciona en un precio exacto; reacciona en una **banda**. Las razones:

- Las órdenes se ejecutan a precios ligeramente distintos alrededor del nivel.
- El spread y la latencia del broker dispersan los puntos de contacto.
- Los participantes no ven el mismo "nivel exacto" al mismo tiempo.

Por eso un POI se modela como un rango `[nivel − banda, nivel + banda]`, no como un valor puntual.

### 1.2 Consecuencia operativa: el descarte

La regla central de este documento:

> **No se descarta una candidatura "a la primera".**
> Se descarta SOLO cuando el precio **sobrepasa la zona del POI**
> por el lado del impulso (la reacción esperada no se produjo ahí).

Un fallo instantáneo de una condición (p. ej. el `brake_ok` de la vela en formación)
es ruido; atravesar la zona POI por completo es señal. El freno deja de hacer
`CANCELLED`/`REJECTED` por condición puntual y lo hace por **sobrepaso de zona**.

---

## 2. Por qué el volumen lateral define el área (forex)

En mercados con volumen real (forex, futuros), el "grosor" de una zona POI se mide
con **volumen lateral**: cuánto se operó en cada nivel de precio. La herramienta
estándar es el **Volume Profile** (perfil de volumen) o **Volume by Price**
(volumen por precio):

- **Eje Y** (vertical, arriba-abajo) = **eje de PRECIO**.
- **Eje X** (horizontal, izquierda-derecha) = **eje de TIEMPO**.
- El histograma de volumen clásico (debajo del gráfico) es **volumen por tiempo**:
  una barra por vela, en el eje X.
- El **Volume Profile** es **volumen por precio**: cuánto se acumuló en CADA nivel,
  dibujado en el eje Y. Cada barra horizontal del perfil dice "este nivel de precio
  concentró N operaciones durante el período".

El área POI en forex = el rango de precios donde el perfil de volumen muestra una
**concentración** (una "joroba" en el perfil). El nivel con más volumen es el núcleo;
la dispersión del perfil a su alrededor define el ancho de la zona. Cada toque
operado "engorda" la zona.

---

## 3. El problema OTC (binarias sin volumen)

En binarias OTC **no existe volumen real** negociado: el broker sintetiza los precios
y no publica cantidad. El volumen lateral es, por definición, inmedible.

Los proxies válidos, en orden de fidelidad:

1. **Ticks (conteo de operaciones)** — el proxy más cercano al volumen real.
   Quotex envía `ticks` por vela y el proyecto ya los captura
   (`src/models.py:20` → `Candle.ticks`; `src/connection.py:88` y `:142`).
   Un Volume Profile construido sumando ticks por nivel de precio es la forma OTC
   de medir el grosor del área en el eje Y.
2. **Conteo de toques** — cuántas mechas rozan el nivel (tolerancia relativa).
   Proxy más barato y determinista; ya usado en `src/market_geometry_ctx.py`
   (tolerancia 0.06%, mínimo 2 toques).
3. **Dispersión de toques** — el rango de precio donde se concentraron los toques
   define el ancho del área sin depender de ticks ni volumen.
4. **Clustering por proximidad** — niveles cercanos dentro de una banda relativa
   (%) se agrupan en una misma zona; el ancho del cluster ES el grosor del área.
   Ya implementado en `src/zone_ia.py` (`ZONE_BAND_PCT = 0.0015` → 0.15%).

> Regla: el proxy elegido debe ser **determinista y causal** (solo usa velas ya
> cerradas), para que el backtest y el vivo midan exactamente lo mismo.

---

## 4. La regla del freno rediseñada

Hoy el freno descarta "a la primera":

- En P1 → `CANCELLED` si se pierde `brake_ok` instantáneo (la vela en formación).
- O `REJECTED` si al cerrar la vela el ratio de compresión ≥ 0.7.

El rediseño propuesto (teoría, no implementado):

1. El freno detecta el POI cercano (zona donde el impulso debería morir).
2. La candidatura se mantiene MIENTRAS el precio esté dentro del área POI
   (o del lado correcto de ella).
3. El descarte ocurre SOLO cuando una vela M15 cierra FUERA de la zona por el
   lado del impulso → el POI fue sobrepasado → la reacción esperada no se
   produjo ahí → la candidatura se cancela.

El "sobrepaso" se define con el cierre de vela (no con el extremo intrabarra):
una mecha que atraviesa la banda y vuelve NO es sobrepaso; un cierre fuera de la
banda SÍ lo es. Esto elimina el descarte por ruido de la vela en formación.

---

## 5. Estado del código — Hoy vs. Mañana

### Hoy (verificado en código)

| Componente | Estado | Dónde |
|---|---|---|
| "POI" en el edificio | Solo marcas temporales `has_poi_p1/p2/p3` (timestamps de aprobación de piso). NO es zona de precio | `src/edificio_contratacion.py:139-156` |
| Freno | Descarta a la primera (`CANCELLED` por `brake_ok`, `REJECTED` por ratio ≥ 0.7). Sin criterio de zona | `src/edificio_contratacion.py` (P1) |
| POI como zona (laboratorio) | POI = swing tocado ≥ 2 veces en 100 velas, banda ±5 pips. Puro backtest de la estrategia M3, no corre en vivo | `src/strategy_lab/poi_filter.py` |
| Swings M15 filtrados | Cuerpo mínimo + ≥2 toques (tolerancia 0.06%), emite líneas S/R. Lo usa STRAT-F | `src/market_geometry_ctx.py` |
| Clustering de zonas | Banda 0.15%, agrupa experiencias cerradas por nivel, emite confidence (win rate observado). Lo usa STRAT-F | `src/zone_ia.py` |
| Ticks de Quotex | Capturados por vela y sumados al resamplear. Usados solo en `zone_strength` (order-flow de la vela del rechazo) | `src/models.py`, `src/connection.py`, `src/zone_strength.py:201` |
| Volume Profile (ticks por nivel) | **NO existe** — construir es agregación pura sobre `Candle.ticks` | — |

### Mañana (propuesta de diseño)

1. Conectar una fuente de zonas al edificio (`zone_ia` es la más madura: banda 0.15% validada).
2. Definir el área POI con banda relativa (±0.15%) alrededor del nivel, engrosada por
   el proxy elegido (ticks por nivel / dispersión de toques).
3. Reemplazar el descarte instantáneo del freno por descarte por sobrepaso de zona
   (cierre M15 fuera de la banda por el lado del impulso).
4. Validar el proxy en el tribunal del Atlas (walk-forward + bootstrap + permutación)
   antes de tocar el edificio (Principio 4 de FILOSOFIA.md).

---

## 6. Referencias de código

- `src/edificio_contratacion.py` — edificio; POIs como marcas de piso (139-156); freno P1.
- `src/strategy_lab/poi_filter.py` — POI como banda ±5 pips, backtest M3.
- `src/market_geometry_ctx.py` — swings M15 filtrados, `sr_levels`, tolerancia 0.06%.
- `src/zone_ia.py` — clustering por proximidad, `ZONE_BAND_PCT = 0.0015` (0.15%).
- `src/zone_strength.py` — `_ticks_in_reject_candle` (201): order-flow por ticks de la vela del rechazo.
- `src/models.py` — `Candle.ticks` (20).
- `src/connection.py` — `raw_to_candle` (88) y resample suma de ticks (142).
- `src/entry_scorer.py` — `HIST_LEVEL_TOUCH_PCT = 0.0015`, `detect_swing_levels` (H1).
- `docs/FILOSOFIA.md` — Principios 1, 2 y 4 (fenómeno, instrumentos, tribunal).
