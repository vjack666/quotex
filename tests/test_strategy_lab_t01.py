"""Tests T0+T1: config_loader y feature_calc sobre fixtures M15 sintéticos."""
import numpy as np
import pytest

from strategy_lab.config_loader import StrategyLabConfig, default_config_path
from strategy_lab import feature_calc as fc

CFG = StrategyLabConfig.load(default_config_path())

# Pip para EURUSD
PIP = 1e-4


def _synth(seed=0, n=200):
    """Serie OHLC sintética: tramo alcista fuerte sostenido y dominante al final."""
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 0.5 * PIP, n)   # ruido chico
    c = np.cumsum(noise)
    # impulso alcista claro: 10 pip/vela en las ultimas 50 velas (>30 pip en 8)
    c[-50:] += np.arange(1, 51) * 10 * PIP
    o = c - rng.normal(0, 0.5 * PIP, n)
    h = np.maximum(o, c) + np.abs(rng.normal(0, 0.5 * PIP, n))
    l = np.minimum(o, c) - np.abs(rng.normal(0, 0.5 * PIP, n))
    return o, h, l, c


def test_config_loads_and_reflects_values():
    assert CFG.seed == 20260728
    assert CFG.p_cut == 0.05
    assert CFG.stochastic["k"] == 14
    assert CFG.impulse["min_pips"] == 30


def test_stochastic_full_shape_and_range():
    o, h, l, c = _synth(1)
    kk, dd = fc.stochastic_full(h, l, c, 14, 3, 3)
    assert kk.shape == c.shape
    # tras el warmup los valores están en [0,100]
    assert np.nanmin(kk[20:]) >= 0.0
    assert np.nanmax(kk[20:]) <= 100.0


def test_stochastic_known_reference():
    # rango plano: %K debe ser 50 (rng=0 -> 50 por definición)
    h = np.full(30, 1.10)
    l = np.full(30, 1.10)
    c = np.full(30, 1.10)
    kk, _ = fc.stochastic_full(h, l, c, 14, 3, 3)
    assert np.allclose(kk[20:], 50.0, atol=1e-9)


def test_features_finite_and_signals_present():
    o, h, l, c = _synth(2)
    f = fc.compute_features(o, h, l, c, CFG.__dict__)
    assert np.isfinite(f.stoch_k).all()
    assert np.isfinite(f.impulse_net).all()
    # el impulso forzado al final debe generar al menos una señal de freno o impulso
    assert np.abs(f.impulse_net).max() > 30 * PIP
    # brake_mask es booleano y acotado
    assert f.brake_mask.dtype == bool


def test_features_no_signals_on_flat():
    c = np.full(200, 1.10)
    o = np.full(200, 1.10)
    h = np.full(200, 1.10)
    l = np.full(200, 1.10)
    f = fc.compute_features(o, h, l, c, CFG.__dict__)
    # sin impulso no hay freno
    assert f.brake_mask.sum() == 0
    assert np.abs(f.impulse_net).max() == 0.0
