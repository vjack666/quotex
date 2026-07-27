# Design — Discovery Engine (Minería de conocimiento del Atlas)

Trazabilidad: referencias R<n> a requirements.md.

## Paquete (`src/discovery/`, nuevo, independiente del Observador)
```
src/discovery/
  config/discovery_v1.yaml     # umbrales versionados (R: principio, sin literales)
  reader.py        # carga trazas+summary desde EpisodeStore (R1)
  space.py         # define el espacio de features explorable (R2)
  splitter.py      # walk-forward por años (R3)
  falsifier.py     # placebo + p-valor (R4)
  miner.py         # búsqueda sobre el espacio (R2,R5,R6)
  law_store.py     # escribe Leyes #N en tabla 'leyes' de la Memoria (R12)
  reporter.py      # emite LAB_0XX canónico + registro de ley (R7,R10,R12)
  config_loader.py # carga cfg versionada
```
Lectura del Atlas SIN reposición de 14 años: todo viene de tablas ya pobladas
por Fase B (R1).

## Principio: comportamiento, no parámetros (D0)
`discovery_v1.yaml` contiene: mínimo de muestra, p-valor corte, frecuencia
mínima, límites de profundidad de búsqueda, semilla, split_year, y la lista de
MERCADOS etiquetables (forex / otc). El código lee el cfg; el SDD no nombra
literales.

## Reader (D1, R1,R8)
`load_episodes(asset=None)` devuelve generador de dicts con traza por barra
(price, distance, mfe, mae, state, vars) y summary. Filtra episodios con
`finished` natural o captura, y EXCLUYE variables de cierre (end_reason, mfe,
mae del resumen) del conjunto de PREDICTORES (R8): solo features hasta cada
barra son inputs válidos. Marca cada episodio con su MERCADO (forex/otc) según
la fuente del parquet (R9b).

## Space (D2, R2)
Define features derivables por barra: pendientes de distance, ratios
mfe/mae acumulados, cambios de state, percentiles de volatility por activo,
buckets de velocity/violence/curve_shape del summary (estos son DESCRIPTORES
del episodio, no del desenlace futuro — se usan para particionar, no para
predecir end_reason). El espacio es el producto de features × operadores
(>,<,entre) × combinaciones lógicas. Búsqueda acotada por profundidad (cfg).

## Splitter (D3, R3,R9b)
`walk_forward(episodes)` parte por ts_open en entrenamiento y prueba. Una ley
cuenta solo si hold-out supera el baseline. Split versionado por año de corte.
RESPETANDO R9b: el split puede particionar también por MERCADO, de modo que una
ley se valide por separado en forex y en OTC (cuando haya datos OTC). La ley
queda etiquetada con los mercados donde pasó R3+R4.

## Falsifier (D4, R4,R6,R9b)
Para cada ley candidata: n de episodios en hold-out, tasa de REBOUND vs
baseline, diferencia, y p-valor por permutaciones de etiquetas. Descarte si
p >= corte o n < mínimo o frecuencia < mínimo (R6). Por mercado (R9b): se
reporta p y tasa POR mercado; una ley de forex no se promueve en OTC sin su
propio p<corte en datos OTC.

## Miner (D5, R2,R5,R10,R12)
Recorre el espacio (R2) generando leyes candidatas; para cada una corre
Splitter+Falsifier. Determinista (semilla cfg, R10). Umbrales desde cfg.
NO propone ley que no pase R3+R4. Acumula resultados, no sobrescribe. Al
promover, delega a law_store (R12).

## Law Store — tabla `leyes` de la Memoria (D6, R12)
`law_store.py` guarda cada ley promovida como registro estructurado:
`id (#N), name, conditions (variables+operadores), probability, confidence,
markets (forex/otc), timeframes, cases_studied, discovery_version, script_ref`.
Es la materialización de la arquitectura de 4 capas: el Laboratorio emite
CONOCIMIENTO que vive en la Memoria y que el scanner consulta por id. La tabla
`leyes` vive junto al Atlas (episodes) en la Memoria del Mercado. Acumula: una
mejora de LAB-001 nace como Ley #0XX, nunca sobrescribe la #1.

## Reporter (D7, R5,R7,R12)
Cada ley promovida se guarda como `docs/LAB_0XX_*.md` canónico con script
reproducible (R5) y bloque de métricas legibles (R7): variables, efecto, IC,
walk-forward, p, frecuencia, MERCADOS validados (R9b). Se añade a feature_list
y a CONSTITUCION como ley ACUMULADA. Además emite el registro en `leyes`.

## Candados (D8, R11,R9b)
- `tests/` reusa `test_observador_no_wallclock.py` extendido a `src/discovery/`.
- Grep anti-bot en `src/discovery/` limpio.
- Grep anti-import de `leyes`/`Memoria` desde el bot: el scanner importa
  Memoria, la Memoria NO importa el bot (unidireccional, R9b).

## Trazabilidad
R1→D1 · R2→D2/D5 · R3→D3 · R4→D4 · R5→D5/D7 · R6→D4 · R7→D7 · R8→D1/D2 ·
R9→(capa Negocio futura) · R9b→D1/D3/D4/D8 · R10→D5 · R11→D8 · R12→D6/D7
