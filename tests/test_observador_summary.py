"""T7 — EpisodeSummary: snapshot de traza sintética conocida, campo a campo."""
from observador.summary import EpisodeSummary

# Fixture de cfg summary con umbrales LOCALES.
CFG_SUMMARY = {
    "summary_version": "summary_v1",
    "quality_symmetry_weight": 0.5,
    "velocity_fast_pips_per_bar": 1.0,
    "violence_high_pips_per_bar": 5.0,
    "curve_flat_mfe_pips": 1.0,
    "curve_convex_retention": 0.5,
}


def _row(i, dist, mfe, mae, state="PRESSURE"):
    return {"bar_index": i, "ts": float(i), "price": 1.1,
            "distance_pips": dist, "mfe": mfe, "mae": mae, "state": state,
            "vars_json": None, "vars_version": "vars_v1"}


def test_snapshot_traza_sintetica_campo_a_campo():
    # traza conocida: sube a 20 pips, retrocede, cierra en 15
    rows = [
        _row(0, 5.0, 5.0, 0.0),
        _row(1, 20.0, 20.0, 0.0),
        _row(2, -5.0, 20.0, -5.0),
        _row(3, 15.0, 20.0, -5.0),
    ]
    s = EpisodeSummary(CFG_SUMMARY).compute(rows, "REBOUND")

    # cálculos a mano:
    # mfe=20, mae=-5, net=15, duration=4
    # symmetry = (net-mae)/(mfe-mae) = 20/25 = 0.8
    # base quality = 20/25 = 0.8; quality = 0.8*0.5 + 0.8*0.5 = 0.8
    # pips/bar = 15/4 = 3.75 >= 1.0 → fast
    # max step = |−5−20| = 25 >= 5 → high
    # mfe(20) >= flat(1) y net/mfe = 0.75 >= 0.5 → convex
    assert s["mfe"] == 20.0
    assert s["mae"] == -5.0
    assert s["duration_bars"] == 4
    assert round(s["symmetry"], 6) == 0.8
    assert round(s["quality"], 6) == 0.8
    assert s["velocity"] == "fast"
    assert s["violence"] == "high"
    assert s["curve_shape"] == "convex"
    assert s["episode_type"] == "REBOUND"
    assert s["summary_version"] == "summary_v1"


def test_traza_plana_y_lenta():
    rows = [_row(i, 0.1, 0.1, 0.0) for i in range(10)]
    s = EpisodeSummary(CFG_SUMMARY).compute(rows, "CHAOS")
    assert s["curve_shape"] == "flat"      # mfe < curve_flat_mfe_pips
    assert s["velocity"] == "slow"
    assert s["violence"] == "low"
    assert s["episode_type"] == "CHAOS"    # hereda resolution_type


def test_curva_concava_devuelve_todo():
    # sube a 20 y devuelve todo (net 0) → cóncava, simetría baja
    rows = [
        _row(0, 10.0, 10.0, 0.0),
        _row(1, 20.0, 20.0, 0.0),
        _row(2, 0.0, 20.0, 0.0),
    ]
    s = EpisodeSummary(CFG_SUMMARY).compute(rows, "CONTINUATION")
    assert s["curve_shape"] == "concave"
    assert round(s["symmetry"], 6) == 0.0  # (0-0)/(20-0)
