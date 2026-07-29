"""Tests para stoch_cross_state: register/get/consume/pending."""
import pytest

from stoch_cross_state import StochCrossState


@pytest.fixture(autouse=True)
def reset_state():
    StochCrossState.get().reset()
    yield
    StochCrossState.get().reset()


def test_register_and_get():
    state = StochCrossState.get()
    state.register_cross("EURUSD_otc", "PUT", idx=7, k_last=93.5, d_last=90.15)
    rec = state.get_cross("EURUSD_otc", "PUT")
    assert rec is not None
    assert rec.idx == 7
    assert rec.k_last == pytest.approx(93.5)
    assert rec.d_last == pytest.approx(90.15)
    assert rec.consumed is False


def test_missing_key_returns_none():
    assert StochCrossState.get().get_cross("NOASSET", "CALL") is None


def test_consume_removes_pending():
    state = StochCrossState.get()
    state.register_cross("EURUSD_otc", "PUT", idx=1, k_last=80.1, d_last=79.4)
    assert state.get_cross("EURUSD_otc", "PUT") is not None
    state.consume("EURUSD_otc", "PUT")
    assert state.get_cross("EURUSD_otc", "PUT") is None
    assert state.pending_count() == 0


def test_pending_count_multiple():
    state = StochCrossState.get()
    state.register_cross("A", "PUT", idx=0, k_last=90.0, d_last=88.0)
    state.register_cross("B", "CALL", idx=2, k_last=15.0, d_last=16.5)
    state.consume("A", "PUT")
    assert state.pending_count() == 1


def test_direction_is_normalized():
    state = StochCrossState.get()
    state.register_cross("X", "call", idx=3, k_last=18.0, d_last=19.5)
    assert state.get_cross("X", "CALL") is not None
    assert state.get_cross("X", "call") is not None
