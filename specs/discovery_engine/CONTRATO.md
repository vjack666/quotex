# CONTRATO COMPARTIDO — Discovery Engine (para agentes en paralelo)

Este archivo es la ÚNICA fuente de verdad de interfaz entre los 3 agentes que
implementan el Discovery Engine en paralelo. CUALQUIER desviación rompe el
ensamblaje. Los agentes NO deben cambiar firmas aquí definidas.

## Paquete
`C:\Users\v_jac\Desktop\QUOTEX\src\discovery\`
`C:\Users\v_jac\Desktop\QUOTEX\tests\test_discovery_*.py`

## Atlas (entrada, YA poblado — NO regenerar)
DB: `data/observador/episodes_eurusd_14y.db` (125.191 episodes, 963.996 evolution,
29.624 summary) y `episodes_eurusd_full.db` (89.832 episodes, 2.822.619 evolution).
Esquema (de `src/observador/store.py`):
- `episodes(id, asset, source, ts_open, ts_close, state_final, resolution_type,
   formula_version, confidence)`  -> source EJ: 'REPLAY:parquet:EURUSD_M1.parquet'
- `episode_evolution(episode_id, bar_index, ts, price, distance_pips, mfe, mae,
   state, vars_json, vars_version)`  -> vars_json = dict serializado (features por barra)
- `episode_summary(episode_id, quality, velocity, violence, curve_shape, symmetry,
   episode_type, duration_bars, mfe, mae, end_reason, end_confidence, finished,
   capture_limit)`  -> velocity/violence/curve_shape SON TEXT ('FAST'/'SLOW'...)

MERCADO y FUENTE se derivan del `source` (R9b):
- si contiene 'parquet' y no '_otc' -> market='forex', source='Dukascopy'
- si contiene '_otc' -> market='otc', source='Quotex OTC'
(helper en reader.py: `classify_source(source_str) -> (market, source)`)

## Reglas duras (candados)
- CERO imports a scanner/strat_fractal/bot desde src/discovery/. Grep debe quedar limpio.
- CERO time.time()/datetime.now(). Usar solo ts de los datos.
- SIN literales numéricos de umbral en el código: TODO viene de
  `config/discovery_v1.yaml` cargado por config_loader.
- Determinismo: misma entrada + misma config => mismo resultado. Usar
  `random.Random(seed)` / `numpy.random.default_rng(seed)` con seed del cfg.
- Explicabilidad (R7): toda ley promovida lleva descripción legible.

## Tipos de datos compartidos (definir en `src/discovery/types.py`)
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class Law:
    id: str                      # '#1', '#2' ...
    name: str
    conditions: str              # variables + operadores legibles
    probability: float           # tasa de REBOUND en hold-out
    confidence: str              # 'LOW'|'MEDIUM'|'HIGH' (derivada de n+p)
    markets: tuple[str, ...]     # ('forex',)
    sources: tuple[str, ...]     # ('Dukascopy',)
    timeframes: tuple[str, ...]  # ('M1','M5')
    cases_studied: int
    state: str                   # 'EXPERIMENTAL'|'VALIDADA'|'FUERTE'|'UNIVERSAL'|'OBSOLETA'  (R13)
    discovery_version: str       # 'discovery_v1'
    script_ref: str              # 'LAB_0XX_*.md'

@dataclass(frozen=True)
class Episode:
    episode_id: int
    asset: str
    market: str
    source: str
    ts_open: float
    ts_close: float
    state_final: str
    evolution: list[dict]        # filas episode_evolution (barra a barra)
    summary: dict                # fila episode_summary

@dataclass(frozen=True)
class LawRelation:
    from_law: str
    to_law: str
    relation_type: str           # 'refuerza'|'contradice'|'requiere'
    strength: float
    discovery_version: str
```

## Contratos por módulo (quién implementa qué — VER task split)
Cada agente crea SUS archivos y SUS tests. NO toca los de los otros.

### T1/T2/T3 -> Agent A
- `config/discovery_v1.yaml` (campos abajo) + `config_loader.py`
  campos yaml: min_sample, p_cut, min_freq, max_depth, seed, split_year,
  sources: [Dukascopy, Quotex OTC], markets: [forex, otc]
- `reader.py`: `load_episodes(db_path, asset=None) -> Iterator[Episode]`,
  `classify_source(source) -> (market, source)`, EXCLUYE end_reason/mfe/mae del
  summary del conjunto PREDICTOR (R8). Test: fixture DB en `tests/fixtures/` o
  usa `episodes_eurusd_14y.db` con LIMIT.
- `space.py`: `build_feature_space() -> list[FeatureSpec]`, `enumerate_features(episode)`
  respeta max_depth. FeatureSpec = dataclass(nombre, tipo, extrae(episode)->valor).
  Features por barra: distancia media, velocidad de distance, cambios de state,
  percentiles de volatility (por asset), buckets de velocity/violence/curve_shape del
  summary (descriptores, no predictor de end_reason). Test: espacio enumerado y respeta max_depth.

### T4/T5/T7 -> Agent B
- `splitter.py`: `walk_forward(episodes, split_year) -> (train, test)`, PARTICIONA
  por source cuando hay >1 (R9b). Misma semilla => mismo split. Test en fixture.
- `falsifier.py`: `evaluate(law_candidate, test_episodes, cfg) -> (n, rate, baseline,
  delta, p_value)` por SOURCE. p por permutaciones (semilla cfg). Test: ley real
  pasa, ley ruido se descarta.
- `law_store.py`: `save_law(conn, law: Law)`, `get_law(conn, law_id) -> Law`,
  `list_laws(conn)`. CREA tabla `leyes` (id TEXT PK, name, conditions, probability,
  confidence, markets TEXT, sources TEXT, timeframes TEXT, cases_studied INT,
  state TEXT, discovery_version TEXT, script_ref TEXT). Acumula, NO sobrescribe.
  `state` por defecto 'EXPERIMENTAL'. NO importa de reader/space/miner (solo tipos).

### T6/T8 -> Agent C
- `miner.py`: `discover(episodes, cfg, space, splitter, falsifier, law_store) ->
  list[Law]`. Recorre el espacio (R2), corre splitter+falsifier por fuente, NO
  promueve ley que no pase R3+R4, asigna state=EXPERIMENTAL, determina id '#N'
  (secuencial por max id existente). Al promover llama law_store.save_law.
  Determinista. Test: sobre fixture pequeño descubre "muerte del empuje" como
  candidata fuerte (debe poder reconocerla: episodios cuyo state_final es
  'DEAD_PUSH' o summary indica rebote).
- `reporter.py`: `emit_lab_doc(law, path)` genera `docs/LAB_0XX_<slug>.md` canónico
  con métricas R7 + markets + sources + state; y `record_law(law, conn)` delega a
  law_store. Test: genera doc con campos R7 y NO sobrescribe LAB-001.

### T9 (candados) -> lo hace el coordinator (no un agente) al ensamblar.
### T10 (smoke E2E) -> lo corre el coordinator tras ensamblar.
### T11/T12 (grafo + lifecycle) -> Agent B entrega `law_relations.py` +
  `relation_miner.py` y Agent C extiende reporter para lifecycle. VER split abajo.

## SPLIT FINAL DE AGENTES (para no pisarse)
- AGENT A: T1 (config), T2 (reader), T3 (space). Archivos: config/*,
  config_loader.py, reader.py, space.py + tests correspondientes.
- AGENT B: T4 (splitter), T5 (falsifier), T7 (law_store), T11 (law_relations +
  relation_miner). Archivos: splitter.py, falsifier.py, law_store.py,
  law_relations.py, relation_miner.py + tests.
  NOTA: law_store.py crea la tabla `leyes`; law_relations.py crea `law_relations`.
- AGENT C: T6 (miner), T8 (reporter), T12 (lifecycle en reporter). Archivos:
  miner.py, reporter.py + tests. reporter.py importa law_store (de B) y tipos.

Agent C DEPENDE de tipos.py (crear por A o por coordinator) y de law_store (B).
Para evitar bloqueo: coordinator crea `src/discovery/types.py` y `src/discovery/__init__.py`
AHORA (antes de lanzar), así A/B/C importan de ahí sin depender entre sí.

## Cómo probar (cada agente, antes de declarar hecho)
```
cd C:\Users\v_jac\Desktop\QUOTEX
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_discovery_<suyo>.py -q
```
Debe quedar en VERDE. Sin imports a bot. Sin time.now. Sin literales de umbral.

## DEFINICIÓN DE "muerte del empuje" para T6 (cómo reconocerla en el fixture)
Un episodio es candidato de "muerte del empuje -> rebote" si:
- summary.end_reason en ('DEAD_PUSH',) O state_final indica empuje muerto, y
- hay rebote medible (mfe>0 tras el punto de muerte, o distance_pips revierte).
El agente C define la condición INTERNA como FeatureSpec/regla y la prueba contra
el fixture; el test solo exige que el miner devuelva >=1 ley con probability>baseline.
NO se hardcodea el número 72-77% en el código (vive en el descubrimiento).
