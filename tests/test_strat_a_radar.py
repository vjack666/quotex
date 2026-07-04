"""Tests unitarios del radar STRAT-A (readiness + tick)."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle, ConsolidationZone
import scanner as scanner_mod
from scanner import AssetScanner
from strat_a_radar import (
    RadarWatchEntry,
    compute_readiness,
    rank_and_trim,
    should_watch,
)


def _zone(age_min: float = 18.0, ceiling: float = 1.1000, floor: float = 1.0950) -> ConsolidationZone:
    return ConsolidationZone(
        asset="EURUSD_otc",
        ceiling=ceiling,
        floor=floor,
        bars_inside=15,
        detected_at=time.time() - age_min * 60,
        range_pct=0.002,
    )


def test_compute_readiness_mature_zone_at_ceiling():
    zone = _zone(age_min=18.0)
    price = zone.ceiling
    score = compute_readiness(
        zone,
        price,
        payout=85,
        entry_mode="rebound_ceiling",
        stage="initial",
        dynamic_touch_tolerance=0.00035,
    )
    assert score >= 70.0


def test_should_watch_rejects_young_zone():
    zone = _zone(age_min=10.0)
    price = zone.ceiling
    assert not should_watch(
        zone,
        price,
        entry_mode="rebound_ceiling",
        stage="initial",
        dynamic_touch_tolerance=0.00035,
    )


def test_rank_and_trim_respects_max_watch():
    entries = [
        RadarWatchEntry(
            asset=f"SYM{i}_otc",
            payout=85,
            zone=_zone(),
            direction="put",
            entry_mode="rebound_ceiling",
            stage="initial",
            readiness_score=70.0 + i,
            side_label="techo",
        )
        for i in range(8)
    ]
    trimmed = rank_and_trim(entries, max_watch=5, min_readiness=70.0)
    assert len(trimmed) == 5
    assert trimmed[0].readiness_score >= trimmed[-1].readiness_score


@pytest.mark.asyncio
async def test_radar_watch_tick_no_crash(monkeypatch):
    class FakeBot:
        def __init__(self):
            self.client = MagicMock()
            self.dry_run = True
            self.trades = {}
            self.stats = {"entries": 0, "scans": 1}
            self.zones = {}
            self.pending_reversals = {}
            self.order_blocks_by_asset = {}
            self.ma_state_by_asset = {}
            self.candle_cache = MagicMock()
            zone = _zone()
            self.radar_watchlist = {
                "EURUSD_otc": RadarWatchEntry(
                    asset="EURUSD_otc",
                    payout=85,
                    zone=zone,
                    direction="put",
                    entry_mode="rebound_ceiling",
                    stage="initial",
                    readiness_score=82.0,
                    side_label="techo",
                ),
            }
            self.zones["EURUSD_otc"] = zone

    bot = FakeBot()
    executor = MagicMock()
    executor.refresh_balance_and_risk = AsyncMock(return_value=False)
    scanner = AssetScanner(bot, executor)

    def _candle(ts: int, price: float) -> Candle:
        return Candle(ts=ts, open=price, high=price + 0.001, low=price - 0.001, close=price)

    async def fake_cache_get(client, asset, tf, count):
        if tf == 60:
            return [_candle(i * 60, 1.1000) for i in range(36)]
        return [_candle(i * 300, 1.0995) for i in range(20)]

    bot.candle_cache.get_or_update = AsyncMock(side_effect=fake_cache_get)
    monkeypatch.setattr(scanner, "_scan_phase_select_execute", AsyncMock())
    monkeypatch.setattr(
        "scanner.evaluate_strat_a",
        lambda **kwargs: MagicMock(
            has_signal=False,
            pending_reversal_hint=None,
            direction="put",
            entry_mode="rebound_ceiling",
            stage="initial",
            skip_reason="pattern_insufficient",
        ),
    )

    result = await scanner.radar_watch_tick()
    assert result is False


def _trending_15m_candles(n: int = 60, *, bullish: bool, base: float = 1.10) -> list[Candle]:
    candles: list[Candle] = []
    for i in range(n):
        drift = i * (0.00015 if bullish else -0.00015)
        price = base + drift
        body = 0.00005 if bullish else -0.00005
        close = price + body
        candles.append(
            Candle(
                ts=i * 900,
                open=price,
                high=max(price, close) + 0.0001,
                low=min(price, close) - 0.0001,
                close=close,
            )
        )
    return candles


@pytest.mark.asyncio
async def test_radar_watch_tick_rejects_htf_misaligned(monkeypatch, caplog):
    """R10: radar con has_signal=True veta HTF misaligned — 0 candidatos + log STRAT-A."""
    class FakeHTFScanner:
        def get_candles_15m(self, sym: str) -> list:
            return _trending_15m_candles(60, bullish=True)

    class FakeBot:
        def __init__(self):
            self.client = MagicMock()
            self.dry_run = True
            self.trades = {}
            self.stats = {"entries": 0, "scans": 1, "skipped": 0}
            self.zones = {}
            self.pending_reversals = {}
            self.order_blocks_by_asset = {}
            self.ma_state_by_asset = {}
            self.candle_cache = MagicMock()
            self.htf_scanner = FakeHTFScanner()
            zone = _zone()
            self.radar_watchlist = {
                "EURUSD_otc": RadarWatchEntry(
                    asset="EURUSD_otc",
                    payout=88,
                    zone=zone,
                    direction="put",
                    entry_mode="rebound_ceiling",
                    stage="initial",
                    readiness_score=82.0,
                    side_label="techo",
                ),
            }
            self.zones["EURUSD_otc"] = zone

    bot = FakeBot()
    executor = MagicMock()
    executor.refresh_balance_and_risk = AsyncMock(return_value=False)
    scanner = AssetScanner(bot, executor)

    monkeypatch.setattr(scanner_mod._runtime_config, "STRAT_A_ONLY", True)

    def _candle(ts: int, price: float) -> Candle:
        return Candle(ts=ts, open=price, high=price + 0.001, low=price - 0.001, close=price)

    async def fake_cache_get(client, asset, tf, count):
        if tf == 60:
            return [_candle(i * 60, 1.1000) for i in range(36)]
        if tf == 300:
            return [_candle(i * 300, 1.0995) for i in range(20)]
        return [_candle(i * 3600, 1.10) for i in range(10)]

    bot.candle_cache.get_or_update = AsyncMock(side_effect=fake_cache_get)
    monkeypatch.setattr(scanner, "_scan_phase_select_execute", AsyncMock())
    monkeypatch.setattr(
        "scanner.evaluate_strat_a",
        lambda **kwargs: MagicMock(
            has_signal=True,
            pending_reversal_hint=None,
            direction="put",
            entry_mode="rebound_ceiling",
            stage="initial",
            skip_reason=None,
        ),
    )

    with caplog.at_level("INFO", logger="scanner"):
        result = await scanner.radar_watch_tick()

    assert result is False
    assert "⛔ [STRAT-A]" in caplog.text
    assert bot.stats["skipped"] >= 1