# Design — maturing_zone_watchlist

## Goal

Hold STRAT-F **R3 young zones** until they mature, re-evaluate with the same
quality stack, then either shadow-log or admit as a normal candidate.

## Skills that inform this design

| Skill | Use |
|-------|-----|
| `cognitive-doc-design` | Spec shape, progressive disclosure |
| `sdd-spec` / `sdd-design` / `sdd-tasks` | EARS + design + task checklist |
| `work-unit-commits` | Keep implementation reviewable |
| Project skill `maturing-zone-watchlist` | Agent rules for future edits |

## Non-negotiables

1. **Do not edit** age logic inside `src/strat_fractal.py`.
2. Capture **only** skip reasons matching R3 young (`zona muy joven`).
3. Default mode **`live`** (user wants deferred real entries); `shadow` for measure-only; `off` disables.
4. No new third-party dependencies.
5. v1 store is **in-memory** on the bot (restart clears).

## Architecture

```
scanner STRAT-F block
  evaluate_strat_f(...)
       │
       ├─ has_signal → stoch help → candidate (unchanged)
       ├─ skip "zona muy joven" + mode≠off
       │       └─► MaturingWatchlist.upsert(...)
       └─ other skip → reject batch (unchanged)

  end of asset loop / start of next scan for watched assets:
       for entry in watchlist.active():
           re-evaluate_strat_f + stoch + score
             ├─ young still → keep
             ├─ full OK + live → CandidateEntry + mark promoted
             ├─ full OK + shadow → metrics only
             └─ hard fail / max age / TTL → drop

  _flush_strat_f_panel
       accepted / rejected / maturing (new)
```

Layer: **Análisis** (scanner orchestration) + pure **Soporte** (`maturing_watchlist.py`).

## Files

### Create

| Path | Role |
|------|------|
| `src/maturing_watchlist.py` | `MaturingEntry`, `MaturingWatchlist` pure store |
| `tests/test_maturing_watchlist.py` | Lifecycle unit tests |
| `tests/test_maturing_watchlist_scanner.py` | Scanner wire mocks |
| `specs/maturing_zone_watchlist/*` | This SDD |
| `.claude/skills/maturing-zone-watchlist/SKILL.md` | Project agent skill |

### Modify

| Path | Change |
|------|--------|
| `src/config.py` | Mode, max age bars, TTL sec, max entries |
| `src/scanner.py` | Capture R3; re-eval watchlist; flush maturing |
| `src/consolidation_bot.py` | Own `maturing_watchlist` instance on bot |
| `hub/strat_f_state.py` | Optional `maturing` list field |
| `hub/strat_f_panel.py` | Accept maturing rows in `record_strat_f` |
| `hub/static/index.html` | Small "Madurando" card/count |
| `feature_list.json` | Feature #11 |

### Do not touch

- `src/strat_fractal.py` R3 formula
- Massaniello / executor stake path (candidates only)

## Public API (`maturing_watchlist.py`)

```python
@dataclass
class MaturingEntry:
    asset: str
    direction: str          # CALL | PUT
    band: float
    m15_context: str
    m5_event: str
    bars_age: int
    payout: int
    first_seen_ts: float
    last_seen_ts: float
    status: str             # maturing | promoted | dropped
    drop_reason: str = ""

class MaturingWatchlist:
    def __init__(self, *, max_entries: int, max_age_bars: int, ttl_sec: float): ...
    def make_key(asset, direction, band) -> str: ...
    def upsert_young(...) -> MaturingEntry: ...
    def get(key) -> MaturingEntry | None: ...
    def active(self) -> list[MaturingEntry]: ...
    def mark_promoted(key) -> None: ...
    def drop(key, reason: str) -> None: ...
    def expire_stale(now: float, *, bars_by_key: dict | None) -> list[MaturingEntry]: ...
    def snapshot(self) -> dict:  # entries + counters
```

## Config defaults

| Key | Default | Meaning |
|-----|---------|---------|
| `MATURING_WATCHLIST_MODE` | `live` | off / shadow / live |
| `MATURING_WATCHLIST_MAX_AGE_BARS` | `12` | drop if still not valid after 12 M5 bars past min age path |
| `MATURING_WATCHLIST_TTL_SEC` | `3600` | hard wall clock TTL |
| `MATURING_WATCHLIST_MAX_ENTRIES` | `40` | capacity |

Env override: `MATURING_WATCHLIST_MODE`.

## Detecting R3 young

```python
def is_r3_young_skip(reason: str | None) -> bool:
    if not reason:
        return False
    r = reason.lower()
    return "zona muy joven" in r or "zone too young" in r
```

Do not parse bars from the string for gate decisions; re-call evaluator.

## Promotion path

1. Entry active and asset still in open list with candles.
2. `evaluate_strat_f(...)` → `has_signal`.
3. Existing stoch help (if hard veto → drop as invalidated stoch).
4. `score_candidate` as today.
5. If live: append `CandidateEntry` with `_strategy_origin='STRAT-F'` and tag
   `_maturing_promoted=True` (optional attr for logs).
6. Counters + remove from active map.

## Hub

- Extend panel state with `maturing: list[{asset, direction, bars_age, band, status}]`.
- UI: compact table or count badge "⏳ Madurando N".
- Root snapshot mirrors maturing like accepted (server already prefers bot panel).

## Risks

| Risk | Mitigation |
|------|------------|
| Memory growth | max entries + TTL |
| Double candidates | key uniqueness; remove on promote |
| Process restart loss | accepted for v1; doc non-goal |
| Too many promotions | same Massaniello / diversifier as normal |

## Testing strategy

- Pure: upsert, promote, expire max age, TTL, cap eviction, R3 detector.
- Scanner: mock evaluate sequence young → young → valid → candidate in live;
  shadow no candidate; off no capture.

## Traceability

| R | Primary test |
|---|--------------|
| R1–R4, R8–R9, R11, R13 | `test_maturing_watchlist.py` |
| R5–R7, R12, R14 | `test_maturing_watchlist_scanner.py` |
| R10 | panel flush unit or hub strat_f test extend |
