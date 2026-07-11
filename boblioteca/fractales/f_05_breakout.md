# f_05 · Estrategia de ruptura (el precio rompe el fractal)

A veces el fractal NO aguanta: el precio lo atraviesa. Eso es momentum, y en
binarias la ruptura también se opera (a favor de la ruptura, no en contra).

## La idea
- El precio rompe un **fractal arriba** (vela de **M1** cierra por encima del
  máximo del fractal) → continúa subiendo → **CALL**.
- El precio rompe un **fractal abajo** (cierra por debajo del mínimo) → sigue
  bajando → **PUT**.

## Pasos (marco M15 / M5 / M1)
1. **M15** (mayor): tendencia definida o ruptura de rango en curso.
2. **M5** (media): se forma un fractal en el borde del rango.
3. **M1** (menor): el precio CIERRA fuera del fractal (rompe el extremo).
4. Disparas en la dirección de la ruptura. Expiración **3 min**.

## Señal tipo
| Contexto M15 | Fractal en M5 | Ruptura en M1 | Apuesta |
|---|---|---|---|
| Tendencia alcista / ruptura | Fractal ARRIBA en resistencia | Vela cierra por encima | **CALL 3 min** |
| Tendencia bajista / ruptura | Fractal ABAJO en soporte | Vela cierra por debajo | **PUT 3 min** |

## Filtros de calidad
- La ruptura debe ser con **cierre de vela**, no solo mecha. La mecha sola suele
  ser la "trampa de liquidez" (ver `f_02`).
- Mejor si el **M15** confirma la misma dirección (las velas de M15 ya rompieron
  el nivel).
- Volumen/noise: en **M1** una ruptura con cuerpo grande es más fiable que con
  mecha fina.

## Qué evitar
- ❌ Ruptura contra la estructura de **M15** (la más probable es falsa).
- ❌ Operar la ruptura y la reversión al mismo tiempo: elige un lado.
- ❌ Expiraciones largas (5–10 min): la ruptura de 1–3 min puede agotarse y
  regresar al fractal.

> Reversión (f_04) y ruptura (f_05) son opuestas. El **M15** decide cuál usar:
> rango → reversión; ruptura de rango → ruptura.
