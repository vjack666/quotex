"""T2 — store Fase B: nuevas tablas + upserts idempotentes."""
from observador.store import EpisodeStore


def _row(i, ts=100.0):
    return {"bar_index": i, "ts": ts + i, "price": 1.1 + i * 0.0001,
            "distance_pips": float(i), "mfe": float(i), "mae": 0.0,
            "state": "IMPULSE", "vars_json": "{}", "vars_version": "vars_v1"}


def _summary(episode_id, quality=0.5):
    return {"episode_id": episode_id, "quality": quality, "velocity": "fast",
            "violence": "low", "curve_shape": "convex", "symmetry": 0.9,
            "episode_type": "Reversal", "duration_bars": 5, "mfe": 4.0,
            "mae": -1.0, "end_reason": "NEW_EXPANSION", "end_confidence": 0.8,
            "finished": 1, "capture_limit": 0,
            "vars_version": "vars_v1", "summary_version": "summary_v1"}


def test_esquema_crea_tablas_nuevas(tmp_path):
    with EpisodeStore(str(tmp_path / "e.db")) as st:
        tables = {r[0] for r in st._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"episode_evolution", "episode_summary",
            "episode_version"} <= tables


def test_save_evolution_no_duplica(tmp_path):
    with EpisodeStore(str(tmp_path / "e.db")) as st:
        rows = [_row(i) for i in range(3)]
        st.save_evolution(7, rows)
        st.save_evolution(7, rows)  # doble llamada = mismo estado
        got = st.get_evolution(7)
        assert len(got) == 3
        assert [r["bar_index"] for r in got] == [0, 1, 2]


def test_save_summary_upsert(tmp_path):
    with EpisodeStore(str(tmp_path / "e.db")) as st:
        st.save_summary(_summary(7, quality=0.5))
        st.save_summary(_summary(7, quality=0.9))
        got = st.get_summary(7)
        assert got["quality"] == 0.9
        n = st._conn.execute(
            "SELECT COUNT(*) FROM episode_summary").fetchone()[0]
        assert n == 1
        ver = st._conn.execute(
            "SELECT * FROM episode_version WHERE episode_id=7").fetchone()
        assert ver["vars_version"] == "vars_v1"
        assert ver["summary_version"] == "summary_v1"
        assert st.get_summary(999) is None
