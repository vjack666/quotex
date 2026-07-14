# 06 — Papel del estocástico en el ESCÁNER (filtro de temporalidad mayor)

Este archivo documenta, con fuentes reales de internet, qué papel juega el
estocástico cuando lo usás como **filtro de temporalidad mayor dentro de un
escáner multi-timeframe**. Es exactamente el rol que le damos en STRAT-F:
el M15 (mayor) define el sesgo del rango, el M5/M1 (menor) busca la entrada.

## La idea central (documentada)

Varias fuentes serias coinciden en el mismo patrón multi-timeframe:

- **FMZ (Multi-Timeframe Stochastic Strategy)**: *"The higher timeframe
  stochastic defines [the trend context]; the current timeframe stochastic
  confirms the signal and filters noise."* → La temporalidad MAYOR define;
  la MENOR confirma y filtra el ruido.
- **Dukascopy**: *"By examining the Stochastic Oscillator on multiple
  timeframes, traders can seek confirmation and validation of signals
  generated on their primary timeframe."* Y dan el ejemplo clásico: usar el
  estocástico semanal para definir la dirección de la tendencia larga, y uno
  más corto (diario/horario) para la entrada.
- **OANDA**: *"Once the long-term trend is established, traders can switch to
  a shorter time frame to find potential entry points using the stochastic."*
- **TradingView**: el estocástico va mejor en temporalidades chicas para
  timing, pero *"use higher timeframes to [filter/define bias]"*.

## Por qué esto es perfecto para STRAT-F

El marco de STRAT-F ya ES multi-timeframe por diseño:
- **M15** = contexto mayor (rango Wyckoff, bandas naranjas, sesgo).
- **M5** = fractal Bill Williams en la banda (la estructura de entrada).
- **M1** = rechazo de la banda (el disparador).

El estocástico M15 encaja como **el filtro de temporalidad mayor del
escáner**: le dice al scanner "¿está el rango M15 en un extremo (recalentado
o congelado) o al medio?". Con eso el escáner:

1. **Filtra ruido**: descarta señales M5 que van contra el estado de rango M15
   (ej: CALL cuando M15 está en sobrecompra sostenida en tendencia alcista →
   es continuación, no techo; ver Autozone en archivo 03).
2. **Refuerza rebotes reales**: si el fractal M5 toca la banda naranja y el
   estocástico M15 está en el extremo opuesto (sobreventa para CALL,
   sobrecompra para PUT), el rebote tiene más peso en el score.
3. **Define sesgo de rango (línea 50)**: por encima de 50 el rango tiene sesgo
   alcista; por debajo, bajista. El scanner puede exigir que la dirección
   STRAT-F no vaya contra ese sesgo salvo que el M15 esté roto.

## Cómo lo modelamos en el escáner (diseño, no fe)

En modo MEDICIÓN (arranque), el estocástico M15 es un **campo observado**, no
un veto:
- Se calcula en cada scan (`compute_stoch(candles_15m, 14,3,3)`).
- Se graba en la caja negra por señal (`stoch_m15`).
- Se muestra en el HUB por señal (estado + cruce + si contradice).
- NO bloquea la entrada todavía.

Solo si el A/B de la caja negra demuestra que sube el win_rate, se promueve a
**veto del escáner** (un `_check_stoch_m15_aligned` en `entry_decision_engine`,
al lado de `_check_htf_available_and_aligned` que ya existe).

## Señales de escáner concretas (del libro 03, aplicadas al scanner)

| Estado M15 stoch | Fractal M5 | Decisión del scanner |
|-----------------|-----------|----------------------|
| SOBRECOMPRA (>=80) + cruce bajista | fractal UP en banda | rebote bajista reforzado → PUT más fuerte |
| SOBREVENTA (<=20) + cruce alcista | fractal DOWN en banda | rebote alcista reforzado → CALL más fuerte |
| NEUTRO (40-60) | fractal en banda | señal débil, subir umbral o descartar |
| SOBRECOMPRA sostenida en tendencia ↑ | fractal UP (techo) | contradice → marcar `stoch_contradicts`, medir |
| Divergencia alcista M15 | fractal DOWN en banda | refuerzo extra (señal #1 de Lane) → CALL |

## Fuentes
- FMZ Quant — Multi-Timeframe Stochastic Strategy.
- Dukascopy — Stochastic Oscillator Strategy: Trader's Guide.
- OANDA — Mastering Stochastic Oscillator Trading Strategies.
- TradingView — Stochastic Oscillator scripts/docs.
- StockCharts ChartSchool (archivos 01-03 de esta biblioteca).

## Conclusión para el plan

El estocástico M15 NO es un indicador suelto: es el **filtro de temporalidad
mayor del escáner STRAT-F**. Por eso va en `scanner.py` (donde ya vive
`evaluate_strat_f`), se graba en la caja negra, y se presenta en el HUB junto
a cada señal. Su promoción a veto depende de los datos, no de la intuición.
