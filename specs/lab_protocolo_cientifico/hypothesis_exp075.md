# Hypothesis — EXP-075 (re-enfocado)

> Este SPEC cumple el Laboratory Charter (docs/LAB_CHARTER.md). No modifica ninguno de sus principios.

## Identificación
- **ID**: EXP-075
- **Título**: ¿La duración (y los descriptores continuos) de la Fase A predicen la dirección/calidad del breakout como variable continua?
- **Dominio**: REAL (Art. 10 — descubrimiento, NO promoción directa al Edificio)
- **Activo(s)**: EURUSD
- **Timeframe(s)**: M15
- **Tipo**: Descubrimiento (REAL) — Art. 13

## Contexto (por qué este EXP existe)
EXP-074 encontró K=2 (sil 0.2185) sugeriendo población mixta. EXP-074b (freno científico)
RECHAZÓ esa partición binaria GMM: no sobrevive a cambio de algoritmo (ARI≈0),
ablación de features (9.7%→48.1%) ni bootstrap (22%→95%). Conclusión de 074b:
lo que sobrevive es **la duración de la Fase A como variable continua**, no 2 poblaciones.

EXP-075 pregunta la consecuencia natural: si la duración es un continuo (no 2 cajas),
¿ese continuo TIENE señal predictiva sobre cómo resuelve la fase? Es decir:
¿las fases largas resuelven distinto (mejor/peor, más alineadas) que las cortas,
de forma MONÓTONA y no binaria?

Además, el dataset ahora cubre 2022→2026 (114k velas). Esto REDIME la PRUEBA 3 OOS
de EXP-074b que estaba BLOQUEADA ("dataset empieza 2022, no hay 2012-2018"):
ahora hay 5 años para un split temporal train(2022-2024) → test(2025-2026).

## Hipótesis
- **H0 (nula)**: Ni la duración ni los descriptores continuos de la Fase A predicen
  la dirección alineada ni la calidad (clean) del breakout. La resolución es ruido
  respecto a las propiedades de la fase.
- **H1 (alternativa)**: La duración (y/o descriptores continuos) de la Fase A predice
  monotónicamente la calidad/dirección del breakout. La relación es CONTINUA, no binaria.

## Métricas
- **Métrica primaria**: asociación de `duration` (continua) con (a) breakout alineado
  a `extreme_side` esperado, (b) breakout `clean` (|move| ≥ umbral mediano local).
- **Métricas secundarias**: regresión logística multivariable (duration + descriptores
  continuos → P(alineado), P(clean)); OR por cuartil de duration; tendencia monotónica
  por cuartil; estabilidad OOS (train 2022-2024 → test 2025-2026).
- **NO es win rate operativa.** Se reporta como MAPA/estructura (Art. 13).

## Parámetros del protocolo (congelados — Art. 6)
- **Nivel α**: 0.05
- **Corrección**: FDR-BH (obligatoria, Art. 9) + Bonferroni para robustez
- **Poder esperado**: 0.80 (con n≈3308 el poder observado es >>0.99; el riesgo es
  falso positivo por exceso de poder → FDR + Effect Size obligatorios)
- **n mínimo**: 100 (escenarios/fases completas)
- **Dataset**: `EURUSD_M15.parquet` en SMC_ROOT (hash declarado en dataset_hash.txt)
- **Ventana de resolución H**: 8 velas M15 (2h, consistente con EXP-073)
- **MAX_PHASE**: 120 velas M15 (≈30h, consistente con EXP-074)
- **Semilla (seed)**: 42

## Effect Size mínimo (R12)
- **Métrica de efecto**: OR por cuartil de duration (regresión logística)
- **Umbral mínimo para promoción**: OR > 1.15 por cuartil CON p_adj_fdr < α.
  Por debajo, aunque p<α, se reporta como ruido continuo (no se promueve).

## Declaración de cumplimiento del Charter
Este experimento cumple el Charter: Sí
