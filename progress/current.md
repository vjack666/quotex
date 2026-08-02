# Progress — 2026-08-02

## Active task
Implementar fix deuda #1 Edificio de Contratación: confirmación del freno con vela M15 cerrada.

## Status
- ✅ Aprobado por el usuario: brake_candidato → esperar cierre vela M15 → comparar range cerrada vs referencia → CONFIRMA/REJECTED.
- ✅ Implementado en `src/edificio_contratacion.py`: campos card (`brake_verdict`, `brake_ratio`, `brake_witness_ts`, `brake_reference_range`, `brake_reference_ts`), helpers `_brake_set_reference`/`_brake_confirm`/`_brake_clear_reference`, lógica P1 reemplaza tiempo+flag por cierre de vela cerrada.
- ✅ Caja negra: columnas nuevas en `src/black_box_recorder.py` (`brake_verdict`, `brake_ratio`, `brake_ref_range`, `brake_witness_ts`, `brake_rule_version`) + INSERT actualizado.
- ✅ Executor: `src/edificio_executor.py` registra verdicts de freno en caja negra + bump `EDIFICIO_RULE_VERSION` a `2026-08-02e`.
- ✅ Tests actualizados: helper `_subir_a_p3` y fixtures de executor/trazabilidad usan veredicto explícito CONFIRMED.
- ✅ Suite EDIFICIO: 44/44 verde (`pytest tests/test_edificio_contratacion.py tests/test_edificio_executor.py tests/test_edificio_trazabilidad.py`).
- ⚠️ Suite completa: 32 fallos preexistentes en módulos no relacionados (STRAT-F, STRAT-A, session lifecycle, etc.), verificados previos a este cambio.

## Next
1. Esperar feedback del usuario sobre comportamiento en demo con la nueva confirmación.
2. Recolectar métricas post-freno con la nueva mecánica.
