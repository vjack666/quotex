"""T3/T4 — EpisodeEvolutionWriter: mfe/mae/distance a mano, versionado."""
import json

from observador.evolution import EpisodeEvolutionWriter
from observador.store import EpisodeStore


def _candle(ts, close):
    return {"ts": ts, "open": close, "high": close, "low": close,
            "close": close}


def test_secuencia_sintetica_mfe_mae_a_mano():
    origin = 1.1000
    w = EpisodeEvolutionWriter("EURUSD", origin_ts=100.0,
                               origin_price=origin, vars_version="vars_v1")
    closes = [1.1005, 1.1010, 1.0995, 1.1020, 1.0990]
    # distancias en pips (pip=1e-4), calculadas a mano:
    exp_dist = [5.0, 10.0, -5.0, 20.0, -10.0]
    exp_mfe = [5.0, 10.0, 10.0, 20.0, 20.0]
    exp_mae = [0.0, 0.0, -5.0, -5.0, -10.0]
    for i, close in enumerate(closes):
        row = w.record(i, _candle(100.0 + i, close), "IMPULSE",
                       {"continuity": 0.5})
        assert row["bar_index"] == i  # 0-based
        assert round(row["distance_pips"], 6) == exp_dist[i]
        assert round(row["mfe"], 6) == exp_mfe[i]
        assert round(row["mae"], 6) == exp_mae[i]
        assert row["ts"] == 100.0 + i
        assert json.loads(row["vars_json"]) == {"continuity": 0.5}


def test_vars_version_se_propaga_y_lee(tmp_path):
    w = EpisodeEvolutionWriter("EURUSD", origin_ts=0.0,
                               origin_price=1.1, vars_version="vars_v7")
    rows = [w.record(i, _candle(float(i), 1.1 + i * 0.0001), "IMPULSE",
                     {"energy": i}) for i in range(3)]
    assert all(r["vars_version"] == "vars_v7" for r in rows)
    with EpisodeStore(str(tmp_path / "e.db")) as st:
        st.save_evolution(1, rows)
        got = st.get_evolution(1)
        assert [r["vars_version"] for r in got] == ["vars_v7"] * 3
        assert [json.loads(r["vars_json"]) for r in got] == [
            {"energy": 0}, {"energy": 1}, {"energy": 2}]
