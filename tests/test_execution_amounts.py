"""Pure execution arithmetic regression tests."""
from execution.amounts import cap_to_balance, expected_profit, round_up_to_cents


def test_round_up_to_cents():
    assert round_up_to_cents(1.001) == 1.01
    assert round_up_to_cents(-1.0) == 0.0


def test_expected_profit_uses_minimum_one_percent():
    assert expected_profit(2.0, 0) == 0.02
    assert expected_profit(2.0, 80) == 1.60


def test_cap_to_balance():
    assert cap_to_balance(10.0, 100.0, 0.20, 1.0) == 10.0
    assert cap_to_balance(30.0, 100.0, 0.20, 1.0) == 20.0
    assert cap_to_balance(0.1, None, 0.20, 1.0) == 1.0
