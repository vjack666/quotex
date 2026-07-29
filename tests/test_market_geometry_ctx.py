"""Tests deterministas de market_geometry_ctx (Feature 29).

Velas M15 sintéticas (dicts {ts,o,h,l,c}). Sin LLM, sin red.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import market_geometry_ctx as mgc
from market_geometry_ctx import (
    GeometryCache,
    compute_daily_geometry,
    level_role,
)

M15 = 900


def _c(ts: int, o: float, h: float, l: float, c: float) -> dict:
    return {"ts": ts, "o": o, "h": h, "l": l, "c": c}


def _range_with_support(support: float = 1.0000, top: float = 1.0100) -> list[dict]:
    """Rango que toca un soporte real 3+ veces con cuerpos significativos."""
    candles: list[dict] = []
    ts = 0
    body = 0.0020  # cuerpo amplio -> supera filtro de cuerpo mínimo

    def push(price_mid: float, low: float, high: float, bullish: bool):
        nonlocal ts
        if bullish:
            o, cl = price_mid - body / 2, price_mid + body / 2
        else:
            o, cl = price_mid + body / 2, price_mid - body / 2
        candles.append(_c(ts * M15, o, high, low, cl))
        ts += 1

    # 3 rebotes desde el soporte, con picos intermedios en el techo.
    for _ in range(3):
        # subida hacia el techo
        push(top - 0.0010, top - 0.0030, top + 0.0002, bullish=True)
        push(top - 0.0020, top - 0.0040, top, bullish=False)
        # descenso hasta rozar el soporte (swing low real)
        push(support + 0.0015, support - 0.0002, support + 0.0035, bullish=False)
        push(support + 0.0010, support, support + 0.0030, bullish=True)
        push(support + 0.0025, support + 0.0005, support + 0.0045, bullish=True)
    # padding para dar contexto a detect_swings (strength=3)
    for _ in range(6):
        push(top - 0.0015, top - 0.0035, top, bullish=True)
    return candles


def _flat_series(n: int = 40, price: float = 1.0) -> list[dict]:
    """Velas OTC planas: cuerpo ~0, sin swings reales."""
    return [_c(i * M15, price, price, price, price) for i in range(n)]


def test_range_detects_real_swing_low():
    candles = _range_with_support()
    ctx = compute_daily_geometry(candles, "EURJPY_otc")
    assert ctx["asset"] == "EURJPY_otc"
    assert ctx["swing_lows"], "debe detectar al menos un swing_low real"
    # el soporte tocado 3+ veces debe aparecer con touches>=2
    best = max(ctx["swing_lows"], key=lambda s: s["touches"])
    assert best["touches"] >= 2
    assert abs(best["price"] - 1.0000) < 0.0015


def test_flat_series_no_false_swings():
    candles = _flat_series()
    ctx = compute_daily_geometry(candles, "EURJPY_otc")
    assert ctx["swing_highs"] == []
    assert ctx["swing_lows"] == []
    assert ctx["sr_levels"] == []


def test_cache_returns_same_object_without_recompute(monkeypatch):
    calls = {"n": 0}
    real = mgc.detect_structure

    def counting(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(mgc, "detect_structure", counting)

    candles = _range_with_support()
    cache = GeometryCache(ttl_sec=900, time_fn=lambda: 1000.0)

    ctx1 = cache.get("EURJPY_otc", candles)
    ctx2 = cache.get("EURJPY_otc", candles)

    assert ctx1 is ctx2, "misma barra -> mismo objeto cacheado"
    assert calls["n"] == 1, "no debe recalcular en la 2ª llamada"


def test_cache_recomputes_on_new_bar():
    t = {"now": 0.0}
    cache = GeometryCache(ttl_sec=900, time_fn=lambda: t["now"])
    candles = _range_with_support()

    ctx1 = cache.get("EURJPY_otc", candles)
    # nueva vela (ts distinto) dentro del TTL -> recalcula
    candles2 = candles + [_c(candles[-1]["ts"] + M15, 1.005, 1.006, 1.004, 1.005)]
    ctx2 = cache.get("EURJPY_otc", candles2)
    assert ctx1 is not ctx2
    assert ctx2["last_ts"] == candles2[-1]["ts"]


def test_level_role_marks_support():
    candles = _range_with_support()
    ctx = compute_daily_geometry(candles, "EURJPY_otc")
    swing_low = min(ctx["swing_lows"], key=lambda s: s["price"])
    price = swing_low["price"]  # price ~ swing_low

    role = level_role(ctx, price)
    assert role["is_support"] is True
    assert role["is_resistance"] is False
    assert role["nearest_swing"] is not None
    assert role["distance_pct"] is not None and role["distance_pct"] >= 0


# ── Wiring end-to-end (T9): el scorer calcula geom desde candles_15m,
#    la puebla en entry.geometry, y el filtro de dirección la consume. ──
def test_scorer_wires_geometry_and_penalizes_put_at_support(monkeypatch):
    import entry_scorer
    from models import Candle, CandidateEntry, ConsolidationZone

    monkeypatch.setattr(entry_scorer, "MARKET_GEOMETRY_ENABLED", True)

    candles_15m = _range_with_support()  # soporte real ~1.0000
    # vela de entrada M1: mecha toca el piso 1.0000, cuerpo alcista (caso EURJPY)
    entry_candle = Candle(ts=999, open=1.0005, high=1.0030, low=1.0000, close=1.0025)
    zone = ConsolidationZone(
        asset="EURJPY_otc", ceiling=1.0100, floor=1.0000,
        bars_inside=10, detected_at=0.0, range_pct=0.01,
    )
    cand = CandidateEntry(
        asset="EURJPY_otc", payout=90, zone=zone,
        direction="put", candles=[entry_candle],
        candles_15m=[Candle(ts=c["ts"], open=c["o"], high=c["h"], low=c["l"], close=c["c"])
                      for c in candles_15m],
    )
    # score_candidate puebla entry.geometry y llama _score_extreme_direction(entry, geom)
    score = entry_scorer.score_candidate(cand, mode=entry_scorer.SignalMode.REBOUND)
    assert cand.geometry is not None, "el scorer debe poblar entry.geometry desde candles_15m"
    assert cand.geometry.get("swing_lows"), "geometría debe traer el soporte detectado"
    # PUT en el piso con cuerpo alcista => penalización por dirección equivocada
    assert cand.score_breakdown.get("extreme_direction") == entry_scorer.EXTREME_DIR_PENALTY
