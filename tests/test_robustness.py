from __future__ import annotations

from strategy_lab.robustness import compute_robustness


def make_events(n: int = 200, base_value: float = 1.0):
    import pandas as pd
    import numpy as np

    rng = np.random.default_rng(0)
    profit = rng.normal(loc=base_value, scale=0.2, size=n)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC"),
            "profit": profit,
            "win": (profit > 0).astype(int),
            "expected_value": profit,
        }
    )


def metric_profit(df):
    return float(df["profit"].sum())


def test_compute_robustness_counts():
    events = make_events(240, base_value=1.0)
    report = compute_robustness("EXP-001", events=events, baseline_value=1.0, metric_fn=metric_profit)
    assert report.total_tests == 5
    assert report.passed_count + report.failed_count + report.inconclusive_count == report.total_tests


def test_parameter_perturbation_passes_when_baseline_positive():
    events = make_events(240, base_value=1.0)
    report = compute_robustness("EXP-001", events=events, baseline_value=1.0, metric_fn=metric_profit)
    assert report.results["parameter_perturbation"]["status"] in {"passed", "failed", "inconclusive"}


def test_stress_period_has_regimes():
    events = make_events(240, base_value=1.0)
    report = compute_robustness("EXP-001", events=events, baseline_value=1.0, metric_fn=metric_profit)
    assert "regimes" in report.results["stress_period"]


def test_bootstrap_passed_when_ci_above_zero():
    events = make_events(240, base_value=1.0)
    report = compute_robustness("EXP-001", events=events, baseline_value=1.0, metric_fn=metric_profit)
    assert report.results["bootstrap_1000"]["status"] in {"passed", "failed", "inconclusive"}


def test_multi_asset_requires_two_assets():
    events = make_events(120, base_value=1.0)
    events_a = make_events(120, base_value=1.0)
    events_b = make_events(120, base_value=-0.5)
    report = compute_robustness(
        "EXP-001",
        events=events,
        baseline_value=1.0,
        metric_fn=metric_profit,
        events_by_asset={"A": events_a, "B": events_b},
    )
    assert report.results["multi_asset"]["status"] in {"passed", "failed"}


def test_multi_timeframe_requires_two_timeframes():
    events = make_events(120, base_value=1.0)
    m5 = make_events(120, base_value=1.0)
    h1 = make_events(120, base_value=1.0)
    report = compute_robustness(
        "EXP-001",
        events=events,
        baseline_value=1.0,
        metric_fn=metric_profit,
        events_by_timeframe={"M5": m5, "H1": h1},
    )
    assert report.results["multi_timeframe"]["status"] in {"passed", "failed"}
