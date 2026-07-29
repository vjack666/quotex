"""Tests for multi-TF confluence scoring (pure functions)."""
from __future__ import annotations

import sys
from collections import namedtuple
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
ROOT = Path(__file__).resolve().parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_tf_correlation import (
    detect_trend,
    calculate_confluence,
    compute_confluence_bonus,
)

Candle = namedtuple("Candle", ["ts", "open", "high", "low", "close"])


def _c(ts: int, o: float, h: float, l: float, c: float) -> Candle:
    return Candle(ts=ts, open=o, high=h, low=l, close=c)


# ---------------------------------------------------------------------------
# detect_trend
# ---------------------------------------------------------------------------


class TestDetectTrend:
    def test_clearly_bullish(self):
        candles = [_c(i, 1.00 + i * 0.005, 1.01 + i * 0.005, 0.99 + i * 0.005, 1.005 + i * 0.005) for i in range(10)]
        assert detect_trend(candles) == "CALL"

    def test_clearly_bearish(self):
        candles = [_c(i, 1.10 - i * 0.005, 1.11 - i * 0.005, 1.09 - i * 0.005, 1.095 - i * 0.005) for i in range(10)]
        assert detect_trend(candles) == "PUT"

    def test_neutral_flat(self):
        candles = [_c(i, 1.00, 1.01, 0.99, 1.00) for i in range(10)]
        assert detect_trend(candles) == "NEUTRAL"

    def test_insufficient_data(self):
        candles = [_c(0, 1.0, 1.01, 0.99, 1.0), _c(1, 1.0, 1.01, 0.99, 1.0)]
        assert detect_trend(candles) == "NEUTRAL"

    def test_empty_list(self):
        assert detect_trend([]) == "NEUTRAL"

    def test_threshold_configurable(self):
        """A small upward slope is CALL with default threshold, NEUTRAL with high threshold."""
        candles = [_c(i, 1.00 + i * 0.0002, 1.01 + i * 0.0002, 0.99 + i * 0.0002, 1.0002 + i * 0.0002) for i in range(10)]
        result_default = detect_trend(candles, threshold=0.001)
        result_high = detect_trend(candles, threshold=0.01)
        # Slope is tiny — should be NEUTRAL with default and also with high
        assert result_default == "NEUTRAL"
        assert result_high == "NEUTRAL"

    def test_strong_slope_high_threshold(self):
        """Very strong slope should be CALL even with a higher threshold."""
        candles = [_c(i, 1.00 + i * 0.01, 1.01 + i * 0.01, 0.99 + i * 0.01, 1.005 + i * 0.01) for i in range(10)]
        assert detect_trend(candles, threshold=0.005) == "CALL"


# ---------------------------------------------------------------------------
# calculate_confluence
# ---------------------------------------------------------------------------


class TestCalculateConfluence:
    def test_4of4_aligned_call(self):
        trends = {"M1": "CALL", "M5": "CALL", "M15": "CALL", "H1": "CALL"}
        label, bonus = calculate_confluence(trends, h1_available=True)
        assert bonus == 0.15
        assert "CALL" in label
        assert "4/4" in label

    def test_4of4_aligned_put(self):
        trends = {"M1": "PUT", "M5": "PUT", "M15": "PUT", "H1": "PUT"}
        label, bonus = calculate_confluence(trends, h1_available=True)
        assert bonus == 0.15
        assert "PUT" in label
        assert "4/4" in label

    def test_3of4_call(self):
        trends = {"M1": "CALL", "M5": "CALL", "M15": "CALL", "H1": "PUT"}
        label, bonus = calculate_confluence(trends, h1_available=True)
        assert bonus == 0.05
        assert "3/4" in label

    def test_2of4_conflict(self):
        trends = {"M1": "CALL", "M5": "PUT", "M15": "CALL", "H1": "PUT"}
        label, bonus = calculate_confluence(trends, h1_available=True)
        assert bonus == -0.05
        assert "MIXED" in label

    def test_all_neutral(self):
        trends = {"M1": "NEUTRAL", "M5": "NEUTRAL", "M15": "NEUTRAL", "H1": "NEUTRAL"}
        label, bonus = calculate_confluence(trends, h1_available=True)
        assert bonus == -0.05
        assert "NO_ALIGN" in label

    def test_h1_unavailable_3of3(self):
        trends = {"M1": "CALL", "M5": "CALL", "M15": "CALL"}
        label, bonus = calculate_confluence(trends, h1_available=False)
        assert bonus == 0.10
        assert "3/3" in label

    def test_h1_unavailable_2of3(self):
        trends = {"M1": "CALL", "M5": "PUT", "M15": "CALL"}
        label, bonus = calculate_confluence(trends, h1_available=False)
        assert bonus == 0.03
        assert "2/3" in label

    def test_h1_unavailable_1of3(self):
        trends = {"M1": "CALL", "M5": "NEUTRAL", "M15": "NEUTRAL"}
        label, bonus = calculate_confluence(trends, h1_available=False)
        assert bonus == -0.03

    def test_partial_neutral_3of4(self):
        """One NEUTRAL TF should not count; remaining 3 aligned -> +0.05."""
        trends = {"M1": "CALL", "M5": "CALL", "M15": "NEUTRAL", "H1": "CALL"}
        label, bonus = calculate_confluence(trends, h1_available=True)
        assert bonus == 0.05
        assert "3/4" in label


# ---------------------------------------------------------------------------
# compute_confluence_bonus (integration)
# ---------------------------------------------------------------------------


def _make_candles(start_price: float, slope: float, n: int = 10) -> list[Candle]:
    """Build n candles with a given linear slope on close prices."""
    return [
        _c(i, start_price + i * slope - abs(slope) * 0.1,
           start_price + i * slope + abs(slope) * 0.3,
           start_price + i * slope - abs(slope) * 0.3,
           start_price + i * slope)
        for i in range(n)
    ]


class TestComputeConfluenceBonus:
    def test_all_aligned_with_h1(self):
        up = _make_candles(1.0, 0.005)
        label, bonus, details = compute_confluence_bonus(up, up, up, candles_1h=up)
        assert bonus == 0.15
        assert details["M1"] == "CALL"
        assert details["H1"] == "CALL"

    def test_all_aligned_without_h1(self):
        up = _make_candles(1.0, 0.005)
        label, bonus, details = compute_confluence_bonus(up, up, up, candles_1h=None)
        assert bonus == 0.10
        assert "H1" not in details

    def test_conflicting_trends(self):
        up = _make_candles(1.0, 0.005)
        down = _make_candles(1.0, -0.005)
        flat = _make_candles(1.0, 0.0)
        label, bonus, details = compute_confluence_bonus(up, down, flat, candles_1h=down)
        assert bonus == -0.05
        assert "MIXED" in label

    def test_threshold_boundary(self):
        """Candles with slope exactly at threshold -> NEUTRAL."""
        exact = [_c(i, 1.000, 1.002, 0.998, 1.000) for i in range(10)]
        _, _, details = compute_confluence_bonus(exact, exact, exact)
        assert details["M1"] == "NEUTRAL"
        assert details["M5"] == "NEUTRAL"
        assert details["M15"] == "NEUTRAL"

    def test_returns_three_tuple(self):
        up = _make_candles(1.0, 0.005)
        result = compute_confluence_bonus(up, up, up)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[2], dict)

    def test_custom_threshold(self):
        """A marginal slope that is CALL with low threshold should be NEUTRAL with high."""
        marginal = [_c(i, 1.000 + i * 0.0003, 1.002, 0.998, 1.000 + i * 0.0003) for i in range(10)]
        _, _, details_low = compute_confluence_bonus(marginal, marginal, marginal, threshold=0.0001)
        _, _, details_high = compute_confluence_bonus(marginal, marginal, marginal, threshold=0.01)
        assert details_low["M1"] == "CALL"
        assert details_high["M1"] == "NEUTRAL"
