from execution.settlement import classify


def test_none_is_not_a_loss():
    result = classify(None)
    assert result.open is True
    assert result.loss is False


def test_win_result():
    result = classify({"status": "win"})
    assert result.win is True
    assert result.loss is False


def test_loss_result():
    result = classify({"status": "loss"})
    assert result.loss is True
