# DATA REQUIREMENTS — Energía Wyckoff (EXP-EW)

> Definido 2026-08-07 tras decisión Trader-Humano (opción C: bloqueo de instrumento, NO
> resultado negativo). Actualizado 2026-08-07 (tarde) tras decisión A: evaluar candidato,
> documentar, verificar contra checklist, NO descargar/congeler/ejecutar.

## 0. Realidad del volumen en FX spot (salvaguarda del Trader-Humano)
EURUSD spot es mercado **OTC descentralizado**: NO existe un "volumen centralizado" como en
una bolsa. Por tanto la pregunta correcta NO es "¿es volumen de bolsa?" sino:
**¿la fuente ofrece un volumen con definición suficientemente sólida y representativa para la
hipótesis Wyckoff (effort/result), aunque sea proxy de actividad?** Ninguna fuente retail/gratuita
ofrece "traded volume del mercado global" en FX spot. Las opciones reales:
- **tick volume** de un feed de alta calidad y continuidad (nº de ticks/cambios de precio por vela).
  Es proxy de actividad, NO lotes negociados; útil SOLO si NO tiene ceros masivos.
- **real volume de un broker grande** = lotes de SUS clientes únicamente (proxy de ESE broker, no
  del mercado). Válido como aproximación si el broker es grande y lo documenta.

## 1. Por qué el dataset actual falla (contexto del bloqueo)
- EURUSD M15 (SMC_ROOT) trae `tick_volume`, NO `volume` real. ~55% de velas con `tick_volume=0`.
- effort/efficiency/absorption quedan indefinidos/artificiales → no se puede responder "¿hay memoria?".

## 2. Candidato evaluado y RECHAZADO (2026-08-07, decisión A — fase de verificación)
**Fuente:** EURUSD_M1 de Dukascopy ya presente en `SMC-SYSTEMS/data/raw` (el repo ya lo usa vía
`build_m15_from_m1.py`, renombrando la columna a `volume` = suma de ticks).
**Qué significa su `volume`:** tick_volume del banco Dukascopy (nº de ticks), NO lotes del mercado.
**Cobertura:** 2022-01-02 → 2026-08-06 (cumple ≥3a y split OOS). Columnas: time/OHLC/tick_volume/spread.
**Verificación contra checklist de 6 pasos:**
1. Columna de volumen existe (`tick_volume`) ✅
2. **Ceros/missing: 97.73% ceros + 1.96% missing en M1**; M15 agregado = **99.7% ceros** ❌ (umbral ≤2% fallado por margen enorme)
3. Continuidad: ratio obser/esperado M1 = 10.3 (datos presentes, pero volumen casi todo cero) ⚠️
4. Distribución: tick_volume M1 max=890, mean=0.53 → cola extremadamente sesgada a cero ❌
5. Sanity: con 97.7% ceros, correlación vol vs |move| dominada por masa en cero → no representa actividad ❌
6. Split OOS: cubre 2022-2024 y 2025-2026 ✅
**VEREDICTO: CANDIDATO RECHAZADO.** Su volumen es tick_volume con 99.7% de ceros en M15 — peor
que el HistData actual (55%). No resuelve el bloqueo; lo empeora. Esto es inherente al tick volume
OTC (cualquier feed individual es disperso/cero-en-gran-parte), no un defecto de Dukascopy.

## 2b. Candidato SECUNDARIO evaluado (decisión A1, 2026-08-07 — factibilidad y semántica, SIN descarga)
**Fuente candidata:** CME Euro FX Futures, **producto Globex `6E`** (ClearPort/IC `EC`; micro `M6E`).
Evaluación puramente conceptual (no se descargó nada, no se modificó pipeline, no se congeló EW-1).

**1. Contrato exacto:** CME Euro FX Futures, código **`6E`**, tamaño 125,000 EUR, cotización USD/EUR,
tick 0.00005 (= $6.25/contrato), expira mensual y trimestral. Micro `M6E` = 1/10 (12,500 EUR).

**2. Campo de volumen y qué representa:** en barras agregadas de CME, `volume` = **nº de contratos
negociados** en el intervalo, registrado por el **central limit order book centralizado (CME Globex)**.
Es volumen de exchange genuino, NO tick volume ni proxy de un broker.

**3. ¿Real o proxy?:** **REAL traded volume de contratos** (no proxy). Esto es exactamente lo que faltaba
en FX spot OTC. Cumple el requisito ideal del DATA REQUIREMENTS (jerarquía §3 nivel 1).

**4. Histórico M15 y fecha:** Databento (`GLBX.MDP3`, símbolo 6E) y Polygon.io dan aggregates M15 con
`volume`=contratos desde años atrás (Databento MBO/MDP3 desde ~2010). Cumple split TRAIN 2022-2024 /
TEST 2025-2026 sobradamente. El propio CME vende histórico de mercado.

**5. Fuente/proveedor único:** SÍ mantenible — Databento y Polygon ofrecen **continuous contract 6E**
con roll por volumen documentado (un solo proveedor cubre todo el período, sin pegar fuentes).

**6. Limitaciones spot → futuros (DEBE QUEDAR EXPLÍCITO — ver nota del Trader-Humano):**
- **CAMBIO DE INSTRUMENTO EXPERIMENTAL:** ya NO es EURUSD spot, es **EUR/USD futures (6E)**. El precio
  rastrea al spot (correlación alta vía cost-of-carry) pero NO es idéntico: hay base (contango/back),
  rollovers y divergencias menores de horario/liquidez.
- **Rollover:** los futuros expiran → se usa **continuous contract con back-adjustment**. Eso introduce
  **saltos artificiales en PRECIO** en fechas de roll (afecta `move`/`rango` de las barras cercanas al
  roll). El VOLUMEN, en cambio, es continuo y limpio.
- **Para EW (effort/result):** el volumen AHORA es válido (centralizado) → MEJORA enorme sobre spot; NO
  invalida EW, lo fortalece. Pero hay que documentar que el universo es "EUR/USD futures CME (6E)",
  NO "EURUSD spot", y que CUALQUIER resultado EW NO se compara 1:1 con EXP-071..075 (que usaron spot).
- La Fase A de EW se define sobre 6E, no sobre EURUSD spot (coherente internamente; cambia el labeled universe).

**7. Coste / acceso / restricciones:**
- Databento: histórico por descarga, de pago (~$5/GB en CME; crédito de bienvenida). API Python `databento`;
  requiere cuenta + API key.
- Polygon.io: free limitado (5 calls/min, histórico ~2a en free; paid amplía). Campo `volume`=contratos.
- CME directo: Market Data Platform, coste según distribuidor.
- **CUELLO REAL:** NINGUNO es gratis/completo como HistData lo fue para spot. Hay coste y registro → el
  lab pasaría de datos gratuitos a datos de pago. Requiere presupuesto/cuenta (fuera del patrón actual).

**VEREDICTO DE FACTIBILIDAD (conceptual, 7 puntos): CANDIDATO PASA** los puntos 1–5 y 7 (con salvedad de
coste). El punto 6 (spot→futuros) NO es bloqueo sino **cambio de instrumento que debe documentarse
explícitamente** y que, de hecho, mejora la validez de EW al dar volumen centralizado real.
**Pendiente autorización del Trader-Humano para la ADQUISICIÓN de datos (elegir proveedor: Databento
vs Polygon vs CME) antes de cualquier descarga, modificación de pipeline o congelación de EW-1.**

## 3. Qué significa "volumen adecuado" para NUESTRO propósito (redefinido)
No basta con que una columna se llame `volume`. Para Wyckoff effort/result necesitamos volumen que
sea **(a) continuo (sin ceros masivos), (b) con definición documentada y representativa**, incluso
si es proxy. Jerarquía aceptable:
1. **real/traded volume de bolsa** (ej. futuros CME EURUSD) — ✅ ideal, pero es futuro no spot.
2. **real volume de broker grande** documentado (lotes de sus clientes) — ✅ proxy aceptable.
3. **tick volume de alta calidad y continuo** (sin ceros masivos) — ⚠️ solo si pasa el checklist.
Lo que ya tenemos (HistData 55% ceros, Dukascopy M1 99.7% ceros) está en la peor categoría.

**Distinción explícita (no asumir equivalencia):**
| Tipo | Qué mide | Utilidad Wyckoff | Estado en este repo |
|------|----------|------------------|---------------------|
| real/traded volume (bolsa, ej. CME futuros) | contratos realmente negociados | ✅ el que Wyckoff requiere | NO disponible aún |
| real volume de broker | lotes de sus clientes | ✅ proxy aceptable si grande | NO verificado |
| tick volume (Dukascopy/HistData/MT5 FX) | nº de ticks por vela | ⚠️ proxy ruidoso | 55–99.7% ceros → inútil |
"MT5 tiene volume real" NO implica automáticamente "tenemos el volumen Wyckoff": en MT5 el real
volume solo se activa si el broker lo provee; para FX por defecto es tick volume.

## 4. Campos mínimos requeridos (por vela M15)
- `time` (UTC), `open/high/low/close`, `volume` = **volumen continuo con definición documentada**,
  `atr` o computable. Deseable: `tick_volume` (comparar), `spread`, fuente del volumen.

## 5. Umbrales de calidad aceptables (ANTES de congelar cualquier EW)
| Métrica | Requisito mínimo | Nota |
|---------|------------------|------|
| % `volume` = 0 o missing | **≤ 2%** (no 55% ni 99.7%) | duro; si no se cumple, el feed no sirve para Wyckoff |
| Continuidad temporal | huecos < 1% de sesiones; sin días enteros faltantes salvo fin de semana | serie continua para autocorrelación |
| Cobertura mínima | **≥ 3 años M15** (split TRAIN 2022-2024 / TEST 2025-2026) | replicar diseño OOS |
| Frecuencia | **M15 exacta** | sensible a ventana |
| Representatividad | feed de broker primario grande O bolsa de futuros; documentado | el volumen debe reflejar actividad real |
| Estabilidad | mismo proveedor en toda la cobertura | evita saltos |

## 6. Verificación de usabilidad ANTES de congelar EW-1 (checklist obligatorio, 6 pasos)
1. Inspección de columnas: confirmar volumen continuo y su DEFINICIÓN semántica (¿traded? ¿broker? ¿tick?).
2. Conteo de ceros: `% volume==0` ≤ 2% global y por año (el candidato Dukascopy falló: 99.7%).
3. Continuidad: huecos por día < 1%.
4. Distribución: cola derecha razonable (no todo en cero ni saturado).
5. Sanity: correlación `volume` vs `|close-open|` y vs `rango` positiva y significativa.
6. Split OOS: cubre ≥ 2022-01 y ≥ 2025-2026.
Solo si los 6 pasan → se congela EXP-EW-1. Si falla alguno → NO se ejecuta; se reporta el fallo.

## 7. Estado y próximo paso (2026-08-07, decisión A1 completada — factibilidad)
- Candidato local (Dukascopy M1 prestado) **RECHAZADO** (99.7% ceros M15).
- Candidato SECUNDARIO CME 6E **EVALUADO por factibilidad y SEMÁNTICA (SIN descarga)** → PASA los
  puntos 1–5 y 7 (salvedad coste); el punto 6 (spot→futuros) es cambio de instrumento que debe
  documentarse explícitamente y mejora la validez de EW al dar volumen centralizado real (§2b).
- **PENDIENTE AUTORIZACIÓN DEL TRADER-HUMANO para la ADQUISICIÓN de datos CME** (elegir proveedor:
  Databento vs Polygon vs CME directo). Hasta entonces: NO se descarga, NO se modifica pipeline,
  NO se congela EW-1, NO se ejecuta experimento.
- (A2 alternativo) Aceptar el bloqueo de la vía por insuficiencia de instrumento (hipótesis NO falseada).
- Regla firme: NO convertir el bloqueo en resultado negativo. Conclusión: "Hipótesis NO EVALUADA
  por insuficiencia del instrumento de medición" (en spot); con CME 6E el instrumento cambia a futuros.
