# 05 — Ejemplos aplicados a binarias (OTC, M15, expiry 3m)

Esto conecta el estocástico con STRAT-F en binarias Quotex PRACTICE. Los
ejemplos siguen la mecánica real del libro (archivo 03), traducida a nuestro
marco M15/M5/M1 y expiry de 3 minutos.

## Setup base que usa el bot

- **M15**: contexto de rango + estocástico (14,3,3).
- **M5**: fractal Bill Williams en banda naranja (zona Wyckoff).
- **M1**: rechazo de la banda (toca y no cierra afuera).
- **Expiry**: 3 velas M1 (3 minutos).

## Ejemplo A — PUT en techo de rango (el caso bueno)

1. M15: par en rango, estocástico **sube a 84** (sobrecompra) y %K cruza %D
   hacia abajo.
2. M5: fractal UP (techo) cae dentro de la banda naranja superior (resistencia
   del rango).
3. M1: vela toca la banda y cierra adentro (rechazo).
4. STRAT-F: señal PUT, score pasa umbral.
5. Estocástico M15 confirma: sobrecompra en techo de rango → alta probabilidad.
6. Entrada PUT, expiry 3m.

Resultado esperado: el rango rebota, PUT gana. La caja negra graba
`stoch_m15={k:84, d:80, estado:SOBRECOMPRA}` + `order_result=WIN`.

## Ejemplo B — CALL en piso de rango (el caso bueno)

1. M15: estocástico **baja a 16** (sobreventa) y %K cruza %D hacia arriba.
2. M5: fractal DOWN (piso) en banda naranja inferior (soporte del rango).
3. M1: rechazo de la banda.
4. STRAT-F: señal CALL.
5. Estocástico confirma sobreventa en piso → rebote probable.
6. Entrada CALL, expiry 3m.

## Ejemplo C — Señal STRAT-F pero estocástico la contradice (la frenamos)

1. M15: tendencia alcista clara, estocástico en **88** sostenido.
2. M5: aparece fractal UP (techo) en banda.
3. M1: rechaza.
4. STRAT-F: querría PUT.
5. PERO el estocástico M15 está en sobrecompra sostenida dentro de una tendencia
   alcista → es continuación, no techo (ver Autozone en archivo 02/03).
6. Decisión de la caja negra: marcar la señal con `stoch_contradicts=True` y
   medir si esas operaciones pierden. Si pierden, se promueve a veto.

## Ejemplo D — Divergencia alcista M15 (la joya)

1. M15: precio hace mínimo más bajo, estocástico hace mínimo más alto
   (divergencia alcista).
2. M5: fractal DOWN en banda naranja.
3. M1: rechazo.
4. STRAT-F: CALL. El estocástico aporta la divergencia (señal #1 de Lane) como
   refuerzo extra. Se graba `stoch_divergence=BULL`.

## Cómo lo grabamos en la caja negra (para calibrar)

Cada trade STRAT-F registra (nuevo esquema en `scan_candidates`):

- `stoch_m15` (JSON): `{k, d, estado, cruce, divergencia}`.
- `stoch_contradicts` (bool): si el estocástico va contra la dirección.
- `loss_reason`: por qué perdió (derivado de ANTES vs resultado).
- `improvement_hint`: sugerencia de calibración (ej: "strength<0.7 + M15
  ranging débil → WIN 38% en 20 ops; subir STRAT_F_MIN_SCORE a 68").

Y para estudiar el POR QUÉ:

- `candles_15m` (snapshot pre-entry).
- `candles_5m`, `candles_1m` (pre-entry).
- `candles_post` (3-5 velas 1m después del cierre, para ver si el fractal
  tenía razón pero la expiry fue corta, o si el precio fue contra todo el camino).
- `entry_price`, `exit_price` (precio al open 1m y al expiry).

Con eso podés responder tu pregunta literal: *"a la hora X:XX se usaron N
velas por la razón de la estrategia, cumplió situaciones A/B/C, se ejecutó,
ganó/perdió por razón Z, y si perdió → cómo mejorar la entrada."* Eso ES la
caja negra de verdad.

## Regla de oro para vos

El estocástico M15 es **contexto**, no el jefe. STRAT-F decide con fractal +
zona + rechazo. El estocástico le da el "estado del rango" y, con el tiempo,
los datos dirán si merece ser filtro. Sin medir, no afinás.

---
Ver también: `04_por_que_sirve_strat_f.md`, `03_senales_reales.md`.
