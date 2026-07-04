"""Tests de scanner.py con activos/velas sintéticas."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datetime import datetime

from candle_patterns import CandleSignal
from models import Candle, ConsolidationZone, PendingReversal
import parallel_fetch
import scan_prefetch
from scanner import AssetScanner


class FakeBot:
    def __init__(self, greylist: set[str] | None = None):
        self.client = MagicMock()
        self.dry_run = True
        self.account_type = "PRACTICE"
        self.zones = {}
        self.broken_zones = {}
        self.trades = {}
        self.stats = {
            "scans": 0, "skipped": 0, "expired_zones": 0,
            "filtered_sensor": 0, "strat_b_signals": 0,
            "rejected_young_zone": 0, "score_rejected_age": 0,
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
        self.capture_dir = Path(__file__).parent / "_tmp_capture"
        self.capture_dir.mkdir(exist_ok=True)
        self._followup_capture_tasks = set()
        self.compensation_pending = False
        self.last_closed_amount = 0.0
        self.last_closed_outcome = ""
        self.accepted_scans_window = __import__("collections").deque(maxlen=10)
        self.current_score_threshold = 65
        self.asset_blacklist_until = {}
        self.htf_scanner = _FakeHTFScanner()


class _FakeHTFScanner:
    def __init__(self, default: list | None = None):
        self._default = default if default is not None else []

    def get_candles_15m(self, sym: str) -> list:
        return self._default


def _bearish_15m_candles(n: int = 60, base: float = 50.0) -> list:
    candles: list[Candle] = []
    for i in range(n):
        drift = i * -0.01
        price = base + drift
        close = price - 0.005
        candles.append(
            Candle(
                ts=i * 900,
                open=price,
                high=max(price, close) + 0.01,
                low=min(price, close) - 0.01,
                close=close,
            )
        )
    return candles


def _candle(ts: int, price: float) -> Candle:
    return Candle(ts=ts, open=price, high=price + 0.001, low=price - 0.001, close=price)


@pytest.mark.asyncio
async def test_scanner_collects_candidates(monkeypatch):
    bot = FakeBot()
    executor = MagicMock()
    executor.refresh_balance_and_risk = AsyncMock(return_value=False)
    executor._check_martin = AsyncMock(return_value=False)
    executor._process_pending_martin = AsyncMock(return_value=([], False))
    executor._update_dynamic_threshold = MagicMock(return_value=65)
    executor._record_scan_acceptances = MagicMock()
    executor._strategy_snapshot = MagicMock(return_value={})
    executor._cleanup_asset_blacklist = MagicMock()
    executor._is_asset_blacklisted = MagicMock(return_value=False)
    executor._log_dry_run_verbose_cycle_summary = MagicMock()
    executor._compute_initial_amount = MagicMock(return_value=(1.0, 0.8))

    scanner = AssetScanner(bot, executor)

    monkeypatch.setattr(
        "scanner.get_open_assets",
        AsyncMock(return_value=[("EURUSD_otc", 85)]),
    )

    async def fake_fetch(client, asset, tf, count, timeout_sec, retries=2):
        if tf == 300:
            return [_candle(i * 300, 1.1000) for i in range(20)]
        return [_candle(i * 60, 1.1000) for i in range(25)]

    monkeypatch.setattr("scanner.fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr(scan_prefetch, "fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr(scanner, "_process_pending_reversals", AsyncMock(return_value=[]))

    await scanner.scan_all()
    assert bot.stats["scans"] == 1


@pytest.mark.asyncio
async def test_scanner_skips_greylisted_asset(monkeypatch):
    bot = FakeBot(greylist={"USDDZD_otc"})
    executor = MagicMock()
    executor.refresh_balance_and_risk = AsyncMock(return_value=False)
    executor._check_martin = AsyncMock(return_value=False)
    executor._process_pending_martin = AsyncMock(return_value=([], False))
    executor._update_dynamic_threshold = MagicMock(return_value=65)
    executor._record_scan_acceptances = MagicMock()
    executor._strategy_snapshot = MagicMock(return_value={})
    executor._cleanup_asset_blacklist = MagicMock()
    executor._is_asset_blacklisted = MagicMock(return_value=False)
    executor._log_dry_run_verbose_cycle_summary = MagicMock()

    scanner = AssetScanner(bot, executor)
    monkeypatch.setattr(
        "scanner.get_open_assets",
        AsyncMock(return_value=[("USDDZD_otc", 90)]),
    )

    async def fake_fetch(*args, **kwargs):
        return [_candle(i, 1.0) for i in range(20)]

    monkeypatch.setattr("scanner.fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr(scan_prefetch, "fetch_candles_with_retry", fake_fetch)

    await scanner.scan_all()
    assert bot.stats["skipped"] >= 1


def _make_scanner_mocks(monkeypatch, assets: list[tuple[str, int]]):
    bot = FakeBot()
    executor = MagicMock()
    executor.refresh_balance_and_risk = AsyncMock(return_value=False)
    executor._check_martin = AsyncMock(return_value=False)
    executor._process_pending_martin = AsyncMock(return_value=([], False))
    executor._update_dynamic_threshold = MagicMock(return_value=65)
    executor._record_scan_acceptances = MagicMock()
    executor._strategy_snapshot = MagicMock(return_value={})
    executor._cleanup_asset_blacklist = MagicMock()
    executor._is_asset_blacklisted = MagicMock(return_value=False)
    executor._log_dry_run_verbose_cycle_summary = MagicMock()
    executor._compute_initial_amount = MagicMock(return_value=(1.0, 0.8))
    executor.enter_trade = AsyncMock(return_value=True)

    scanner = AssetScanner(bot, executor)
    monkeypatch.setattr(
        "scanner.get_open_assets",
        AsyncMock(return_value=assets),
    )
    monkeypatch.setattr(scanner, "_process_pending_reversals", AsyncMock(return_value=[]))
    return bot, executor, scanner


@pytest.mark.asyncio
async def test_parallel_fetch_uses_semaphore(monkeypatch):
    sem_created: list[asyncio.Semaphore] = []
    original_sem = asyncio.Semaphore

    class TrackingSemaphore(original_sem):
        def __init__(self, value: int) -> None:
            super().__init__(value)
            sem_created.append(self)

    monkeypatch.setattr(asyncio, "Semaphore", TrackingSemaphore)
    monkeypatch.setattr(
        parallel_fetch,
        "fetch_candles_with_retry",
        AsyncMock(return_value=[]),
    )

    await parallel_fetch.fetch_candles_parallel(
        MagicMock(),
        ["A", "B", "C"],
        300,
        10,
        concurrency=3,
        timeout_sec=1.0,
    )

    assert len(sem_created) == 1


@pytest.mark.asyncio
async def test_parallel_fetch_respects_concurrency_limit(monkeypatch):
    concurrency = 2
    active = 0
    max_active = 0
    lock = asyncio.Lock()

    async def slow_fetch(client, asset, tf, count, timeout_sec, retries=2):
        nonlocal active, max_active
        async with lock:
            active += 1
            max_active = max(max_active, active)
        await asyncio.sleep(0.03)
        async with lock:
            active -= 1
        return [_candle(0, 1.0)]

    monkeypatch.setattr(parallel_fetch, "fetch_candles_with_retry", slow_fetch)

    symbols = [f"SYM{i}" for i in range(6)]
    t0 = time.monotonic()
    result = await parallel_fetch.fetch_candles_parallel(
        MagicMock(),
        symbols,
        300,
        10,
        concurrency=concurrency,
        timeout_sec=5.0,
    )
    elapsed = time.monotonic() - t0

    assert len(result) == len(symbols)
    assert max_active <= concurrency
    sequential_estimate = len(symbols) * 0.03
    assert elapsed < sequential_estimate


@pytest.mark.asyncio
async def test_scan_all_prefetches_before_eval(monkeypatch):
    num_assets = 4
    delay_sec = 0.05
    assets = [(f"ASSET{i}_otc", 85 + i) for i in range(num_assets)]
    fetch_started: list[float] = []
    fetch_completed: list[float] = []
    eval_started_at: list[float] = []

    async def fake_fetch(client, asset, tf, count, timeout_sec, retries=2):
        if tf in (300, 60, 180, 3600):
            fetch_started.append(time.monotonic())
            await asyncio.sleep(delay_sec)
            fetch_completed.append(time.monotonic())
        n = 25 if tf == 60 else 20
        return [_candle(i * max(tf, 1), 1.1000) for i in range(n)]

    def detect_with_flag(candles, **kwargs):
        eval_started_at.append(time.monotonic())
        return None

    _, _, scanner = _make_scanner_mocks(monkeypatch, assets)
    monkeypatch.setattr(scan_prefetch, "fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr("scanner.fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr("scanner.detect_consolidation", detect_with_flag)
    monkeypatch.setattr(scan_prefetch, "SCAN_WS_INTER_ASSET_DELAY_SEC", 0)

    await scanner.scan_all()

    expected_primary = num_assets * 2
    expected_secondary = num_assets * 2
    expected_prefetch_calls = expected_primary + expected_secondary
    assert len(fetch_started) == expected_prefetch_calls
    assert len(fetch_completed) == expected_prefetch_calls
    assert eval_started_at, "debe evaluar al menos un activo tras prefetch"

    prefetch_span = max(fetch_completed) - min(fetch_started)
    sequential_sum = expected_prefetch_calls * delay_sec
    assert prefetch_span < sequential_sum * 0.75

    assert max(fetch_completed) <= min(eval_started_at) + 0.01


@pytest.mark.asyncio
async def test_strat_a_only_skips_momentum_candidate(monkeypatch):
    import scanner as scanner_mod
    from scan_prefetch import ScanCycleData

    _, _, scanner = _make_scanner_mocks(monkeypatch, [("EURUSD_otc", 85)])
    monkeypatch.setattr(scanner_mod._runtime_config, "STRAT_A_ONLY", True)
    monkeypatch.setattr(scanner_mod._runtime_config, "STRAT_MOMENTUM_ENABLED", False)
    monkeypatch.setattr(
        "scanner.detect_momentum_1m",
        lambda _candles: ("call", 0.85),
    )

    candles_1m = [_candle(i * 60, 1.1000) for i in range(25)]
    cycle = ScanCycleData(
        symbols=["EURUSD_otc"],
        assets=[("EURUSD_otc", 85)],
        candles_5m={"EURUSD_otc": []},
        candles_1m={"EURUSD_otc": candles_1m},
    )

    result = await scanner._scan_phase_evaluate_assets(cycle)
    momentum = [
        c for c in result["candidates"]
        if getattr(c, "_strategy_origin", None) == "STRAT-MOMENTUM"
    ]
    assert len(momentum) == 0


@pytest.mark.asyncio
async def test_process_pending_reversals_confirmed_pattern_no_attribute_error(monkeypatch):
    """Regression: confirmed pending reversal must not crash on strat_a helpers."""
    bot = FakeBot()
    bot.htf_scanner = _FakeHTFScanner(default=_bearish_15m_candles(60, base=50.0))
    executor = MagicMock()
    executor._compute_initial_amount = MagicMock(return_value=(2.5, 0.8))
    scanner = AssetScanner(bot, executor)

    zone = ConsolidationZone(
        asset="USDEGP_otc",
        ceiling=50.0,
        floor=49.0,
        bars_inside=10,
        detected_at=time.time(),
        range_pct=0.02,
    )
    bot.pending_reversals["USDEGP_otc"] = PendingReversal(
        asset="USDEGP_otc",
        zone=zone,
        proposed_direction="put",
        conflicting_pattern="none",
        detected_at=datetime.now(),
        entry_mode="rebound_ceiling",
        payout=85,
    )

    candles_1m = [
        Candle(ts=0, open=49.5, high=49.6, low=49.4, close=49.55),
        Candle(ts=60, open=50.0, high=50.5, low=49.2, close=49.3),
        Candle(ts=120, open=49.3, high=49.4, low=49.2, close=49.35),
    ]

    monkeypatch.setattr(
        "scanner.detect_reversal_pattern",
        lambda _candles, _direction: CandleSignal("shooting_star", 0.75, True),
    )
    monkeypatch.setattr(
        "scanner.fetch_candles_with_retry",
        AsyncMock(return_value=[]),
    )

    result = await scanner._process_pending_reversals(
        {"USDEGP_otc": 85},
        {"USDEGP_otc": candles_1m},
        {"USDEGP_otc": 50.0},
    )

    assert len(result) == 1
    assert result[0].asset == "USDEGP_otc"
    assert result[0].direction == "put"
    assert getattr(result[0], "_reversal_pattern") == "shooting_star"
    assert "USDEGP_otc" not in bot.pending_reversals
    executor._compute_initial_amount.assert_called_once_with(85)