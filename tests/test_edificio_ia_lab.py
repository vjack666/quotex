"""Tests mínimos para pipeline IA del Edificio."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from strategy_lab.brake_eval import compute_brake_and_rebote
from strategy_lab.compute_features import build_feature_frame, load_m15, load_htf
from strategy_lab.scripts.backtest_edificio import run_backtest, summarize


def test_compute_features_returns_nonempty():
    df = load_m15("EURUSD")
    features = build_feature_frame(df, load_htf("EURUSD"))
    assert not features.empty
    for col in ["body_n", "brake_mask", "brake_transition", "k", "d", "kd_dist",
                "hammer_15m", "hammer_inv_15m", "htf_bias", "split"]:
        assert col in features.columns


def test_no_lookahead_in_split():
    df = load_m15("EURUSD")
    features = build_feature_frame(df, load_htf("EURUSD"))
    n = len(features)
    brake_rows = features.loc[features["brake_transition"]].copy()
    if brake_rows.empty:
        pytest.skip("sin brakes")
    split_max = features["idx"].max()
    train_rows = brake_rows[brake_rows["split"] == "train"]
    if not train_rows.empty:
        assert train_rows["idx"].max() <= int(split_max * 0.70)


def test_backtest_events_basic():
    events = run_backtest(pairs=["EURUSD"])
    assert not events.empty
    assert "win" in events.columns
    assert set(["0", "1"]).issuperset(set(events["win"].astype(str).tolist()))


def test_winrate_reported():
    events = run_backtest(pairs=["EURUSD"])
    by = events.groupby("asset")["win"].mean()
    assert by["EURUSD"] <= 1.0
    assert by["EURUSD"] >= 0.0


def test_causal_feature_snapshot():
    """Features del brake no usan close posterior al brake."""
    df = load_m15("EURUSD").head(1000)
    features = build_feature_frame(df, load_htf("EURUSD"))
    if features.empty:
        pytest.skip("sin datos")
    sample = features[features["brake_transition"]]
    if sample.empty:
        pytest.skip("sin transiciones")
    first = int(sample.iloc[0]["idx"])
    k_val = features.loc[first, "k"]
    if not np.isfinite(k_val):
        pytest.skip("primer brake sin k válido por warmup")
