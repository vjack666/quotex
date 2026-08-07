# Índice EXP-074b-NULL — Control nulo / surrogate + temporal OOS (cierre del clustering)

| Campo | Valor |
|---|---|
| ID | EXP-074b-NULL |
| Título | ¿La partición de 2 poblaciones de Fase A excede la geometría del método bajo ausencia de estructura conjunta? |
| Dominio | REAL (descubrimiento, Art. 13) |
| Activo / TF | EURUSD / M15 |
| Período | 2022-01-03 → 2026-08-05 (3307 Fases A) |
| Veredicto | **NO SOPORTADA** — hipótesis de población mixta rechazada como régimen estable |
| Cumple Charter | Sí |

## Archivos (de esta sesión)
- `scripts/lab_exp074b_null.py` — null (B=200 shuffle independiente) + Prueba temporal OOS
- `specs/lab_protocolo_cientifico/hypothesis_exp074b_null.md` — protocolo congelado
- `specs/lab_protocolo_cientifico/risks_exp074b_null.md` — amenazas + mitigaciones
- `specs/lab_protocolo_cientifico/validation_exp074b_null.md` — veredicto del tribunal
- `reports/EXP-074b_NULL/summary.txt` — salida inmutable
- `reports/EXP-074b_NULL/protocol_frozen.json`
- `data/strategy_lab/exp074b_null_curves.parquet` — curvas del null

## Veredicto científico completo (cierre del hilo)
1. **Null (shuffle independiente)**: silhouette del null (0.40) > REAL (0.22) → el null es
   geométricamente más favorable (null "fuerte"); NO se usa silhouette para refutar.
   structure score REAL (0.49) > null (0.23) pero por construcción del null (borra correlación).
   %minoritario REAL 24.4% en el borde del null (máx 21.6%).
2. **OOS temporal (TRAIN 2022-2024 → TEST 2025-2026)**: TEST 100% "corto" → colapso total
   (diff 81.8pp, silhouette TEST=nan). **No hay estabilidad temporal.**
3. **EXP-074b previo**: ARI≈0 entre métodos; ablación 9.7%→48.1%; bootstrap 22%→95%.
4. **EXP-075 (continuo)**: RESULTADO NEGATIVO (FDR 0/36, OR≈1.0, OOS plano).

**Conclusión**: el clustering de Fase A es geometría del método, no régimen del mercado.
Hilo del clustering CERRADO. No se promueve al Edificio (Art. 13).

## Relación con la hoja de ruta de Grok/ChatGPT (validada por el Trader-Humano)
`074 → 074b (algoritmo/ablation/bootstrap/temporal/interpretabilidad/reglas) → 074b-NULL
(null + OOS real) → [RECHAZO] → NO EXP-075-promovido`. La secuencia se ejecutó completa y
terminó en rechazo en cada eslabón. La única pieza que faltaba (control nulo + OOS real con
2022-2026) ahora está hecha.

## Siguiente (pendiente de aprobación del Trader-Humano, NO ejecutado)
Diseñar (no correr) **Energía Wyckoff**: volumen + rango + resultado, no estocástico.
Variables: esfuerzo=vol/|move|, resultado=desplazamiento/rango/body/ATR, eficiencia=move/vol,
absorción=vol alto / poco resultado, climax=vol/rango anómalos, compresión=resultado decreciente
con esfuerzo sostenido. Pregunta inicial: ¿estas variables contienen memoria/estructura de
transición que el K-D M15 no contiene? (ver hypothesis_exp_energy_wyckoff_design.md).
