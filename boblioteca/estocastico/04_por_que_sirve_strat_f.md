# 04 — Por qué el estocástico M15 sirve a STRAT-F

## El problema que tiene STRAT-F hoy

STRAT-F detecta un **fractal Bill Williams en M5** que cae en una **banda
naranja (zona Wyckoff)** y espera que el **M1 rechace**. Eso es la estructura
de entrada. Pero le falta contexto de **momentum de rango**: ¿está el par en
un extremo de su rango M15 (recalentado o congelado) o está al medio?

Sin eso, STRAT-F puede entrar CALL justo cuando el M15 lleva 20 velas subiendo
y el precio ya está "quemado" arriba → la continuación falsa lo come. O entrar
PUT cuando el M15 está en sobreventa extrema y rebota fuerte.

## Por qué el estocástico M15 encaja

El estocástico M15 responde justo esa pregunta: *"¿dónde está el cierre
actual dentro del rango de las últimas 14 velas M15?"*. Es el contexto de
rango que STRAT-F necesita, en la temporalidad mayor (M15 manda, regla de
STRAT-F).

Casos de uso directo:

1. **Filtro de rebote**. STRAT-F quiere un PUT en banda naranja (techo de
   rango). Si el estocástico M15 está en **sobrecompra (>=80)**, el techo
   tiene más peso → señal más fuerte. Si el estocástico M15 está en 40, el
   "techo" es dudoso → podemos subir el umbral o descartar.
2. **Filtro de continuación falsa**. STRAT-F quiere CALL en banda (piso).
   Si el estocástico M15 está en **sobreventa (<=20)**, el piso es real →
   rebote probable. Si está en 85, la CALL es contra una suba recalentada →
   riesgo alto.
3. **Sesgo de rango (línea 50)**. Si el estocástico M15 está por encima de 50,
   el rango tiene sesgo alcista; por debajo, sesgo bajista. Ayuda a no operar
   rebotes contra el sesgo del rango cuando el M15 no está roto.

## La regla de oro para integrarlo (medir, no creer)

NO lo vamos a poner como filtro duro de entrada desde el día 1. La caja negra
de STRAT-F ya grabó señales sin estocástico. El plan:

1. Calcular `stoch_m15` (Slow/Full 14,3,3) en cada scan STRAT-F.
2. **Grabarlo** en la caja negra junto con la señal y el resultado.
3. Hacer **A/B con datos reales**: misma señal STRAT-F con y sin el filtro
   estocástico, comparar win_rate y expectancy.
4. Solo si los datos dicen "sube el win_rate", lo promovemos a filtro.

Esto cumple tu forma de trabajar: sin constantes fijas de fe, todo con
volatilidad/momentum medido y confirmado por el diario.

## Parámetros iniciales sugeridos

- Temporalidad: **M15** (contexto mayor de STRAT-F).
- Configuración: **(14, 3, 3)** Slow/Full.
- Umbrales de extremo: **>=80 sobrecompra**, **<=20 sobreventa** (ajustables
  con datos).
- Uso: filtro de contexto + campo en caja negra. No es el disparador.

## Qué NO hace

- No reemplaza el fractal M5 ni el rechazo M1. Es contexto, no estructura.
- No funciona solo en tendencia M15 fuerte (ahí lo usamos a favor, no contra).
- No es señal de entrada por sí mismo.

---
Ver también: `01_historia_y_que_es.md`, `02_cuando_usarlo.md`,
`03_senales_reales.md`, y `05_ejemplos_aplicados_binarias.md`.
