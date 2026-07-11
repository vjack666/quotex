# 2 · La regla de las líneas naranjas (la regla de oro)

Todo el libro se reduce a esto. Si solo recuerdas una cosa, que sea esta.

## La regla
**Las entradas se toman EXCLUSIVAMENTE donde el precio toca una de las dos
bandas naranjas continuas.**

- Banda INFERIOR (soporte) → buscamos que el precio **rebote hacia arriba**.
- Banda SUPERIOR (resistencia) → buscamos que el precio **rebote hacia abajo**.

No entramos a mitad de rango. No entramos "porque se ve una vela". Solo en el
borde naranja. Punto.

## CALL (sube) vs PUT (baja)
| Toque en… | Señal buscada | Apuesta |
|---|---|---|
| Banda INFERIOR (soporte) | El precio toca, NO lo rompe, y muestra rechazo (mecha inferior larga, cierre sobre la línea). | **CALL** (a 3 min sube). |
| Banda SUPERIOR (resistencia) | El precio toca, NO lo rompe, y muestra rechazo (mecha superior larga, cierra bajo la línea). | **PUT** (a 3 min baja). |

## Qué cuenta como "toque"
- El cuerpo o la mecha de la vela de **M1** toca la banda naranja.
- Inmediatamente después el precio se aleja de la banda (rechazo).
- La vela de confirmación cierra del lado "correcto" (arriba del soporte para
  CALL, abajo de la resistencia para PUT).

## Qué NO hacer (filtros duros)
- ❌ Entrar si la vela rompe la banda y CIERRA fuera de ella (eso es ruptura,
  ver Fase D).
- ❌ Entrar con la vela todavía tocando la banda sin rechazo confirmado.
- ❌ Entrar en la mitad del rango solo porque "está cerca".
- ❌ Entrar si la fase dice "no operar" (ver cada fase).

## La entrada en 3 pasos
1. **M15** (mayor) te dice en qué fase estamos y si el rango es válido.
2. **M5** (media) te confirma que el precio llegó a la banda naranja y respeta el rango (y muestra el evento Wyckoff: LPS/Spring).
3. **M1** (menor) te da la vela de rechazo exacta → disparas CALL o PUT.
   Expiración = **3 minutos** (3 velas de M1).

La mecánica de los 3 pasos está en `03_marco_temporal_15_5_1.md`.
