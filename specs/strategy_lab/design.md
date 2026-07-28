# Design — Strategy Lab (Laboratorio de estrategias)

Trazabilidad: referencias SL-R<n> a requirements.md.

## Paquete (`src/strategy_lab/`, nuevo, independiente)
```
src/strategy_lab/
  config/strategy_lab_v1.yaml  # umbrales versionados (sin literales)
  strategy_parser.py  # descompone estrategia propuesta en pasos (SL-R2)
  variant_searcher.py # orden/inclusión/umbrales, acotado (SL-R3,R10)
  backtester.py       # mide edge walk-forward sobre velas M15 (SL-R4)
  ablator.py          # importancia por ablation (SL-R6,R7)
  falsifier.py        # placebo + p-valor por paso (SL-R5)
  orderer.py          # compara secuencias alternativas (SL-R8)
  optimizer.py        # orquesta: descubre variante óptima (SL-R3..R9,R13)
  strategy_store.py   # emite estrategia optimizada como objeto (SL-R9,R12)
  feature_calc.py     # estocastico(14,3,3)+impulso/freno/POI/rebote desde OHLC (SL-R14)
  config_loader.py    # carga cfg versionado
```
Lectura de datos SIN reposición de 14 años: todo viene de velas M15 vía Market Replay
Engine (ParquetSource read-only sobre data/smc_borrowed/EURUSD_M15.parquet, prestado de
SMC-Dukascopy). La Memoria se lee en modo SOLO LECTURA (SL-R12); el Atlas se usa solo
como referencia de leyes, no como datos de backtest (carece de estocástico/M15).

## Principio: comportamiento, no parámetros (SD0)
`strategy_lab_v1.yaml` contiene: min_contribution, p_cut, min_sample, max_depth,
seed, split_year. El código lee el cfg; el SDD no nombra literales.

## Strategy Parser (SD1, SL-R2,SL-R12)
`parse_strategy(proposed)` devuelve lista de pasos; cada paso es predicado sobre
features del episodio o referencia a Law #N (id). Valida que toda referencia
exista en la Memoria (consulta `leyes` en lectura). Rechaza pasos con ley
inexistente.

## Variant Searcher (SD2, SL-R3,R10)
Genera variantes: permutaciones de orden (acotadas), subconjuntos de pasos
(inclusión/exclusión), umbrales de filtro por paso. Determinista (semilla cfg).
Acotado por max_depth (cfg). Respeta SL-R13: solo variantes de la propuesta.

## Backtester (SD3, SL-R4)
`score_variant(variant, episodes)` aplica la secuencia de pasos como filtros sobre
los episodios del Atlas y mide tasa de REBOUND / edge walk-forward (entrenamiento
vs hold-out). Reusa el `splitter` de Discovery (mismo estándar R3).

## Ablator + Falsifier (SD4, SL-R5,R6,R7)
Para cada paso: `ablation` (quitar paso → Δedge) da importancia; `falsifier`
(permutar etiquetas) da p-valor. Paso con contribución < min_contribution o
p >= corte se marca para ELIMINACIÓN (SL-R7). Responde "¿qué parte sobra?".

## Orderer (SD5, SL-R8)
Compara secuencias alternativas (A/B/C) por edge walk-forward; reporta la mejor.
Responde "¿qué orden es óptimo?" por evidencia, no por intuición.

## Optimizer (SD6, SL-R3..R9,R13)
Orquesta: parse → search variantes → backtest → ablation/falsify → elimina
inútiles → ordena → emite estrategia óptima. Acumula resultados. Respeta SL-R13
(solo variantes de la propuesta). Une las respuestas: ¿en qué leyes se apoya?
¿qué aporta más? ¿qué sobra? ¿qué filtros mejoran la probabilidad?

## Strategy Store — estrategia optimizada (SD7, SL-R9,R12)
`strategy_store.py` emite la estrategia optimizada como objeto estructurado:
`id, steps_ordenados, law_refs, importance_por_paso, contribution_por_paso,
edge_walkforward, p_valor, sources, markets`. Se guarda como artefacto legible
(`docs/STRAT_OPT_*.md`) y opcionalmente en tabla `strategies` de la Memoria (solo
lectura para la capa Estrategia). NO escribe leyes (SL-R12).

## Candados (SD8, SL-R11,R12)
- `tests/` reusa `test_observador_no_wallclock.py` extendido a `src/strategy_lab/`.
- Grep anti-bot en `src/strategy_lab/` limpio.
- Grep unidireccional: `strategy_lab` importa Memoria (lectura); la Memoria NO
  importa `strategy_lab`.

## Trazabilidad
SL-R1→SD1/SD3 · SL-R2→SD1 · SL-R3→SD2/SD6 · SL-R4→SD3 · SL-R5→SD4 · SL-R6→SD4 ·
SL-R7→SD4 · SL-R8→SD5 · SL-R9→SD7 · SL-R10→SD2 · SL-R11→SD8 · SL-R12→SD1/SD7/SD8 ·
SL-R13→SD2/SD6
