"""Tests T2 — pressure_point con aritmética calculada a mano."""
from observador.metric import Metric
from observador.pressure import pressure_point


def mk(ts, o, c):
    return {"ts": ts, "open": o, "high": max(o, c) + 0.001, "low": min(o, c) - 0.001, "close": c}


def test_net_advance_hand_arithmetic():
    # 5 velas, todos los cuerpos = 0.01 -> mediana 0.01
    # close anterior 1.00, close actual 1.02 -> raw = 0.02
    # normalized = 0.02 / (2 * 0.01) = 1.0
    window = [
        mk(0, 0.96, 0.97),
        mk(60, 0.97, 0.98),
        mk(120, 0.98, 0.99),
        mk(180, 0.99, 1.00),
        mk(240, 1.01, 1.02),  # cuerpo 0.01, close 1.02
    ]
    pt = pressure_point(window, direction=1)
    assert pt["direction"] == 1
    assert pt["formula_version"] == "pressure_v1"
    na = pt["net_advance"]
    assert isinstance(na, Metric)
    assert abs(na.raw - 0.02) < 1e-12
    assert na.normalized == 1.0
    assert na.confidence == 1.0
    # continuidad: las 5 velas son alcistas -> 5/5 = 1.0, ventana completa
    cont = pt["continuity"]
    assert cont.raw == 1.0 and cont.normalized == 1.0 and cont.confidence == 1.0


def test_net_advance_partial_normalization():
    # mediana cuerpos 0.01; raw = (1.005 - 1.00) * 1 = 0.005
    # normalized = 0.005 / 0.02 = 0.25
    window = [
        mk(0, 0.97, 0.98),
        mk(60, 0.98, 0.99),
        mk(120, 0.99, 1.00),
        mk(180, 1.01, 1.00),   # bajista, close 1.00
        mk(240, 0.995, 1.005),  # cuerpo 0.01, close 1.005
    ]
    pt = pressure_point(window, direction=1)
    assert abs(pt["net_advance"].raw - 0.005) < 1e-12
    assert abs(pt["net_advance"].normalized - 0.25) < 1e-12
    # continuidad: 4 de 5 alcistas -> 0.8
    assert abs(pt["continuity"].raw - 0.8) < 1e-12


def test_negative_advance_clamps_to_zero():
    # direction +1 pero el precio baja -> raw negativo, normalized clavado en 0
    window = [mk(0, 1.00, 1.01), mk(60, 1.01, 1.00)]
    pt = pressure_point(window, direction=1)
    assert pt["net_advance"].raw < 0
    assert pt["net_advance"].normalized == 0.0


def test_zero_median_degrades_confidence():
    # todas doji (cuerpo 0) -> mediana 0 -> normalized 0, confidence 0.5
    window = [mk(0, 1.00, 1.00), mk(60, 1.01, 1.01)]
    pt = pressure_point(window, direction=1)
    assert pt["net_advance"].normalized == 0.0
    assert pt["net_advance"].confidence == 0.5


def test_short_window_degrades_continuity_confidence():
    window = [mk(0, 1.00, 1.01), mk(60, 1.01, 1.02)]  # solo 2 velas
    pt = pressure_point(window, direction=1)
    assert pt["continuity"].confidence == 0.5
    assert pt["continuity"].raw == 1.0  # 2/2 alcistas


def test_direction_minus_one():
    # bajista: closes 1.02 -> 1.00, direction -1 -> raw = 0.02
    window = [
        mk(0, 1.05, 1.04),
        mk(60, 1.04, 1.03),
        mk(120, 1.03, 1.02),
        mk(180, 1.02, 1.02 - 0.01),
        mk(240, 1.01, 1.00),
    ]
    pt = pressure_point(window, direction=-1)
    assert abs(pt["net_advance"].raw - 0.01) < 1e-12
    assert pt["continuity"].raw == 1.0
