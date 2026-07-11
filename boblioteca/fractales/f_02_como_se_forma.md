# f_02 · Cómo se forma un fractal (las 5 velas)

## La forma canónica
```
Fractal ARRIBA (bajista):
   \   /        <- vela 1 y 2 (máximos menores)
    \ /         <- vela 3 (MÁXIMO más alto)  <-- flecha arriba
     |          <- vela 4 (máximo menor)
     |          <- vela 5 (máximo menor)

Fractal ABAJO (alcista):
     |          <- vela 1 y 2 (mínimos mayores)
     |          <- vela 3 (MÍNIMO más bajo)  <-- flecha abajo
    / \         <- vela 4 (mínimo mayor)
   /   \        <- vela 5 (mínimo mayor)
```
La vela 3 siempre es el extremo. Las velas 1, 2, 4, 5 lo flanquean con máximos
(mínimos) menores.

## Confirmación
El fractal **no existe** hasta que las velas 4 y 5 se forman. Hasta entonces es
"en formación". Por eso el indicador dibuja la flecha con retraso: espera las 2
velas de la derecha.

## Fractal verdadero vs falso (filtro de calidad)
No todos los fractales valen lo mismo:
- **Fractal arriba VERDADERO**: el mínimo de la vela 5 es **mayor** que el mínimo
  de la vela 1. Señala continuación de la subida (pequeño impulso de reversión).
- **Fractal arriba FALSO**: la vela 5 tiene un mínimo más bajo que la vela 1 → es
  más probable que el precio siga bajando (el "techo" no aguantó).
- Análogo al revés para fractales abajo.

Esto importa porque un fractal "falso" a menudo es una **trampa de liquidez**: los
grandes empujan el precio más allá del fractal para cazar stops y luego revierten.

## Detalles prácticos
- Lo ideal son **5 velas**. Con 3 es señal débil; con 7 el fractal llega muy
  tarde (tras la vela central faltan 4 más).
- Los fractales se basan en **máximos y mínimos**, no en apertura/cierre.
- En temporalidades cortas (**M1**) aparecen muchos fractales y muchos son ruido.
  Por eso usamos el **M15** (mayor) para dar contexto (ver `f_03_marco_temporal.md`).
- El indicador **no repinta**: una vez pintado el fractal, se queda.

## Qué hacer con esta info
Cuando veas una flecha de fractal en **M5** en una zona de soporte/resistencia,
esa es tu "marca de giro". La usas como referencia para la entrada de **M1**.
