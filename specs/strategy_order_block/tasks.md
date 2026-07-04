# Tasks — strategy_order_block

- [x] T1 — Crear `src/strat_order_block.py` con `detect_order_block_entry`. Cubre: R1, R2, R3, R4, R7.
- [x] T2 — Añadir `STRAT_ORDER_BLOCK_ENABLED` y `STRAT_ORDER_BLOCK_MIN_STRENGTH` en `config.py`. Cubre: R5.
- [x] T3 — Integrar order_block en `scanner.py` (nuevo bloque post-reversal-swing). Cubre: R5, R6.
- [x] T4 — Tests en `tests/test_strat_order_block.py`: OB alcista → CALL, OB bajista → PUT, OB mitigado → None, sin OB → None. Cubre: R1, R2, R3, R8.
- [x] T5 — Verificar `python -m pytest tests/ -v` pasa y `.\init.ps1` termina en verde.
