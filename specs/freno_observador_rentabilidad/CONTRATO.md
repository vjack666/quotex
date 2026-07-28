# CONTRATO — Freno (A) / Observador (B) / Rentabilidad (C)

Lanzamiento paralelo de 3 agentes leaf. Regla sagrada: **archivos disjuntos**,
cero edición cruzada. Cada agente entrega código + su propio test verde.
NO git commit (lo hace el orquestador al ensamblar).

## Reglas duras (aplican a los 3)
- CERO import del bot: `scanner`, `strat_fractal`, `pyquotex`, `consolidation_bot`,
  `connection`, `caffeine`, `loop_utils`. El candado lo verifica el orquestador con `ast`.
- CERO reloj de pared en código fuente: no `time.time()`, no `datetime.now()`.
  (Los scripts de análisis pueden medir duración con `time.perf_counter` SOLO para
  log, pero la lógica de señal debe ser pura sobre arrays).
- Todo umbral en config YAML o parámetro de función, nunca literal mágico.
- Determinismo: semilla fija si hay random.
- Estilo: inglés en nombres de función/variable, docstrings cortos, KISS/DRY.

## Bases compartidas YA EXISTENTES (solo lectura, no editar)
- `src/marketfeed/base.py` :: `Event` (frozen dataclass), `MarketFeed` (Protocol).
  `VALID_KINDS = ['CANDLE_CLOSED','FEED_GAP','TICK']`.
- `src/strategy_lab/brake_eval.py` ::
    `compute_brake_and_rebote(open_, high, low, close, cfg) -> dict[str, np.ndarray]`
    con claves `brake_mask, impulse_net, rebote_up, rebote_dn` (bool/int arrays, len n).
    `brake_winrate(feat) -> dict(n, wr, n_up, wr_up, n_dn, wr_dn)`.
    `cfg` = `{"stochastic":{...}, "impulse":{"window":8,"min_pips":30},
             "brake":{"fwd":3,"max_advance_frac":0.10,"require_alternation":True},
             "rebote":{"fwd":3,"min_pips":8}}`.
- Datos prestados (SMC-SYSTEMS, solo lectura):
    `SRC = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")`
    `BORROWED = ROOT/"data"/"smc_borrowed"` (copia local ya poblada).
    Leer con: `df = pd.read_parquet(p); df = df.sort_values("time")`, columnas
    `open,high,low,close,time`. Limitar a `df.iloc[-200_000:]` para velocidad.
    Pares M15: EURUSD, XAUUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY.
    Resolver path: `local = BORROWED/f"{name}_M15.parquet"; smc = SRC/f"{name}_M15.parquet"; p = local if local.exists() else smc`.

## Dueño de archivos (DISJUNTO)
- Agente A (POI): `src/strategy_lab/poi_filter.py` + `tests/test_strategy_lab_poi_filter.py`
- Agente B (Observador): `specs/observador/{requirements,design,tasks}.md`
  + `src/marketfeed/recorder.py` + `tests/test_marketfeed_recorder.py`
- Agente C (Rentabilidad): `src/strategy_lab/pnl_sim.py`
  + `scripts/simular_rentabilidad_freno.py` + `tests/test_strategy_lab_pnl_sim.py`

Ningún archivo es tocado por más de un agente. Se cruza SOLO vía las bases
compartidas arriba (import read-only).

## Cómo verificar (cada agente, en su sesión)
```
cd C:/Users/v_jac/Desktop/QUOTEX
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/<su_test>.py -q
```
Debe terminar en verde. Reportar el conteo.
