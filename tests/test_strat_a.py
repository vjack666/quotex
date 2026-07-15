"""Tests unitarios de strat_a (lógica pura)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from candle_patterns import CandleSignal
from models import Candle, ConsolidationZone
import config
from strat_a import (
    broke_above,
    detect_consolidation,
    evaluate_strat_a,
    price_at_ceiling,
    validate_rejection_candle,
)


def _flat_candle(ts: int, price: float, body: float = 0.0001) -> Candle:
    return Candle(ts=ts, open=price, high=price + body, low=price - body, close=price + body)


def _make_tight_consolidation(n: int = 15, base: float = 1.1000) -> list[Candle]:
    candles = []
    for i in range(n):
        p = base + (0.0001 if i % 2 == 0 else -0.0001)
        candles.append(_flat_candle(1000 + i * 300, p, 0.00005))
    return candles


def _zone(
    ceiling: float = 1.1000,
    floor: float = 1.0950,
    age_min: float = 30.0,
) -> ConsolidationZone:
    return ConsolidationZone(
        asset="EURUSD",
        ceiling=ceiling,
        floor=floor,
        bars_inside=15,
        detected_at=time.time() - age_min * 60,
        range_pct=0.005,
    )


def _base_5m_history(ceiling: float = 1.1000, floor: float = 1.0950) -> list[Candle]:
    mid = (ceiling + floor) / 2
    return [
        Candle(ts=i, open=mid, high=mid + 0.0002, low=mid - 0.0002, close=mid)
        for i in range(14)
    ]


def _valid_put_rejection_1m() -> list[Candle]:
    return [
        Candle(ts=1, open=1.0, high=1.01, low=0.99, close=1.0),
        Candle(ts=2, open=1.010, high=1.015, low=1.000, close=1.002),
        Candle(ts=3, open=1.002, high=1.003, low=1.001, close=1.002),
    ]


def _valid_call_rejection_1m() -> list[Candle]:
    return [
        Candle(ts=1, open=1.0, high=1.01, low=0.99, close=1.0),
        Candle(ts=2, open=1.0, high=1.02, low=0.99, close=1.015),
        Candle(ts=3, open=1.01, high=1.02, low=1.0, close=1.018),
    ]


def test_detect_consolidation_valid_zone():
    candles = _make_tight_consolidation()
    zone = detect_consolidation(candles, max_range_pct=0.01)
    assert zone is not None
    assert zone.ceiling >= zone.floor
    assert zone.bars_inside >= 12


def test_broke_above_detects_breakout():
    ceiling = 1.1050
    candle = Candle(ts=1, open=1.1040, high=1.1060, low=1.1030, close=1.1060)
    assert broke_above(candle, ceiling) is True


def test_price_at_ceiling_within_tolerance():
    assert price_at_ceiling(1.1000, 1.1000, tolerance_pct=0.001) is True


def test_validate_rejection_candle_call_ok():
    candles = _valid_call_rejection_1m()
    ok, reason = validate_rejection_candle(candles, "call")
    assert ok is True
    assert reason == ""


def test_strat_a_no_side_effects(monkeypatch):
    """R3: evaluate_strat_a sin I/O de red ni archivos."""
    called = {"network": False}

    def fake_import(name, *args, **kwargs):
        if name == "pyquotex" or name.startswith("pyquotex."):
            called["network"] = True
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", fake_import)

    zone = _zone()
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0995, high=1.1000, low=1.0990, close=1.1000),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=_valid_put_rejection_1m(),
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        pattern_signal=CandleSignal("shooting_star", 0.70, True),
    )
    assert ev is not None
    assert called["network"] is False


def test_evaluate_strat_a_rebound_ceiling_put():
    zone = _zone(ceiling=1.1000, floor=1.0950)
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0998, high=1.1001, low=1.0995, close=1.1000),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=_valid_put_rejection_1m(),
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        h1_confirm_enabled=False,
        pattern_signal=CandleSignal("shooting_star", 0.70, True),
    )
    assert ev.has_signal is True
    assert ev.direction == "put"
    assert ev.entry_mode == "rebound_ceiling"
    assert ev.rejection_ok is True


def test_evaluate_strat_a_rebound_floor_call():
    zone = _zone(ceiling=1.1000, floor=1.0950)
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0952, high=1.0955, low=1.0948, close=1.0950),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=_valid_call_rejection_1m(),
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        h1_confirm_enabled=False,
        pattern_signal=CandleSignal("hammer", 0.65, True),
    )
    assert ev.has_signal is True
    assert ev.direction == "call"
    assert ev.entry_mode == "rebound_floor"


def test_evaluate_strat_a_bullish_engulfing_call_rebound():
    zone = _zone(ceiling=1.1000, floor=1.0950)
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0952, high=1.0955, low=1.0948, close=1.0950),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=_valid_call_rejection_1m(),
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        h1_confirm_enabled=False,
        pattern_signal=CandleSignal("bullish_engulfing", 0.75, True),
    )
    assert ev.has_signal is True
    assert ev.direction == "call"
    assert ev.entry_mode == "rebound_floor"
    assert ev.confirms is True


def test_evaluate_strat_a_breakout_above_with_volume():
    ceiling, floor = 1.1000, 1.0950
    zone = _zone(ceiling=ceiling, floor=floor)
    history = [
        Candle(ts=i, open=1.0975, high=1.0980, low=1.0970, close=1.0975)
        for i in range(14)
    ]
    breakout = Candle(ts=14, open=1.1005, high=1.1025, low=1.1000, close=1.1020)
    ev = evaluate_strat_a(
        candles_5m=history + [breakout],
        candles_1m=[],
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        h1_confirm_enabled=False,
    )
    assert ev.has_signal is True
    assert ev.direction == "call"
    assert ev.entry_mode == "breakout_above"
    assert ev.stage == "breakout"
    assert ev.breakout_strength_ok is True
    assert ev.skip_zone_age_check is True


def test_evaluate_strat_a_breakout_below_with_volume():
    ceiling, floor = 1.1000, 1.0950
    zone = _zone(ceiling=ceiling, floor=floor)
    history = [
        Candle(ts=i, open=1.0975, high=1.0980, low=1.0970, close=1.0975)
        for i in range(14)
    ]
    breakout = Candle(ts=14, open=1.0945, high=1.0950, low=1.0930, close=1.0935)
    ev = evaluate_strat_a(
        candles_5m=history + [breakout],
        candles_1m=[],
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        h1_confirm_enabled=False,
    )
    assert ev.has_signal is True
    assert ev.direction == "put"
    assert ev.entry_mode == "breakout_below"
    assert ev.breakout_strength_ok is True
    assert ev.skip_zone_age_check is True


def test_credible_break_accepts_normal_breakout():
    from strat_a import is_credible_zone_break

    zone = _zone(ceiling=1.1000, floor=1.0950)
    history = [
        Candle(ts=i, open=1.0975, high=1.0980, low=1.0970, close=1.0975)
        for i in range(14)
    ]
    breakout = Candle(ts=14, open=1.0945, high=1.0950, low=1.0930, close=1.0935)
    ok, why = is_credible_zone_break(
        breakout, history + [breakout], zone, side="below",
    )
    assert ok is True
    assert why == ""


def test_credible_break_rejects_otc_glitch_like_nzdjpy():
    """93→83 style spike must NOT kill the zone as BROKEN_BELOW."""
    from strat_a import is_credible_zone_break, evaluate_strat_a

    zone = _zone(ceiling=93.125, floor=92.826)
    history = [
        Candle(ts=i, open=92.90, high=92.95, low=92.85, close=92.90)
        for i in range(14)
    ]
    glitch = Candle(ts=14, open=83.14, high=83.53, low=83.03, close=83.36)
    ok, why = is_credible_zone_break(glitch, history + [glitch], zone, side="below")
    assert ok is False
    assert "spike" in why

    ev = evaluate_strat_a(
        candles_5m=history + [glitch],
        candles_1m=[],
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        h1_confirm_enabled=False,
    )
    # No breakout signal / no zone kill path
    assert ev.entry_mode != "breakout_below"
    assert ev.stage != "breakout" or not ev.has_signal


def test_evaluate_strat_a_rejects_young_zone_rebound():
    zone = _zone(age_min=5.0)
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0998, high=1.1001, low=1.0995, close=1.1000),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=_valid_put_rejection_1m(),
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        zone_age_rebound_min=20,
        pattern_signal=CandleSignal("shooting_star", 0.70, True),
    )
    assert ev.has_signal is False
    assert ev.skip_reason == "zone_too_young"


def test_evaluate_strat_a_no_direction_in_range_center():
    zone = _zone()
    mid = (zone.ceiling + zone.floor) / 2
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=mid, high=mid + 0.0001, low=mid - 0.0001, close=mid),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=[],
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
    )
    assert ev.has_signal is False
    assert ev.entry_mode == "none"
    assert ev.direction is None
    assert ev.skip_reason == "no_direction"


def test_evaluate_strat_a_rejection_candle_emits_pending_hint():
    zone = _zone()
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0998, high=1.1001, low=1.0995, close=1.1000),
    ]
    bad_1m = [
        Candle(ts=1, open=1.0, high=1.01, low=0.99, close=1.0),
        Candle(ts=2, open=1.0, high=1.02, low=0.99, close=1.015),
        Candle(ts=3, open=1.01, high=1.02, low=1.0, close=1.018),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=bad_1m,
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        pattern_signal=CandleSignal("shooting_star", 0.70, True),
    )
    assert ev.has_signal is False
    assert ev.skip_reason == "rejection_candle_fail"
    assert ev.pending_reversal_hint is not None
    assert ev.pending_reversal_hint.proposed_direction == "put"
    assert ev.pending_reversal_hint.entry_mode == "rebound_ceiling"


def test_evaluate_strat_a_put_pattern_blacklisted_emits_pending_hint():
    zone = _zone()
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0998, high=1.1001, low=1.0995, close=1.1000),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=_valid_put_rejection_1m(),
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        pattern_signal=CandleSignal("bearish_engulfing", 0.80, True),
    )
    assert ev.has_signal is False
    assert ev.skip_reason == "put_pattern_blacklisted"
    assert ev.pending_reversal_hint is not None
    assert ev.pending_reversal_hint.conflicting_pattern == "bearish_engulfing"


def test_evaluate_strat_a_h1_conflict_skips_signal():
    zone = _zone()
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0998, high=1.1001, low=1.0995, close=1.1000),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=_valid_put_rejection_1m(),
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        h1_trend="bullish",
        h1_confirm_enabled=True,
        pattern_signal=CandleSignal("shooting_star", 0.70, True),
    )
    assert ev.has_signal is False
    assert ev.skip_reason == "h1_conflict"


def test_config_strat_a_quality_constants():
    assert config.STRAT_A_MIN_PAYOUT == 87
    assert config.STRAT_A_MIN_SCORE == 75
    assert config.STRAT_A_ZONE_MIN_AGE_REBOUND == 30
    assert config.MIN_PAYOUT == 80


def test_evaluate_strat_a_rejects_rebound_zone_under_30min():
    zone = _zone(age_min=25.0)
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0998, high=1.1001, low=1.0995, close=1.1000),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=_valid_put_rejection_1m(),
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        h1_confirm_enabled=False,
        pattern_signal=CandleSignal("shooting_star", 0.70, True),
    )
    assert ev.has_signal is False
    assert ev.skip_reason == "zone_too_young"


def test_evaluate_strat_a_rebound_rejects_missing_pattern():
    zone = _zone()
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0998, high=1.1001, low=1.0995, close=1.1000),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=_valid_put_rejection_1m(),
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        h1_confirm_enabled=False,
        pattern_signal=CandleSignal("none", 0.0, False),
    )
    assert ev.has_signal is False
    assert ev.skip_reason == "pattern_missing"
    assert ev.pending_reversal_hint is not None


def test_evaluate_strat_a_score_adjustments_on_confirmed_pattern():
    zone = _zone()
    candles_5m = _base_5m_history() + [
        Candle(ts=14, open=1.0998, high=1.1001, low=1.0995, close=1.1000),
    ]
    ev = evaluate_strat_a(
        candles_5m=candles_5m,
        candles_1m=_valid_put_rejection_1m(),
        zone=zone,
        blocks={"bull": [], "bear": []},
        ma_state=None,
        dynamic_touch_tolerance=0.001,
        h1_confirm_enabled=False,
        pattern_signal=CandleSignal("shooting_star", 0.72, True),
    )
    assert ev.has_signal is True
    assert ev.score_adjustments.reversal_bonus == 8.0