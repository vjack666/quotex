# f_03 · Marco temporal: M15 (mayor) / M5 (media) / M1 (menor)

Wyckoff es fractal, y los fractales de Bill Williams también: el mismo patrón de
5 velas se repite en cualquier escala. Lo que importa no es el "minutaje" en
abstracto sino la **jerarquía**: la temporalidad mayor manda y las menores viven
dentro de ella.

Para binarias acotamos la pirámide a tres escalas. La más grande que usamos es
**M15** (no subimos a H1/H4: para apuestas de 3 min de expiración, M15 ya da
todo el contexto). Debajo van **M5** (media) y **M1** (menor).

## La jerarquía (la mayor manda)
```
M15  → contexto: ¿hay tendencia o rango? ¿Dónde caen los fractales grandes?
 │
M5   → estructura/zona: ¿se formó un fractal en un nivel clave? ¿verdadero o falso?
 │
M1   → ejecución: la vela de confirmación justo tras el fractal → abres la binaria.
```
Lo que diga M15 pesa más. Si M15 dice "rango alcista" y M1 dice "vende", el M1
probablemente es solo un pullback → no vendes contra M15.

## Los tres relojes
| Temporalidad | Rol en la jerarquía | Qué buscas |
|---|---|---|
| **M15** (la MÁS GRANDE) | Contexto | ¿Hay tendencia o rango? ¿Dónde caen los fractales grandes? |
| **M5** (la MEDIA) | Zona / estructura | ¿Se formó un fractal en un nivel clave? ¿Es verdadero o falso? |
| **M1** (la MÁS PEQUEÑA) | Ejecución | La vela de confirmación en la zona del fractal. Aquí abres. |

## Por qué este orden
- **M15 filtra lo malo**: un fractal de M1 en contra de la estructura de M15 es
  ruido. El mayor manda.
- **M5 te da el fractal real**: menos ruido que M1, más oportunidades que M15.
  Aquí ves el fractal ya confirmado y si es verdadero/falso.
- **M1 es el gatillo**: esperas a que el precio reaccione en la zona del fractal
  (rechazo para reversión, o cierre fuera para ruptura) y disparas.

## Expiración: 3 minutos
- La apuesta vence a los **3 minutos** = exactamente **3 velas de M1**.
- Coherencia con el libro de Wyckoff: mismo horizonte. El fractal marca el giro;
  das 3 velas para que la reversión o ruptura se confirme.
- No uses expiraciones de 5–10 min en rupturas: el precio puede regresar al
  fractal y dejarte fuera.

## Alineación = mayor probabilidad
La buena entrada aparece cuando las tres escalas cuentan la misma historia:
| Temporalidad | Estado buscado |
|---|---|
| M15 | Rango o tendencia suave (contexto favorable) |
| M5 | Fractal en un nivel clave, preferiblemente verdadero |
| M1 | Rechazo (reversión) o cierre fuera (ruptura) en esa zona |

Si M15+M5 dicen "compra" y M1 te da el rechazo, esa confluencia es la entrada de
calidad. Si M1 dice "vende" pero M15/M5 dicen "compra", es pullback → esperas el
rechazo alcista, no vendes.

## Flujo típico
1. **M15** (mayor): identificas que el par está en rango o tendencia suave.
2. **M5** (media): aparece un fractal abajo en la zona baja del rango (suelo).
3. **M1** (menor): el precio toca esa zona y forma vela de rechazo (cierra arriba).
4. Disparas **CALL**, expiración **3 min**.

> Regla de oro fractal: **la temporalidad mayor manda**. En binarias esa mayor es
> M15. Nunca operes un fractal de M1 que vaya contra M15.
