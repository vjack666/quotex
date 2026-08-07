# EXP-POI-STOCH — Validación y protocolo de ejecución

## Protocolo congelado (antes de cualquier run)

Escribir `protocol_frozen.json` con:
- seed = 42
- alpha = 0.05
- fdr_method = "fdr_bh"
- domain = "REAL_price_stoch_M15"
- oos_split = "temporal" (documentar fechas exactas)
- poi_min_efficacy = valor fijo (ej. 0.35 o el que use zone_strength por defecto)
- kd_healthy_low / kd_healthy_high = percentiles o valores fijos definidos a priori
- kd_excessive = percentil alto fijo
- n_forward_candles_clean = 4 y 8 (reportar ambos)
- min_events_for_nn = 300
- effect_size_min_diff = 0.05
- effect_size_min_or = 1.25

## Pasos de ejecución (orden estricto, hands-free)

1. **Extracción de zonas POI**  
   Usar lógica de zone_strength / compute_support_efficacy (o equivalente geométrico: clustering de toques + bounce rate).  
   Solo zonas formadas con datos pasados.

2. **Detección de retornos**  
   Precio entra en la banda de una zona ya definida. Registrar timestamp del open de la vela M15 de entrada.

3. **Features de estocástico en el momento del retorno**  
   K, D, |K-D|, sticky_flag (n velas consecutivas en extremo), slope reciente.

4. **Labels**  
   - clean_bounce_4 / clean_bounce_8  
   - next_candle_retrace (para H2)

5. **Test H1 (patrón completo)**  
   Median-split o umbrales fijos de “saludable”.  
   χ² / OR + FDR.  
   Replicar en OOS.

6. **Test H2 (separación excesiva → retrace)**  
   Umbral alto de |K-D|.  
   Misma batería estadística + OOS.

7. **H3 — Neural net (solo si n ≥ min_events_for_nn)**  
   - Input: secuencia de 8–16 velas M15 alrededor del retorno (OHLC normalizado + K/D + flags de zona).  
   - Target: clean_bounce o probabilidad de éxito.  
   - Modelo: LSTM/Transformer ligero o gradient boosting sobre features agregadas (empezar simple).  
   - Evaluación: solo OOS temporal.  
   - Comparar AUC / precision@k contra la regla fija de H1.  
   - Si la red no supera a la regla fija de forma clara → documentar “NN no aporta” y quedarse con reglas.

8. **Reporte inmutable**  
   - summary.txt con veredictos H1/H2/H3 (ACEPTADA / REFUTADA / INCONCLUSA)  
   - protocol_frozen.json  
   - tablas de tasas, OR, p_adj, IC bootstrap  
   - si NN: métricas TRAIN vs OOS y feature importance / atención si aplica  

9. **Cierre**  
   Actualizar progress/current.md y HANDOFF con el veredicto.  
   No proponer cambios al Edificio.  
   No pedir confirmación intermedia al Trader-Humano salvo error fatal de datos.

## Criterios de veredicto

| Hipótesis | ACEPTADA | REFUTADA | INCONCLUSA |
|-----------|----------|----------|------------|
| H1        | p_adj < 0.05 + effect size + OOS replica | p_adj ≥ 0.05 o effect size insuficiente o OOS falla | n demasiado bajo |
| H2        | igual | igual | igual |
| H3        | AUC OOS ≥ regla fija + gap TRAIN-TEST < 0.08 | AUC OOS ≤ regla fija | n < 300 o inestable |

## Hands-free clause

Este documento + hypothesis.md + risks.md constituyen la orden completa.  
El agente ejecuta, escribe reportes, actualiza estado y se detiene.  
No hace preguntas.  
No modifica umbrales después de ver resultados.  
Si falta un dato crítico (ej. no hay suficientes M15 de un par), documenta la limitación y continúa con los pares disponibles.
