# Requirements — stoch_entry_help

> M15 stochastic as a **help layer** over already-formed STRAT-F signals.
> Zones by %K only; boost when extreme favors direction; veto only opposite
> extreme in `hard` mode. Does **not** change `evaluate_strat_f`.

## Context

Today the scanner already calls `compute_stoch` after STRAT-F and records
`stoch_m15` / `stoch_contradicts` in the black box (**measurement only**).
This feature turns that measurement into an optional help layer controlled by
`STOCH_HELP_MODE` (`off` | `soft` | `hard`). Decision v1 uses **%K zone +
direction only** — never cruce or divergencia.

## Functional requirements (EARS)

## R1 — Pure zone module
The system MUST provide a pure module `src/stochastic_zones.py` (no I/O, no
broker imports) that maps %K to one of five zones: Z1 (0–20), Z2 (20–40),
Z3 (40–60), Z4 (60–80), Z5 (80–100).

## R2 — Zone boundaries (%K)
CUANDO %K is numeric, the system MUST assign zones with these closed/open
bounds (aligned with existing oversold/overbought):
- Z1: `0 <= k <= 20`
- Z2: `20 < k <= 40`
- Z3: `40 < k <= 60`
- Z4: `60 < k < 80`
- Z5: `80 <= k <= 100`
Values outside `[0, 100]` MUST be clamped to that range before zoning.

## R3 — Action matrix (CALL)
CUANDO direction is CALL and a zone is known, the system MUST resolve action
and score_delta as:
| Zone | action (soft/hard) | score_delta |
|------|--------------------|-------------|
| Z1 | BOOST | +10 |
| Z2 | BOOST | +5 |
| Z3 | PASS | 0 |
| Z4 | PASS | 0 |
| Z5 | VETO if mode=`hard`, else PASS | 0 |

## R4 — Action matrix (PUT)
CUANDO direction is PUT and a zone is known, the system MUST resolve action
and score_delta as:
| Zone | action (soft/hard) | score_delta |
|------|--------------------|-------------|
| Z1 | VETO if mode=`hard`, else PASS | 0 |
| Z2 | PASS | 0 |
| Z3 | PASS | 0 |
| Z4 | BOOST | +5 |
| Z5 | BOOST | +10 |

## R5 — Mode `off` (measurement only)
MIENTRAS `STOCH_HELP_MODE` is `off`, the system MUST keep current behavior:
compute and record stoch, and MUST NOT change STRAT-F candidate scores or
reject candidates for stoch reasons.

## R6 — Mode `soft` (boost only)
MIENTRAS `STOCH_HELP_MODE` is `soft`, the system MUST apply score boosts from
R3/R4 and MUST NOT veto any candidate for stoch extremes (CALL+Z5 and PUT+Z1
are PASS with score_delta 0).

## R7 — Mode `hard` (boost + opposite extreme veto)
MIENTRAS `STOCH_HELP_MODE` is `hard`, the system MUST apply boosts from R3/R4
and MUST veto CALL+Z5 and PUT+Z1 so that no `CandidateEntry` is produced for
that asset in the cycle.

## R8 — Veto reject reason
CUANDO a hard-mode stoch veto occurs, the system MUST set reject reason
`stoch_extreme_against` (and black-box / batch decision as rejected for that
reason, not as a STRAT-F skip).

## R9 — Decision v1 ignores cruce / divergencia
CUANDO applying stoch help, the system MUST derive zone/action/score_delta
from %K and direction only. The system MUST NOT use `cruce` or `divergencia`
for the help decision (they MAY still be computed by `compute_stoch` for
measurement).

## R10 — Missing %K is non-blocking
SI `compute_stoch` returns `k is None` (insufficient candles / indicator
unavailable), ENTONCES the system MUST treat help as PASS with score_delta 0
(no veto, no boost) and still allow a STRAT-F candidate when STRAT-F has a
signal.

## R11 — Config flag
The system MUST expose `STOCH_HELP_MODE` in `src/config.py` with allowed
values `off` | `soft` | `hard` and default **`hard`**. The flag MUST be
overridable via environment without changing STRAT-F code.

## R12 — STRAT-F core untouched
The system MUST NOT modify `evaluate_strat_f` or other decision logic inside
`src/strat_fractal.py`. Help is applied only after STRAT-F evaluation returns.

## R13 — Scanner integration point
CUANDO the scanner has run `evaluate_strat_f` and `compute_stoch` for an
asset, and `STOCH_HELP_MODE != off`, the system MUST call `apply_stoch_help`
(from `stochastic_zones`) before appending a STRAT-F candidate.

## R14 — Boost applied to candidate score
CUANDO help action is BOOST and a STRAT-F candidate is created, the system
MUST add `score_delta` to the candidate score after normal scoring (so the
delta is visible in the final score used for ranking).

## R15 — Black box records help fields
CUANDO the black box records a STRAT-F decision with `stoch_m15`, the system
MUST also record `zone`, `action`, and `score_delta` together with that stoch
payload (fields present even when mode is `off`, with action PASS / delta 0
or mode-appropriate measurement-only values).

## R16 — Easy disable
CUANDO `STOCH_HELP_MODE` is set to `off`, the system MUST disable score
adjustments and vetoes without redeploying or altering STRAT-F logic.

## R17 — Tests
The system MUST include unit tests for zone mapping and the full action
matrix (soft/hard, CALL/PUT), plus a scanner integration test with mocked
STRAT-F / stoch that asserts veto vs boost behavior. `pytest` for those
tests MUST pass.

## Out of scope

- Changing fractal / Wyckoff detection in `strat_fractal.py`.
- Using cruce, divergencia, or `contradicts` as gates in v1.
- Hub UI changes for stoch help (may display recorded fields later).
- Live A/B promotion logic beyond the three modes above.

## Acceptance mapping (feature_list #9)

| Acceptance bullet | Requirements |
|---|---|
| Pure `stochastic_zones.py` zones + action | R1, R2, R3, R4 |
| `evaluate_strat_f` unmodified | R12 |
| Scanner after eval + compute_stoch | R13, R5–R7 |
| hard veto / soft score-only | R6, R7, R8 |
| Boost table; no cruce/div in decision | R3, R4, R9 |
| `STOCH_HELP_MODE` default hard; off = measure | R5, R11, R16 |
| Black box zone + action + score_delta | R15 |
| Unit + scanner mock tests green | R10, R14, R17 |
