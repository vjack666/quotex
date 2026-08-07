# Risks — EXP-074b-NULL

> Cumple docs/LAB_CHARTER.md (Art. 4 datos inmutables, Art. 9 falsos positivos).
> Toda amenaza no mitigada se marca como bloqueante.

## Amenazas del laboratorio
| # | Amenaza | ¿Mitigada? | Mitigacion / Nota |
|---|---|---|---|
| 1 | El surrogate (shuffle de columnas) destruye TODA dependencia, no solo temporal -> podria sobre-rechazar H0 | Parcial | Es exactamente lo que se testea: ¿hay correlacion conjunta que el mercado mantiene y el null no? Se reporta la dist. de sil_null para juzgar si es razonable. |
| 2 | StandardScaler sobre datos ya normalizados por shuffle cambia algo | Sí | Estandarizacion idéntica a REAL (misma transformacion por columna). |
| 3 | B insuficiente para el rango de sil_null | Sí | B=200, n=3307 fases -> IC estrecho del percentil 95. |
| 4 | hdbscan no instalado en el entorno | Sí | Se usan GMM + KMeans (metodos principales de 074b). Documentado; no afecta el null. |
| 5 | Afinar el metodo despues de ver el resultado | Sí | Protocolo congelado (Art. 6). Criterios fijados en hypothesis antes de correr. |
| 6 | Leakage en la Prueba temporal OOS | Sí | Split cronologico estricto TRAIN 2022-2024 / TEST 2025-2026; GMM se ajusta SOLO en TRAIN; TEST se predice sin re-entrenar. |
| 7 | Confundir "el clustering encuentra geometria" con "el mercado tiene regimenes" | Sí | Veredicto explícito separando ambos (Art. del cierre). |

## Amenazas del sistema (no bloqueantes para este experimento)
| # | Amenaza | Estado |
|---|---|---|
| 8 | 22 tests legacy rotos (era STRAT-F) ensucian init.ps1 | Conocido; no afecta Edificio ni lab científico. |
| 9 | Sin pushes ni commits sin OK del Trader-Humano | Respetado. |
