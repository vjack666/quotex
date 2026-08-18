from execution.session_summary import build_session_summary


def test_session_summary_complete():
    result = build_session_summary({"wins": 3, "losses": 1, "entries": 4, "balance": 34, "initial_capital": 30, "complete": True}, "target")
    assert result["status"] == "SESSION_COMPLETE"
    assert result["trades"] == 4
    assert result["win_rate"] == 75.0
    assert result["pnl"] == 4.0


def test_session_summary_failure_precedence():
    result = build_session_summary({"wins": 0, "losses": 2, "failed": True, "timeout": True}, "risk")
    assert result["status"] == "SESSION_FAILED"
