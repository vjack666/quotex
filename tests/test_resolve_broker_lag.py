"""Broker lag: never treat profitAmount==0 as LOSS."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from executor import TradeExecutor


def test_profit_zero_is_not_loss():
    assert TradeExecutor._interpret_broker_result(0.0) is None
    assert TradeExecutor._interpret_broker_result(
        status="loss", payload={"profitAmount": 0},
    ) is None
    assert TradeExecutor._interpret_broker_result(
        status="win", payload={"profitAmount": 0},
    ) is None


def test_positive_profit_is_win():
    out = TradeExecutor._interpret_broker_result(12.5)
    assert out == ("WIN", 12.5)
    out2 = TradeExecutor._interpret_broker_result(
        status="win", payload={"profitAmount": 8.2},
    )
    assert out2 == ("WIN", 8.2)


def test_negative_profit_is_loss():
    out = TradeExecutor._interpret_broker_result(-10.0)
    assert out == ("LOSS", -10.0)
    out2 = TradeExecutor._interpret_broker_result(
        status="loss", payload={"profitAmount": -5.0},
    )
    assert out2 == ("LOSS", -5.0)


def test_bool_check_win():
    assert TradeExecutor._interpret_broker_result(True, trade_amount=10.0, payout_pct=80) == (
        "WIN",
        8.0,
    )
    assert TradeExecutor._interpret_broker_result(False, trade_amount=10.0) == ("LOSS", -10.0)


def test_missing_history_is_pending():
    assert TradeExecutor._interpret_broker_result(status=None, payload=None) is None
