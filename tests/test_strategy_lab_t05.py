"""Tests T5: ablator + falsifier."""
import numpy as np
import pandas as pd
import pytest

from strategy_lab.config_loader import StrategyLabConfig, default_config_path
from strategy_lab import feature_calc as fc
from strategy_lab.strategy_parser import parse_strategy
from strategy_lab.variant_searcher import variant_from_included
from strategy_lab.ablator import ablate
from strategy_lab.falsifier import falsify

CFG = StrategyLabConfig.load(default_config_path())
PIP = 1e-4


def _series(n=400):
    rng = np.random.default_rng(7)
    c = np.cumsum(rng.normal(0, 0.5 * PIP, n))
    for start in (100, 250):
        ramp = start + 40
        c[start:ramp] += np.arange(1, 41) * 10 * PIP
        peak = c[ramp - 1]
        c[ramp]   = peak + 1 * PIP
        c[ramp+1] = peak - 1 * PIP
        c[ramp+2] = peak + 0.5 * PIP
    o = c.copy()
    for start in (100, 250):
        ramp = start + 40
        o[ramp]   = c[ramp]   - 1 * PIP
        o[ramp+1] = c[ramp+1] + 1 * PIP
        o[ramp+2] = c[ramp+2] - 0.5 * PIP
    h = np.maximum(o, c) + 0.3 * PIP
    l = np.minimum(o, c) - 0.3 * PIP
    t = pd.date_range("2018-01-01", periods=n, freq="15min")
    feats = fc.compute_features(o, h, l, c, CFG.__dict__)
    return feats, np.array(t.values)


def test_ablate_reports_one_row_per_step():
    feats, t = _series()
    ps = parse_strategy({
        "name": "x",
        "steps": [
            {"name": "imp", "primitive": "impulse_up"},
            {"name": "brk", "primitive": "brake"},
            {"name": "ob", "primitive": "stoch_overbought"},
        ],
    }, known_law_ids={"#1"})
    v = variant_from_included(ps, [0, 1, 2])
    rows = ablate(v, ps, feats, CFG.__dict__, t)
    assert len(rows) == 3
    assert all(0.0 <= r.delta <= 1.0 for r in rows)


def test_ablate_marks_useless_step_for_removal():
    feats, t = _series()
    # paso inútil: poi_zone (no aporta en este fixture) junto a impulse_up
    ps = parse_strategy({
        "name": "x",
        "steps": [
            {"name": "imp", "primitive": "impulse_up"},
            {"name": "poi", "primitive": "poi_zone"},
        ],
    }, known_law_ids=set())
    v = variant_from_included(ps, [0, 1])
    rows = ablate(v, ps, feats, CFG.__dict__, t)
    # el paso poi_zone debe tener delta bajo (se marca para eliminar)
    poi = [r for r in rows if r.step_name == "poi"][0]
    assert poi.delta < CFG.min_contribution or poi.edge_without >= poi.edge_full - 1e-9


def test_falsify_real_signal_has_low_p():
    feats, t = _series()
    ps = parse_strategy({
        "name": "x",
        "steps": [
            {"name": "imp", "primitive": "impulse_up"},
            {"name": "brk", "primitive": "brake"},
            {"name": "ob", "primitive": "stoch_overbought"},
        ],
    }, known_law_ids={"#1"})
    v = variant_from_included(ps, [0, 1, 2])
    rows = falsify(v, ps, feats, CFG.__dict__, t, n_perm=50)
    assert len(rows) == 3
    assert all(0.0 <= r.p_value <= 1.0 for r in rows)
