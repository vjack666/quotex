# EXP-EDIFICIO-NN-SCORE — Validación y protocolo

## Protocolo congelado (antes de entrenar)

Escribir `protocol_frozen.json` con:
- seed = 42
- alpha = 0.05
- domain = "REAL_edificio_features"
- oos_split = "temporal" (fechas o índice de corte documentados)
- model = "lightgbm" (o equivalente tabular; empezar simple)
- hyperparams fijos (max_depth, learning_rate, n_estimators, subsample, colsample, min_child_samples)
- top_k_fractions = [0.2, 0.3]
- min_train_events = 500
- auc_gap_warn = 0.08
- features_whitelist = lista explícita
- target = "win_loss" | "clean_N" (documentar N)

## Pasos de ejecución (orden estricto)

1. Extraer candidatos del Edificio (o del pipeline que genera zonas + señales).
2. Adjuntar features de la whitelist (solo pasado).
3. Adjuntar label (WIN/LOSS real o proxy clean).
4. Split temporal TRAIN / TEST.
5. Baseline: score actual del Edificio → AUC, win-rate global, win-rate top-k en TRAIN y TEST.
6. Entrenar modelo solo en TRAIN (early stopping sobre validación temporal interna del TRAIN si aplica).
7. Evaluar en TEST: AUC, win-rate top-k, lift vs baseline, IC95% (bootstrap).
8. Calibración OOS (reliability diagram o ECE).
9. Escribir summary.txt con veredictos H1/H2/H3.
10. Actualizar progress/current.md y HANDOFF.
11. Commit solo archivos de este EXP. Sin push. Sin tocar producción.
12. Parar.

## Tabla resumen OOS (obligatoria en summary.txt)

El `summary.txt` debe incluir esta tabla rellenada con números reales:

```
| Métrica                    | Score Edificio | Modelo     | Diff / Lift | IC95%           | n    |
|----------------------------|----------------|------------|-------------|-----------------|------|
| AUC OOS                    |                |            |             |                 |      |
| WR global OOS              |                |            |             |                 |      |
| WR top 20% OOS             |                |            |             |                 |      |
| WR top 30% OOS             |                |            |             |                 |      |
| Lift top 20% vs baseline   | —              |            |             |                 |      |
| Lift top 30% vs baseline   | —              |            |             |                 |      |
| ECE OOS (calibración)      |                |            |             | —               | —    |
| Gap AUC TRAIN−TEST         | —              |            |             | —               | —    |
```

- IC95% de rates: Wilson o bootstrap.
- IC95% de lift (diff de WR): bootstrap.
- Si n top-k es bajo, indicarlo en la celda o en nota bajo la tabla.

## Criterios de veredicto

| Hipótesis | ACEPTADA | REFUTADA | INCONCLUSA |
|-----------|----------|----------|------------|
| H1 (ranking) | AUC_OOS modelo > AUC_OOS score Edificio de forma clara | AUC_OOS modelo ≤ score | n bajo o inestable |
| H2 (top-k WR) | lift OOS con IC95% del diff que no incluye 0 | lift ≤ 0 o IC incluye 0 | n top-k insuficiente |
| H3 (calibración) | ECE o bandas no peores que score actual | calibración claramente peor | no evaluable |

## Hands-free clause

El agente ejecuta el protocolo sin preguntar.  
No modifica features ni hiperparámetros tras ver OOS.  
No integra nada al Edificio.  
Si faltan logs de trades reales, usa proxy documentado y lo declara en summary.  
Si n_train < 500, declara potencia baja y no fuerza conclusiones fuertes.
