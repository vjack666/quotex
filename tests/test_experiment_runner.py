import pytest

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.evidence import compute_evidence
from strategy_lab.experiment_runner import run_experiment
from strategy_lab.promotion_gate import GateDecision
from strategy_lab.registry import ExperimentRegistry
from strategy_lab.robustness import RobustnessReport


def _make_events(n: int = 180, win_rate: float = 0.58):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(3)
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


def test_run_experiment_returns_full_artifacts(tmp_path):
    events = _make_events()
    baseline = Baseline(id="BASELINE-001", version="1.0", created_at="2026-08-04T00:00:00Z", author="hermes", description="baseline", metrics={"win_rate": 0.37, "expected_value": 0.0}, dataset_checksum="abc")
    baseline_manager = BaselineManager()
    baseline_manager.register(baseline)
    registry = ExperimentRegistry(baseline_manager=baseline_manager)

    artifacts = run_experiment(
        "EXP-001",
        events,
        hypothesis="H1",
        tribunal_version="1.0",
        baseline_id="BASELINE-001",
        baseline_version="1.0",
        registry=registry,
        baseline_manager=baseline_manager,
        report_dir=tmp_path / "reports",
    )
    assert artifacts.evidence_report.experiment_id == "EXP-001"
    assert artifacts.robustness_report.experiment_id == "EXP-001"
    assert isinstance(artifacts.gate_decision, GateDecision)
    assert artifacts.registry_record is not None
    assert artifacts.report_path.endswith("EXP-001_report.md")


def test_run_experiment_creates_registry_record(tmp_path):
    events = _make_events(win_rate=0.60)
    baseline = Baseline(id="BASELINE-001", version="1.0", created_at="2026-08-04T00:00:00Z", author="hermes", description="baseline", metrics={"win_rate": 0.37, "expected_value": 0.0}, dataset_checksum="abc")
    baseline_manager = BaselineManager()
    baseline_manager.register(baseline)
    registry = ExperimentRegistry(baseline_manager=baseline_manager)

    run_experiment(
        "EXP-002",
        events,
        registry=registry,
        baseline_manager=baseline_manager,
        report_dir=tmp_path / "reports",
    )
    record = registry.get("EXP-002")
    assert record.evidence_report is not None
    assert record.robustness_report is not None
    assert record.gate_decision is not None


def test_run_experiment_without_baseline():
    events = _make_events()
    registry = ExperimentRegistry()
    artifacts = run_experiment("EXP-003", events, registry=registry)
    assert artifacts.baseline_comparison is None
    assert artifacts.gate_decision is not None
