import pytest

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.evidence import EvidenceReport, compute_evidence
from strategy_lab.promotion_gate import GateDecision, evaluate
from strategy_lab.registry import ExperimentRegistry
from strategy_lab.robustness import RobustnessReport, compute_robustness, metric_profit


def _make_events(n: int = 140, win_rate: float = 0.57):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(9)
    win = (rng.random(n) < win_rate).astype(int)
    profits = np.where(win == 1, 1.0, -1.0)
    splits = ["train"] * (n // 2) + ["test"] * (n - n // 2)
    return pd.DataFrame(
        {
            "win": win,
            "profit": profits,
            "expected_value": profits,
            "split": splits,
            "timeframe": ["M15"] * n,
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="min"),
            "asset": ["EURUSD"] * n,
        }
    )


def _good_evidence() -> EvidenceReport:
    events = _make_events()
    return compute_evidence(events, baseline_win_rate=0.50, baseline_expected_value=0.0)


def _good_robustness(events) -> RobustnessReport:
    return compute_robustness("EXP-001", events=events, baseline_value=0.0, metric_fn=metric_profit)


def _baseline_manager():
    manager = BaselineManager()
    manager.register(
        Baseline(id="BASELINE-001", version="1.0", created_at="2026-08-04T00:00:00Z", author="hermes", description="baseline", metrics={"win_rate": 0.37}, dataset_checksum="abc")
    )
    return manager


def test_registry_creates_and_exports_record():
    registry = ExperimentRegistry(baseline_manager=_baseline_manager())
    record = registry.create("EXP-001", hypothesis="H1", tribunal_version="1.0", baseline_id="BASELINE-001", baseline_version="1.0", tags=["edificio"])
    assert registry.get("EXP-001").experiment_id == "EXP-001"
    exported = registry.export("EXP-001")
    assert exported["hypothesis"] == "H1"
    assert exported["baseline_id"] == "BASELINE-001"


def test_registry_attaches_full_evidence_pipeline():
    events = _make_events()
    registry = ExperimentRegistry(baseline_manager=_baseline_manager())
    registry.create("EXP-001", tribunal_version="1.0", baseline_id="BASELINE-001", baseline_version="1.0")
    registry.attach_evidence("EXP-001", _good_evidence())
    registry.attach_robustness("EXP-001", _good_robustness(events))
    decision = evaluate("EXP-001", evidence=_good_evidence(), robustness=_good_robustness(events))
    registry.attach_gate_decision("EXP-001", decision)
    record = registry.get("EXP-001")
    assert record.evidence_report is not None
    assert record.robustness_report is not None
    assert record.gate_decision is not None
    assert record.status == decision.verdict.lower()
    assert record.promotion_path is not None


def test_registry_lists_by_status():
    registry = ExperimentRegistry(baseline_manager=_baseline_manager())
    registry.create("EXP-001", tribunal_version="1.0")
    registry.create("EXP-002", tribunal_version="1.0")
    registry.attach_evidence("EXP-001", _good_evidence())
    registry.attach_evidence("EXP-002", _good_evidence())
    assert len(registry.list_by_status("evidence_attached")) == 2
    assert len(registry.list_by_status("created")) == 0


def test_registry_missing_experiment_raises():
    registry = ExperimentRegistry(baseline_manager=_baseline_manager())
    with pytest.raises(KeyError):
        registry.get("MISSING")


def test_registry_version_mismatch_raises():
    manager = _baseline_manager()
    registry = ExperimentRegistry(baseline_manager=manager)
    with pytest.raises(ValueError):
        registry.create("EXP-001", tribunal_version="1.0", baseline_id="BASELINE-001", baseline_version="2.0")
