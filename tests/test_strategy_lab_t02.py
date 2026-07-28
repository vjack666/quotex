"""Tests T2: strategy_parser descompone y valida pasos/leyes."""
import numpy as np
import pytest

from strategy_lab.strategy_parser import (
    parse_strategy, primitive_predicate, UnknownStepError, KNOWN_PRIMITIVES,
)
from strategy_lab.config_loader import StrategyLabConfig, default_config_path
from strategy_lab import feature_calc as fc

CFG = StrategyLabConfig.load(default_config_path())
PIP = 1e-4


def _feats():
    n = 120
    c = np.cumsum(np.random.default_rng(0).normal(0, 0.5 * PIP, n))
    c[-50:] += np.arange(1, 51) * 10 * PIP
    o = c - 0.3 * PIP
    h = np.maximum(o, c) + 0.3 * PIP
    l = np.minimum(o, c) - 0.3 * PIP
    return fc.compute_features(o, h, l, c, CFG.__dict__)


def test_parse_primitives_only():
    prop = {"name": "rebote", "steps": [
        {"name": "imp", "primitive": "impulse_up"},
        {"name": "brk", "primitive": "brake"},
    ]}
    ps = parse_strategy(prop, known_law_ids={"#1"})
    assert ps.name == "rebote"
    assert len(ps.steps) == 2
    assert all(not s.is_law() for s in ps.steps)


def test_parse_rejects_unknown_primitive():
    prop = {"name": "x", "steps": [{"name": "bad", "primitive": "no_existe"}]}
    with pytest.raises(UnknownStepError):
        parse_strategy(prop, known_law_ids={"#1"})


def test_parse_rejects_unknown_law_ref():
    prop = {"name": "x", "steps": [{"name": "l", "law_ref": "#99"}]}
    with pytest.raises(UnknownStepError):
        parse_strategy(prop, known_law_ids={"#1"})


def test_parse_accepts_known_law_ref():
    prop = {"name": "x", "steps": [{"name": "l", "law_ref": "#1"}]}
    ps = parse_strategy(prop, known_law_ids={"#1"})
    assert ps.steps[0].is_law()
    assert ps.steps[0].spec["law_ref"] == "#1"


def test_primitive_predicate_impulse_up_true_on_ramp():
    f = _feats()
    step = parse_strategy(
        {"name": "x", "steps": [{"name": "imp", "primitive": "impulse_up"}]},
        known_law_ids=set(),
    ).steps[0]
    mask = primitive_predicate(step, f, CFG.__dict__)
    assert mask.dtype == bool
    assert mask.any()


def test_primitive_predicate_brake_combines_with_stoch():
    f = _feats()
    brk = parse_strategy(
        {"name": "x", "steps": [{"name": "b", "primitive": "brake"}]},
        known_law_ids=set(),
    ).steps[0]
    ob = parse_strategy(
        {"name": "x", "steps": [{"name": "o", "primitive": "stoch_overbought"}]},
        known_law_ids=set(),
    ).steps[0]
    m_brk = primitive_predicate(brk, f, CFG.__dict__)
    m_ob = primitive_predicate(ob, f, CFG.__dict__)
    assert m_brk.shape == m_ob.shape == f.brake_mask.shape
