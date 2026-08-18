from execution.adaptive_threshold import calculate_threshold
from execution.asset_guard import is_blacklisted, register_loss, register_win
from execution.broker_result import interpret_settlement
from execution.cycle import CycleSnapshot, apply_outcome, reset_snapshot


def test_adaptive_threshold():
    assert calculate_threshold([], 70, 65, 75, 3) == 70
    assert calculate_threshold([0, 0, 0], 70, 65, 75, 3) == 65
    assert calculate_threshold([1, 1, 1], 70, 65, 75, 3) == 75


def test_asset_guard():
    streaks, blacklist = {}, {}
    register_loss(streaks, blacklist, "EURUSD", 2, 10, now=100)
    assert not is_blacklisted(blacklist, "EURUSD", 100)
    register_loss(streaks, blacklist, "EURUSD", 2, 10, now=100)
    assert is_blacklisted(blacklist, "EURUSD", 101)
    register_win(streaks, "EURUSD")
    assert streaks["EURUSD"] == 0


def test_cycle_accounting():
    s = apply_outcome(CycleSnapshot(0, 0, 0, 0), "WIN", 1.5)
    assert s == CycleSnapshot(1, 1, 0, 1.5)
    assert reset_snapshot(s) == CycleSnapshot(0, 0, 0, 0.0)


def test_unsettled_broker_result_is_not_forced_to_loss():
    assert interpret_settlement(None, status=None, payload=None, trade_amount=1, payout_pct=80) is None
