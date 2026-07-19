# Requirements — maturing_zone_watchlist

> Watchlist for STRAT-F setups rejected only as **zona muy joven** (R3).
> Hold them until the M5 zone matures, re-evaluate, then admit or drop.
> Improves entry timing without lowering `STRAT_F_ZONE_MIN_AGE` globally.

## Context

Today `evaluate_strat_f` rejects with
`zona muy joven (N < STRAT_F_ZONE_MIN_AGE velas M5)` and the setup is forgotten.
Many of those zones may become valid 1–3 M5 bars later. This feature keeps them
in a **maturing watchlist**, re-checks each scan, and either:

- **shadow**: records would-be admission (no order), or
- **live**: produces a normal STRAT-F candidate when fully valid.

Does **not** change the math inside `evaluate_strat_f` age gate; maturity is
re-checked by calling the same evaluator when bars age.

## Functional requirements (EARS)

## R1 — Pure watchlist module
The system MUST provide a pure in-memory module `src/maturing_watchlist.py`
(no broker I/O) that stores maturing zone entries keyed by
`asset + direction + band` (band rounded to stable precision).

## R2 — Config modes
The system MUST support `MATURING_WATCHLIST_MODE` with values
`off` | `shadow` | `live` (default `live`).
Invalid env/config values MUST behave as `off` (fail-safe).

## R3 — Capture on R3 young reject
CUANDO STRAT-F evaluation skips an asset solely because the zone is younger
than `STRAT_F_ZONE_MIN_AGE` (skip_reason contains `zona muy joven`) AND mode
is not `off`, the system MUST upsert a maturing entry with at least:
asset, direction, band, m15_context, m5_event, fractal bars age snapshot,
payout, first_seen_ts, last_seen_ts, status=`maturing`.

## R4 — Do not capture other rejects
CUANDO skip_reason is not R3 age (e.g. M1, stoch veto, score, M15 trend),
the system MUST NOT add a maturing entry for that reason alone.

## R5 — Re-evaluate each scan cycle
CUANDO a scan evaluates an asset that has a maturing entry, the system MUST
re-run `evaluate_strat_f` (and existing post-filters: stoch help, score) with
current candles.

## R6 — Promote when fully valid
CUANDO re-evaluation yields `has_signal=True` and post-filters allow admission,
MIENTRAS mode is `live`, the system MUST create a normal STRAT-F
`CandidateEntry` (same path as immediate accepts) and mark the entry
`promoted` then remove or archive it from the active watchlist.

## R7 — Shadow promotion
CUANDO re-evaluation would admit a candidate MIENTRAS mode is `shadow`,
the system MUST record a shadow promotion (log + black-box/phase if available)
and MUST NOT create a live `CandidateEntry` for that promotion alone.

## R8 — Drop when invalid or expired
SI the zone is invalidated (evaluator skip for non-age hard fails, or age
exceeds `MATURING_WATCHLIST_MAX_AGE_BARS`, or entry older than
`MATURING_WATCHLIST_TTL_SEC`) ENTONCES the system MUST drop the entry with a
terminal reason (`expired` | `invalidated` | `ttl`).

## R9 — Caps
The system MUST enforce `MATURING_WATCHLIST_MAX_ENTRIES` (default 40) by
dropping oldest `last_seen_ts` first when over capacity.

## R10 — Hub visibility
CUANDO the hub STRAT-F panel is flushed, the system MUST expose active
maturing entries (count + rows with asset/dir/age/reason) so the operator
sees a third state beyond only accepted/rejected empty tables.

## R11 — Metrics counters
The system MUST maintain counters: captured, promoted_live, promoted_shadow,
dropped_expired, dropped_invalid (readable from bot stats or watchlist snapshot).

## R12 — No change to evaluate_strat_f age formula
The system MUST NOT modify the R3 age comparison inside `strat_fractal.py`
(`bars_since_fractal < zone_min_age`).

## R13 — Idempotent upsert
CUANDO the same asset/direction/band is seen young again, the system MUST
update `last_seen_ts` and age fields and MUST NOT create a duplicate key.

## R14 — Tests
The system MUST include unit tests for pure watchlist lifecycle and scanner
integration tests (mock evaluate) covering capture, promote live, shadow, expire.

## Non-goals

- Changing Massaniello stake math
- Multi-strategy watchlists (STRAT-A radar remains separate)
- Persistent SQLite for v1 (memory only; lost on process restart)
- Lowering global `STRAT_F_ZONE_MIN_AGE` as the primary solution
