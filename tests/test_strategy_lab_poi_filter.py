"""Tests del filtro POI (M3) del freno."""
import numpy as np

from strategy_lab.poi_filter import poi_zones, brake_within_poi


def _flat(n, base=1.1000):
    o = np.full(n, base); h = o + 0.0002; l = o - 0.0002; c = o.copy()
    return o, h, l, c


def _series_with_level():
    """Serie sintética: nivel 1.1050 tocado como swing high 2 veces."""
    n = 60
    o, h, l, c = _flat(n)
    for peak in (10, 30):
        h[peak] = 1.1050
        h[peak - 1] = h[peak + 1] = 1.1030
    # velas posteriores que vuelven a tocar la banda
    h[40] = 1.1049
    return o, h, l, c


def test_poi_zones_marks_touched_level():
    o, h, l, c = _series_with_level()
    z = poi_zones(o, h, l, c, lookback=50, min_touches=2, tol_pips=5.0)["poi_zone"]
    assert z.dtype == bool and len(z) == 60
    assert z[30]           # segundo toque activa la zona
    assert z[40]           # retesteo dentro de la banda
    assert not z[5]        # antes de activarse, causal


def test_poi_zones_no_level_all_false():
    o, h, l, c = _flat(50)
    # sin swings únicos (serie plana) -> sin zonas
    z = poi_zones(o, h, l, c)["poi_zone"]
    assert not z.any()


def _synthetic_feat(n=100):
    brake = np.zeros(n, bool)
    brake[[20, 40, 60, 80]] = True
    net = np.full(n, -0.005)          # impulsos bajistas -> rebote up
    up = np.zeros(n, bool)
    up[[20, 40, 60]] = True           # 3 de 4 ganan
    dn = np.zeros(n, bool)
    return {"brake_mask": brake, "impulse_net": net,
            "rebote_up": up, "rebote_dn": dn}


def test_brake_within_poi_coherent_wr():
    feat = _synthetic_feat()
    zone = np.zeros(100, bool)
    zone[[20, 40]] = True             # solo 2 señales caen en POI, ambas ganan
    res = brake_within_poi(feat, {"poi_zone": zone})
    assert res["n_total"] == 4 and res["n_filtrado"] == 2
    assert res["wr_total"] == 0.75
    assert res["wr_filtrado"] == 1.0
    assert abs(res["pct_kept"] - 0.5) < 1e-12


def test_pct_kept_in_unit_interval():
    feat = _synthetic_feat()
    rng = np.random.default_rng(7)
    zone = rng.random(100) > 0.5
    res = brake_within_poi(feat, {"poi_zone": zone})
    assert 0.0 <= res["pct_kept"] <= 1.0


def test_empty_poi_no_crash():
    feat = _synthetic_feat()
    res = brake_within_poi(feat, {"poi_zone": np.zeros(100, bool)})
    assert res["n_filtrado"] == 0
    assert res["wr_filtrado"] == 0.0
    assert res["pct_kept"] == 0.0
