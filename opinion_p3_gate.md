# Opinión del Agente Arquitecto/Lógico — Puerta P3→CONTRATADO

**VEREDICTO: A FAVOR (con condición de umbral).**

La regla actual en P3 es **CONTRADICTORIA por diseño**. La narrativa del edificio es coherente: el estocástico entró al extremo (P2), volvió a él (P3), y debe confirmar "saliendo a favor" para comprar. Pero P3 exige un "cruce limpio K/D" justo donde K y D están abrazadas en la línea 20/80. En el extremo, %K y %D son casi idénticas (ambas pegadas al suelo/techo), así que un cruce limpio —K separándose y cruzando a D con margen— es estadísticamente rarísimo. Por eso 122 velas quedan "esperando cruce limpio" y CONTRATADO=0. El edificio abre la puerta (P3=700 velas) pero la cerradura exige algo que la geometría del indicador impide en ese lugar: es una puerta que no tiene forma de abrirse.

Cambiar a "K se aleja del extremo en dirección del trade" alinea la cerradura con la historia: CALL → K sube desde ≤20; PUT → K baja desde ≥80.

**DETALLE DE IMPLEMENTACIÓN (la condición):**
- No uses 1 punto: el ruido de %K en el extremo produce falsos rebotes. Exige un buffer de separación del extremo, p.ej. CALL cuando K ≥ 25 (5 puntos fuera de 20) y, crucialmente, K separada de D por ≥ 2–3 puntos (K>D con margen).
- Validar AMBAS: (a) distancia al extremo ≥ umbral, y (b) K-D spread, para no confundir micro-jitter con dirección real.
- Sugerencia: umbral de alejamiento = 4–5 puntos, tuneado contra el dataset 2024 (24.970 velas) antes de fijarlo.

Sin ese doble filtro, el "alejarse" se vuelve ruido y revienta el edge.
