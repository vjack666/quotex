# Requirements — Discovery Engine (Minería de conocimiento del Atlas)

Feature: discovery_engine
Capa: 2.5 (sobre el Atlas / Observador Fase B). Lee episodios YA grabados
(trazas + summaries) y EMITE LEYES (#N) como conocimiento de la Memoria del
Mercado. NO decide, NO opera, NO toca el feed, NO toca el bot. Cambio de
paradigma (Ruben 2026-07-27): el Laboratorio confirmaba "¿mi hipótesis
funciona?"; el Discovery Engine pregunta "Mercado, ¿qué leyes escondes?". El
motor BUSCA, no confirma.

Documentos rectores: `docs/FILOSOFIA.md` (falsación, acumular no borrar),
`docs/PTM_V3.md`, `docs/CONSTITUCION_REBOTE.md`, specs/observador_fase_b/,
`progress/ARQUITECTURA_2GEN.md` (arquitectura de 4 capas + nota forex/OTC +
refinamientos de diseño).

## Principio rector (heredado de Fase B)
> EL SDD DEFINE COMPORTAMIENTO, NO PARÁMETROS. Los umbrales de significancia,
> cortes de rama, mínimos de muestra y definiciones de "ley candidata" viven
> en config versionada bajo `discovery/config/` y los valida el Atlas. Ningún
> literal numérico en este documento.

## Requisitos funcionales

**R1 — Entrada es el Atlas, no el mercado.** El motor DEBE leer desde
`EpisodeStore` (Fase A) y las tablas `episode_evolution` / `episode_summary`
(Fase B): trazas completas + snapshots. NUNCA consume feed en vivo ni
re-reproduce 14 años. (Eficiencia: el costo de cómputo ya se pagó al grabar.)

**R2 — Espacio de hipótesis abierto.** El motor DEBE poder explorar combinaciones
de variables ya grabadas (pressure/energy/continuity/volatility/spread por barra
+ campos del summary: quality, velocity, violence, curve_shape, symmetry,
duration_bars, mfe, mae, end_reason, finished) SIN que el humano las liste
una por una. Búsqueda automática sobre el espacio de features. El espacio TAMBIÉN
incluye variables derivadas de INDICADORES descompuestos en primitivas (ej.
geometría del estocástico: posición %K, %D, distancia(K,D), ángulo %K/%D,
velocidad de apertura, tiempo desde cruce, máximo/mínimo alejamiento, distancia a
niveles 20/50/80, pendiente media, aceleración) de modo que pueda descubrir leyes
como "Ley #34: geometría óptima del estocástico → X% de continuación" que luego
el Strategy Lab CONSUME como paso (ver specs/strategy_lab/).

**R3 — Split temporal obligatorio.** Toda ley candidata DEBE validarse
walk-forward: se descubre en años de entrenamiento y se confirma en años
vírgenes. Una señal que no sobrevive el split se descarta. Hereda LAB-001.

**R4 — Placebo / falsación.** Toda ley candidata DEBE compararse contra
barajados de desenlace (permutaciones) con p-valor. Solo se promueve si
p < umbral versionado. Hereda LAB-001.

**R5 — Reproducibilidad y versionado.** Cada ley descubierta DEBE guardarse
como experimento canónico (script + resultado) con su `discovery_version`.
Las leyes NO reemplazan LAB previos: se ACUMULAN. Una mejora de una ley
existente nace como nueva entrada (LAB-0XX), nunca sobrescribe.

**R6 — Significancia mínima por muestra.** El motor NO DEBE reportar leyes con
muestra bajo el mínimo versionado, ni con frecuencia de señal no-tradeable
(umbral versionado; ej. señales/día mínimo por vehículo).

**R7 — Explicabilidad.** Toda ley promovida DEBE emitir: descripción legible
(variables + operadores), tamaño de efecto, intervalo, walk-forward por época,
p-valor, y frecuencia estimada. No se aceptan "cajas negras sin interpretar".

**R8 — Sin fuga de información (look-ahead).** El motor NO DEBE usar en el
descubrimiento ninguna variable calculada con conocimiento del desenlace
(end_reason, mfe/mae ya son del FUTURO del episodio). Explora solo features
disponibles AL MOMENTO de cada barra de la traza. (El summary es metadata de
cierre; usarlo como PREDICTOR está prohibido — es el desenlace.)

**R9 — Agnóstico al vehículo.** El motor descubre propiedades del episodio, no
de binarias/FX. La traducción a vehículo queda en la capa de Negocio (futura).

**R9b — Candado Mercado Y FUENTE (de `ARQUITECTURA_2GEN.md`).** El Atlas actual
está entrenado SOLO con datos FOREX (+ oro) de Dukascopy; el bot opera forex Y
OTC. El motor DEBE etiquetar cada ley con los MERCADOS y las FUENTES concretas
en las que fue validada (ej. Dukascopy, Quotex OTC, Broker X, IC Markets). Dos
brokers OTC pueden comportarse distinto: la ley queda validada para la FUENTE
donde se demostró, NO para "OTC" en general. El motor DEBE poder correr por
separado sobre una fuente OTC cuando exista. El scanner solo podrá consultar
"¿Ley #N validada en esta fuente?" y la Memoria contesta sí/no POR FUENTE. Una
ley de una fuente NO se promueve como válida en otra hasta no pasar R3+R4 sobre
datos de esa otra fuente. (Evita aplicar leyes no validadas al setup OTC.)

**R10 — Determinismo.** Misma entrada + misma config => mismas leyes. Semilla
de barajado versionada.

**R11 — Sin reloj de pared / sin bot.** No usa time.time()/datetime.now(); no
importa scanner/strat_fractal (candados reusados).

**R12 — Emite LEYES (#N) como objeto de la Memoria.** El motor NO emite texto
suelto ni código. Cada ley promovida DEBE materializarse como un registro
estructurado con id `#N`, nombre, condiciones (variables+operadores),
probabilidad, confianza, mercados, fuentes, timeframes y casos estudiados, y
DEBE guardarse en la tabla `leyes` de la Memoria del Mercado (junto al Atlas de
episodios). El scanner del futuro consulta por id (#N) con un sí/no. Esto es
el aporte central de la arquitectura de 4 capas: el laboratorio genera
CONOCIMIENTO reutilizable para máquinas, no documentos para humanos.

**R13 — Ciclo de vida de la ley.** Toda ley DEBE llevar un `state` que evoluciona
con la evidencia acumulada: EXPERIMENTAL → VALIDADA → FUERTE → UNIVERSAL →
OBSOLETA. Una ley NUNCA se borra: solo cambia de estado (conserva el historial
científico y el grado de evidencia). Las transiciones de estado se registran
con su `discovery_version` y motivo. El scanner consulta el estado para decidir
el peso de la ley, no su existencia.

**R14 — Grafo de conocimiento (relaciones entre leyes).** La Memoria DEBE admitir
RELACIONES dirigidas entre leyes: `refuerza`, `contradice`, `requiere` (con
fuerza y versión). Esto convierte la Memoria en un GRAFO, no solo una tabla. El
scanner DEBE poder preguntar "¿qué leyes apoyan esta situación?" (consulta por
relaciones) además de "¿existe la Ley #N?" (consulta por id). El motor puede
proponer relaciones nuevas entre leyes ya existentes (acumulando estructura).

## Relación con el resto
- Consume la SALIDA de Fase B (películas + summaries). Depende de que el
  backfill de 14 años esté poblado.
- Las leyes que descubra alimentan (no reescriben) CONSTITUCION_REBOTE.md y la
  tabla `leyes` de la Memoria.
- Es el paso 3 del nuevo orden de Rubén: tras LAB-001 congelado y Fase B, antes
  del motor de trading y del puente scanner→Memoria.
- Respeta la arquitectura de 4 capas (Laboratorio → Memoria → Estrategas): el
  Discovery Engine es el Laboratorio; la tabla `leyes` + grafo es la Memoria;
  el scanner futuro solo consulta. Las 5 responsabilidades (Laboratorio observa,
  Discovery descubre, Memoria recuerda, Scanner consulta, Estrategia decide) se
  mantienen separadas para que cada pieza evolucione sin romper las demás.
