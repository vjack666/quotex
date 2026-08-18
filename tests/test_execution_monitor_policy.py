from execution.monitor_policy import window


def test_monitor_window_includes_grace():
    assert window(300, 2).wait_sec == 302


def test_monitor_window_never_negative():
    assert window(-1, -2).wait_sec == 0
