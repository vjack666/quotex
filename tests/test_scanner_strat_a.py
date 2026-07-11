"""E2E y pending_reversals STRAT-A — scanner con mocks."""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from candle_patterns import CandleSignal
from models import Candle, CandidateEntry, ConsolidationZone, OrderBlock, PendingReversal
from scan_prefetch import ScanCycleData
import scanner as scanner_mod
import strat_a as strat_a_mod
from entry_scorer import select_best
from scanner import AssetScanner
from strat_a import detect_consolidation


class FakeHTFScanner:
    def __init__(self, candles_map: dict[str, list] | None = None, default: list | None = None):
        self._map = candles_map or {}
        self._default = default if default is not None else []

    def get_candles_15m(self, sym: str) -> list:
        return self._map.get(sym, self._default)


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


class FakeBot:
    def __init__(self, greylist: set[str] | None = None):
        self.client = MagicMock()
        self.dry_run = True
        self.account_type = "PRACTICE"
        self.zones = {}
        self.broken_zones = {}
        self.trades = {}
        self.stats = {
            "scans": 0,
            "skipped": 0,
            "expired_zones": 0,
            "filtered_sensor": 0,
            "rejected_young_zone": 0,
            "score_rejected_age": 0,
            "score_rejected_score": 0,
        }
        self.greylist_assets = greylist or set()
        self.failed_assets = {}
        self.pending_reversals = {}
        self.pending_martin = {}
        self.last_known_price = {}
        self.order_blocks_by_asset = {}
        self.ma_state_by_asset = {}
        self.watched_candidates = {}
        self.capture_dir = Path(__file__).parent / "_tmp_capture_strat_a"
        self.capture_dir.mkdir(exist_ok=True)
        self._followup_capture_tasks = set()
        self.compensation_pending = False
        self.last_closed_amount = 0.0
        self.last_closed_outcome = ""
        self.accepted_scans_window = __import__("collections").deque(maxlen=10)
        self.current_score_threshold = 65
        self.asset_blacklist_until = {}
        self._trade_tasks = set()
        self.radar_watchlist = {}
        self.htf_scanner = FakeHTFScanner()


def _candle(ts: int, price: float, body: float = 0.0001) -> Candle:
    return Candle(
        ts=ts,
        open=price,
        high=price + body,
        low=price - body,
        close=price + body,
    )


def _base_consolidation_body(n: int = 14) -> list[Candle]:
    ceiling, floor = 1.1000, 1.0950
    mid = (ceiling + floor) / 2
    candles: list[Candle] = []
    for i in range(n):
        if i == 0:
            p, hi, lo = floor, floor + 0.0003, floor - 0.0001
        elif i == 1:
            p, hi, lo = ceiling, ceiling + 0.0001, ceiling - 0.0003
        else:
            p = mid + (0.0001 if i % 2 == 0 else -0.0001)
            hi = min(p + 0.0002, ceiling + 0.0001)
            lo = max(p - 0.0002, floor - 0.0001)
        candles.append(Candle(ts=i * 300, open=p, high=hi, low=lo, close=p))
    return candles


def _consolidation_candles_5m_at_ceiling(n: int = 15) -> tuple[list[Candle], ConsolidationZone]:
    body = _base_consolidation_body(n - 1)
    probe = detect_consolidation(body)
    assert probe is not None
    last = Candle(
        ts=(n - 1) * 300,
        open=probe.ceiling - 0.0002,
        high=probe.ceiling + 0.00005,
        low=probe.ceiling - 0.0005,
        close=probe.ceiling,
    )
    candles = body + [last]
    zone = detect_consolidation(candles)
    assert zone is not None
    return candles, zone


def _consolidation_candles_5m_breakout(n: int = 15) -> tuple[list[Candle], ConsolidationZone]:
    body = _base_consolidation_body(n - 1)
    probe = detect_consolidation(body)
    assert probe is not None
    last = Candle(
        ts=(n - 1) * 300,
        open=probe.ceiling + 0.0005,
        high=probe.ceiling + 0.0025,
        low=probe.ceiling,
        close=probe.ceiling + 0.0020,
    )
    candles = body + [last]
    zone = detect_consolidation(candles)
    assert zone is not None
    return candles, zone


def _patch_shooting_star(monkeypatch) -> None:
    signal = CandleSignal("shooting_star", 0.70, True)

    def _fake(_candles, _direction):
        return signal

    monkeypatch.setattr(strat_a_mod, "detect_reversal_pattern", _fake)
    monkeypatch.setattr(scanner_mod, "detect_reversal_pattern", _fake)


def _valid_put_rejection_1m() -> list[Candle]:
    return [
        Candle(ts=1, open=1.0, high=1.01, low=0.99, close=1.0),
        Candle(ts=2, open=1.010, high=1.015, low=1.000, close=1.002),
        Candle(ts=3, open=1.002, high=1.003, low=1.001, close=1.002),
    ]


def _invalid_put_rejection_1m() -> list[Candle]:
    return [
        Candle(ts=1, open=1.0, high=1.01, low=0.99, close=1.0),
        Candle(ts=2, open=1.0, high=1.02, low=0.99, close=1.015),
        Candle(ts=3, open=1.01, high=1.02, low=1.0, close=1.018),
    ]


def _many_1m_candles(base: list[Candle], n: int = 25) -> list[Candle]:
    if len(base) >= n:
        return base
    pad = [_candle(100 + i * 60, 1.0975) for i in range(n - len(base))]
    return pad + base


def _mature_zone(sym: str, zone: ConsolidationZone) -> ConsolidationZone:
    return ConsolidationZone(
        asset=sym,
        ceiling=zone.ceiling,
        floor=zone.floor,
        bars_inside=zone.bars_inside,
        detected_at=time.time() - 30 * 60,
        range_pct=zone.range_pct,
    )


def _make_strat_a_scanner(
    monkeypatch,
    assets: list[tuple[str, int]],
    *,
    htf_default: list | None = None,
):
    bot = FakeBot()
    if htf_default is not None:
        bot.htf_scanner = FakeHTFScanner(default=htf_default)
    executor = MagicMock()
    executor.refresh_balance_and_risk = AsyncMock(return_value=False)
    executor._check_martin = AsyncMock(return_value=False)
    executor._process_pending_martin = AsyncMock(
        side_effect=lambda candidates: (candidates, False),
    )
    executor._update_dynamic_threshold = MagicMock(return_value=65)
    executor._record_scan_acceptances = MagicMock()
    executor._strategy_snapshot = MagicMock(return_value={})
    executor._cleanup_asset_blacklist = MagicMock()
    executor._is_asset_blacklisted = MagicMock(return_value=False)
    executor._log_dry_run_verbose_cycle_summary = MagicMock()
    executor._compute_initial_amount = MagicMock(return_value=(1.0, 0.8))
    executor.enter_trade = AsyncMock(return_value=True)

    journal = MagicMock()
    journal._conn = None
    journal.log_candidate = MagicMock(return_value=1)
    journal.log_expired_zone = MagicMock(return_value=1)
    monkeypatch.setattr(scanner_mod, "get_journal", lambda: journal)

    scanner = AssetScanner(bot, executor)
    monkeypatch.setattr(
        scanner_mod,
        "get_open_assets",
        AsyncMock(return_value=assets),
    )
    monkeypatch.setattr(
        scanner,
        "_handle_breakout_side_effects",
        AsyncMock(),
    )
    monkeypatch.setattr(scanner_mod._runtime_config, "STRAT_A_ONLY", True)
    monkeypatch.setattr(scanner_mod._runtime_config, "STRAT_MOMENTUM_ENABLED", False)
    monkeypatch.setattr(scanner_mod, "sleep_with_inline_countdown", AsyncMock())
    return bot, executor, scanner


@pytest.mark.asyncio
async def test_strat_a_e2e_rebound_ceiling_produces_scored_candidate(monkeypatch):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(
        monkeypatch,
        [(sym, 88)],
        htf_default=_trending_15m_candles(60, bullish=False),
    )
    candles_5m, zone = _consolidation_candles_5m_at_ceiling()
    bot.zones[sym] = _mature_zone(sym, zone)
    candles_1m = _many_1m_candles(_valid_put_rejection_1m())

    _patch_shooting_star(monkeypatch)

    cycle = ScanCycleData(
        symbols=[sym],
        assets=[(sym, 88)],
        candles_5m={sym: candles_5m},
        candles_1m={sym: candles_1m},
        candles_h1={sym: []},
    )

    result = await scanner._scan_phase_evaluate_assets(cycle)
    strat_a = [
        c for c in result["candidates"]
        if getattr(c, "_entry_mode", "") == "rebound_ceiling"
    ]

    assert len(strat_a) == 1
    candidate = strat_a[0]
    assert candidate.direction == "put"
    assert candidate.score > 0
    assert getattr(candidate, "_stage") == "initial"
    assert getattr(candidate, "_reversal_pattern") == "shooting_star"


@pytest.mark.asyncio
async def test_strat_a_e2e_breakout_above_sets_stage_breakout(monkeypatch):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(
        monkeypatch,
        [(sym, 88)],
        htf_default=_trending_15m_candles(60, bullish=True),
    )
    candles_5m, zone = _consolidation_candles_5m_breakout()
    bot.zones[sym] = _mature_zone(sym, zone)
    candles_1m = _many_1m_candles([], n=25)

    cycle = ScanCycleData(
        symbols=[sym],
        assets=[(sym, 88)],
        candles_5m={sym: candles_5m},
        candles_1m={sym: candles_1m},
        candles_h1={sym: []},
    )

    result = await scanner._scan_phase_evaluate_assets(cycle)
    breakouts = [
        c for c in result["candidates"]
        if getattr(c, "_stage", "") == "breakout"
    ]

    assert len(breakouts) == 1
    candidate = breakouts[0]
    assert candidate.direction == "call"
    assert getattr(candidate, "_entry_mode") == "breakout_above"
    assert candidate.score > 0
    assert len(candidate.candles_15m) >= 10


@pytest.mark.asyncio
async def test_strat_a_e2e_young_zone_skips_candidate(monkeypatch):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(monkeypatch, [(sym, 88)])

    candles_5m, _zone = _consolidation_candles_5m_at_ceiling()
    candles_1m = _many_1m_candles(_valid_put_rejection_1m())

    _patch_shooting_star(monkeypatch)

    cycle = ScanCycleData(
        symbols=[sym],
        assets=[(sym, 88)],
        candles_5m={sym: candles_5m},
        candles_1m={sym: candles_1m},
        candles_h1={sym: []},
    )

    result = await scanner._scan_phase_evaluate_assets(cycle)

    assert result["candidates"] == []
    assert bot.stats["rejected_young_zone"] == 1


@pytest.mark.asyncio
async def test_strat_a_e2e_pending_hint_enqueues_reversal(monkeypatch):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(monkeypatch, [(sym, 88)])
    candles_5m, zone = _consolidation_candles_5m_at_ceiling()
    bot.zones[sym] = _mature_zone(sym, zone)
    candles_1m = _many_1m_candles(_invalid_put_rejection_1m())

    _patch_shooting_star(monkeypatch)

    cycle = ScanCycleData(
        symbols=[sym],
        assets=[(sym, 88)],
        candles_5m={sym: candles_5m},
        candles_1m={sym: candles_1m},
        candles_h1={sym: []},
    )

    result = await scanner._scan_phase_evaluate_assets(cycle)

    assert result["candidates"] == []
    assert sym in bot.pending_reversals
    pr = bot.pending_reversals[sym]
    assert pr.proposed_direction == "put"
    assert pr.entry_mode == "rebound_ceiling"


@pytest.mark.asyncio
async def test_strat_a_e2e_select_best_only_above_threshold(monkeypatch):
    sym_hi = "EURUSD_otc"
    sym_lo = "GBPUSD_otc"
    bot, executor, scanner = _make_strat_a_scanner(
        monkeypatch,
        [(sym_hi, 88), (sym_lo, 88)],
    )

    _, detected = _consolidation_candles_5m_at_ceiling()
    zone_hi = _mature_zone(sym_hi, detected)
    zone_lo = _mature_zone(sym_lo, detected)

    high = CandidateEntry(
        asset=sym_hi,
        payout=88,
        zone=zone_hi,
        direction="put",
        candles=[],
        score=80.0,
        score_breakdown={"compression": 20, "bounce": 20, "trend": 20, "payout": 20},
    )
    setattr(high, "_amount", 1.0)
    setattr(high, "_stage", "initial")
    setattr(high, "_strategy_origin", "STRAT-A")
    setattr(high, "_reversal_pattern", "shooting_star")

    low = CandidateEntry(
        asset=sym_lo,
        payout=88,
        zone=zone_lo,
        direction="put",
        candles=[],
        score=40.0,
        score_breakdown={"compression": 10, "bounce": 10, "trend": 10, "payout": 10},
    )
    setattr(low, "_amount", 1.0)
    setattr(low, "_stage", "initial")
    setattr(low, "_strategy_origin", "STRAT-A")
    setattr(low, "_reversal_pattern", "shooting_star")

    eval_result = {
        "candidates": [high, low],
        "cycle_ob_summary": {},
        "cycle_ma_summary": {},
        "candles_1m_collected": {},
        "last_prices_collected": {},
    }

    await scanner._scan_phase_select_execute(eval_result, [(sym_hi, 88), (sym_lo, 88)])

    assert executor.enter_trade.await_count == 1
    call_args = executor.enter_trade.await_args
    assert call_args.args[0] == sym_hi
    assert bot.stats["score_rejected_score"] == 1


@pytest.mark.asyncio
async def test_pending_reversal_active_wait_increments_scans_waited(monkeypatch):
    sym = "EURUSD_otc"
    bot, executor, scanner = _make_strat_a_scanner(monkeypatch, [(sym, 88)])
    _, detected = _consolidation_candles_5m_at_ceiling()
    zone = _mature_zone(sym, detected)
    bot.pending_reversals[sym] = PendingReversal(
        asset=sym,
        zone=zone,
        proposed_direction="put",
        conflicting_pattern="rejection_candle_fail",
        detected_at=datetime.now(),
        entry_mode="rebound_ceiling",
        payout=88,
        max_wait_scans=3,
        scans_waited=0,
    )

    candles_1m = _many_1m_candles(_invalid_put_rejection_1m())
    monkeypatch.setattr(
        scanner_mod,
        "detect_reversal_pattern",
        lambda _candles, _direction: CandleSignal("none", 0.0, False),
    )

    result = await scanner._process_pending_reversals(
        {sym: 88},
        {sym: candles_1m},
        {sym: zone.ceiling},
    )

    assert result == []
    assert sym in bot.pending_reversals
    assert bot.pending_reversals[sym].scans_waited == 1


@pytest.mark.asyncio
async def test_pending_reversal_confirmed_returns_candidate_and_clears(monkeypatch):
    sym = "EURUSD_otc"
    bot, executor, scanner = _make_strat_a_scanner(
        monkeypatch,
        [(sym, 88)],
        htf_default=_trending_15m_candles(60, bullish=False),
    )
    _, detected = _consolidation_candles_5m_at_ceiling()
    zone = _mature_zone(sym, detected)
    bot.pending_reversals[sym] = PendingReversal(
        asset=sym,
        zone=zone,
        proposed_direction="put",
        conflicting_pattern="rejection_candle_fail",
        detected_at=datetime.now(),
        entry_mode="rebound_ceiling",
        payout=88,
        max_wait_scans=3,
        scans_waited=0,
    )

    candles_1m = _many_1m_candles(_valid_put_rejection_1m())
    monkeypatch.setattr(
        scanner_mod,
        "detect_reversal_pattern",
        lambda _candles, _direction: CandleSignal("shooting_star", 0.75, True),
    )
    monkeypatch.setattr(
        scanner_mod,
        "fetch_candles_with_retry",
        AsyncMock(return_value=[]),
    )

    result = await scanner._process_pending_reversals(
        {sym: 88},
        {sym: candles_1m},
        {sym: zone.ceiling},
    )

    assert len(result) == 1
    assert result[0].asset == sym
    assert result[0].direction == "put"
    assert getattr(result[0], "_from_pending") is True
    assert sym not in bot.pending_reversals
    executor._compute_initial_amount.assert_called_once_with(88)


@pytest.mark.asyncio
async def test_pending_reversal_expires_after_max_wait_scans(monkeypatch):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(monkeypatch, [(sym, 88)])
    _, detected = _consolidation_candles_5m_at_ceiling()
    zone = _mature_zone(sym, detected)
    bot.pending_reversals[sym] = PendingReversal(
        asset=sym,
        zone=zone,
        proposed_direction="put",
        conflicting_pattern="rejection_candle_fail",
        detected_at=datetime.now(),
        entry_mode="rebound_ceiling",
        payout=88,
        max_wait_scans=3,
        scans_waited=2,
    )

    candles_1m = _many_1m_candles(_invalid_put_rejection_1m())
    monkeypatch.setattr(
        scanner_mod,
        "detect_reversal_pattern",
        lambda _candles, _direction: CandleSignal("none", 0.0, False),
    )

    result = await scanner._process_pending_reversals(
        {sym: 88},
        {sym: candles_1m},
        {sym: zone.ceiling},
    )

    assert result == []
    assert sym not in bot.pending_reversals


@pytest.mark.asyncio
async def test_pending_reversal_cancelled_when_price_leaves_extreme(monkeypatch):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(monkeypatch, [(sym, 88)])
    _, detected = _consolidation_candles_5m_at_ceiling()
    zone = _mature_zone(sym, detected)
    bot.pending_reversals[sym] = PendingReversal(
        asset=sym,
        zone=zone,
        proposed_direction="put",
        conflicting_pattern="rejection_candle_fail",
        detected_at=datetime.now(),
        entry_mode="rebound_ceiling",
        payout=88,
        max_wait_scans=3,
        scans_waited=0,
    )

    candles_1m = _many_1m_candles(_valid_put_rejection_1m())
    monkeypatch.setattr(
        scanner_mod,
        "detect_reversal_pattern",
        lambda _candles, _direction: CandleSignal("shooting_star", 0.75, True),
    )

    result = await scanner._process_pending_reversals(
        {sym: 88},
        {sym: candles_1m},
        {sym: zone.floor},
    )

    assert result == []
    assert sym not in bot.pending_reversals


@pytest.mark.asyncio
async def test_strat_a_scan_excludes_low_payout_asset(monkeypatch, caplog):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(monkeypatch, [(sym, 86)])
    candles_5m, zone = _consolidation_candles_5m_at_ceiling()
    bot.zones[sym] = _mature_zone(sym, zone)
    candles_1m = _many_1m_candles(_valid_put_rejection_1m())

    _patch_shooting_star(monkeypatch)

    cycle = ScanCycleData(
        symbols=[sym],
        assets=[(sym, 86)],
        candles_5m={sym: candles_5m},
        candles_1m={sym: candles_1m},
        candles_h1={sym: []},
    )

    with caplog.at_level("INFO", logger="scanner"):
        result = await scanner._scan_phase_evaluate_assets(cycle)

    assert result["candidates"] == []
    assert bot.stats["skipped"] >= 1
    assert "⛔ [STRAT-A]" in caplog.text
    assert sym in caplog.text
    assert "payout=86" in caplog.text
    assert "< 87" in caplog.text


@pytest.mark.asyncio
async def test_strat_a_scan_logs_pattern_missing_veto(monkeypatch, caplog):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(monkeypatch, [(sym, 88)])
    candles_5m, zone = _consolidation_candles_5m_at_ceiling()
    bot.zones[sym] = _mature_zone(sym, zone)
    candles_1m = _many_1m_candles(_valid_put_rejection_1m())

    monkeypatch.setattr(
        scanner_mod,
        "detect_reversal_pattern",
        lambda _candles, _direction: CandleSignal("none", 0.0, False),
    )
    monkeypatch.setattr(
        strat_a_mod,
        "detect_reversal_pattern",
        lambda _candles, _direction: CandleSignal("none", 0.0, False),
    )

    cycle = ScanCycleData(
        symbols=[sym],
        assets=[(sym, 88)],
        candles_5m={sym: candles_5m},
        candles_1m={sym: candles_1m},
        candles_h1={sym: []},
    )

    with caplog.at_level("INFO", logger="scanner"):
        result = await scanner._scan_phase_evaluate_assets(cycle)

    assert result["candidates"] == []
    assert "⛔ [STRAT-A]" in caplog.text
    assert sym in caplog.text
    assert "rebote techo" in caplog.text
    assert "sin patrón 1m confirmado" in caplog.text


def test_strat_a_select_best_uses_fixed_threshold_75():
    _, detected = _consolidation_candles_5m_at_ceiling()
    zone = _mature_zone("EURUSD_otc", detected)
    candidate = CandidateEntry(
        asset="EURUSD_otc",
        payout=88,
        zone=zone,
        direction="put",
        candles=[],
        score=70.0,
        score_breakdown={"compression": 18, "bounce": 18, "trend": 18, "payout": 16},
    )
    setattr(candidate, "_strategy_origin", "STRAT-A")

    selected, rejected = select_best(
        [candidate],
        threshold=65,
        threshold_for=lambda c: 75 if getattr(c, "_strategy_origin", "") == "STRAT-A" else 65,
    )

    assert selected == []
    assert candidate in rejected


@pytest.mark.asyncio
async def test_scan_rejects_without_htf_alignment(monkeypatch, caplog):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(
        monkeypatch,
        [(sym, 88)],
        htf_default=_trending_15m_candles(60, bullish=False),
    )
    candles_5m, zone = _consolidation_candles_5m_breakout()
    bot.zones[sym] = _mature_zone(sym, zone)
    candles_1m = _many_1m_candles([], n=25)

    cycle = ScanCycleData(
        symbols=[sym],
        assets=[(sym, 88)],
        candles_5m={sym: candles_5m},
        candles_1m={sym: candles_1m},
        candles_h1={sym: []},
    )

    with caplog.at_level("INFO", logger="scanner"):
        result = await scanner._scan_phase_evaluate_assets(cycle)

    assert result["candidates"] == []
    assert "⛔ [STRAT-A]" in caplog.text
    assert sym in caplog.text


@pytest.mark.asyncio
async def test_scan_uses_htf_cache_not_fetch(monkeypatch):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(
        monkeypatch,
        [(sym, 88)],
        htf_default=_trending_15m_candles(60, bullish=True),
    )
    candles_5m, zone = _consolidation_candles_5m_breakout()
    bot.zones[sym] = _mature_zone(sym, zone)
    candles_1m = _many_1m_candles([], n=25)

    fetch_calls: list[int] = []
    original_fetch = scanner_mod.fetch_candles_with_retry

    async def spy_fetch(client, asset, tf_sec, count, **kwargs):
        fetch_calls.append(tf_sec)
        return await original_fetch(client, asset, tf_sec, count, **kwargs)

    monkeypatch.setattr(scanner_mod, "fetch_candles_with_retry", spy_fetch)

    cycle = ScanCycleData(
        symbols=[sym],
        assets=[(sym, 88)],
        candles_5m={sym: candles_5m},
        candles_1m={sym: candles_1m},
        candles_h1={sym: []},
    )

    await scanner._scan_phase_evaluate_assets(cycle)

    assert 900 not in fetch_calls


@pytest.mark.asyncio
async def test_evaluate_phase_no_ob_network_io(monkeypatch):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(
        monkeypatch,
        [(sym, 88)],
        htf_default=_trending_15m_candles(60, bullish=False),
    )
    candles_5m, zone = _consolidation_candles_5m_at_ceiling()
    bot.zones[sym] = _mature_zone(sym, zone)
    candles_1m = _many_1m_candles(_valid_put_rejection_1m())
    _patch_shooting_star(monkeypatch)

    ob_fetch_calls: list[int] = []

    async def spy_fetch(client, asset, tf_sec, count, **kwargs):
        if tf_sec == 180:
            ob_fetch_calls.append(tf_sec)
        return []

    monkeypatch.setattr(scanner_mod, "fetch_candles_with_retry", spy_fetch)

    known_blocks = {
        "bull": [
            OrderBlock(
                side="bull",
                low=1.0950,
                high=1.0960,
                created_ts=100,
                created_index=5,
                bars_ago=3,
            ),
        ],
        "bear": [],
    }
    cycle = ScanCycleData(
        symbols=[sym],
        assets=[(sym, 88)],
        candles_5m={sym: candles_5m},
        candles_1m={sym: candles_1m},
        candles_h1={sym: []},
        blocks_by_symbol={sym: known_blocks},
        ob_tf_labels={sym: "3m"},
    )

    await scanner._scan_phase_evaluate_assets(cycle)

    assert ob_fetch_calls == []


@pytest.mark.asyncio
async def test_evaluate_receives_precalculated_blocks(monkeypatch):
    sym = "EURUSD_otc"
    bot, _, scanner = _make_strat_a_scanner(
        monkeypatch,
        [(sym, 88)],
        htf_default=_trending_15m_candles(60, bullish=False),
    )
    candles_5m, zone = _consolidation_candles_5m_at_ceiling()
    bot.zones[sym] = _mature_zone(sym, zone)
    candles_1m = _many_1m_candles(_valid_put_rejection_1m())
    _patch_shooting_star(monkeypatch)

    known_blocks = {
        "bull": [],
        "bear": [
            OrderBlock(
                side="bear",
                low=1.1040,
                high=1.1050,
                created_ts=200,
                created_index=8,
                bars_ago=2,
            ),
        ],
    }
    received_blocks: list[dict] = []
    original_evaluate = strat_a_mod.evaluate_strat_a

    def spy_evaluate(*args, **kwargs):
        received_blocks.append(kwargs.get("blocks"))
        return original_evaluate(*args, **kwargs)

    monkeypatch.setattr(scanner_mod, "evaluate_strat_a", spy_evaluate)

    cycle = ScanCycleData(
        symbols=[sym],
        assets=[(sym, 88)],
        candles_5m={sym: candles_5m},
        candles_1m={sym: candles_1m},
        candles_h1={sym: []},
        blocks_by_symbol={sym: known_blocks},
        ob_tf_labels={sym: "3m"},
    )

    await scanner._scan_phase_evaluate_assets(cycle)

    assert len(received_blocks) == 1
    assert received_blocks[0] is known_blocks
    assert bot.order_blocks_by_asset[sym] is known_blocks