# EXP-C — Comparación de puertas P2→P3 del Edificio (EURUSD 2024)

Dataset: `backtest quotex/datos de velas/data/EURUSD` — M15 = 24.970 velas, M5 = 74.888 velas (SOLO LECTURA).
Auditoría de EMBUDO (no win rate, no P&L). Config común: `hold=8v`, `sticky_desc=2.0`.

Comandos:

```
python scripts/audit_edificio_funnel.py 2024 EURUSD cross_clean
python scripts/audit_edificio_funnel.py 2024 EURUSD return_to_extreme no5m
```

> Nota metodológica: el script escribe siempre al mismo CSV
> (`reports/AUDITORIA_FUNNEL/edificio_funnel_EURUSD_2024.csv`), por lo que la segunda corrida
> sobreescribe la primera. Se copió cada CSV antes de la siguiente corrida y los conteos de esta
> tabla están verificados contra el CSV, no solo contra la salida impresa.

## Tabla comparativa

| Métrica | ORIGINAL `cross_clean` | NUEVA `return_to_extreme` (no5m) |
|---|---:|---:|
| Piso máximo alcanzado | **P2** | **P3** |
| Transiciones → P1 | 1 | 1 |
| Transiciones P1→P2 | **305** | **287** |
| Transiciones P2→P3 | **0** | **573** |
| Transiciones P3→CONTRATADO | 0 | 0 |
| Contratados totales | 0 | 0 |
| Velas con piso final = P1 | 15.938 | 14.790 |
| Velas con piso final = P2 | 1.442 | 1.890 |
| Velas con piso final = P3 | **0** | **700** |
| Velas con piso final = CONTRATADO | 0 | 0 |
| **TOTAL descartes** | **4.271** | **14.833** |
| · cruce pegajoso al entrar a P2 (\|K-D\|<2.0) | 4.271 | 4.089 |
| · sin retorno a extremo en 8 velas M15 | — | 10.744 |

Señales crudas (idénticas en ambas corridas, confirma que solo cambió la puerta):
`brake_ok` 4.188 (16,78%) · `extreme_ok` 9.875 (39,57%) · `cross_ok` 3.721 (14,91%) · `cross_sticky` 6.870 (27,53%).

### Motivos por piso (del CSV)

**cross_clean — P2 (1.442 velas, ninguna sale):**

| motivo | conteo |
|---|---:|
| P2 OK — sticky: esperar separación K/D | 753 |
| P2 OK — tarjeta de acceso: freno CONFIRMED | 305 |
| P2 OK — esperando cruce K/D | 298 |
| P2 OK — separación K/D detectada, esperando confirmación | 84 |
| P2 OK — esperando confirmación separación (60s) | 2 |

**return_to_extreme — P2 (1.890) y P3 (700):**

| piso | motivo | conteo |
|---|---|---:|
| P2 | esperando retorno a extremo 80 | 556 |
| P2 | Baja a P2 — freno perdido | 548 |
| P2 | esperando retorno a extremo 20 | 474 |
| P2 | tarjeta de acceso: freno CONFIRMED | 287 |
| P2 | Baja a P2 — extremo perdido | 25 |
| P3 | estocástico regresó a extremo 80 | 342 |
| P3 | estocástico regresó a extremo 20 | 231 |
| P3 | esperando cruce limpio | 122 |
| P3 | entrada marcada, delay 5 min | 5 |

## Veredicto honesto

1. **Cuál fluye más al P3:** `return_to_extreme`, de forma inequívoca. Pasa de **0 → 573**
   transiciones P2→P3 sobre exactamente el mismo dataset y las mismas señales crudas. La puerta
   original nunca abre: 1.442 velas se quedan atascadas en P2, la mayoría (753) esperando una
   separación K/D que, con el requisito de cruce limpio + 60 s, prácticamente nunca se materializa
   dentro de la ventana de permanencia.

2. **Cuál es más estricta (más descartes):** `return_to_extreme` descarta **3,5× más**
   (14.833 vs 4.271). Pero la estrictez es de otra naturaleza: la original descarta 4.271 veces
   *antes* de P2 por cruce pegajoso y luego simplemente **no resuelve** (deja la card viva en P2
   sin veredicto). La nueva descarta explícitamente 10.744 veces por "sin retorno a extremo en
   8 velas M15" — es decir, cierra el ciclo con un NO en vez de dejarlo colgado. Más descartes
   aquí significa **más decisiones tomadas**, no necesariamente más filtro efectivo.

3. **¿Resuelve el tapón P2→P3 de EXP-037 ("sin cross_clean 0 entradas")?**
   **Sí, resuelve el tapón P2→P3, pero NO produce entradas todavía.** Ambos modos terminan con
   **0 CONTRATADOS**. El cuello de botella se ha *movido* de P2→P3 a P3→P4: 573 cards llegan a
   P3, 122 se quedan "esperando cruce limpio" y solo 5 llegan a "entrada marcada, delay 5 min"
   sin que ninguna complete la contratación. Conclusión: el retorno a la línea 80/20 es una puerta
   P2→P3 **viable y con flujo real**, y desbloquea el diagnóstico, pero el siguiente experimento
   debe atacar la puerta P3→CONTRATADO (cruce limpio en P3 + delay de 5 min), que es donde ahora
   muere el 100 % del embudo.

4. **Advertencia de comparabilidad:** la corrida `return_to_extreme` se ejecutó con `no5m`
   (gate M5 desactivado), tal como pide el protocolo, mientras que `cross_clean` corrió con el
   gate M5 activo. La diferencia de flujo al P3 es tan grande (0 vs 573) que no puede explicarse
   solo por eso, pero para una comparación estrictamente pareada convendría correr también
   `cross_clean no5m`.

No se modificó nada en `src/`. Datos externos accedidos en solo lectura.
