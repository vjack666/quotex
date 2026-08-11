# EXP-A — Auditoría Funnel del Edificio de Contratación · modo `return_to_extreme`

**Activo:** EURUSD · **Años:** 2023, 2024 · **TF base:** M15 (confirmación 5m opcional)
**Script:** `scripts/audit_edificio_funnel.py <año> EURUSD return_to_extreme [no5m]`
**CSV:** `reports/AUDITORIA_FUNNEL/edificio_funnel_EURUSD_<año>.csv`
**Leyes activas:** `EDIFICIO_P2_MAX_HOLD_VELAS=8`, `EDIFICIO_DESCARTE_STICKY_THRESHOLD=2.0`
**Alcance:** AUDITORÍA DE EMBUDO (eventos y motivos por piso). NO se mide win rate.

## Puerta auditada (P2→P3)

El estocástico que entró en extremo al llegar a P2 debe **salir** del extremo y luego
**regresar a la línea 80/20**. Sin cronómetro de reloj: la permanencia se mide en velas
M15 (máx. 8). Si no regresa dentro de esa ventana → descarte por permanencia.

---

## 2024 — modo `return_to_extreme` (con filtro vela 5m)

Velas: M15=24.970 · M5=74.888

**Embudo (transiciones ascendentes):**

| Piso | Entradas |
|---|---|
| P1 | 1 |
| P2 | 287 |
| P3 | 573 |
| CONTRATADO | 0 |

**Distribución de piso final por ciclo:** P1=14.790 · P2=1.890 · P3=700 · CONTRATADO=0

**Descartes — TOTAL 14.833**

| Motivo | Conteo |
|---|---|
| Sin retorno a extremo en 8 velas M15 | 10.744 |
| Cruce pegajoso al entrar a P2 (\|K−D\|<2.0) | 4.089 |

**Tasas de gate sobre velas con estocástico:**
brake_ok 4.188 (16,78%) · extreme_ok 9.875 (39,57%) · cross_ok 3.721 (14,91%) · cross_sticky 6.870 (27,53%)

**Motivos por piso (top):**
- P1: 11.210 esperando freno · 3.171 freno candidato esperando M15 cerrada · 214 descarte sin retorno · 121 freno sin compresión · 73 descarte cruce pegajoso · 1 "Paga bien"
- P2: 556 esperando retorno a extremo 80 · 548 baja a P2 (freno perdido) · 474 esperando retorno a extremo 20 · 287 tarjeta de acceso (freno CONFIRMED) · 25 baja a P2 (extremo perdido)
- P3: 342 regresó a extremo 80 · 231 regresó a extremo 20 · 122 esperando cruce limpio · 4 vela 5m sin confirmar · 1 entrada marcada (delay 5 min)

## 2024 — modo `return_to_extreme no5m` (sin filtro vela 5m)

Embudo, distribución, descartes y tasas de gate: **idénticos** al caso con filtro 5m
(P1=1 · P2=287 · P3=573 · CONTRATADO=0; descartes 14.833 = 10.744 + 4.089).

Única diferencia observada, en los motivos del piso P3: desaparecen los 4 eventos
"vela 5m sin confirmar" y los eventos "entrada marcada, delay 5 min" pasan de 1 a 5.

---

## 2023 — modo `return_to_extreme` (con filtro vela 5m)

Velas: M15=21.632 · M5=64.857

**Embudo (transiciones ascendentes):**

| Piso | Entradas |
|---|---|
| P1 | 1 |
| P2 | 289 |
| P3 | 604 |
| CONTRATADO | 0 |

**Distribución de piso final por ciclo:** P1=12.579 · P2=1.867 · P3=732 · CONTRATADO=0

**Descartes — TOTAL 12.647**

| Motivo | Conteo |
|---|---|
| Sin retorno a extremo en 8 velas M15 | 8.900 |
| Cruce pegajoso al entrar a P2 (\|K−D\|<2.0) | 3.747 |

**Tasas de gate sobre velas con estocástico:**
brake_ok 3.689 (17,06%) · extreme_ok 8.770 (40,57%) · cross_ok 3.261 (15,08%) · cross_sticky 6.157 (28,48%)

**Motivos por piso (top):**
- P1: 9.485 esperando freno · 2.714 freno candidato esperando M15 cerrada · 210 descarte sin retorno · 90 freno sin compresión · 79 descarte cruce pegajoso · 1 "Paga bien"
- P2: 577 baja a P2 (freno perdido) · 498 esperando retorno a extremo 20 · 476 esperando retorno a extremo 80 · 289 tarjeta de acceso (freno CONFIRMED) · 27 baja a P2 (extremo perdido)
- P3: 328 regresó a extremo 80 · 276 regresó a extremo 20 · 126 esperando cruce limpio · 2 vela 5m sin confirmar / entrada marcada delay 5 min

## 2023 — modo `return_to_extreme no5m`

Igual que 2023 con filtro: mismo embudo (P2=289, P3=604), mismos 12.647 descartes
(8.900 + 3.747) y mismas tasas de gate. En P3 los 2 eventos "vela 5m sin confirmar"
se convierten en 2 eventos "entrada marcada, delay 5 min".

---

## Veredicto honesto

El embudo llega hasta P3 con volumen razonable y consistente entre años
(2024: 573 entradas a P3; 2023: 604), pero **CONTRATADO = 0 en los cuatro escenarios**.
Es decir, la nueva puerta P2→P3 por retorno a extremo sí produce candidatos —de hecho
más entradas a P3 (573/604) que a P2 (287/289), lo que indica reingresos repetidos al
mismo piso dentro de un ciclo—, y sin embargo ningún ciclo cruza el último umbral hacia
contratación. El cuello de botella no está en la puerta auditada: está aguas abajo, en el
paso P3→CONTRATADO (los motivos P3 muestran 122/126 eventos "esperando cruce limpio" y
apenas 1–5 "entrada marcada, delay 5 min", ninguno consumado).

Sobre los descartes: dominan abrumadoramente los de permanencia —72,4% en 2024
(10.744/14.833) y 70,4% en 2023 (8.900/12.647) por "sin retorno a extremo en 8 velas M15"—
frente a ~27–30% por cruce pegajoso. Esto no permite concluir todavía si `MAX_HOLD=8`
es demasiado estricto o si simplemente el retorno a extremo es un evento genuinamente
raro; hace falta un barrido del parámetro para separar ambas hipótesis.

Hallazgo adicional a registrar: **el filtro de vela 5m es prácticamente inerte en este modo**.
Con y sin `no5m` el embudo, los descartes y las tasas de gate son idénticos; solo se
reetiquetan 2–5 eventos en P3. Con contrataciones en cero, el filtro 5m no puede evaluarse:
nunca llega a ser el factor decisivo. Cualquier juicio sobre su utilidad debe posponerse
hasta que el embudo produzca contrataciones.

**Nota metodológica:** los CSV en `reports/AUDITORIA_FUNNEL/edificio_funnel_EURUSD_<año>.csv`
se sobrescriben en cada corrida; los archivos actualmente en disco corresponden a la última
ejecución (`no5m`). Los conteos con filtro 5m de este documento provienen de la salida
estándar de la corrida correspondiente.
