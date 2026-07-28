"""Tests de brake_eval — edge del freno aislado (muerte del impulso)."""
import numpy as np
import pytest

from strategy_lab import brake_eval as be


def _serie_freno_claro():
    """2 impulsos que mueren y rebotan en la vela siguiente (fwd=1)."""
    n = 12
    brake = np.zeros(n, dtype=bool)
    net = np.zeros(n)
    up = np.zeros(n, dtype=bool)
    dn = np.zeros(n, dtype=bool)
    # impulso bajista que muere en i=4 -> rebote alcista anclado en i=4
    net[4] = -0.0030
    brake[4] = True
    up[4] = True
    # impulso alcista que muere en i=8 -> rebote bajista anclado en i=8
    net[8] = +0.0030
    brake[8] = True
    dn[8] = True
    return {"brake_mask": brake, "impulse_net": net,
            "rebote_up": up, "rebote_dn": dn}


def test_freno_claro_da_wr_1():
    st = be.brake_winrate(_serie_freno_claro())
    assert st["n"] == 2
    assert st["wr"] == pytest.approx(1.0, abs=1e-9)
    assert st["n_up"] == 1 and st["wr_up"] == 1.0
    assert st["n_dn"] == 1 and st["wr_dn"] == 1.0


def test_sin_freno_da_n_cero():
    s = _serie_freno_claro()
    s = {k: np.zeros(len(v), dtype=bool) if v.dtype == bool else np.zeros(len(v))
         for k, v in s.items()}
    st = be.brake_winrate(s)
    assert st["n"] == 0
    assert st["wr"] == 0.0


def test_vectorizado_coincide_con_feature_calc():
    """El brake/rebote vectorizado debe coincidir con compute_features (ref)."""
    from strategy_lab import feature_calc as fc
    rng = np.random.default_rng(0)
    n = 200
    c = np.cumsum(rng.normal(0, 1e-4, n)) + 1.0
    o = c - rng.normal(0, 5e-5, n)
    h = np.maximum(c, o) + np.abs(rng.normal(0, 5e-5, n))
    l = np.minimum(c, o) - np.abs(rng.normal(0, 5e-5, n))
    cfg = {
        "stochastic": {"k": 14, "d": 3, "smooth": 3},
        "impulse": {"window": 8, "min_pips": 30},
        "brake": {"fwd": 3, "max_advance_frac": 0.10, "require_alternation": True},
        "rebote": {"fwd": 3, "min_pips": 8},
    }
    ref = fc.compute_features(o, h, l, c, cfg)
    vec = be.compute_brake_and_rebote(o, h, l, c, cfg)
    assert np.array_equal(ref.brake_mask, vec["brake_mask"]), "brake_mask difiere"
    assert np.array_equal(ref.rebote_up, vec["rebote_up"]), "rebote_up difiere"
    assert np.array_equal(ref.rebote_dn, vec["rebote_dn"]), "rebote_dn difiere"
