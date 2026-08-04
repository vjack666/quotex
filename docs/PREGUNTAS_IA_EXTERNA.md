# Preguntas para IA externa — Edificio de Contratación + Laboratorio neuronal

Objetivo: una IA externa lee este proyecto y ayuda a definir la secuencia real del Edificio, el orden correcto de sus pasos, y cómo entrenar redes neuronales en el Laboratorio para que entiendan y repliquen el comportamiento del Edificio en experimentos.

## 1. Lectura del proyecto
- ¿Qué archivos del repositorio describen la arquitectura cognitiva del Edificio de Contratación?
- ¿Dónde están definidas las reglas de transición entre pisos (P1, P2, P3)?
- ¿Qué módulos online replican esas reglas y en qué se diferencian de los experimentos del Laboratorio?

## 2. Secuencia del pipeline
- Según la documentación y el código, ¿cuál es la secuencia canónica de eventos desde que un activo entra al Edificio hasta que se emite una orden?
- ¿Qué condiciones son secuenciales y cuáles pueden ocurrir en paralelo?
- ¿Qué eventos descartan un activo y en qué piso se produce el descarte?

## 3. Features y confirmaciones temporales
- ¿Qué features del Laboratorio replican fielmente la lógica online y cuáles están desalineadas?
- ¿Cómo debe medirse el “freno confirmado” para que sea causal, sin look-ahead y alineado con el código online?
- ¿Cómo debe medirse el “cruce limpio” para que represente una vela M15 cerrada y no un tick?

## 4. Redes neuronales en el Laboratorio
- ¿Qué arquitectura de red neuronal se adapta mejor a clasificar variantes de secuencia del Edificio?
- ¿Qué entrada debe recibir la red en el momento del brake confirmado para predecir si esa secuencia será ganadora?
- ¿Cómo se entrena la red sin filtrar información futura y cómo se valida con split temporal?
- ¿Cómo puede la red ayudar a buscar configuraciones óptimas de P2/P3 sin correr miles de experimentos ciegos?

## 5. Experimentación y falsación
- ¿Cómo debe estructurarse un experimento para falsar una regla del Edificio sin contaminar la muestra?
- ¿Qué métricas son suficientes para declarar PASS/FAIL y cómo se integran con el tribunal del Laboratorio?
- ¿Cómo debe el Laboratorio documentar cada hallazgo para que el Edificio lo pueda adoptar sin ambigüedades?

## 6. Próximos pasos accionables
- Dada la desviación actual entre el Laboratorio y el Edificio, ¿cuál es el primer experimento que debería ejecutarse para alinear ambos?
- ¿Qué parámetros del Edificio deben volverse configurables para que el Laboratorio pueda experimentar con ellos sin tocar el código productivo?
- ¿Cómo debe evolucionar el Laboratorio para convertirse en la autoridad científica que provea conocimiento validado al Edificio?
