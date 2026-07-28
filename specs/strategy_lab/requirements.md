# Requirements — Strategy Lab (Laboratorio de estrategias)

Feature: strategy_lab
Capa: 2.6 (por encima del Discovery Engine; consume la Memoria). Toma una
estrategia PROPUESTA por Rubén, la descompone en pasos elementales, prueba
miles de variantes (orden, filtros, inclusión/exclusión), elimina los pasos que
no aportan, ordena por importancia estadística y DEVUELVE la versión óptima
basada en evidencia. NO inventa estrategias nuevas: perfecciona la propuesta.
NO opera, NO toca el feed, NO toca el bot. Cambio conceptual (Ruben 2026-07-27):
el Discovery responde "¿qué leyes existen en el mercado?"; el Strategy Lab
responde "¿cómo se comporta mi estrategia frente a esas leyes?".

Documentos rectores: `docs/FILOSOFIA.md`, `docs/PTM_V3.md`,
`docs/CONSTITUCION_REBOTE.md`, specs/discovery_engine/,
specs/observador_fase_b/, `progress/ARQUITECTURA_2GEN.md`.

## Principio rector
> EL SDD DEFINE COMPORTAMIENTO, NO PARÁMETROS. Umbrales de contribución, cortes
> de importancia, mínimos de muestra y definición de "paso" viven en config
> versionada bajo `strategy_lab/config/`. Ningún literal numérico en este doc.

## Requisitos funcionales

**SL-R1 — Entrada es estrategia + Memoria + datos de velas, no el mercado vivo.** El
motor DEBE leer la estrategia propuesta (como lista de pasos), la tabla `leyes` de la
Memoria y DATOS DE VELAS (OHLC) vía el Market Replay Engine en modo READ-ONLY. NUNCA
consume feed en vivo ni re-reproduce 14 años. Nota: el Atlas (episodios con estados
QUIET/EXPANSION/PRESSURE/BRAKE) NO trae estocástico ni granularidad M15, por lo que la
fuente de backtest del Strategy Lab son las VELAS CRUDAS (ej. EURUSD M15 14y prestada
de SMC-Dukascopy), no el Atlas. El Atlas/Memoria se usan como REFERENCIAS de leyes, no
como datos de backtest.

**SL-R2 — Descomposición en pasos elementales.** Cada paso DEBE ser un predicado
sobre features del episodio o una REFERENCIA a una Ley #N de la Memoria. El motor
descompone la estrategia propuesta en pasos atómicos y valida que toda referencia
a ley exista en la Memoria.

**SL-R3 — Búsqueda de variantes.** El motor DEBE poder probar combinaciones de:
orden de los pasos, inclusión/exclusión de cada paso, y umbrales de filtro de cada
paso. Búsqueda acotada por profundidad (cfg). Determinista (semilla).

**SL-R4 — Split temporal obligatorio.** Toda variante DEBE medirse walk-forward
(entrenamiento vs años vírgenes). Una variante que no sobrevive el split se
descarta. Hereda estándar LAB-001 / Discovery Engine.

**SL-R5 — Placebo / falsación por paso.** La contribución de cada paso DEBE
medirse contra etiquetas barajadas (permutaciones) con p-valor. Solo se retiene
un paso con p < corte versionado.

**SL-R6 — Atribución de importancia (ablation).** El motor DEBE medir la
contribución de cada paso mediante ablation: eliminar el paso y cuantificar la
caída de edge. Reporta importancia por paso (cuánto aporta cada condición).

**SL-R7 — Eliminación de pasos inútiles.** El motor NO DEBE retener pasos cuya
contribución esté bajo el mínimo versionado. Los descarta de la versión óptima
("¿qué parte sobra?").

**SL-R8 — Optimización de orden.** El motor DEBE poder comparar secuencias
alternativas (ej. impulso→estocástico vs estocástico→impulso vs
impulso→liquidez→estocástico) y reportar cuál tiene mayor tasa de acierto
walk-forward. El orden óptimo se DESCUBRE, no se asume.

**SL-R9 — Salida es estrategia optimizada (objeto).** El motor DEBE emitir una
estrategia optimizada como objeto estructurado: pasos ordenados, predicados/leyes
referenciadas, importancia por paso, contribución por paso, edge walk-forward,
p-valor, y fuentes/mercados donde aplica. NO emite código ni ejecuta operaciones.

**SL-R10 — Determinismo.** Misma entrada + misma config => misma estrategia óptima.
Semilla de barajado versionada.

**SL-R11 — Sin reloj de pared / sin bot.** No usa time.time()/datetime.now(); no
importa scanner/strat_fractal (candados reusados).

**SL-R12 — Solo LEE la Memoria, no la escribe.** El Strategy Lab consulta las Leyes
#N (y el grafo) de la Memoria; NO crea ni modifica leyes (eso es del Discovery
Engine). Unidireccional: Strategy Lab → Memoria (lectura). La Memoria NO importa
Strategy Lab.

**SL-R13 — No inventa estrategias.** El motor SOLO perfecciona la estrategia
PROPUESTA; el alcance está acotado a variantes de esa estrategia, no a estrategias
nuevas. "Perfecciona la tuya, asigna prioridades, descarta filtros inútiles,
cuantifica cuánto aporta cada condición."

**SL-R14 — Primitivas calculadas desde velas (feature_calc).** El motor DEBE poder
calcular features desde OHLC M15 para descomponer la estrategia propuesta en
primitivas atómicas y verificables: (a) estocástico Full (14,3,3) como "reloj" que
marca el momento del freno; (b) impulso = recorrido neto de cuerpos de N velas en
una dirección; (c) freno = achique de cuerpos + alternancia de signo tras el pico
(criterio LAB-001: avance chico + <10% del pico + velas alternadas); (d) POI/zona =
nivel de reversión; (e) rebote = reversión de >=M pips en las K velas tras la señal.
Estas primitivas son PREDICADOS sobre velas, no sobre estados del Atlas. La definición
operativa de cada una (N, M, K, umbrales de "chico"/"alternado") vive en
config/strategy_lab_v1.yaml, no en código.

## Relación con el resto
- Consume SALIDA de Discovery Engine (leyes en Memoria) + Atlas (episodios).
- Su salida (estrategia optimizada) alimenta la capa de Estrategia/Bot (futura),
  vía el Scanner como consultor.
- Es el paso 4 del nuevo orden: tras Discovery Engine (paso 3), antes del puente
  scanner→Memoria y del motor de trading.
- Mantiene la separación de 6 responsabilidades: Laboratorio (observa), Discovery
  (descubre leyes), Memoria (recuerda), Strategy Lab (perfecciona estrategia),
  Scanner (consulta), Estrategia (decide).
