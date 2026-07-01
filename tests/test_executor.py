"""Tests de executor.py con mocks."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from executor import TradeExecutor
from models import ConsolidationZone


class FakeBot:
    def __init__(self):
        self.dry_run = True
        self.account_type = "PRACTICE"
        self.trades = {}
        self.stats = {
            "martin_attempts_session": 0,
            "entries": 0,
            "strat_a_signals": 0,
            "strat_b_signals": 0,
            "rejected_same_asset_limit": 0,
            "martins": 0,
        }
        self.zones = {}
        self.pending_martin = {}
        self.watched_candidates = {}
        self.compensation_pending = False
        self.last_closed_amount = 0.0
        self.current_balance = 1000.0
        self.session_start_balance = 1000.0
        self.massaniello = MagicMock()
        self.massaniello.next_stake.return_value = (1.0, "OK")
        self.massaniello.current_balance = 1000.0
        self.massaniello.can_enter.return_value = True
        self.massaniello.is_session_complete.return_value = False
        self.massaniello.is_session_failed.return_value = False
        self.massaniello.is_session_timeout.return_value = False
        self.massaniello.is_session_exhausted.return_value = False
        self.massaniello.session_start_time = None
        self.session_start_time = None
        self.last_entry_asset = None
        self.last_entry_asset_streak = 0
        self.accepted_scans_window = __import__("collections").deque(maxlen=10)
        self.current_score_threshold = 65
        self.cycle_id = 1
        self.cycle_ops = 0
        self.cycle_wins = 0
        self.cycle_losses = 0
        self.cycle_profit = 0.0
        self.cycle_start_balance = 1000.0
        self.asset_loss_streaks = {}
        self.asset_blacklist_until = {}
        self._trade_tasks = set()
        self._followup_capture_tasks = set()
        self.session_stop_hit = False
        self.last_known_price = {}


@pytest.mark.asyncio
async def test_executor_dry_run_order(monkeypatch):
    bot = FakeBot()
    client = MagicMock()
    client.get_balance = AsyncMock(return_value=1000.0)
    ex = TradeExecutor(client, bot)

    zone = ConsolidationZone(
        asset="EURUSD_otc", ceiling=1.1, floor=1.0,
        bars_inside=15, detected_at=0.0, range_pct=0.001,
    )

    monkeypatch.setattr(
        "executor.place_order",
        AsyncMock(return_value=(True, "DRY-1", 0.0, 0, "")),
    )
    monkeypatch.setattr(
        ex, "_sync_to_next_candle_open",
        AsyncMock(return_value=__import__("executor").EntryTimingInfo(
            ok=True, lag_sec=0.0, duration_sec=30,
            time_since_open_sec=0.0, secs_to_close_sec=60.0, decision="SYNC_DISABLED",
        )),
    )
    monkeypatch.setattr(ex, "_resolve_trade_after_expiry", AsyncMock())

    ok = await ex.enter_trade(
        "EURUSD_otc", "call", 1.0, zone, "test", "initial",
    )
    assert ok is True
    assert "EURUSD_otc" in bot.trades


def test_executor_cycle_reset_on_target():
    bot = FakeBot()
    bot.cycle_wins = 3
    bot.cycle_ops = 4
    ex = TradeExecutor(MagicMock(), bot)
    ex._update_cycle_after_result("WIN", 1.0)
    assert bot.cycle_ops == 0
    assert bot.cycle_wins == 0