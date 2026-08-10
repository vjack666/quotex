## Revisión trader-humano — hub_operacional_edificio (Feature 41)

### Veredicto
APROBADO (con condición de seguridad)

### Dictamen (lenguaje trader)
La feature tiene sentido de taller: el Edificio ya está construido (pisos P1-P3, gate de la fábrica enchufado, executor que manda al broker). Lo que falta es CERRAR el ciclo para que opere de verdad y acumule datos propios, porque no tenemos velas históricas de la señal en vivo. Tres puntos que el trader exige:

1. **Cuenta REAL = decisión del humano, no del agente.** El bot ya tiene el código de envío. El riesgo es que el agente "se entusiasme" y mande a REAL. El flag `EDIFICIO_ALLOW_REAL=False` por defecto + credenciales ausentes es la barrera correcta. Aprobado SOLO si se mantiene esa barrera. En DEMO (PRACTICE) el agente puede operar libremente para recolectar muestras.

2. **Massaniello desde el comienzo = correcto.** En el taller, si no fijas el tamaño de la apuesta antes de la 1ª operación, la 1ª operación es un tiro al aire. El motor Massaniello ya existe; solo falta invocarlo al arranque. Bien.

3. **Caja negra sin borrar velas = mandatorio.** Las velas 1m son la materia prima para futuros experimentos (ya vimos que spot M15 no pesca; el 1m en vivo es el único dato nuevo que vamos a tener). Borrarlas es tirar el laboratorio. Retención infinita en crudo + export, sí.

4. **Verificación física del hub = no negociable.** El trader no lee código; valida por OJO. Cada botón y cada opción de dropdown deben responder de verdad. Si algo es adorno, se elimina. Aprobado.

### Faltantes que exige el trader
- Que el hub muestre CLARAMENTE si está en DEMO o REAL (color rojo/verde), para no confundirse operando.
- Que el export de caja negra sea un botón real, no solo script.
- Que la trazabilidad de la herramienta que originó la señal (feature 40) viaje en la orden y en la caja negra (R13): el trader quiere saber si fue arcoíris, POI o válvula la que disparó.
- Que la verificación física quede documentada con capturas (no solo "funciona").

### Condición de seguridad
El implementer NO debe, bajo ninguna circunstancia, poner `EDIFICIO_ALLOW_REAL=True` ni editar `.env` con credenciales. Esa es decisión y acción del humano fuera de sesión.
