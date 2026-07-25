"""Tests del reemplazo de evaluación de S/R por ZONE STRENGTH (línea imaginaria).

Valida:
- compute_rebound_strength devuelve % de fuerza medible (no heurística).
- Una línea DÉBIL (poco histórico, veloz impacto) => sufficient=False.
- Una línea FUERTE (mucho histórico, order-flow, impacto suave) => sufficient=True.
- entry_scorer STRAT-F usa ZoneStrength y DESCALIFICA (score 0 + WEAK_LINE_STRENGTH)
  cuando la línea no es suficiente.
- No rompe cuando la memoria está vacía (determinista, sin red).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from models import Candle, ConsolidationZone, CandidateEntry, SignalMode


# ── Stub de memoria (Experience Engine) para tests deterministas ──
@dataclass
class _Exp:
    nivel: float
    decision: str  # WIN/LOSS
    hold: float

    def is_closed(self):
        return True

    @property
    def evento(self):
        return {"nivel": self.nivel}

    @property
    def resultado(self):
        return {"decision": self.decision}

    @property
    def evolucion(self):
        return {"tiempo_a_invalidacion_s": self.hold}


class _Mem:
    def __init__(self, exps):
        self._exps = exps

    def query_similar(self, profile, limit=200):
        return list(self._exps)


def _c(ts, o, h, l, c, ticks=0):
    return Candle(ts=ts, open=o, high=h, low=l, close=c, ticks=ticks)


def _zone(floor, ceiling, bars=20):
    return ConsolidationZone(
        asset="X", ceiling=ceiling, floor=floor, bars_inside=bars,
        detected_at=0.0, range_pct=0.0,
    )


# ─────────────────────────────────────────────────────────────────────
def _m15_candles(level, touch_idx, n=96):
    """Genera `n` velas M15: toca `level` en `touch_idx`, aguantan tras toque."""
    out = []
    ts = 0
    for i in range(n):
        if i in touch_idx:
            o = level - 0.3
            l = level - 0.02
            h = level + 0.5
            c = level + 0.4
        else:
            # rango normal BIEN lejos del nivel (>3 pts) para no caer en la
            # banda de tolerancia (level*0.0008 ≈ 1.1 pts en M15 real).
            off = 3.0 + (i % 5) * 0.5
            o = level + off
            l = level + off - 0.3
            h = l + 0.6
            c = o + 0.2
        out.append(_c(ts, o, h, l, c, ticks=5))
        ts += 900
    return out


def test_rebound_strength_weak_line_rejected():
    """CALL en piso con M15 bajando (ángulo negativo) y línea sin toques M15."""
    from zone_strength import compute_rebound_strength

    # Velas M15 que NO tocan el nivel => eficacia 0 => línea débil.
    c15 = _m15_candles(1381.54, touch_idx=set())
    mq = {"angle_deg": -9.57, "r_squared": 0.835, "hurst": 0.9}
    res = compute_rebound_strength(
        asset="USDNGN_otc", direction="CALL", level=1381.54,
        candles_15m=c15, math_quality=mq, mem=_Mem([]),
    )
    # Sin toques => eficacia 0 => línea fina => no suficiente.
    assert res["efficacy"] == 0.0, res
    assert res["line_thickness"] < 0.3, res
    assert res["sufficient"] is False, res
    assert 0.0 <= res["strength_pct"] <= 1.0


def test_rebound_strength_strong_line_accepted():
    """CALL en piso con 10 toques M15 que aguantan + llegada suave."""
    from zone_strength import compute_rebound_strength

    touch = {20, 40, 60, 80, 100, 110, 120, 130, 140, 150}
    c15 = _m15_candles(1381.54, touch_idx=touch, n=160)
    mq = {"angle_deg": -2.0, "r_squared": 0.9, "hurst": 0.6}
    res = compute_rebound_strength(
        asset="USDNGN_otc", direction="CALL", level=1381.54,
        candles_15m=c15, math_quality=mq, mem=_Mem([]),
    )
    assert res["efficacy_touch_count"] == 10, res
    assert res["efficacy_bounce_rate"] == 1.0, res
    assert res["line_thickness"] > 0.5, res
    assert res["sufficient"] is True, res
    assert res["strength_pct"] > 0.5, res


def test_rebound_strength_velocity_kills_weak_line():
    """Mismo grosor pero impacto empinado => fuerza baja."""
    from zone_strength import compute_rebound_strength

    touch = {20, 40, 60, 80, 100, 110, 120, 130, 140, 150}
    c15 = _m15_candles(1381.54, touch_idx=touch, n=160)
    mq_slow = {"angle_deg": -2.0}
    mq_fast = {"angle_deg": -24.0}
    slow = compute_rebound_strength(
        asset="X", direction="CALL", level=1381.54,
        candles_15m=c15, math_quality=mq_slow, mem=_Mem([]),
    )
    fast = compute_rebound_strength(
        asset="X", direction="CALL", level=1381.54,
        candles_15m=c15, math_quality=mq_fast, mem=_Mem([]),
    )
    assert fast["strength_pct"] < slow["strength_pct"], (slow, fast)


def test_entry_scorer_stratf_uses_zone_strength_and_rejects_weak():
    """STRAT-F con línea débil (sin toques M15) => score 0 + WEAK_LINE_STRENGTH."""
    from entry_scorer import score_candidate

    c15 = _m15_candles(1381.54, touch_idx=set())  # sin toques => débil
    entry = CandidateEntry(
        asset="USDNGN_otc", payout=93, zone=_zone(1381.50, 1381.60),
        direction="CALL", candles=[_c(1, 1381.6, 1381.7, 1381.50, 1381.54, ticks=2)],
        mode=SignalMode.REBOUND,
    )
    entry._strategy_origin = "STRAT-F"
    entry._reversal_strength = 0.86
    entry.math_quality = {"angle_deg": -9.57, "r_squared": 0.835, "hurst": 0.9}
    entry.score_breakdown = {"payout": 20.0}
    entry.candles_15m = c15

    score = score_candidate(entry)
    assert score == 0.0, entry.score_breakdown
    assert entry.reject_reason == "WEAK_LINE_STRENGTH", entry.score_breakdown
    assert "rebound_strength_pct" in entry.score_breakdown


def test_entry_scorer_stratf_accepts_strong_line():
    """STRAT-F con línea fuerte (10 toques M15 que aguantan) => score > 0."""
    from entry_scorer import score_candidate

    touch = {20, 40, 60, 80, 100, 110, 120, 130, 140, 150}
    c15 = _m15_candles(1381.54, touch_idx=touch, n=160)
    entry = CandidateEntry(
        asset="USDNGN_otc", payout=93, zone=_zone(1381.50, 1381.60),
        direction="CALL", candles=[_c(1, 1381.6, 1381.7, 1381.50, 1381.62, ticks=55)],
        mode=SignalMode.REBOUND,
    )
    entry._strategy_origin = "STRAT-F"
    entry._reversal_strength = 0.86
    entry.math_quality = {"angle_deg": -2.0, "r_squared": 0.9, "hurst": 0.6}
    entry.score_breakdown = {"payout": 20.0}
    entry.candles_15m = c15

    score = score_candidate(entry)
    assert score > 0.0, entry.score_breakdown
    assert entry.reject_reason is None, entry.score_breakdown
    assert entry.score_breakdown.get("rebound_strength_pct", 0) > 0.5



def test_support_efficacy_real_3d_m15():
    """Eficacia estructural sobre 288 velas M15 (3 días) con soporte real."""
    from zone_strength import compute_support_efficacy
    from models import Candle

    level = 100.0
    # 288 velas: soporte en 100.0 con EXACTAMENTE 10 toques (índices pares
    # de un conjunto acotado), todos aguantan (cierran arriba del nivel).
    touch_at = [20, 60, 100, 140, 180, 200, 220, 240, 260, 280]
    candles = []
    ts = 0
    for i in range(288):
        if i in touch_at:
            # toca el suelo en 100.0 y cierra arriba => rebote que aguanta
            o = level - 0.3
            l = level - 0.02
            h = level + 0.5
            c = level + 0.4
        else:
            # rango normal por encima del nivel, BIEN lejos (>3 pts) para no
            # caer en la banda de tolerancia (level*0.0008 ≈ 0.08 pts aquí).
            o = level + 3.0 + (i % 5) * 0.5
            l = level + 3.0 + (i % 5) * 0.5 - 0.3
            h = l + 0.6
            c = o + 0.2
        candles.append(Candle(ts=ts, open=o, high=h, low=l, close=c, ticks=5))
        ts += 900
    eff = compute_support_efficacy(level, candles, direction="CALL")
    assert eff["touch_count"] == 10, eff
    assert eff["bounce_count"] == 10, eff  # todos aguantaron
    assert eff["bounce_rate"] == 1.0, eff
    assert eff["efficacy"] > 0.5, eff


def test_support_efficacy_fast_timing():
    """Cálculo de eficacia sobre 288 velas debe ser < 5ms (no alenta el scan)."""
    import time
    from zone_strength import compute_support_efficacy
    from models import Candle

    level = 50.0
    candles = [
        Candle(ts=i * 900, open=level, high=level + 1, low=level - 0.02, close=level + 0.3, ticks=4)
        if i % 30 == 0 else
        Candle(ts=i * 900, open=level + 1, high=level + 1.5, low=level + 0.5, close=level + 1.2, ticks=4)
        for i in range(288)
    ]
    t0 = time.perf_counter()
    for _ in range(50):
        compute_support_efficacy(level, candles, direction="CALL")
    dt = (time.perf_counter() - t0) / 50
    assert dt < 0.005, f"eficacia lenta: {dt*1000:.1f}ms"
