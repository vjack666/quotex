# Investigación: "Muerte del empuje" en el Atlas (Discovery Engine, 2026-07-27)

## Origen de la hipótesis (NO es nueva)

La idea de que "cuando un impulso fuerte PIERDE FUERZA (muere) tras llegar a
una zona, el precio rebota" NO es invento de esta sesión. Está documentada y
VALIDADA previamente en el proyecto:

- `docs/CONSTITUCION_REBOTE.md` (Ley 1, M2 "Índice de freno", historia canónica
  pasos 3-4-5): el rebote nace cuando el paso se acorta, aparecen mechas contra
  el viaje y una vela cierra del lado contrario.
- `docs/CONSTITUCION_REBOTE.md` §Estado de la evidencia (v1.0, líneas 98-107):
  **LA PRUEBA CENTRAL PASÓ**. MUERTE TOTAL (avance chico + <10% del pico +
  velas alternadas) → REBOUND **69.8%** (n=16,834) vs 23.7% el resto;
  empuje VIVO → 13.1%. Walk-forward 2012-19: 69.3% / 2020-26: 70.5%.
  Placebo p<0.001. Es el LAB-001.
- `docs/TEORIA_VS_EVIDENCIA.md` (§15-24, §41-46, §91-98): confirma que lo que
  predice NO es "frenar" a secas, sino la **MUERTE COMPLETA** del impulso.
  "Pierde presión" a secas fue REFUTADO; la MUERTE (avance chico + <10% pico +
  alternancia) es lo que discrimina 70% vs 23%.

El número "72-77%" que el dueño recuerda es coherente con ese 69.8% validado
(LAB-001). No es una invención: es la regla fundacional de la 2ª generación.

## Por qué el Discovery Engine (esta sesión) NO la encontró

El motor que armé (Capa 2.5) corrió sobre `data/observador/episodes_eurusd_14y.db`
(Atlas v2, modelo PTM v3). Dos razones por las que rechazó la candidata:

1. **Definición incorrecta de la causa.** Mi primera candidata usó
   `end_reason == 'DEAD_PUSH'`. Ese vocabulario NO existe en el Atlas v2
   (PTM v3 usa QUIET/EXPANSION/PRESSURE/BRAKE/TRANSITION/RESOLUTION; el
   `end_reason` real es siempre `RESOLUTION`). Por eso la candidata predicaba
   0 episodios → 0 leyes. No era que la ley fuera falsa; era que la busqué mal.

2. **Variable objetivo mal elegida.** El "efecto rebote" lo medí primero como
   `mfe > 0`, que en el Atlas v2 ocurre en ~88% de los episodios (ruido, no
   discrimina). Luego lo corregí a `distance_pips final < 0` (reversión del
   empuje), que da baseline ~49%. Ninguna de las dos es la variable de LAB-001.

## Experimento real sobre el Atlas v2 (2026-07-27)

Para ser honestos, PROBÉ la hipótesis sobre el Atlas v2 con la variable
objetivo CORRECTA (`resolution_type == 'REBOUND'`, que SÍ existe en v2:
baseline 30.1%, n=18081/60000) y un proxy de "muerte" construido con los datos
disponibles (estados + distance_pips neto):

```
MUERTE (proxy) = contiene PRESSURE + BRAKE  Y  distance_pips final < 0.9*pico
```

Resultado sobre 60k episodios EURUSD M1:
- baseline REBOUND: 30.1%
- MUERTE (proxy): 30.5%  ← **IGUAL al baseline**

Conclusión del experimento: el proxy "frenar" (PRESSURE→BRAKE sin continuar)
**NO predice rebote**. Esto es EXACTAMENTE lo que dice `TEORIA_VS_EVIDENCIA.md`:
"pierde presión a secas fue REFUTADO; es la MUERTE (avance chico + <10% pico +
alternancia), no frenar". Mi proxy solo captura el "freno", no la "muerte
completa". Por eso no apareció.

## Por qué el Discovery necesita el criterio de LAB-001 para encontrarla

El criterio operativo de LAB-001 es:
- **avance chico**: el recorrido de las velas tras el pico es pequeño.
- **<10% del pico**: el avance posterior es menor al 10% del recorrido del impulso.
- **velas alternadas**: el signo de los cuerpos de vela se alterna (primer cierre contrario).

Eso requiere el **recorrido de cada vela (cuerpos)**, no solo `distance_pips`
(red neta al inicio del episodio). El Atlas v2 (PTM v3) NO graba el recorrido
de vela por barra: solo `distance_pips`, `mfe`, `mae`, `state`. Por eso:

- LAB-001 se validó sobre el Atlas v1 (que sí medía el recorrido del impulso),
  o requiere enriquecer el Observador (Fase B) para grabar cuerpos de vela.
- El Discovery Engine de esta sesión NO puede reconstruir "avance chico +
  <10% pico + alternancia" fielmente con los datos de v2. Por eso emitió
  leyes sobre `curve_shape` (que SÍ está en v2) en lugar de "muerte del empuje".

## Conclusión honesta

1. La "muerte del empuje → rebote" es REAL y está VALIDADA (LAB-001, 69.8%),
   no es especulación ni invento de este chat.
2. Mi Discovery la rechazó por una DEFINICIÓN MALA mía (end_reason inexistente
   + proxy de "freno" que = baseline), NO porque la ley sea falsa. Lo aclaro
   expresamente para no dejar la impresión errónea de que "el motor la falsó".
3. Para que el Discovery la redescubra SOBRE el Atlas v2, falta grabar el
   recorrido de velas (cuerpos) en el Observador — trabajo de Fase B, no del
   Discovery. Mientras tanto, la ley vive en la Constitución como LAB-001.
4. El experimento que SÍ corrí (proxy "freno") confirma empíricamente que
   "frenar solo" no predice rebote, alineado con TEORIA_VS_EVIDENCIA. Esto es
   falsación honesta, no conformismo.

## Acción recomendada

Si queremos que el Discovery Engine EMITA la Ley "muerte del empuje" como #N
sobre datos frescos (no solo citarla de LAB-001), el Observador (Capa 2) debe
grabar en `episode_evolution` el recorrido de la vela (body high/low o delta de
cierre) para que el Discovery pueda computar "avance chico + <10% pico +
alternancia". Eso es un cambio en PTM v3 (Fase B del Observador), fuera del
alcance del Discovery Engine.
