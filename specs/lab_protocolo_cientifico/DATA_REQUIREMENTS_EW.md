# DATA REQUIREMENTS — Energía Wyckoff (EXP-EW)

> Definido 2026-08-07 tras decisión Trader-Humano (opción C: bloqueo de instrumento, NO
> resultado negativo). Propósito: especificar QUÉ feed necesitamos ANTES de buscar/cambiar
> de fuente. No ejecuta nada. No asume que "MT5 tiene volume" = "tenemos el volumen Wyckoff".

## 1. Por qué el dataset actual falla (contexto del bloqueo)
- EURUSD M15 (SMC_ROOT) trae `tick_volume`, NO `volume` real.
- ~55% de las velas (62912/114237) tienen `tick_volume = 0`.
- Con eso, `esfuerzo = vol/max(move,eps)`, `eficiencia = move/vol`, `absorción` quedan
  indefinidos/artificiales → no se puede responder "¿hay memoria?" sin medir artefactos del feed.
- Filtrar `tick_volume>0` se RECHAZA (sesgo de selección: cambia la población).

## 2. Qué significa "volumen real" para NUESTRO propósito
No basta con que una columna se llame `volume`. Para Wyckoff effort/result necesitamos
**volumen negociado (traded/real volume)**: número de contratos/lotes realmente transados en
la vela, proporcional al interés real de los participantes. El `tick_volume` (nº de ticks/cambios
de precio en la vela) es un PROXY ruidoso: correlaciona con actividad pero NO con tamaño de
contrato, y es exactamente lo que produce ceros masivos en feeds agregados/HistData.

**Distinción explícita (no asumir equivalencia):**
| Tipo | Qué mide | Utilidad Wyckoff | Riesgo en este dataset |
|------|----------|------------------|------------------------|
| real/traded volume | contratos/lotes realmente negociados | ✅ el que Wyckoff requiere | el actual NO lo trae |
| tick volume | nº de ticks/cambios de precio por vela | ⚠️ proxy ruidoso de actividad | 55% ceros → inutilizable |
| calidad/continuidad del feed | gaps, horas muertas, fines de semana | determina si la serie es continua | HistData puede tener huecos |
| representatividad del instrumento | ¿el símbolo refleja volumen del mercado real? | si es un derivado sintético, el volumen es del broker, no del mercado | verificar contra fuente primaria |

**Regla:** "MT5 tiene volume real" NO implica automáticamente "tenemos el volumen que Wyckoff
necesita". Hay que verificar (a) que sea traded volume y (b) que el símbolo/feed represente
volumen negociado del mercado, no solo recuento de ticks del broker.

## 3. Campos mínimos requeridos (por vela M15)
- `time` (timestamp, tz UTC)
- `open`, `high`, `low`, `close` (OHLC)
- `volume` = **traded/real volume** (columna explícita, no tick_volume; si solo hay tick_volume,
  se documenta y se rechaza para EW)
- `atr` o computable (ATR(14)) — ya disponible vía compute_features
- Opcional pero deseable: `tick_volume` (para comparar proxies), `spread`, `real_volume_source`

## 4. Umbrales de calidad aceptables (antes de congelar cualquier EW)
| Métrica | Requisito mínimo | Motivo |
|---------|-----------------|--------|
| % de `volume` = 0 o missing | **≤ 2%** (no 55%) | >2% invalida effort/efficiency/absorción |
| Continuidad temporal | huecos < 1% de sesiones esperadas; sin días enteros faltantes salvo fin de semana | la autocorrelación requiere serie continua |
| Cobertura mínima | **≥ 3 años de M15** (para split TRAIN 2022-2024 / TEST 2025-2026 como en 074b/075) | replicar diseño OOS del Charter |
| Frecuencia | **M15 exacta** (no agregada de M1 ni resampleada de H1) | las variables de energía son sensibles a la ventana |
| Representatividad | feed de broker primario o datos de mercado real (no recuento de ticks de un solo LP) | el volumen debe reflejar el mercado |
| Estabilidad del feed | mismo proveedor en toda la cobertura (sin pegado de fuentes incompatibles) | evita saltos espurios en volumen |

## 5. Verificación de usabilidad ANTES de congelar EW-1 (checklist obligatorio)
Antes de escribir una sola línea de EXP-EW-1, el feed candidato debe pasar:
1. **Inspección de columnas**: confirmar que existe `volume` (traded) y no solo `tick_volume`.
2. **Conteo de ceros**: `% volume==0` ≤ 2% en toda la cobertura y por año.
3. **Continuidad**: gráfico/estadístico de huecos por día; sesiones faltantes < 1%.
4. **Distribución**: `volume` con cola derecha razonable (no todo en un valor constante ni saturado).
5. **Sanity**: correlación `volume` vs `|close-open|` y vs `rango` positiva y significativa
   (esperado en volumen real; ausente/ruidosa en tick_volume con ceros).
6. **Split OOS**: el feed cubre ≥ 2022-01 y ≥ 2025-2026 para el TRAIN/TEST del Charter.
Solo si los 6 pasan → se congela EXP-EW-1. Si falla alguno → NO se ejecuta; se reporta el fallo.

## 6. Qué NO hacer (según orden)
- NO ejecutar EW-1 con el dataset actual (ni A ni B como parche).
- NO buscar/descargar otro dataset por cuenta propia antes de tu decisión A/B.
- NO convertir el bloqueo de datos en "resultado negativo". Conclusión: hipótesis no evaluada
  por insuficiencia del instrumento de medición.
- NO asumir que "MT5 volume" es automáticamente el volumen Wyckoff (ver §2).

## 7. Próximo paso
Trader-Humano decide:
- **(A)** buscar feed adecuado (verificar contra §2–§5) y, si pasa el checklist, congelar EW-1.
- **(B)** abandonar Energía Wyckoff por falta de datos adecuados (hipótesis queda viva, no falseada).
Hasta tu decisión: diseño congelado, sin ejecución.
