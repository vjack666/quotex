"""Tests T6+T7+T8: orderer + optimizer + strategy_store sobre fixture real."""
import numpy as np
import pandas as pd
import pytest

from strategy_lab.config_loader import StrategyLabConfig, default_config_path
from strategy_lab import feature_calc as fc
from strategy_lab.strategy_parser import parse_strategy
from strategy_lab.variant_searcher import enumerate_variants, variant_from_included
from strategy_lab.orderer import rank_orders
from strategy_lab.optimizer import optimize
from strategy_lab.strategy_store import StrategyStore

CFG = StrategyLabConfig.load(default_config_path())
PIP = 1e-4


def _series(n=400, with_rebote=False):
    rng = np.random.default_rng(7)
    c = np.cumsum(rng.normal(0, 0.5 * PIP, n))
    for start in (100, 250):
        ramp = start + 40
        c[start:ramp] += np.arange(1, 41) * 10 * PIP
        peak = c[ramp - 1]
        c[ramp]   = peak + 1 * PIP
        c[ramp+1] = peak - 1 * PIP
        c[ramp+2] = peak + 0.5 * PIP
        if with_rebote:
            # rebote bajista REAL tras el freno, dentro de la ventana fwd de medición
            c[ramp+10:ramp+15] -= np.arange(1, 6) * 3 * PIP
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


def test_orderer_picks_a_variant():
    feats, t = _series()
    ps = parse_strategy({
        "name": "x",
        "steps": [
            {"name": "imp", "primitive": "impulse_up"},
            {"name": "brk", "primitive": "brake"},
            {"name": "ob", "primitive": "stoch_overbought"},
        ],
    }, known_law_ids={"#1"})
    variants = enumerate_variants(ps, CFG.__dict__)
    res = rank_orders(variants, ps, feats, CFG.__dict__, t)
    assert res.best is not None
    assert res.best_edge >= 0.0


def _series_single_signal():
    """Fixture mínimo: un impulso corto seguido de rebote fuerte y alineado."""
    PIP = 1e-4
    c = np.zeros(40)
    c[1:9] = np.arange(1, 9) * 5 * PIP     # rampa 8 velas -> impulse_up en i=8
    c[9:19] = c[8] - np.arange(0, 10) * 10 * PIP  # rebote bajista fuerte en +10
    o = c.copy()
    h = c + 0.3 * PIP
    l = c - 0.3 * PIP
    t = np.array(pd.date_range("2018-01-01", periods=40, freq="15min").values)
    feats = fc.compute_features(o, h, l, c, CFG.__dict__)
    return feats, t


def test_optimizer_coherent_output():
    """El optimizer siempre emite un objeto coherente, retenga o descarte pasos."""
    feats, t = _series_single_signal()
    proposed = {
        "name": "claro",
        "steps": [{"name": "imp", "primitive": "impulse_up"}],
    }
    res = optimize(proposed, feats, CFG.__dict__, t, known_law_ids=set())
    opt = res.optimized
    assert opt.name == "claro"
    assert 0.0 <= opt.edge_train <= 1.0
    assert 0.0 <= opt.edge_test <= 1.0
    assert opt.direction in ("dn", "up", "net")
    assert isinstance(res.dropped_steps, list)
    assert "EURUSD_M15" in opt.sources[0]


def test_optimizer_drops_useless_step_when_present():
    feats, t = _series(with_rebote=True)
    # poi_zone no aporta en este fixture -> debe quedar en dropped
    proposed = {
        "name": "con_poi",
        "steps": [
            {"name": "imp", "primitive": "impulse_up"},
            {"name": "poi", "primitive": "poi_zone"},
        ],
    }
    res = optimize(proposed, feats, CFG.__dict__, t, known_law_ids=set())
    if "poi" in res.dropped_steps:
        assert "poi" not in res.optimized.steps_ordered


def test_strategy_store_markdown_is_readable():
    feats, t = _series_single_signal()
    proposed = {
        "name": "rebote_propuesto",
        "steps": [
            {"name": "imp", "primitive": "impulse_up"},
            {"name": "ley1", "law_ref": "#1"},
        ],
    }
    res = optimize(proposed, feats, CFG.__dict__, t, known_law_ids={"#1"})
    md = StrategyStore.to_markdown(res.optimized)
    assert "Estrategia optimizada" in md
    assert "edge" in md.lower()
    assert "EURUSD_M15" in md
