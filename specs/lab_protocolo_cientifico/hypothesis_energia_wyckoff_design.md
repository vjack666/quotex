# Hypothesis — DISEÑO ENERGÍA WYCKOFF (NO EJECUTADO)

> Experimentos pendientes de aprobación. Solo DISEÑO (la orden exige hipótesis antes de experimentar).
> Cumple docs/LAB_CHARTER.md (Art. 6 congelar antes de correr; Art. 13 REAL=descubrimiento).
> NO se ha corrido ningún código de esta sección.

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
- EURUSD_M15 (SMC_ROOT) ya tiene `volume`/`tick_volume`, `open`/`high`/`low`/`close`, `atr`.
- Revisar si `volume` es real o tick_volume (afecta la interpretación de `esfuerzo`).
- Sin datasets/ externos (patrón establecido: SMC_ROOT directo).

## Próximo paso
Esperar OK del Trader-Humano para (1) verificar columna de volumen en el parquet y
(2) correr EXP-EW-1 (autocorrelación de energía vs estocástico). Hasta entonces, diseño congelado.
