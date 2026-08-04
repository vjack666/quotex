# P2 — Reglas del Edificio de Contratación

## Objetivo de P2

P2 es el cerebro técnico del edificio. Confirma que el activo está frenado y listo para esperar el cruce de líneas del estocástico. No genera entradas; solo emite la tarjeta de acceso a P3.

## Reglas de P2

- Prueba A — brake_eval: mide si el impulso está muerto después de una extensión clara. No es quiquilloso: si el freno está parcialmente confirmado, pasa. Filtra impulsos claramente vivos, no busca confirmación perfecta.
- Prueba B — extremo del estocástico M15: el estocástico debe estar en sobrecompra (>=80 para PUT) o sobreventa (<=20 para CALL). Si está en el medio, no está listo para el cruce; la estadía en P2 no se sostiene sin extremo.
- Tarjeta de acceso: cuando Prueba A y Prueba B se cumplen al mismo tiempo, el activo sube a P3. Esa tarjeta no es una entrada; solo significa que el par está preparado para esperar el cruce.
- Estadía en P2: se sostiene con la tarjeta + extremo vigente. El brake_ok instantáneo de la vela en formación no revoca la tarjeta (es ruidoso).
- Baja a P1: si se pierde el extremo mientras espera el cruce, el activo baja a P1 y pierde la tarjeta.

## Regla de descarte y re-evaluación por POI

- No se descarta solo porque el precio se mueva en contra del sesgo.
- Se evalúa descarte en dos pasos:
  1. Ruptura de POI: el nivel HTF cercano se rompe con claridad.
  2. Ausencia de rebote: después de la ruptura, no hay intención de regresar al POI.
- Solo cuando AMBAS se cumplen, el activo baja a P1.
- Si el POI se rompe pero hay señales de rebote (vela de rechazo, recuperación parcial, volumen de absorción), no se descarta. Se habilita la reevaluación en el siguiente POI cercano.
- El laboratorio debe medir la distancia al POI alternativo, definir umbral de proximidad y evaluar si el nuevo POI tiene la misma calidad estructural.

## Contexto adicional

- Si hay un nivel de soporte/resistencia HTF cerca del precio actual, suma puntos, pero no obliga ni bloquea.
