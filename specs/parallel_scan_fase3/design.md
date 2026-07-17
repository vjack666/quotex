# Design — parallel_scan_fase3 (OPCIÓN 1: solo STRAT-F al pool)

## Decisión (modo plan, usuario)
Extraer SOLO el bloque STRAT-F del `for` de `_scan_phase_evaluate_assets` a un
ProcessPool. STRAT-A, momentum, swing y order-block QUEDAN en el loop serial,
SIN tocar su código. Esto es seguro: no se reescribe la máquina A (estable en
vivo) y se libera el loop del cómputo pesado de STRAT-F (`evaluate_strat_f` +
`compute_stoch` + `apply_stoch_help`).

## Por qué es canónico y no un atajo
STRAT-F y STRAT-A están en el mismo `for`, pero STRAT-F USA las velas 5m CRUDAS
(`candles_5m_by_asset[sym]`), NO el zone/ma_state que calcula STRAT-A después.
Por tanto el bloque F es autónomo respecto a A: se puede extraer sin mover A.
La teoría de A NO está "guardada" para F; F solo recicla las velas 5m que ya
están en memoria. El loop prepara el "plato" (velas) y F lo procesa en paralelo.

## Frontera de la función pura (solo bloque F)
`_evaluate_strat_f_serial(ctx: StratFEvalContext) -> StratFEvalResult`
(module-level, SIN `self`, picklable). El loop itera los activos, y para cada
uno que llega al bloque F envía `ctx` al pool vía `run_in_executor`, recopila
con `asyncio.gather(..., return_exceptions=True)`.

### StratFEvalContext (dataclass picklable) — ENTRADA
- `sym: str`, `payout: int`
- `candles_5m: list`, `candles_1m: list`, `candles_15m: list`
- `strat_f_only_mode: bool`
- `flags`: STRAT_A_ONLY, STRAT_F_ENABLED, MIN_PAYOUT, STOCH_HELP_MODE, MATURING_WATCHLIST_MODE
- `maturing_snapshot: MaturingSnapshot` (active entries por sym/dir para decidir
  promote/drop/upsert; el worker devuelve OPS, el loop las aplica)
- `bb_scan_id: str`, `session_id: str` (para grabar en caja negra en el LOOP)

### StratFEvalResult (dataclass) — SALIDA (todo lo que hoy muta el bloque F)
- `f_candidate: Optional[CandidateEntry]` (None si no hay señal)
- `reject_counts_delta: dict[str, int]`
- `strat_f_batch_delta: list[dict]` (los `_rec` para `_batch[0]`/`_batch[1]`)
- `strat_f_accepts: int` (0 o 1)
- `black_box_record: Optional[dict]` (el loop lo graba con `_bb.record_candidate`)
- `black_box_cid: Optional[int]` (para vincular a f_candidate en el loop)
- `maturing_ops: list[tuple[str, tuple]]` (("upsert_young", args), ("drop", ...),
  ("mark_promoted", ...)) — el loop las aplica en `bot.maturing_watchlist`
- `logs: list[str]` (mensajes que hoy hace `log.info`/`asset_detail`; el loop los
  re-emite para no perder trazabilidad)

## Lo que QUEDA en el loop (serial, sin tocar)
- Filtros de estado (trades/greylist/blacklist/failed).
- momentum / swing / order-block.
- STRAT-A tail completo (`detect_consolidation` → `evaluate_strat_a` → side-effects).
- Aplicación de deltas del bloque F: `candidates.append`, `reject_counts.update`,
  `_batch` extend, `_bb.record_candidate`, `maturing_watchlist` ops, `log` re-emit.

## Riesgos / mitigaciones
- **Regresión STRAT-F en vivo**: TDD estricto. RED: test que graba el
  comportamiento del bloque F serial actual (mismos `f_candidate`, mismos
  `reject_counts`, misma caja negra grabada). GREEN: extraer a
  `_evaluate_strat_f_serial` sin pool, el test sigue verde. Luego conectar pool.
- **Pickling**: velas son dataclasses/listas nativas → picklables.
  `CandidateEntry`, `MaturingSnapshot` deben ser picklables (tipos nativos).
- **Caja negra en otro proceso**: NO se graba en el worker. El worker devuelve
  `black_box_record` y el loop lo graba con `_bb.record_candidate` en el MISMO
  orden que hoy (iterando activos en orden).
- **maturing_watchlist en otro proceso**: el worker no lo muta; devuelve
  `maturing_ops` y el loop las aplica.

## Alternativas descartadas
- Refactor de TODO el monolito (opción A original): riesgo desproporcionado a
  STRAT-A en vivo; el usuario eligió acotar a F.
- "Opción B" (solo detect_*): el bloque F no separa detect de estado → inviable.
- Multiagentes para escribir el refactor: prohíbe la regla de hierro (2º motor /
  ambigüedad). Alcance ya acotado → lo hace el implementer principal con TDD.
