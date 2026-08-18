from execution.live_duration import get


def test_live_duration_is_integer():
    assert isinstance(get(), int)
    assert get() > 0
