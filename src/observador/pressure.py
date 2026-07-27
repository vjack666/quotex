"""PressureCurve — punto de presión por vela M1 (R3.1, PTM v3).

Cada punto lleva dirección, avance neto y continuidad como Metric
(raw, normalized, confidence, formula_version). Sin números desnudos.
"""
from __future__ import annotations

from statistics import median

from observador.metric import Metric

FORMULA_VERSION = "pressure_v1"
CONTINUITY_WINDOW = 5
NORMALIZATION_BODIES = 2.0  # raw se normaliza contra 2x mediana de cuerpos


def _bodies(candles: list[dict]) -> list[float]:
    return [abs(c["close"] - c["open"]) for c in candles]


def median_body(candles: list[dict]) -> float:
    """Mediana de |close-open| de la ventana (0.0 si vacía)."""
    bodies = _bodies(candles)
    return median(bodies) if bodies else 0.0


def continuity_fraction(candles: list[dict], direction: int) -> float:
    """Fracción de las últimas 5 velas cuyo cierre va en `direction`."""
    last = candles[-CONTINUITY_WINDOW:]
    if not last:
        return 0.0
    hits = sum(1 for c in last if (c["close"] - c["open"]) * direction > 0)
    return hits / len(last)


def pressure_point(candles_window: list[dict], direction: int) -> dict:
    """Punto de PressureCurve para la última vela de la ventana.

    net_advance.raw = (close_actual - close_anterior) * direction
    net_advance.normalized = clamp(raw / (2 * mediana de cuerpos), 0, 1)
      mediana 0 -> normalized 0 y confidence degradada a 0.5.
    continuity.raw = fracción de las últimas 5 velas en `direction`.
      confidence 1.0 con ventana completa (>=5 velas), 0.5 si hay menos.
    """
    if direction not in (1, -1):
        raise ValueError(f"direction debe ser +1 o -1, no {direction!r}")
    if len(candles_window) < 2:
        raise ValueError("pressure_point requiere al menos 2 velas")

    close_now = candles_window[-1]["close"]
    close_prev = candles_window[-2]["close"]
    raw_adv = (close_now - close_prev) * direction

    med = median_body(candles_window)
    if med == 0.0:
        norm_adv, conf_adv = 0.0, 0.5
    else:
        norm_adv = min(1.0, max(0.0, raw_adv / (NORMALIZATION_BODIES * med)))
        conf_adv = 1.0

    cont_raw = continuity_fraction(candles_window, direction)
    cont_conf = 1.0 if len(candles_window) >= CONTINUITY_WINDOW else 0.5

    return {
        "direction": direction,
        "net_advance": Metric(raw_adv, norm_adv, conf_adv, FORMULA_VERSION),
        "continuity": Metric(cont_raw, cont_raw, cont_conf, FORMULA_VERSION),
        "formula_version": FORMULA_VERSION,
    }
