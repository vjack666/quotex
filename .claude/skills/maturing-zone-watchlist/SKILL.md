---
name: maturing-zone-watchlist
description: "Trigger: maturing zones, zona muy joven, deferred STRAT-F entry, watchlist R3, pending setup promote. Rules for the maturing zone watchlist feature."
---

# Maturing Zone Watchlist

## When to use

Any change touching:

- `src/maturing_watchlist.py`
- scanner capture of `zona muy joven`
- deferred STRAT-F promotion
- hub "Madurando" panel

## Hard rules

1. **Never** change the R3 age comparison inside `src/strat_fractal.py`.
2. Capture **only** R3 young skips (`zona muy joven` / `zone too young`).
3. Re-admit only through full `evaluate_strat_f` + existing stoch/score path.
4. Modes: `off` | `shadow` | `live` — invalid → `off`.
5. v1 store is **in-memory**; do not invent SQLite unless a new SDD says so.
6. Enforce max entries, max age bars, and TTL on every maintenance pass.
7. Key = `asset|direction|band` (stable band rounding).

## Architecture reminder

```
R3 young → upsert watchlist
each scan → re-evaluate
  live + valid → CandidateEntry + drop active
  shadow + valid → metrics only
  invalid/expired → drop
```

## Tests required

- `tests/test_maturing_watchlist.py`
- `tests/test_maturing_watchlist_scanner.py`

## Spec

`specs/maturing_zone_watchlist/{requirements,design,tasks}.md`
