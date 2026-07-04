# Tasks — diversification_enforcer

- [ ] T1 — Añadir constantes a `src/config.py` (MAX_SIMULTANEOUS_TRADES, MIN_ASSET_SPREAD, MAX_ENTRIES_PER_ASSET). Cubre: R7.
- [ ] T2 — Crear `src/diversification_enforcer.py` con clase `DiversificationEnforcer` y método `check()`. Cubre: R1, R2, R3, R4, R5.
- [ ] T3 — Integrar en `ConsolidationBot.__init__` (crear instancia). Cubre: R6.
- [ ] T4 — Integrar en scanner.py `_scan_phase_select_execute` (guardia antes de entrar winners). Cubre: R6.
- [ ] T5 — Integrar en scanner.py `_scan_phase_evaluate_assets` (guardia antes de STRAT-B). Cubre: R6.
- [ ] T6 — Tests en `tests/test_diversification_enforcer.py` (mínimo 6). Cubre: R1–R5.
- [ ] T7 — Verificar `python -m pytest tests/test_diversification_enforcer.py -v` y `.\init.ps1`.
