# Hypothesis — DISEÑO ENERGÍA WYCKOFF (NO EJECUTADO — BLOQUEADO POR CALIDAD DE DATOS)

> Experimentos pendientes de aprobación. Solo DISEÑO (la orden exige hipótesis antes de experimentar).
> Cumple docs/LAB_CHARTER.md (Art. 6 congelar antes de correr; Art. 13 REAL=descubrimiento).
> NO se ha corrido ningún código de esta sección.

> ## ⛔ BLOCKED — DATA QUALITY (decisión Trader-Humano 2026-08-07)
> El EURUSD M15 disponible contiene `tick_volume` en lugar de volumen real y ~55% de sus
> observaciones tienen valor cero. El dataset NO se considera apto para validar hipótesis de
> esfuerzo/resultado Wyckoff. Esto es un **BLOQUEO DE INSTRUMENTO**, NO un resultado negativo
> de la hipótesis. Conclusión correcta: **"Hipótesis no evaluada por insuficiencia del
> instrumento de medición."** No se ejecuta EW-1 con este dataset (ni filtrando tick_volume>0:
> introduciría sesgo de selección). Ver `DATA_REQUIREMENTS_EW.md`.
>
> **2026-08-07 (tarde) decisión A — evaluado candidato local y RECHAZADO:** el EURUSD_M1 de
> Dukascopy ya presente en `SMC-SYSTEMS/data/raw` (usado por `build_m15_from_m1.py`) tiene
> **99.7% de ceros en volumen M15** (tick volume del banco). Peor que HistData. FX spot OTC no
> tiene volumen centralizado; el tick volume de cualquier feed individual es disperso/cero. NO se
> descargó nada nuevo, NO se congeló EW-1. Pendiente decisión A1 (evaluar futuros CME, volumen de
> bolsa real) o A2 (aceptar bloqueo). Ver `DATA_REQUIREMENTS_EW.md` §2 y §7.
>
> **2026-08-07 (decisión A1) — CME 6E EVALUADO por factibilidad/semántica (SIN descarga):** el
> candidato CME Euro FX Futures (`6E`, 125k EUR/contrato) da `volume` = nº de contratos negociados
> en central limit order book CME = **REAL traded volume** (no tick, no proxy). Cubre M15 desde años
> atrás (Databento/Polygon/CME), pasa split OOS. Limitación spot→futuros: cambia el instrumento
> experimental a EUR/USD futures (no spot); rollover introduce saltos en PRECIO (no en volumen).
> MEJORA la validez de EW al dar volumen centralizado. **Aprobado conceptualmente; pendiente tu
> autorización de ADQUISICIÓN de datos (elegir proveedor) antes de descargar/modificar/congelar.**

## Contexto y motivación
EXP-074b-NULL cerró el hilo del clustering por el LADO DEL ESTOCÁSTICO: ni binario (074b)
ni continuo (075) predice la resolución de la Fase A. El estocástico M15 describe ESTADO,
no CONTROL ni transición (EXP-072 mean-reverting, EXP-073 nada predice). La hipótesis de
trabajo del Trader-Humano: el estocástico puede no captar la **energía/esfuerzo** del mercado,
que SÍ estaría en el VOLUMEN y el RESULTADO de las velas. Esa es la vía Wyckoff de
"effort vs result".

## Pregunta inicial (la única que importa al arrancar)
> ¿Las variables de ENERGÍA WYCKOFF contienen MEMORIA / ESTRUCTURA DE TRANSICIÓN que el
> K-D M15 NO contiene?

NO es "¿qué señal gana?". Si no hay memoria ni separación reproducible, se acepta y se
descarta también esta vía. Solo si hay memoria, se justifica un experimento de predicción.

## Definición de variables (sobre cada vela M15 de EURUSD)
- `move` = |close - open| (resultado absoluto direccional de la vela)
- `rango` = high - low
- `body` = |close - open|
- `atr` = ATR(14) de la serie
- `vol` = volume (o tick_volume si el feed no trae volume real)
- **esfuerzo** = `vol / max(move, eps)`  → cuánto volumen por unidad de movimiento
- **resultado** = `move / max(rango, eps)` → eficiencia direccional de la vela (0..1)
- **eficiencia** = `move / max(vol, eps)` → movimiento por unidad de volumen
- **absorción** = `vol` alto (>p80) Y `resultado` bajo (<p20) → volumen sin avance (climax de absorción)
- **climax** = `vol` anómalo (>p95) O `rango` anómalo (>p95) → evento de capitulación/extensión
- **compresión** = pendiente negativa de `resultado` (ventana 5-10 velas) con `vol` sostenido (>media)

## Diseño del experimento (propuestas, sin correr)
### EXP-EW-1 — ¿Hay memoria en la energía? (baseline obligatorio)
- Test de autocorrelación de `eficiencia` y `absorción` a lags 1-20 velas (Ljung-Box).
- Comparar contra autocorrelación del K-D M15 (ya sabemos del estocástico en 072: revierte).
- Si la energía NO autocorrelaciona → no hay memoria → descartar vía (como el estocástico).
- Si autocorrelaciona → hay proceso con memoria que el estocástico no ve → justifica EXP-EW-2.

### EXP-EW-2 — ¿Separación de transición reproducible?
- Etiquetar cada Fase A con su estado de energía previo (ventana antes del breakout):
  alta absorción / climax / compresión / neutro.
- ¿La transición (qué pasa en las N velas post-breakout) difiere por estado de energía?
- Método: FDR-BH sobre la asociación estado-energía × dirección/calidad del breakout,
  igual que EXP-075 (sin win rate, descubrimiento).
- Split temporal OOS (TRAIN 2022-2024 / TEST 2025-2026) desde el inicio.

### EXP-EW-3 (solo si EW-1/EW-2 dan memoria) — ¿Edge de estructura?
- Si hay memoria y separación: buscar si un estado de energía precede a breakout direccional.
- SIN buscar el split favorable. FDR + Effect Size (OR>1.15) + OOS.

## Criterios de rechazo (freno científico, reutilizados)
- FDR-BH sobre descriptores de energía: esperado 0/n significativos si no hay señal.
- Bootstrap del OR por cuartil de `eficiencia`/`absorción`: IC debe incluir 1.0 → NO señal.
- OOS: la memoria/separación debe replicarse en 2025-2026.
- Si EW-1 da "no hay memoria" → **descartar la vía completa** y documentar como resultado negativo.

## Qué NO hacer (según la orden)
- NO correr EXP-EW hasta que el Trader-Humano apruebe este diseño.
- NO inventar edge condicionado por la misma variable descubierta en los datos.
- NO usar el estocástico como feature de energía (es el lado que ya falló).

## Datos necesarios
- EURUSD_M15 (SMC_ROOT): revisado 2026-08-07 → **NO APTO**. Columna disponible es
  `tick_volume` (no `volume` real), con ~55% de observaciones en cero (62912/114237 velas,
  rango 2022-01-02 → 2026-08-06). Las variables `esfuerzo`/`eficiencia`/`absorción` quedan
  indefinidas o artificiales sobre esa base → **BLOQUEO DE INSTRUMENTO** (no resultado negativo).
- Requisitos del feed correcto: ver `DATA_REQUIREMENTS_EW.md` (definido 2026-08-07, pendiente
  de decisión A/B del Trader-Humano antes de buscar/usar cualquier fuente).
- Sin datasets/ externos hasta que el DATA REQUIREMENTS esté aprobado y el feed verificado.

## Próximo paso
- **BLOQUEADO por instrumento** (no por hipótesis). No ejecutar EW-1/2/3 con el dataset actual.
- Pendiente: Trader-Humano decide (A) buscar feed adecuado tras aprobar `DATA_REQUIREMENTS_EW.md`
  y continuar EW-1, o (B) abandonar Energía Wyckoff por falta de datos adecuados.
- La hipótesis de energía Wyckoff QUEDA VIVA como hipótesis científica; solo está bloqueado el
  instrumento de medición actual. No convertir el bloqueo en resultado negativo.
