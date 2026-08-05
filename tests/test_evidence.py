import math

from typing import Optional

import numpy as np
import pandas as pd
import pytest

from strategy_lab.evidence import (
    EvidenceReport,
    _power_analysis,
    _profit_factor,
    _wilson_ci,
    compute_evidence,
    events_from_csv,
)


def make_events(
    n: int = 120,
    *,
    win_rate: float = 0.55,
    split: str = "train",
    profit_values: Optional[np.ndarray] = None,
    ev_values: Optional[np.ndarray] = None,
    timestamps: Optional[pd.DatetimeIndex] = None,
) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    win = (rng.random(n) < win_rate).astype(int)
    df = pd.DataFrame(
        {
            "split": [split] * n,
            "win": win,
            "profit": profit_values if profit_values is not None else np.where(win == 1, 1.0, -1.0),
            "expected_value": ev_values if ev_values is not None else np.where(win == 1, 1.0, -1.0),
            "timestamp": timestamps if timestamps is not None else pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC"),
        }
    )
    return df


def test_wilson_ci_basic():
    lower, upper = _wilson_ci(55, 100)
    assert 0.0 <= lower <= upper <= 1.0
    assert lower < 0.55 < upper


def test_wilson_ci_zero_n():
    assert _wilson_ci(0, 0) == (0.0, 0.0)


def test_profit_factor_basic():
    profits = np.array([2.0, -1.0, 3.0, -1.5])
    pf = _profit_factor(profits)
    assert pf == pytest.approx((2.0 + 3.0) / (1.0 + 1.5))


def test_profit_factor_all_losses():
    assert _profit_factor(np.array([-1.0, -2.0])) == pytest.approx(0.0)


def test_power_analysis_increases_with_n():
    low = _power_analysis(0.05, 0.5, 150)
    high = _power_analysis(0.05, 0.5, 1200)
    assert low < high


def test_compute_evidence_missing_labels_no_split_column():
    df = make_events(80, win_rate=0.55)
    df = df.drop(columns=["split"])
    report = compute_evidence(df, baseline_win_rate=0.50)
    assert report.events_train == 40
    assert report.events_test == 40
    assert "No train/test labels found" not in report.warnings


def test_compute_evidence_missing_labels_unknown_split():
    df = make_events(80, win_rate=0.55)
    df["split"] = "unknown"
    report = compute_evidence(df, baseline_win_rate=0.50)
    assert report.events_train == 40
    assert report.events_test == 40
    assert "No train/test labels found" not in report.warnings


def test_compute_evidence_train_test_split():
    df = make_events(120, win_rate=0.55)
    df.loc[:59, "split"] = "train"
    df.loc[60:, "split"] = "test"
    report = compute_evidence(df, baseline_win_rate=0.50)
    assert report.events_train == 60
    assert report.events_test == 60
    assert report.train_test_divergence_pp is not None


def test_compute_evidence_overfit_alarm():
    df = make_events(120, win_rate=0.55)
    df.loc[:59, "win"] = 1
    df.loc[60:, "win"] = 0
    df.loc[:59, "split"] = "train"
    df.loc[60:, "split"] = "test"
    report = compute_evidence(df, baseline_win_rate=0.50, divergence_alarm_pp=10.0)
    assert report.overfit_alarm is True


def test_compute_evidence_baseline_improvements():
    wins = np.ones(120)
    df = pd.DataFrame(
        {
            "split": ["train"] * 120,
            "win": wins,
            "profit": np.ones(120),
            "expected_value": np.ones(120),
            "timestamp": pd.date_range("2024-01-01", periods=120, freq="15min", tz="UTC"),
        }
    )
    report = compute_evidence(df, baseline_win_rate=0.50, baseline_expected_value=0.1)
    assert report.improvement_win_rate_pp == pytest.approx(50.0)
    assert report.improvement_expected_value_percent == pytest.approx(900.0)


def test_compute_evidence_missing_win_column():
    df = pd.DataFrame({"split": ["train"] * 10})
    with pytest.raises(KeyError):
        compute_evidence(df)
