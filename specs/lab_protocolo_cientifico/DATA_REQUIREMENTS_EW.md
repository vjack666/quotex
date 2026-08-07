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

## 7. Estado y próximo paso (2026-08-07 tarde)
- Candidato local (Dukascopy M1 prestado) **RECHAZADO** (99.7% ceros M15).
- NO se descargó nada nuevo, NO se congeló EW-1, NO se ejecutó experimento (cumpliendo instrucción A).
- **Pendiente decisión del Trader-Humano:**
  - (A1) Evaluar un SEGUNDO candidato: **volumen de bolsa de futuros CME EURUSD** (traded volume
    real de bolsa, aunque sea futuro no spot) — única fuente que daría volumen genuino. Requiere
    investigar acceso (sin descargar aún).
  - (A2) Aceptar el bloqueo de la vía Energía Wyckoff por insuficiencia de instrumento (hipótesis
    NO falseada, solo NO EVALUADA).
- Regla firme: NO convertir el bloqueo en resultado negativo. Conclusión: "Hipótesis NO EVALUADA
  por insuficiencia del instrumento de medición."
