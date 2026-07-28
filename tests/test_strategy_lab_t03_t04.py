"""Tests T3+T4: variant_searcher + backtester walk-forward."""
import numpy as np
import pandas as pd
import pytest

from strategy_lab.config_loader import StrategyLabConfig, default_config_path
from strategy_lab import feature_calc as fc
from strategy_lab.strategy_parser import parse_strategy
from strategy_lab.variant_searcher import enumerate_variants, variant_from_included
from strategy_lab.backtester import score_variant

CFG = StrategyLabConfig.load(default_config_path())
PIP = 1e-4


def _series(n=400):
    rng = np.random.default_rng(7)
    c = np.cumsum(rng.normal(0, 0.5 * PIP, n))
    # impulso alcista fuerte seguido de FRENO con alternancia real de cuerpos
    for start in (100, 250):
        ramp = start + 40
        c[start:ramp] += np.arange(1, 41) * 10 * PIP        # rampa 40 velas
        peak = c[ramp - 1]
        c[ramp]   = peak + 1 * PIP
        c[ramp+1] = peak - 1 * PIP
        c[ramp+2] = peak + 0.5 * PIP
    o = c.copy()
    # cuerpos alternados en la zona de freno para disparar 'brake'
    for start in (100, 250):
        ramp = start + 40
        o[ramp]   = c[ramp]   - 1 * PIP    # cuerpo +
        o[ramp+1] = c[ramp+1] + 1 * PIP    # cuerpo -
        o[ramp+2] = c[ramp+2] - 0.5 * PIP  # cuerpo +
    h = np.maximum(o, c) + 0.3 * PIP
    l = np.minimum(o, c) - 0.3 * PIP
    t = pd.date_range("2018-01-01", periods=n, freq="15min")
    feats = fc.compute_features(o, h, l, c, CFG.__dict__)
    return feats, np.array(t.values)


def _strategy():
    return parse_strategy({
        "name": "rebote_test",
        "steps": [
            {"name": "imp", "primitive": "impulse_up"},
            {"name": "brk", "primitive": "brake"},
            {"name": "ob", "primitive": "stoch_overbought"},
        ],
    }, known_law_ids={"#1"})


def test_enumerate_variants_respects_max_depth_and_no_extra_steps():
    ps = _strategy()
    vars_ = enumerate_variants(ps, CFG.__dict__)
    # 3 pasos -> subconjuntos no vacíos de tamaño 1..3, permutaciones, todas <= max_depth(6)
    assert len(vars_) > 0
    for v in vars_:
        assert len(v.order) <= CFG.max_depth
        assert set(v.order).issubset(set(range(len(ps.steps))))


def test_enumerate_is_deterministic():
    ps = _strategy()
    a = enumerate_variants(ps, CFG.__dict__)
    b = enumerate_variants(ps, CFG.__dict__)
    assert [v.order for v in a] == [v.order for v in b]


def test_variant_from_included_keeps_original_order():
    ps = _strategy()
    v = variant_from_included(ps, [2, 0])  # ob, imp
    assert v.order == (2, 0)


def test_score_variant_known_gives_edge_and_split():
    feats, t = _series()
    ps = _strategy()
    v = variant_from_included(ps, [0, 1, 2])  # impulse_up + brake + overbought
    sc = score_variant(v, ps, feats, CFG.__dict__, t, split_year=2020)
    assert sc.direction == "dn"
    assert sc.n_train + sc.n_test > 0
    # edge en [0,1]
    assert 0.0 <= sc.edge_train <= 1.0
    assert 0.0 <= sc.edge_test <= 1.0


def test_score_variant_no_signal_returns_zero():
    # serie monótona alcista: nunca hay impulse_dn -> la estrategia no dispara
    c = np.arange(1, 401) * 1e-4
    o = c - 0.1e-4
    h = c + 0.1e-4
    l = o - 0.1e-4
    t = np.array(pd.date_range("2018-01-01", periods=400, freq="15min").values)
    feats = fc.compute_features(o, h, l, c, CFG.__dict__)
    ps = parse_strategy({
        "name": "x",
        "steps": [
            {"name": "d", "primitive": "impulse_dn"},
            {"name": "o", "primitive": "stoch_overbought"},
        ],
    }, known_law_ids=set())
    v = variant_from_included(ps, [0, 1])
    sc = score_variant(v, ps, feats, CFG.__dict__, t, split_year=2020)
    assert sc.n_train == 0 and sc.n_test == 0
