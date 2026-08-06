# EXP-002 — Features derivadas de datos crudos M15 multi-par

## Objetivo

Generar eventos desde datos crudos OHLCV M15 de múltiples pares,
derivando features de máquina de estados y evaluando si una
condición estructural sobrevive al tribunal v1.0.

## Hipótesis

H1: Una condición basada en estructura de velas M15 multi-par
(tendencia + rango + volatilidad) genera eventos con WR > 50% y EV > 0,
sobreviviendo al tribunal v1.0.

## Tribunal

- tribunal.version: 1.0
- baseline.id: BASELINE-EDIFICIO
- baseline.version: 1.0

## Protocolo

1. Cargar datos M15 reales de 7 pares desde parquet.
2. Calcular features por par: tendencia (EMA fast/slow), rango (ATR),
   volatilidad (std returns), cuerpo (body/range).
3. Generar eventos por par según reglas estructurales.
4. Unificar eventos multi-par.
5. Calcular evidencia con `evidence.py`.
6. Ejecutar 5 pruebas de robustez con `robustness.py`.
7. Evaluar con `promotion_gate.py`.
8. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: ema_fast, ema_slow, atr, body_ratio, volatility
- `regla_estructural`: EMA fast > EMA slow AND body_ratio > 0.5 AND volatility > percentil_75

## Aislamiento

Prueba UNA condición estructural multi-par.
No mezcla con cross_separation, body_n_brake, ni otras variables.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp002.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
