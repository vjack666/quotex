# f_07 · Doble fractal (entrada más fuerte)

Esperar a que se formen **dos fractales seguidos en la misma dirección** antes de
entrar. Filtra gran parte del ruido de los fractales simples.

## La idea
- Dos **fractales abajo** consecutivos (ambos en la zona baja) = el precio probó
  el suelo dos veces y no lo rompió → rebote fuerte probable → **CALL**.
- Dos **fractales arriba** consecutivos (en la zona alta) = el techo aguantó dos
  veces → bajada probable → **PUT**.

## Pasos
1. **M15** (mayor): rango o tendencia suave.
2. **M5** (media): se forma fractal 1 en el borde; luego, sin alejarse mucho, se forma
   fractal 2 en la misma zona.
3. **M1** (menor): el precio reacciona tras el segundo fractal.
4. Disparas en la dirección del rechazo. Expiración **3 min**.

## Señal tipo
| Contexto M15 | Doble fractal (M5) | Entrada M1 | Apuesta |
|---|---|---|---|
| Rango | Dos fractales ABAJO en suelo | Rebote | **CALL 3 min** |
| Rango | Dos fractales ARRIBA en techo | Rebote | **PUT 3 min** |

## Por qué es más fuerte
- Un fractal puede ser casual. Dos en el mismo nivel dicen "el mercado defendió
  ese precio dos veces". Eso es oferta/demanda real, no ruido.
- En binarias, donde las señales falsas duelen, el doble fractal es tu filtro de
  paciencia: esperas la segunda confirmación.

## Qué evitar
- ❌ Dos fractales muy separados (ya no es "la misma zona").
- ❌ Doble fractal en contra de la ruptura de **M15**.
- ❌ Forzar el segundo fractal si el precio ya rompió el nivel: ahí cambias a
  ruptura (f_05), no doble fractal.
