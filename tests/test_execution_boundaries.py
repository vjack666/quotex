"""Smoke tests for the canonical execution package boundaries."""
from execution import ExecutionContext, OrderContext, ExecutionSessionSnapshot
from execution.config import live_duration_sec


def test_execution_value_objects():
    ctx = ExecutionContext("EURUSD", "call", 1.0, 300)
    order = OrderContext("EURUSD", "call", 1.0, 300)
    session = ExecutionSessionSnapshot("running", trades=1, wins=1)
    assert ctx.duration_sec == order.duration_sec == 300
    assert order.asset == "EURUSD"
    assert session.wins == 1


def test_live_duration_access_is_dynamic():
    assert isinstance(live_duration_sec(), int)
