from execution.session_policy import gate_massaniello


def test_session_policy_blocks_completed_session():
    result = gate_massaniello(enabled=True, complete=True)
    assert result.blocked


def test_session_policy_allows_healthy_session():
    result = gate_massaniello(enabled=True, can_enter=True)
    assert not result.blocked


def test_session_policy_is_disabled_without_massaniello():
    result = gate_massaniello(enabled=False, failed=True)
    assert not result.blocked
