"""Tests for scan loop alignment to 5m candle open."""
from __future__ import annotations

import loop_utils


def test_align_lead0_at_exact_open_returns_zero(monkeypatch):
    """phase==0 → wait 0 (scan immediately at candle open)."""
    monkeypatch.setattr(loop_utils, "ALIGN_SCAN_TO_CANDLE", True)
    monkeypatch.setattr(loop_utils, "SCAN_LEAD_SEC", 0.0)
    monkeypatch.setattr(loop_utils, "TF_5M", 300)

    # 2020-01-01 00:00:00 UTC — exact 5m boundary
    now = 1577836800.0
    assert int(now) % 300 == 0
    assert loop_utils.seconds_until_next_scan(now) == 0.0


def test_align_lead0_mid_candle_waits_until_next_open(monkeypatch):
    """phase=100 → wait ~200 until next open."""
    monkeypatch.setattr(loop_utils, "ALIGN_SCAN_TO_CANDLE", True)
    monkeypatch.setattr(loop_utils, "SCAN_LEAD_SEC", 0.0)
    monkeypatch.setattr(loop_utils, "TF_5M", 300)

    open_ts = 1577836800.0  # exact open
    now = open_ts + 100.0  # phase 100
    wait = loop_utils.seconds_until_next_scan(now)
    assert abs(wait - 200.0) < 0.01


def test_align_lead0_fractional_seconds(monkeypatch):
    """phase>0 with fractional now still waits until next open."""
    monkeypatch.setattr(loop_utils, "ALIGN_SCAN_TO_CANDLE", True)
    monkeypatch.setattr(loop_utils, "SCAN_LEAD_SEC", 0.0)
    monkeypatch.setattr(loop_utils, "TF_5M", 300)

    open_ts = 1577836800.0
    now = open_ts + 50.7  # phase 50
    wait = loop_utils.seconds_until_next_scan(now)
    # next_open - now = 300 - 50.7 = 249.3
    assert abs(wait - 249.3) < 0.01


def test_align_lead35_before_window(monkeypatch):
    """LEAD 35: mid-candle still before target → wait until next_open - 35."""
    monkeypatch.setattr(loop_utils, "ALIGN_SCAN_TO_CANDLE", True)
    monkeypatch.setattr(loop_utils, "SCAN_LEAD_SEC", 35.0)
    monkeypatch.setattr(loop_utils, "TF_5M", 300)

    open_ts = 1577836800.0
    # At phase 100: next_open = open+300, target = open+265, wait = 165
    now = open_ts + 100.0
    wait = loop_utils.seconds_until_next_scan(now)
    assert abs(wait - 165.0) < 0.01


def test_align_lead35_past_window_rolls_forward(monkeypatch):
    """LEAD 35: already past this cycle's lead window → roll to next cycle."""
    monkeypatch.setattr(loop_utils, "ALIGN_SCAN_TO_CANDLE", True)
    monkeypatch.setattr(loop_utils, "SCAN_LEAD_SEC", 35.0)
    monkeypatch.setattr(loop_utils, "TF_5M", 300)

    open_ts = 1577836800.0
    # At phase 280: target for this next_open is open+265, already past →
    # target = open+300+300-35 = open+565, wait = 565-280 = 285
    now = open_ts + 280.0
    wait = loop_utils.seconds_until_next_scan(now)
    assert abs(wait - 285.0) < 0.01


def test_align_false_returns_scan_interval(monkeypatch):
    """ALIGN False → max(5.0, SCAN_INTERVAL_SEC)."""
    monkeypatch.setattr(loop_utils, "ALIGN_SCAN_TO_CANDLE", False)
    monkeypatch.setattr(loop_utils, "SCAN_INTERVAL_SEC", 60)

    wait = loop_utils.seconds_until_next_scan(1577836800.0)
    assert wait == 60.0
