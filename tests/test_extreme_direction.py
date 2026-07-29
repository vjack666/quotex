# Feature 29 / RG6 — tests deterministas del filtro de dirección en extremo.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import entry_scorer
from models import Candle, CandidateEntry, ConsolidationZone


def _zone(floor=100.0, ceiling=101.0):
    return ConsolidationZone(
        asset="X_otc", ceiling=ceiling, floor=floor,
        bars_inside=10, detected_at=0.0, range_pct=0.01,
    )


def _entry(direction, candle, zone=None):
    return CandidateEntry(
        asset="X_otc", payout=90, zone=zone if zone is not None else _zone(),
        direction=direction, candles=[candle],
    )


def test_put_at_floor_wick_touch_body_up_penalized(monkeypatch):
    monkeypatch.setattr(entry_scorer, "MARKET_GEOMETRY_ENABLED", True)
    # mecha toca el piso 100.0 pero cuerpo alcista (caso EURJPY)
    c = Candle(ts=0, open=100.05, high=100.30, low=100.00, close=100.25)
    adj = entry_scorer._score_extreme_direction(_entry("put", c))
    assert adj == entry_scorer.EXTREME_DIR_PENALTY


def test_put_at_floor_conviction_body_down_neutral(monkeypatch):
    monkeypatch.setattr(entry_scorer, "MARKET_GEOMETRY_ENABLED", True)
    # spike con convicción: cuerpo bajista decidido, cierre en mitad baja
    c = Candle(ts=0, open=100.28, high=100.30, low=100.00, close=100.02)
    adj = entry_scorer._score_extreme_direction(_entry("put", c))
    assert adj == 0.0


def test_call_at_ceiling_no_body_penalized(monkeypatch):
    monkeypatch.setattr(entry_scorer, "MARKET_GEOMETRY_ENABLED", True)
    # mecha toca el techo 101.0 pero cuerpo bajista
    c = Candle(ts=0, open=100.95, high=101.00, low=100.70, close=100.72)
    adj = entry_scorer._score_extreme_direction(_entry("call", c))
    assert adj == entry_scorer.EXTREME_DIR_PENALTY


def test_call_at_ceiling_conviction_neutral(monkeypatch):
    monkeypatch.setattr(entry_scorer, "MARKET_GEOMETRY_ENABLED", True)
    c = Candle(ts=0, open=100.72, high=101.00, low=100.70, close=100.98)
    adj = entry_scorer._score_extreme_direction(_entry("call", c))
    assert adj == 0.0


def test_not_at_extreme_neutral(monkeypatch):
    monkeypatch.setattr(entry_scorer, "MARKET_GEOMETRY_ENABLED", True)
    # vela en medio del rango: filtro inactivo aunque cuerpo contradiga
    c = Candle(ts=0, open=100.45, high=100.60, low=100.40, close=100.58)
    adj = entry_scorer._score_extreme_direction(_entry("put", c))
    assert adj == 0.0


def test_no_zone_no_geom_neutral(monkeypatch):
    monkeypatch.setattr(entry_scorer, "MARKET_GEOMETRY_ENABLED", True)
    c = Candle(ts=0, open=100.05, high=100.30, low=100.00, close=100.25)
    e = _entry("put", c)
    e.zone = None
    assert entry_scorer._score_extreme_direction(e) == 0.0


def test_flag_off_neutral(monkeypatch):
    monkeypatch.setattr(entry_scorer, "MARKET_GEOMETRY_ENABLED", False)
    c = Candle(ts=0, open=100.05, high=100.30, low=100.00, close=100.25)
    assert entry_scorer._score_extreme_direction(_entry("put", c)) == 0.0


def test_geom_swing_low_used(monkeypatch):
    monkeypatch.setattr(entry_scorer, "MARKET_GEOMETRY_ENABLED", True)

    class Geom:
        swing_lows = [100.0]
        swing_highs = []

    c = Candle(ts=0, open=100.05, high=100.30, low=100.00, close=100.25)
    e = _entry("put", c)
    e.zone = None
    adj = entry_scorer._score_extreme_direction(e, geom=Geom())
    assert adj == entry_scorer.EXTREME_DIR_PENALTY


def test_eurjpy_case_from_memory(monkeypatch):
    """Réplica de la vela de entrada EURJPY 2247864af2e7b77e (piso 186.012)."""
    monkeypatch.setattr(entry_scorer, "MARKET_GEOMETRY_ENABLED", True)
    zone = _zone(floor=186.012, ceiling=186.101)
    # última M1 real: o=186.086 h=186.091 l=186.071 c=186.082 → cuerpo NO
    # confirma PUT; ni siquiera está en el extremo → probamos con la vela
    # que barrió el piso (5m): o=186.054 h=186.054 l=186.004 c=186.008
    # → cuerpo bajista con cierre bajo cerca del piso = convicción → 0.0.
    sweep = Candle(ts=0, open=186.054, high=186.054, low=186.004, close=186.008)
    assert entry_scorer._score_extreme_direction(_entry("put", sweep, zone)) == 0.0
    # pero la vela siguiente (rebote: o=186.008 c=186.053, low=186.0) sí
    # habría sido penalizada: mecha tocó el piso y el cuerpo cerró alcista.
    rebound = Candle(ts=0, open=186.008, high=186.078, low=186.000, close=186.053)
    assert (
        entry_scorer._score_extreme_direction(_entry("put", rebound, zone))
        == entry_scorer.EXTREME_DIR_PENALTY
    )
