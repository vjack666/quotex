from execution.martin_policy import cap_amount, session_available


def test_martin_blocked_by_massaniello():
    assert not session_available(uses_massaniello=True, used=0, limit=3).allowed


def test_martin_session_limit():
    assert not session_available(uses_massaniello=False, used=3, limit=3).allowed


def test_martin_amount_is_capped_by_balance():
    assert cap_amount(12, 10) == 10
