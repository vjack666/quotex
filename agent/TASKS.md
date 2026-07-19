# TASKS

> Maintained by agents at session end. Sync with `feature_list.json` and `docs/ROADMAP.md`.
> Last updated: 2026-07-15 — STRAT-F live; foco datos + stoch entry

---

## In Progress

| ID / item | Task | Notes |
|-----------|------|-------|
| #8 | `schedule_auto` | Spec+impl listos (`specs/schedule_auto/`, T1–T7 `[x]`). Status `in_progress` hasta review/cierre formal. |
| ops | `duration_live` | Fix en código + `tests/test_duration_live.py`. Awaiting reviewer. No mezclar con nueva feature. |

---

## Next

| Priority | Task | Notes |
|----------|------|-------|
| **P0** | **STRAT-F: recolectar datos de sesión** | Black box con señal, `stoch_m15`, resultado. Volumen antes de tocar reglas. |
| **P0** | **STRAT-F: análisis estocástico → mejora de entrada** | Hoy stoch solo se observa. Objetivo: A/B y SDD para boost/veto en extremos, cruces, divergencias (`boblioteca/estocastico/`). |
| P1 | Reviewer: `schedule_auto` + `duration_live` | Marcar done solo con trazabilidad y tests verdes en entorno limpio. |
| P2 | Tests: no contaminar con `hub_bankroll.json` min_payout=90 | Restaura `init.ps1` verde. |
| P3 | Rotar `consolidation_bot.log` si crece | Mantenimiento |

---

## Completed (tracks recientes)

### STRAT-F + hub (post–Strategy B)

| ID | Task | Completed | Notes |
|----|------|-----------|-------|
| #1 | `scanner_multi_tf_prefetch` | 2026-07-11 | `candles_15m` en scan |
| #2 | `strat_f_baseline` | 2026-07-11 | `strat_fractal.evaluate_strat_f` |
| #3 | `strat_f_scanner_wiring` | 2026-07-11 | Origen `STRAT-F` en scanner |
| #4 | `strat_f_filters` | 2026-07-11 | payout / alineación / edad |
| #5 | `strat_f_backtest` | 2026-07-11 | Backtester reconoce STRAT-F |
| #6 | `strat_f_live_validation` | 2026-07-11 | Demo / reject-first |
| #7 | `hub_strat_f_replacement` | 2026-07-11 | Panel aceptadas vs rechazadas |
| — | Go-live G1+G2 | 2026-07-11 | Panel en bot real + `STRAT_F_ONLY` |
| — | Engineering docs | 2026-07-11 | SRS/ADR/ERD/API en `docs/engineering/` |
| — | Hub bankroll + resolve lag | 2026-07-14 | Massaniello desde UI; UNRESOLVED vs LOSS falso |

### Roadmap legacy (pre–STRAT-F, cerrado)

Features #1–#22 del roadmap viejo (modular bot, Massaniello, strategies A/B/momentum/swing/OB, hub WS, Kelly, diversificación, alerts, etc.) — **done 2026-07-04**. Strategy B eliminada 2026-07-11. Detalle histórico: `progress/history.md`.

---

## Task movement rules

1. Move to **In Progress** when `feature_list.json` status → `in_progress`.
2. Move to **Completed** when reviewer approves and status → `done`.
3. Never have more than one **feature de producto** In Progress (Harness). Housekeeping/bugfix se documenta aparte.
4. **No inventar SDD de stoch** sin datos de black box + análisis.
5. Operational tasks (credenciales, corridas live) stay in **Next** until the human closes them.
