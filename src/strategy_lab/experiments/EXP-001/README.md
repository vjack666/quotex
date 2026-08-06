# EXP-001 — Filtro combinado: cross_separation >= 4.5 y minutes_brake_to_cross >= 16

## Objetivo

Validar si combinar separación K/D amplia con un tiempo mínimo desde freno hasta cruce mejora la calidad estadística del Edificio.

## Hipótesis

H1: Las entradas con `cross_separation >= 4.5` y `minutes_brake_to_cross >= 16` tienen WR > 50% y EV > 0, sobreviviendo al tribunal v1.0.

## Tribunal

- tribunal.version: 1.0
- baseline.id: BASELINE-EDIFICIO
- baseline.version: 1.0

## Protocolo

1. Cargar dataset real del Edificio (946 eventos).
2. Filtrar por condiciones combinadas.
3. Calcular evidencia con `evidence.py`.
4. Ejecutar 5 pruebas de robustez con `robustness.py`.
5. Evaluar con `promotion_gate.py`.
6. Exportar informe.

## Variables

- `cross_separation_threshold`: 4.5
- `minutes_brake_to_cross_min`: 16
- `events_esperados`: ~108 (946 - 18 eventos de cruce muy rápido)

## Aislamiento

Prueba UNA condición combinada: separación K/D amplia + tiempo mínimo.
No mezcla con body_n, martillo M15, ni otras variables.

## Trazabilidad

- Dataset: `src/strategy_lab/results/edificio_events.csv`
- Código: `src/strategy_lab/scripts/run_experiment_exp001.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
