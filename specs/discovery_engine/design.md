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
  reporter.py      # emite leyes explicables (R7,R10)
  config_loader.py # carga cfg versionada
```
Lectura del Atlas SIN reposición de 14 años: todo viene de tablas ya pobladas
por Fase B (R1).

## Principio: comportamiento, no parámetros (D0)
`discovery_v1.yaml` contiene: mínimo de muestra, p-valor corte, frecuencia
mínima, límites de profundidad de búsqueda, semilla. El código lee el cfg;
el SDD no nombra literales.

## Reader (D1, R1,R8)
`load_episodes(asset=None)` devuelve generador de dicts con traza por barra
(price, distance, mfe, mae, state, vars) y summary. Filtra episodios con
`finished` natural o captura, y EXCLUYE variables de cierre (end_reason, mfe,
mae del resumen) del conjunto de PREDICTORES (R8): solo features hasta cada
barra son inputs válidos.

## Space (D2, R2)
Define features derivables por barra: pendientes de distance, ratios
mfe/mae acumulados, cambios de state, percentiles de volatility por activo,
buckets de velocity/violence/curve_shape del summary (estos son DESCRIPTORES
del episodio, no del desenlace futuro — se usan para particionar, no para
predecir end_reason). El espacio es el producto de features × operadores
(>,<,entre) × combinaciones lógicas. Búsqueda acotada por profundidad (cfg).

## Splitter (D3, R3)
`walk_forward(episodes)` parte por ts_open en entrenamiento (pre-2020) y
prueba (2020+). Una ley cuenta solo si hold-out supera el baseline del
 Atlantis de entrenamiento. Split versionado por año de corte.

## Falsifier (D4, R4,R6)
Para cada ley candidata: n de episodios en hold-out, tasa de REBOUND vs
baseline, diferencia, y p-valor por 1,000 permutaciones de etiquetas.
Descarte si p >= corte o n < mínimo o frecuencia < mínimo (R6).

## Miner (D5, R2,R5,R10)
Recorre el espacio (R2) generando leyes candidatas; para cada una corre
Splitter+Falsifier. Determinista (semilla cfg, R10). Umbrales desde cfg.
NO propone ley que no pase R3+R4. Acumula resultados, no sobrescribe.

## Reporter (D6, R5,R7)
Cada ley promovida se guarda como `docs/LAB_0XX_*.md` canónico con script
reproducible (R5) y bloque de métricas legibles (R7): variables, efecto, IC,
walk-forward, p, frecuencia. Se añade a feature_list y a CONSTITUCION como
ley ACUMULADA, nunca reemplazando LAB previos.

## Candados (D7, R11)
- `tests/` reusa `test_observador_no_wallclock.py` extendido a `src/discovery/`.
- Grep anti-bot en `src/discovery/` limpio.

## Trazabilidad
R1→D1 · R2→D2/D5 · R3→D3 · R4→D4 · R5→D5/D6 · R6→D4 · R7→D6 · R8→D1/D2 ·
R9→(capa Negocio futura) · R10→D5 · R11→D7
