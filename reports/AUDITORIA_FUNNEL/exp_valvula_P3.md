# EXP — VÁLVULA P3→CONTRATADO sobre embudo return_to_extreme (EURUSD 2024)

**Fecha:** 2026-08-08 · **Autor:** Hermes ( medición sobre máquina validada exp_funnel_b)
**Script:** `scripts/exp_funnel_valvula.py` (reusa `exp_funnel_b.Sim`, añade forward-scan de válvula)

## Metodología
- Embudo P1→P2→P3 = **misma máquina validada** de `exp_funnel_b.py` (return_to_extreme).
  Reusada por herencia (no reescrita) para evitar divergencias: P1→P2=896, P2→P3=855.
- Válvula P3→CONTRATADO (modo `valvula` de `src/edificio_contratacion.py`):
  se ABRE cuando K sale del extremo en dirección del trade **Y** |K−D| abre con
  presión acumulada (viene subiendo en las últimas 3 velas, no salto aislado).
- Barrido de umbral acordado: **|K−D| ∈ {1, 3, 5}**. No se optimiza fuera de esto.
- WR por semestre del MISMO año: **H1 = primeras velas (descubrimiento)**,
  **H2 = resto (holdout)**. Definición fiel al bot real:
  `WIN = (CALL ∧ exit>entry) ∨ (PUT ∧ exit<entry)`, entry≈señal+5min, exit≈+15min.
  En M15 se aproxima **entry=i+1, exit=i+2** (ver LIMITACIÓN).

## Resultados

| Umbral | P1→P2 | P2→P3 | CONTRATADO | BLOQUEADOS | Tasa P3→CONTRATADO | WR H1 (descubr.) | WR H2 (holdout) |
|---|---:|---:|---:|---:|---:|---:|---:|
| |K−D|≥1 | 896 | 855 | **706** | 149 | 82.6% | 45.6% (n=349) | **51.5%** (n=357) |
| |K−D|≥3 | 896 | 855 | **688** | 167 | 80.5% | 45.9% (n=344) | **52.0%** (n=344) |
| |K−D|≥5 | 896 | 855 | **645** | 210 | 75.4% | 47.8% (n=322) | **50.8%** (n=323) |

Decompose WIN/LOSS H2 (holdout, el que importa):
- |K−D|≥1: W184 / L173 (51.5%)
- |K−D|≥3: W179 / L165 (52.0%)
- |K−D|≥5: W164 / L159 (50.8%)

## Interpretación honesta (consejo científico)

**Lo que SÍ se refutó (y lo que NO):**

- ✅ REFUTADA: la hipótesis de que **la separación K/D puede usarse como VÁLVULA de
  confirmación P3→CONTRATIVO** aporta ventaja predictiva. Los umbrales 1/3/5 dieron
  WR H2 ≈ 50–52% (cercano al azar) y dejaron pasar 75–83% de las señales.
- ❌ NO se refutó: que el **estocástico completo** no sirva.
- ❌ NO se refutó: que la **secuencia extremo → retorno → salida** esté mal.
- ❌ NO se refutó: que **todo el edificio** esté mal.

Lo único que golpeó el experimento es una hipótesis concreta: usar |K−D| como filtro
de calidad para decidir la contratación. Esa distinción importa para no tirar por la
borda lo que SÍ se aprendió.

**Por qué la válvula no filtra:** tras un retorno al extremo, casi siempre K ya salió
en dirección del trade y la separación K−D ya venía creciendo. La compuerta se queda
abierta sola; no quita ruido.

## Hallazgo de código (deuda de ingeniería, SEPARADA del experimento)

- La puerta P2→P3 del **Edificio REAL** (`src/edificio_contratacion.py`, modo
  `return_to_extreme`) está ROTA por diseño: define "zona" como [20,80] (al revés) y
  exige `extreme_ok` (stoch en extremo) para mantenerse en P2, lo que contradice el
  retorno (que requiere que el stoch SALGA primero). Por eso el Edificio real da 0 P3.
- La medición de la válvula se hizo sobre la máquina validada de `exp_funnel_b`
  (Máquina B: P1→P2→P3→válvula), **NO** sobre el motor real (Máquina A: P1→P2→❌P3).
- **No confundir "la válvula falló" con "el Edificio completo falló".** El experimento
  de la válvula puede estar correctamente falsado, pero queda la deuda: ¿cuál es el
  comportamiento correcto de P2→P3 cuando arreglemos el motor real?
- **Decisión:** el bug P2→P3 se REGISTRA como deuda de ingeniería pero **NO se arregla
  aquí**. Arreglarlo y volver a medir la válvula mezclaría dos experimentos.

## Veredicto (redacción precisa, EXP-VALVULA-P3)

> La hipótesis de que la separación K/D puede utilizarse como válvula de confirmación
> P3→CONTRATADO no mostró ventaja predictiva fuera de muestra en este experimento. Los
> umbrales 1, 3 y 5 produjeron WR H2 cercano al azar (51,5%, 52,0%, 50,8%) y permitieron
> el paso de la mayoría de señales. La hipótesis queda refutada para este contexto,
> timeframe y definición de entrada/expiración. No implica que el estocástico completo
> ni la secuencia del edificio estén refutados.

**Disposición:**
- **Válvula K/D:** REFUTADA como hipótesis de filtro. No activar (default producción =
  `cruce_limpio`).
- **Código de válvula:** se conserva configurable en `src/`. No porque "quizá funcione
  algún día", sino porque ya está aislada y claramente marcada como **NO ADOPTADA**;
  no hay razón para borrar una implementación experimental aislada.
- **Bug P2→P3:** registrado como deuda de ingeniería (ver arriba). No se arregla en
  este experimento.

## Por qué esto fue un experimento exitoso (aunque la hipótesis muriera)

```
HIPÓTESIS: "el cruce limpio bloquea demasiado"
   ↓
CAMBIO: "sigamos el retorno"
   ↓
573 llegan a P3 (return_to_extreme)
   ↓
HIPÓTESIS NUEVA: "K/D separándose = presión"
   ↓
VÁLVULA
   ↓
H1 (descubrimiento) ~46%
   ↓
H2 (holdout) ~51%
   ↓
≈50%  ❌ REFUTADA
```

Evitó lo peligroso: ver una condición que "se ve lógica", meterla en REAL y descubrir
después que era básicamente una moneda. El consejo hizo lo que debe hacer un laboratorio.

## LIMITACIÓN (crítica, transparente — se mantiene del experimento)
- **WR aproximado temporalmente:** entry/exit se aproximan con close M15 (i+1/i+2).
  El bot real entra ~300s tras la señal (openPrice intravela del broker); el CSV M15
  no reconstruye ese precio. Por tanto estos WR son una **aproximación de timing**, no
  réplica del broker. La conclusión "≈50%, sin edge" es robusta al método porque el
  ruido domina cualquier desfase de 1–2 velas.
- **Embudo con stoch reimplementado:** `compute_stoch_full` fue reimplementado (el
  original del empleado A se perdió). Los VOLÚMENES (896/855) no son los 287/573 que el
  empleado A validó, pero la MÁQUINA del embudo (return_to_extreme) es idéntica a la de
  `exp_funnel_b` (que el empleado A/B validaron como fiel). El WR es relativo a este embudo.
- **H2 = holdout del mismo año (mitades), no datos externos.** Detecta sobreajuste
  intra-año, no garantiza edge fuera de 2024.

---

## APÉNDICE (2026-08-08, retractación de falsa alarma — ver exp_edf_02_holdout_2023.md)

La conclusión arriba ("REFUTADA", ~50%) es válida **para la definición de válvula de
este barrido** (máquina B: `k>=k_prev` + `sep>=umbral`, presión en VELAS_EVOLVE).
Pero era una **falsa alarma generalizar "la válvula K/D no sirve"**.

El experimento EXP-EDF midió la **válvula del motor real** (`run_ramas`, DESVIO=5,
EVOLVE=3, MAX_HOLD=8: salir del extremo + |K−D|>=5 + presión creciente en 3 velas)
sobre datos reales M15+M5, y al correr el **holdout externo 2023** (mismos parámetros
congelados, sin re-optimizar) dio:

- 2024: CONTR=352, WR H1=50.3%, WR H2=63.5%
- 2023: CONTR=335, WR H1=62.6%, WR H2=60.0%

Es decir: **~60% WR en 2 años independientes**. Eso es edge débil pero REPRODUCIBLE,
no casualidad de un año. El salto H1→H2 de 2024 (50→63) era ruido de esa primera
mitad, no sobreajuste del parámetro (que viene de la sim, no de 2024).

**Retractación explícita:** la afirmación "la válvula K/D está refutada / no aporta
nada" fue excesiva. Con la definición del motor real, la válvula muestra un edge débil
reproducible (~60% WR, 2 años). Pasa de REFUTADA a **EDGE DÉBIL REPRODUCIBLE** (ver
config.py). El cruce_limpio+M5 SÍ queda descartado (48% en ambos años = moneda).

La definición de este barrido (máquina B, |K−D|≥5) se mantiene en ~50% y sigue siendo
un dato honesto — solo aclaro que NO es la misma definición que la válvula del motor
real que da 60%.
