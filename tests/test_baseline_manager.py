import pytest

from strategy_lab.baseline_manager import Baseline, BaselineManager


def test_register_and_get_baseline():
    manager = BaselineManager()
    baseline = Baseline(
        id="BASELINE-001",
        version="1.0",
        created_at="2026-08-04T00:00:00Z",
        author="hermes",
        description="baseline edificio actual",
        metrics={"win_rate": 0.371, "expected_value": -0.05},
        dataset_checksum="abc123",
    )
    manager.register(baseline)
    assert manager.get("BASELINE-001").version == "1.0"


def test_duplicate_register_raises():
    manager = BaselineManager()
    baseline = Baseline(
        id="BASELINE-001",
        version="1.0",
        created_at="2026-08-04T00:00:00Z",
        author="hermes",
        description="baseline",
        metrics={"win_rate": 0.371},
        dataset_checksum="abc123",
    )
    manager.register(baseline)
    with pytest.raises(ValueError):
        manager.register(baseline)


def test_list_active_baselines():
    manager = BaselineManager()
    manager.register(
        Baseline(id="B1", version="1.0", created_at="2026-08-04T00:00:00Z", author="a", description="", metrics={}, dataset_checksum="1")
    )
    manager.register(
        Baseline(id="B2", version="1.0", created_at="2026-08-04T00:00:00Z", author="a", description="", metrics={}, dataset_checksum="2", status="inactive")
    )
    assert len(manager.list_active()) == 1


def test_supersede_marks_history():
    manager = BaselineManager()
    old = Baseline(id="B1", version="1.0", created_at="2026-08-04T00:00:00Z", author="a", description="", metrics={}, dataset_checksum="1")
    new = Baseline(id="B2", version="1.0", created_at="2026-08-04T00:00:00Z", author="a", description="", metrics={}, dataset_checksum="2")
    manager.register(old)
    manager.register(new)
    manager.supersede("B1", new, reason="mejor evidencia")
    assert manager.get("B1").status == "superseded"
    assert manager.get("B1").superseded_by == "B2"
    assert len(manager.history()) == 1


def test_compare_returns_deltas():
    manager = BaselineManager()
    baseline = Baseline(id="B1", version="1.0", created_at="2026-08-04T00:00:00Z", author="a", description="", metrics={"win_rate": 0.40, "expected_value": 0.1}, dataset_checksum="1")
    manager.register(baseline)
    result = manager.compare("B1", {"win_rate": 0.45, "expected_value": 0.2, "new_metric": 1.0})
    assert result["deltas"]["win_rate"] == pytest.approx(0.05)
    assert result["deltas"]["expected_value"] == pytest.approx(0.1)
    assert "new_metric" not in result["deltas"]
    assert result["delta_count"] == 2


def test_compare_inactive_baseline_raises():
    manager = BaselineManager()
    baseline = Baseline(id="B1", version="1.0", created_at="2026-08-04T00:00:00Z", author="a", description="", metrics={}, dataset_checksum="1", status="inactive")
    manager.register(baseline)
    with pytest.raises(ValueError):
        manager.compare("B1", {})
