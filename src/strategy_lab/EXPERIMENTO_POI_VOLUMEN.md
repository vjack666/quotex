# Experimento LAB — POI de VOLUMEN en el eje Y (franja)

> **Tipo:** Laboratorio (src/strategy_lab) — experimento documentado, sin código de producción.
> **Fecha:** 2026-08-03.
> **Estado:** DISEÑADO — pendiente de ejecutar la descarga y el análisis.
> **Filosofía:** Principios 4 y 6 de `docs/FILOSOFIA.md` — toda hipótesis se falsa con datos
> propios antes de entrar al núcleo. Este experimento corre en el laboratorio y NO toca el edificio.

> **⚠ ACTUALIZACIÓN (2026-08-03, corrección de enfoque):** este documento medía la
> efectividad como WR implícito — eso fue un error de enfoque. El POI es el CONTEXTO
> de la fase de freno, NO un predictor de resultado; el WR se mide al final de la cadena
> (freno → K/D → señal). El experimento de comportamiento que responde las 4 hipótesis
> correctas (sostiene / timing del freno / aguante a caída / flip de rol) está en
> `src/strategy_lab/poi_behavior.py`, su runner en `scripts/run_poi_behavior_experiment.py`,
> y su veredicto en `src/strategy_lab/resumen_poi_comportamiento.md`. Las secciones
> siguientes de este doc quedan como diseño del POI de volumen (construcción de franja),
> y la parte de WR (sección 6) se relega a la validación FINAL de la cadena.

---

## 1. Objetivo

Responder dos preguntas con datos reales:

1. **¿Cuántas velas M15 se pueden descargar de Quotex por par, y en cuánto tiempo?**
   (La API estándar limita a 199 velas/llamada ≈ 2 días de M15; la paginación profunda
   llega a semanas/meses — ver `docs/TEORIA_POI.md` §5 y la investigación 2026-08-03).
2. **¿Un POI de VOLUMEN (franja en el eje Y) es más efectivo que el POI actual?**

La idea del POI de volumen: en lugar de un POI como **línea** (nivel exacto) o como
**marca temporal** (los `has_poi_p1/p2/p3` del edificio), definir el POI como una
**FRANJA de precio** donde se acumuló más volumen (suma de `ticks` de las velas cuyo
rango toca ese nivel). Es análogo a un pivote, pero en franja: no un solo precio,
sino una banda con grosor definido por la acumulación.

---

## 2. Hipótesis

> **H1:** La franja de mayor acumulación de volumen (eje Y, M15) — el **POC dentro de su
> Área de Valor** (terminología Volume Profile estándar) — contiene el nivel donde el
> precio reacciona con más frecuencia que el POI actual (marcas de piso).

> **H2:** El grosor de la franja (definido por la dispersión de la acumulación) reduce
> los descartes "a la primera": el precio puede vagar dentro de la franja sin cancelar
> la candidatura; el descarte ocurre solo al sobrepasarla.

---

## 3. Universo de prueba — pares en PISO 1 (snapshot 2026-08-03 16:53)

Extraído del log de runtime `data/logs/runtime/consolidation_bot.log` (último evento por par).
Bot en vivo, 0 CONFIRMED (ningún par subió de P1 → TODOS estos están en P1):

**62 pares:**

```
ATOUSD, AUDCAD, AUDCHF, AUDJPY, AUDNZD, AUDUSD, AVAUSD, AXSUSD,
BCHUSD, BNBUSD, BRLUSD, BTCUSD, CADCHF, CADJPY, CHFJPY, DASUSD,
DOTUSD, ETCUSD, ETHUSD, EURAUD, EURCAD, EURCHF, EURGBP, EURJPY,
EURNZD, EURUSD, GBPAUD, GBPCAD, GBPCHF, GBPJPY, GBPNZD, GBPUSD,
LINUSD, LTCUSD, NZDCAD, NZDCHF, NZDJPY, NZDUSD, SOLUSD, TONUSD,
TRUUSD, UKBrent, USCrude, USDARS, USDBDT, USDCAD, USDCHF, USDCOP,
USDDZD, USDEGP, USDIDR, USDINR, USDJPY, USDMXN, USDPHP, USDPKR,
USDZAR, XAGUSD, XAUUSD, XRPUSD, ZECUSD
```

TODOS con sufijo `_otc`. Incluyen: 27 forex, 18 crypto, 3 metales, 2 energías,
3 índices (DASUSD, AVAUSD, TRUUSD), 9 exóticos de USD, 2 pares cruzados.

> Nota: los 62 están en P1 porque paga ≥ 90% (filtro de recepción). Son el universo
> exacto que el edificio está mirando AHORA. Un subconjunto (`*` en la lista de
> `CANCELLED`) ya intentó el freno y volvió — igual siguen en P1.

---

## 4. Protocolo de descarga (M15, paginación profunda)

### 4.1 Parámetros de la llamada (reverse-engineered por la comunidad)

| Parámetro | Valor correcto | Por qué |
|---|---|---|
| `get_candles(asset, end_time, offset, period)` | `period=900` (M15) | timeframe M15 = 900 s |
| `offset` | **fijo en 3600** | no es el tamaño del chunk |
| `step` | **2940 s hacia atrás** | paso de paginación validado |
| `index` | **12 dígitos** (`int(time.time() * 100)`) | el WS rechaza 10 dígitos en silencio |
| Clave de respuesta | `message["data"]` (no `["history"]`) | pyquotex original descarta los datos paginados |

### 4.2 Mediciones a registrar (por par)

| Métrica | Unidad |
|---|---|
| Velas pedidas (target) | n |
| Velas recibidas | n |
| Velas únicas tras dedupe | n |
| Gaps detectados | n |
| **Tiempo de descarga** | segundos |
| Ticks totales (suma `ticks` por vela) | n |
| Ticks máximos en una vela | n |

### 4.3 Targets sugeridos (a validar con el usuario)

| Ventana | Velas M15 esperadas | Uso |
|---|---|---|
| 2 días (≈ 192 velas) | 192 | igual que el límite estándar — baseline |
| 7 días (≈ 672 velas) | 672 | franja corto plazo |
| 30 días (≈ 2,880 velas) | 2,880 | franja robusta (mes) |

El experimento debe medir el TIEMPO para cada target y verificar si 30 días de M15
se descargan sin gaps (la comunidad reportó 28,441 velas de M1 en 52 s → M15 debería
ser ~2,880 velas en pocos segundos).

---

## 5. Definición del POI de VOLUMEN (franja en el eje Y)

### 5.1 Construcción del perfil de volumen (por nivel de precio)

1. Para cada vela M15 con `ticks > 0`, repartir sus ticks sobre los niveles de precio
   que la vela toca (`[low, high]`) — o simplificar: asignar todos los ticks de la vela
   al cierre (proxy barato) y validar ambas variantes.
2. Agrupar por **banda de precio** (ancho de franja): usar la banda relativa ya validada
   `ZONE_BAND_PCT = 0.0015` (0.15%) de `src/zone_ia.py` como ancho base de celda.
3. El resultado es un histograma en el eje Y: `nivel_de_precio → ticks_acumulados`.

### 5.2 Extracción de la FRANJA (el "pivote en franja")

Terminología estándar (Volume Profile, validada con la fuente de FBS — ver 5.4):

- **POC (Point of Control):** el nivel con más ticks acumulados. NO es un precio único:
  es la celda más alta del histograma.
- **HVN (nodos de alto volumen):** la franja alrededor del POC — actúa como soporte/resistencia.
- **LVN (nodos de bajo volumen):** zonas con poca actividad — el precio las atraviesa rápido.
- **VA (Value Area):** el rango de precios donde se operó el 70% del volumen total,
  con bordes VAH (alto) / VAL (bajo). Es el "pivote en franja" con terminología de mercado.

**Extracción — dos variantes a comparar (A/B):**

- **Variante A (nuestra propuesta original):** celdas contiguas ≥ 60% del POC.
- **Variante B (estándar del mercado):** VA = el rango mínimo que acumula el 70% del
  volumen total (ordenando celdas de mayor a menor y expandiendo hasta cubrir el 70%).

La franja tiene `[floor, ceiling]` → **grosor real en el eje Y**.
El POI de volumen queda definido como: `{poc, vah, val, ticks, grosor}`.

### 5.3 Proxy de volumen en OTC

Sin volumen real en binarias OTC, el proxy es **`Candle.ticks`** (Quotex lo envía;
ya capturado en `src/models.py:20` y usado en `src/zone_strength.py:201`).

### 5.4 Fundamento teórico — Volume Profile (fuente FBS, 2026-08-26)

https://esfbs.com/es/fbs-academy/traders-blog/volume-profile-indicator

La página valida que nuestro "pivote en franja" es exactamente el **POC dentro de su
Área de Valor (VA)** del Volume Profile estándar. Aporta 4 lecciones que ajustan este
experimento:

1. **Umbral estándar del VA = 70% del volumen total** (no "≥ 60% del POC"). Por eso el
   diseño compara las variantes A y B en 5.2.
2. **El POC solo actúa como "imán" en equilibrio/consolidación**, no en tendencia fuerte.
   → Filtro de contexto obligatorio (ver 6.3): la franja solo se evalúa cuando el precio
   llega en régimen de consolidación, no en impulso de tendencia.
3. **Los LVN justifican el descarte al sobrepasar:** fuera del HVN el volumen cae, el
   precio se acelera y atraviesa la zona rápido. Es el fundamento teórico de "descarte
   solo al sobrepasar la franja" (H2).
4. La página asume **volumen real** (forex). En OTC binario usamos ticks como proxy —
   el experimento debe reportar la calidad del proxy (correlación ticks ↔ reacciones).

---

## 6. Comparación de efectividad: POI volumen vs POI actual

### 6.1 POI actual (baseline)

- **En el edificio:** marcas temporales `has_poi_p1/p2/p3` (aprobación de piso) —
  NO son zonas de precio. Medir su efectividad: ¿cuántos rebotes reales hubo en el
  nivel de la marca dentro de la ventana?
- **En el laboratorio (M3):** `src/strategy_lab/poi_filter.py` — nivel de swing tocado
  ≥ 2 veces en 100 velas, banda ±5 pips.

### 6.2 Métricas de efectividad (idénticas para ambos POIs — comparación justa)

| Métrica | Definición |
|---|---|
| **Tasa de rebote** | toques a la zona que produjeron reversión (n velas después) / toques totales |
| **Falsos positivos** | toques que la atravesaron sin reacción |
| **WR implícito** | % de toques donde un CALL/PUT de 15 min habría ganado |
| **Señales retenidas** | candidaturas del freno que NO se descartan mientras el precio está en la franja |
| **Grosor real** | ancho de la franja en pips / % del precio |

### 6.3 Juicio

**Filtro de contexto (lección FBS #2):** la franja se evalúa solo en toques que llegan
en **consolidación** (p. ej. ADX bajo, o rango de las últimas N velas contenido).
Los toques en tendencia fuerte se registran por separado y NO cuentan para el veredicto
principal — el POC no actúa como imán en tendencia (fuente FBS).

El POI de volumen "gana" si, con datos del mismo período y el mismo universo de pares:
- tasa de rebote > POI actual, Y
- el WR implícito ≥ 50% + margen, Y
- retiene ≥ 1 candidatura del freno que hoy se descartaría a la primera (sin dañar el WR).

Criterio mínimo para seguir investigando (tribunal del Atlas): diferencia ≥ 5 puntos
de WR implícito o ≥ 10% de tasa de rebote, con n ≥ 30 toques por franja.

---

## 7. Entregables del experimento (en el laboratorio)

| Archivo | Contenido | Estado |
|---|---|---|
| `src/strategy_lab/EXPERIMENTO_POI_VOLUMEN.md` | este diseño | ✅ hecho |
| `src/strategy_lab/data_poi_volumen/` | velas M15 descargadas (CSV por par) + tiempos de descarga | ⏳ pendiente |
| `src/strategy_lab/resultados_poi_volumen.csv` | por par: franjas detectadas + métricas de efectividad | ⏳ pendiente |
| `src/strategy_lab/resumen_poi_volumen.md` | comparación POI volumen vs POI actual, veredicto | ⏳ pendiente |

> Regla del laboratorio: los scripts de descarga/análisis viven AQUÍ (o en `scripts/`),
> nunca en `src/` del bot. Si la hipótesis sobrevive, recién ahí se diseña la integración
> al edificio (SDD, con spec y aprobación humana).

---

## 8. Riesgos y supuestos

- **Riesgo:** descargar con otra sesión de Quotex mientras el bot opera en vivo puede
  saturar el WS del broker. La descarga debe usar la MISMA conexión del bot (o hacerse
  con el bot en pausa / cuenta demo).
- **Supuesto:** `ticks` está disponible en la respuesta de M15 de Quotex (confirmado por
  la comunidad en los CSVs de descarga y por el comentario de `src/models.py:20`).
- **Supuesto:** 30 días de M15 se descargan sin gaps significativos (a verificar en 4.2).
- **No se toca el edificio** en este experimento: todo corre en el laboratorio.

---

## 9. Pasos siguientes (cuando el usuario apruebe)

1. Ejecutar descarga M15 para los 62 pares de P1 (target: 2 días / 7 días / 30 días) y medir tiempos.
2. Construir perfil de volumen por par (celdas de 0.15%).
3. Extraer franja con **ambas variantes** (A: ≥ 60% POC; B: VA estándar 70%) y compararlas.
4. Comparar efectividad contra POI actual (sección 6), aplicando el filtro de consolidación.
5. Escribir `resumen_poi_volumen.md` con veredicto.
6. Si gana → diseñar integración al edificio (spec SDD) y pasar por aprobación humana.
