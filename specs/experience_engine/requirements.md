# Requirements — Experience Engine (Market Memory)

> **Feature ID:** 27
> **Status:** spec_ready
> **Depends on:** Feature 18 (Entry Intelligence Agent) — es el primer lector
> **Concepto aprobado:** `docs/experience_engine_concept.md`

---

## Contexto / Alcance (Ruben 2026-07-24)

El proyecto deja de construir "detectores" (reglas que deciden qué es un soporte,
una resistencia, un FVG, un order block). Pasa a construir **memoria del mercado**:
un Experience Engine que adquiere una EXPERIENCIA del mercado en cada cambio
relevante y la DISTRIBUYE a las IAs, que solo leen. Ninguna IA escribe en la memoria
ni modifica la captura.

Unidad de información = **arco de experiencia** (contexto previo → evento →
evolución → resultado → consecuencias), NO un snapshot fotográfico. Esto hace la
memoria reutilizable: cualquier IA futura lee el arco completo y pregunta lo que
quiera, sin que hayamos anticipado su pregunta al capturar.

El conocimiento NO se programa: nace de relacionar los datos de la experiencia con
lo que ocurrió después. El sistema NO sabe por qué una zona funcionó; solo sabe que
experiencias con cierto perfil terminaron en +N pips el X% de las veces.

**Restricción (decisión del usuario):** CERO reglas hardcoded de detección. No
"3 toques → soporte", no "FVG → zona", no "Order Block → entrar", no decaimiento
por heurística (`_DECAY_TABLE`), no tablas separadas por tipo de detector
(`reaction_zones`, `expired_zones` con rol hardcoded). El modelo descubre esas
relaciones.

---

## R1 — Adquisición de experiencia en cada cambio relevante

CUANDO el mercado cambia de estado de forma relevante (reacción en un nivel,
ruptura, entrada del scanner, cierre de trade, invalidación de estructura), el
sistema DEBE adquirir un arco de experiencia completo y escribirlo en la memoria
única.

---

## R2 — Estructura del arco de experiencia

EL arco de experiencia DEBE contener, como mínimo: contexto previo, evento,
evolución posterior, resultado medible, y consecuencias de segundo orden. El arco
DEBE poder reconstruirse íntegro desde la memoria (no solo el punto del evento).

---

## R3 — Memoria única (sin silos)

EL sistema DEBE almacenar TODAS las experiencias en una ÚNICA fuente de memoria.
NO DEBE crear tablas separadas por tipo de detector (soportes, FVG, zonas,
patrones, momentum). Cualquier IA futura SE DEBE poder entrenar desde esa memoria
única sin re-capturar ni re-estructurar datos.

---

## R4 — Las IAs solo leen

MIENTRAS una IA consulta la memoria, el sistema DEBE garantizar que la IA SOLO
LEE. Ninguna IA DEBE escribir en la memoria ni modificar la captura ni otra IA.
Una IA publica su salida (Confidence Score / distribución) hacia afuera, no hacia
la memoria.

---

## R5 — Modo activo del Engine

CUANDO ocurre en vivo una experiencia similar a experiencias previas de la memoria,
el sistema DEBE distribuir la experiencia relevante a las IAs conectadas para que
reaccionen con un Confidence Score (o distribución). El engine empuja; las IAs no
van a buscar.

---

## R6 — Feature 18 como primer lector

CUANDO el Experience Engine existe, EL sistema DEBE permitir que el Entry
Intelligence Agent (F18) se re-entrene desde la memoria única leyendo el arco de
experiencia de cada entrada, SIN cambiar su contrato de emisión de Confidence Score.

---

## R7 — Observación sin juicio

EL sistema DEBE registrar el contexto previo y la evolución posterior TAL CUAL
ocurrieron (precio, estructura, indicadores, horario, correlación, pips recorridos,
tiempo a invalidación), sin etiquetar la experiencia como "soporte" o "resistencia"
en el momento de la captura. La etiqueta la descubre el modelo, no el capturador.

---

## R8 — Reentrenamiento de IAs desde la memoria

CUANDO una IA se reentrena, EL sistema DEBE alimentarla exclusivamente desde la
memoria única. El schema de captura NO DEBE cambiar para acomodar una IA nueva.

---

## R9 — Ausencia de reglas de detección

EL sistema NO DEBE contener lógica que decida por regla si un nivel "es" soporte o
resistencia, si un FVG "es" válido, o si un Order Block "es" entrada. Esas
clasificaciones son salida de las IAs, no del capturador.

---

## R10 — Ingesta post-trade (evolución + resultado + consecuencias)

CUANDO un trade se resuelve, EL sistema DEBE completar el arco de la experiencia
de esa entrada con: pips recorridos, estructura rota o no, tiempo a invalidación,
y resultado WIN/LOSS. La experiencia queda cerrada y reutilizable.

---

## R11 — Tests de la memoria

Los tests DEBEN cubrir: adquisición de un arco completo (mock de mercado),
reconstrucción íntegra del arco desde la memoria, que dos IAs distintas leen la
misma memoria sin que ninguna la escriba, modo activo (inyección de experiencia
similar dispara distribución a la IA), y que F18 se re-entrena desde la memoria sin
cambiar su contrato.

---

## R12 — Sin tocar el bot hasta aprobar implementación

MIENTRAS la feature esté en `spec_ready`, el sistema NO DEBE modificar el bot en
vivo ni crear tablas de producción. La implementación (elegida tras esta puerta)
se hace tras aprobación humana.
