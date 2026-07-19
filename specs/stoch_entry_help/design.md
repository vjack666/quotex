# Design — stoch_entry_help

## Goal

Add a thin, pure **stoch help layer** between STRAT-F evaluation and candidate
admission in the scanner. Measurement stays always-on via `compute_stoch`;
`STOCH_HELP_MODE` decides whether that measurement can boost scores or veto
opposite extremes.

## Non-negotiables

1. **Do not edit** `src/strat_fractal.py` decision paths (`evaluate_strat_f`).
2. Decision v1 uses **%K zone + direction + mode only**.
3. Default mode is **`hard`**; `off` restores pure measurement.
4. No new third-party dependencies.

## Architecture placement

```
scanner (STRAT-F block)
  │
  ├── evaluate_strat_f(...)          # UNCHANGED
  ├── compute_stoch(candles_15m, …)  # EXISTING measurement
  ├── apply_stoch_help(k, dir, mode) # NEW pure helper
  │     └── zone_from_k / matrix
  ├── candidate create + score_candidate + score_delta
  │     OR reject stoch_extreme_against
  └── black_box.record_candidate(... stoch_m15 enriched ...)
```

Layer: **Análisis** (`scanner.py`) + pure helper in **Soporte/estrategia fina**
(`stochastic_zones.py`). Matches architecture rule: strategies/helpers stay
I/O-free; scanner orchestrates.

## Files

### Create

| Path | Role |
|------|------|
| `src/stochastic_zones.py` | Pure zone + action + score_delta API |
| `tests/test_stochastic_zones.py` | Unit matrix + boundaries + missing k |
| `tests/test_stoch_entry_help_scanner.py` | Scanner integration with mocks |

### Modify

| Path | Change |
|------|--------|
| `src/config.py` | Add `STOCH_HELP_MODE` (`off`\|`soft`\|`hard`, default `"hard"`) |
| `src/scanner.py` | After `compute_stoch`, apply help when mode ≠ off; enrich black box |
| `src/black_box_recorder.py` | Only if needed so enriched `stoch_m15` JSON is stored as-is (prefer no schema migration: nest fields inside existing `stoch_m15` TEXT) |

### Do not touch

- `src/strat_fractal.py`
- Fractal band / M1 reject / M15 context logic
- Hub panels (out of scope)

## Public API (`stochastic_zones.py`)

```python
"""M15 stoch zone help over STRAT-F (pure, no I/O)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Zone = Literal["Z1", "Z2", "Z3", "Z4", "Z5"]
Action = Literal["BOOST", "PASS", "VETO"]
StochHelpMode = Literal["off", "soft", "hard"]

@dataclass(frozen=True)
class StochHelpResult:
    zone: Optional[Zone]
    action: Action
    score_delta: int
    reason: str  # e.g. "stoch_boost", "stoch_pass", "stoch_extreme_against", "stoch_no_k"

def zone_from_k(k: Optional[float]) -> Optional[Zone]:
    """Map %K to Z1..Z5; None if k is None. Clamp to [0, 100]."""
    ...

def apply_stoch_help(
    k: Optional[float],
    direction: str,
    mode: str,
) -> StochHelpResult:
    """Return zone/action/score_delta for STRAT-F direction.

    - mode "off": always PASS, score_delta 0 (zone still resolved if k present)
    - mode "soft": boosts only; never VETO
    - mode "hard": boosts + VETO on CALL+Z5 and PUT+Z1
    - k is None: PASS, score_delta 0, zone None
    - direction normalized case-insensitively to CALL/PUT
    - unknown mode: behave as "off" (fail-safe: no veto)
    """
    ...
```

### Zone boundaries

| Zone | %K |
|------|-----|
| Z1 | `0 <= k <= 20` |
| Z2 | `20 < k <= 40` |
| Z3 | `40 < k <= 60` |
| Z4 | `60 < k < 80` |
| Z5 | `80 <= k <= 100` |

Rationale: aligns with `compute_stoch` oversold `k <= 20` and overbought
`k >= 80` (20 belongs to Z1; 80 belongs to Z5).

### Action matrix (locked)

| Zone | CALL | PUT |
|------|------|-----|
| Z1 | BOOST +10 | VETO if hard else PASS |
| Z2 | BOOST +5 | PASS |
| Z3 | PASS | PASS |
| Z4 | PASS | BOOST +5 |
| Z5 | VETO if hard else PASS | BOOST +10 |

`score_delta` is 0 for PASS and VETO; only BOOST rows use +5 / +10.

## Config

```python
# src/config.py
STOCH_HELP_MODE = os.getenv("STOCH_HELP_MODE", "hard").strip().lower()
# Valid: "off" | "soft" | "hard". Invalid values treated as "off" by apply_stoch_help.
```

Prefer reading via existing `_runtime_config` / config import pattern used for
`STRAT_F_ENABLED` so tests can monkeypatch.

## Scanner integration (STRAT-F block)

Current order (simplified):

1. `f_eval = evaluate_strat_f(...)`
2. `stoch_m15 = compute_stoch(...)`
3. if signal → build candidate → `score_candidate` → append
4. black box record

New order:

1. `f_eval = evaluate_strat_f(...)`  # unchanged
2. `stoch_m15 = compute_stoch(...)`  # unchanged measurement
3. Resolve help (always compute result for recording when stoch ran):
   ```python
   mode = getattr(_runtime_config, "STOCH_HELP_MODE", "hard")
   k = (stoch_m15 or {}).get("k")
   help_res = apply_stoch_help(k, f_eval.direction or "", mode)
   # Enrich measurement payload for black box
   if stoch_m15 is not None:
       stoch_m15 = {
           **stoch_m15,
           "zone": help_res.zone,
           "action": help_res.action,
           "score_delta": help_res.score_delta,
       }
   ```
4. If `f_eval.has_signal` and direction/zone present:
   - If `help_res.action == "VETO"`:
     - Do **not** create/append candidate
     - `_rec["decision"] = "REJECTED_STOCH"`
     - `reject_reason = "stoch_extreme_against"`
     - count reject; log at DEBUG/INFO consistent with other STRAT-F rejects
   - Else:
     - Build candidate as today
     - `score_candidate(f_candidate)`
     - If `help_res.score_delta`:
       - `f_candidate.score = round(f_candidate.score + help_res.score_delta, 1)`
       - put `"stoch_help": float(help_res.score_delta)` into `score_breakdown` if dict exists
     - append as today
5. Black box: pass enriched `stoch_m15`; on stoch veto set
   `decision` / `reject_reason` accordingly (`stoch_extreme_against`).

Notes:

- When mode is `off`, `apply_stoch_help` returns PASS / 0; optional micro-opt:
  still call it so black box always gets zone/action/score_delta consistently
  (recommended — one code path).
- Acceptance says “applies apply_stoch_help if mode != off” for **score/veto
  effects**; recording zone when mode is off is still required (R15).
- Do not gate STRAT-F skip_reason path: if STRAT-F already rejected, only
  enrich stoch fields; no double-reject for stoch.

## Black box

Prefer **embedding** in existing `stoch_m15` JSON:

```json
{
  "k": 18.2, "d": 22.1, "estado": "SOBREVENTA",
  "cruce": null, "divergencia": null, "contradicts": 0,
  "zone": "Z1", "action": "BOOST", "score_delta": 10
}
```

No SQLite migration if `stoch_m15` is already TEXT JSON. `stoch_contradicts`
column (if present) stays driven by measurement `contradicts`; help action is
orthogonal.

## Testing strategy

### `tests/test_stochastic_zones.py`

- Boundaries: k at 0, 20, 20.01, 40, 40.01, 60, 60.01, 79.99, 80, 100
- Clamp: k=-5 → Z1, k=120 → Z5
- Full CALL/PUT × soft/hard matrix for all five zones
- mode `off` → always PASS, delta 0, zone still set when k present
- k=None → zone None, PASS, 0, reason `stoch_no_k`
- direction case: `call`/`CALL` equivalent
- unknown mode → fail-safe off behavior
- Prove cruce/divergencia are **not parameters** of `apply_stoch_help`

### `tests/test_stoch_entry_help_scanner.py`

- Mock `evaluate_strat_f` signal + mock/fixed stoch k
- hard + CALL + k=85 → no candidate, reject `stoch_extreme_against`
- hard + PUT + k=10 → same
- soft + CALL + k=85 → candidate exists, score_delta 0
- hard + CALL + k=10 → candidate, score increased by +10 vs baseline
- mode off + extreme → candidate still created (measurement only)
- Assert black-box payload / `_rec["stoch_m15"]` contains zone/action/score_delta

No real broker; synthetic candles or patched pure functions only.

## Alternatives discarded

| Alternative | Why discarded |
|-------------|---------------|
| Fold zone logic into `stochastic_m15.py` | Mixes measurement (pyquotex formula, cruce, divergencia) with product policy; harder to disable and test matrix alone |
| Veto inside `evaluate_strat_f` | Violates locked rule; couples indicator policy to fractal core; breaks measurement A/B cleanliness |
| Soft as default | Product lock: default `hard`; `off` is the safe rollback |
| Use `contradicts` / cruce as gate | Explicitly out of v1; keep as recorded signals only |
| Separate DB columns for zone/action | Unnecessary migration risk; nest in `stoch_m15` JSON |

## Risks

| Risk | Mitigation |
|------|------------|
| Boundary off-by-one vs operator intuition | Spec R2 + explicit unit table; document 20→Z1, 80→Z5 |
| `score_candidate` overwrites score after boost | Apply delta **after** `score_candidate` |
| Double reject noise when STRAT-F already skips | Only apply veto path when STRAT-F would have accepted |
| Invalid env mode accidentally hard-vetoes | Unknown mode → off (fail-safe) |
| Tests depend on full scanner I/O | Patch eval/stoch/black box; or extract a small pure “admit strat-f candidate” helper only if tests force it — prefer minimal scanner edit first |

## Implementation order

1. `stochastic_zones.py` + unit tests (TDD on matrix)
2. `config.STOCH_HELP_MODE`
3. Scanner wire + black box enrich
4. Scanner integration tests
5. Full `pytest` / `.\init.ps1` green
