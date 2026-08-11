# EXP-B — Puerta P2→P3 con retorno CONFIRMADO + K/D a favor (EURUSD 2024)

Simulación independiente (scripts/exp_funnel_b.py). **No se modificó `src/`.**
Datos M15 reales: `C:\Users\v_jac\Desktop\backtest quotex\datos de velas\data\EURUSD\M15\2024.csv` (24970 velas, solo lectura).

## Reglas comparadas

- **BASE (`return_to_extreme`)**: %K vuelve a tocar la línea de extremo de entrada (20 CALL / 80 PUT) habiendo salido antes de [20,80]. Un tick basta.
- **VARIANTE B (`confirmado`)**: además (1) la vela M15 siguiente debe seguir en la misma zona extremo, y (2) K/D en dirección del trade (CALL: K subiendo y K≥D; PUT: K bajando y K≤D).

Común a ambas: P1→P2 exige freno confirmado (rango < 0.7×rango previo) + extremo + no-sticky (|K−D|≥2.0); ley de permanencia de 8 velas M15.

## Conteos del embudo

### BASE — return_to_extreme

- Entradas a P2: **896**
- Promociones P2→P3: **855**
- Tasa P2→P3: **95.42%**
- Descartes totales: **798**

| motivo de descarte | conteo |
|---|---:|
| cruce pegajoso al entrar a P2 (|K-D|<2.0) | 757 |
| sin retorno válido en 8 velas M15 | 41 |

### VARIANTE B — retorno confirmado + K/D a favor

- Entradas a P2: **734**
- Promociones P2→P3: **602**
- Tasa P2→P3: **82.02%**
- Descartes totales: **1838**

| motivo de descarte | conteo |
|---|---:|
| K/D en contra del trade | 918 |
| cruce pegajoso al entrar a P2 (|K-D|<2.0) | 578 |
| retorno NO confirmado (tick aislado) | 210 |
| sin retorno válido en 8 velas M15 | 132 |

## Comparativa

| métrica | BASE | VARIANTE B | Δ |
|---|---:|---:|---:|
| entradas P2 | 896 | 734 | -162 |
| promociones P3 | 855 | 602 | -253 |
| tasa P2→P3 | 95.42% | 82.02% | -13.41 pp |
| descartes | 798 | 1838 | 1040 |

## Muestra de eventos (primeros 30 de la VARIANTE B)

| # | fecha (UTC) | evento | dir | extremo | K | D | motivo |
|---|---|---|---|---:|---:|---:|---|
| 28 | 2024-01-01 23:45:00+00:00 | P2→P3 | CALL | 20.0 | 18.36 | 10.85 | retorno CONFIRMADO a 20 + K/D a favor |
| 57 | 2024-01-02 07:00:00+00:00 | P2→P3 | CALL | 20.0 | 4.26 | 2.23 | retorno CONFIRMADO a 20 + K/D a favor |
| 119 | 2024-01-02 22:45:00+00:00 | DESCARTE | CALL | 20.0 |  |  | sin retorno válido en 8 velas M15 |
| 125 | 2024-01-03 00:00:00+00:00 | P2→P3 | PUT | 80.0 | 85.57 | 89.47 | retorno CONFIRMADO a 80 + K/D a favor |
| 150 | 2024-01-03 06:15:00+00:00 | P2→P3 | CALL | 20.0 | 3.15 | 3.06 | retorno CONFIRMADO a 20 + K/D a favor |
| 157 | 2024-01-03 08:00:00+00:00 | P2→P3 | CALL | 20.0 | 18.98 | 17.44 | retorno CONFIRMADO a 20 + K/D a favor |
| 200 | 2024-01-03 18:45:00+00:00 | P2→P3 | PUT | 80.0 | 80.88 | 86.18 | retorno CONFIRMADO a 80 + K/D a favor |
| 238 | 2024-01-04 04:30:00+00:00 | DESCARTE | CALL | 20.0 |  |  | sin retorno válido en 8 velas M15 |
| 241 | 2024-01-04 05:00:00+00:00 | P2→P3 | PUT | 80.0 | 83.51 | 93.85 | retorno CONFIRMADO a 80 + K/D a favor |
| 313 | 2024-01-04 23:00:00+00:00 | P2→P3 | CALL | 20.0 | 4.96 | 2.0 | retorno CONFIRMADO a 20 + K/D a favor |
| 383 | 2024-01-05 16:30:00+00:00 | P2→P3 | CALL | 20.0 | 14.79 | 14.69 | retorno CONFIRMADO a 20 + K/D a favor |
| 397 | 2024-01-07 20:00:00+00:00 | P2→P3 | PUT | 80.0 | 91.87 | 92.76 | retorno CONFIRMADO a 80 + K/D a favor |
| 430 | 2024-01-08 04:15:00+00:00 | P2→P3 | CALL | 20.0 | 18.05 | 16.07 | retorno CONFIRMADO a 20 + K/D a favor |
| 482 | 2024-01-08 17:15:00+00:00 | P2→P3 | CALL | 20.0 | 11.69 | 10.39 | retorno CONFIRMADO a 20 + K/D a favor |
| 510 | 2024-01-09 00:30:00+00:00 | DESCARTE | CALL | 20.0 |  |  | sin retorno válido en 8 velas M15 |
| 513 | 2024-01-09 01:00:00+00:00 | P2→P3 | CALL | 20.0 | 17.3 | 7.07 | retorno CONFIRMADO a 20 + K/D a favor |
| 535 | 2024-01-09 06:30:00+00:00 | P2→P3 | CALL | 20.0 | 10.23 | 8.55 | retorno CONFIRMADO a 20 + K/D a favor |
| 623 | 2024-01-10 04:30:00+00:00 | P2→P3 | PUT | 80.0 | 87.57 | 90.49 | retorno CONFIRMADO a 80 + K/D a favor |
| 658 | 2024-01-10 13:15:00+00:00 | P2→P3 | PUT | 80.0 | 91.74 | 93.49 | retorno CONFIRMADO a 80 + K/D a favor |
| 680 | 2024-01-10 18:45:00+00:00 | P2→P3 | PUT | 80.0 | 93.36 | 95.05 | retorno CONFIRMADO a 80 + K/D a favor |
| 720 | 2024-01-11 04:45:00+00:00 | P2→P3 | CALL | 20.0 | 11.85 | 9.02 | retorno CONFIRMADO a 20 + K/D a favor |
| 777 | 2024-01-11 19:00:00+00:00 | P2→P3 | PUT | 80.0 | 86.78 | 88.59 | retorno CONFIRMADO a 80 + K/D a favor |
| 820 | 2024-01-12 06:00:00+00:00 | DESCARTE | PUT | 80.0 |  |  | sin retorno válido en 8 velas M15 |
| 825 | 2024-01-12 07:00:00+00:00 | P2→P3 | CALL | 20.0 | 8.4 | 5.33 | retorno CONFIRMADO a 20 + K/D a favor |
| 865 | 2024-01-14 17:15:00+00:00 | DESCARTE | PUT | 80.0 |  |  | sin retorno válido en 8 velas M15 |
| 886 | 2024-01-14 22:30:00+00:00 | DESCARTE | CALL | 20.0 |  |  | sin retorno válido en 8 velas M15 |
| 915 | 2024-01-15 05:30:00+00:00 | P2→P3 | CALL | 20.0 | 11.6 | 7.63 | retorno CONFIRMADO a 20 + K/D a favor |
| 968 | 2024-01-15 19:45:00+00:00 | P2→P3 | CALL | 20.0 | 6.88 | 5.05 | retorno CONFIRMADO a 20 + K/D a favor |
| 981 | 2024-01-15 23:00:00+00:00 | P2→P3 | CALL | 20.0 | 17.58 | 14.48 | retorno CONFIRMADO a 20 + K/D a favor |
| 1009 | 2024-01-16 06:00:00+00:00 | P2→P3 | CALL | 20.0 | 11.73 | 5.65 | retorno CONFIRMADO a 20 + K/D a favor |

## Veredicto honesto

La variante B **FLUYE MENOS** que la base: 602 promociones a P3 frente a 855 (70.4% del flujo base).

Razón mecánica: la base promueve con un **único toque** de %K en la línea de extremo, que es un evento frecuente porque el estocástico oscila con rapidez. La variante añade dos filtros en serie sobre ese mismo toque: la vela siguiente debe permanecer en la zona (elimina los toques-aguja de una sola vela) y K/D debe girar a favor del trade en esa vela de confirmación. Ambos filtros sólo pueden restar eventos, nunca añadirlos, y como el tiempo de espera sigue acotado por la ley de permanencia (8 velas), los toques no confirmados no obtienen segunda oportunidad dentro del mismo ciclo salvo que reaparezcan.

Interpretación de embudo (no de win rate): el tapón P2→P3 se **estrecha**. Esta auditoría NO mide si los eventos supervivientes son mejores; sólo cuantifica el caudal. Para decidir si el filtro compensa hace falta un experimento de resultado, no de embudo.
