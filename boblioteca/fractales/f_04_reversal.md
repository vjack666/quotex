# f_04 · Estrategia de reversión (el fractal como techo/suelo)

La más directa para binarias: usas el fractal como un nivel donde el precio suele
girar. Esperas el toque y la reversión.

## La idea
- **Fractal abajo** (flecha abajo en el mínimo) = posible **suelo**. El precio
  lo respeta y sube → **CALL**.
- **Fractal arriba** (flecha arriba en el máximo) = posible **techo**. El precio
  lo respeta y baja → **PUT**.

## Pasos (marco M15 / M5 / M1)
1. **M15** (mayor): el par en rango o tendencia suave (no ruptura violenta).
2. **M5** (media): se confirma un fractal en un extremo del rango.
3. **M1** (menor): el precio regresa a la zona del fractal y forma vela de rechazo
   (mecha larga en dirección opuesta al fractal, cierra del lado bueno).
4. Disparas CALL (si fue fractal abajo) o PUT (si fue fractal arriba).
   Expiración **3 min**.

## Señal tipo
| Contexto M15 | Fractal en M5 | Entrada M1 | Apuesta |
|---|---|---|---|
| Rango lateral | Fractal ABAJO en suelo del rango | Vela que rebota arriba del fractal | **CALL 3 min** |
| Rango lateral | Fractal ARRIBA en techo del rango | Vela que rebota abajo del fractal | **PUT 3 min** |

## Filtros de calidad
- Prefiere fractales **verdaderos** (ver `f_02_como_se_forma.md`).
- Mejor si el fractal coincide con una zona redonda (1.15500, 1.17000) o con una
  banda de las del libro de Wyckoff.
- Espera a que el **M1 confirme**: no dispares apenas ves la flecha en M5;
  espera el rechazo real.

## Qué evitar
- ❌ Reversión en medio de una ruptura de **M15**: el fractal se va a romper.
- ❌ Fractal "falso" en zona sin soporte claro: ruido.
- ❌ CALL en fractal abajo si el **M15** está en caída libre: vas contra corriente.
