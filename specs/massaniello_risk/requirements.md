# Requirements — massaniello_risk

## R1 — Motor Massaniello

El bot debe calcular stakes con la lógica de `masaniello.py` (tabla de multiplicadores, 5 operaciones, 3 ITM).

## R2 — Wrapper de sesión

`MassanielloRiskManager` expone: `set_balance`, `next_stake`, `register_win`, `register_loss`, `can_enter`, `session_status`, `is_session_complete`, `is_session_failed`, límites de tiempo y conteo de entradas.

## R3 — Integración executor

`executor.py` usa Massaniello en lugar de MartingaleCalculator; desactiva martingala intra-trade y bloquea entradas al cerrar/fallar/timeout de sesión.

## R4 — Solo demo

Con `RISK_MANAGER=massaniello`, la cuenta debe forzarse a PRACTICE aunque se pase `--real`.

## R5 — Configuración

`MASSANIELLO_OPERATIONS=5`, `MASSANIELLO_EXPECTED_WINS=3`, `SESSION_MAX_MIN=60`, `RISK_MANAGER=massaniello`, ciclo alineado 5/3.

## R6 — Observabilidad

Log `🎯 SESIÓN MASSANIELLO CUMPLIDA` al alcanzar 3 wins en sesión.

## R7 — Tests

`test_massaniello_engine.py` y `test_massaniello_risk.py` cubren escenarios 5 ops / 3 ITM; `test_executor.py` actualizado.