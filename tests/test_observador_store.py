import sqlite3

from observador.store import EpisodeStore


def make_episode():
    return {
        "asset": "EURUSD",
        "source": "live",
        "ts_open": 1000.0,
        "ts_close": 1600.0,
        "state_final": "RESUELTO",
        "resolution_type": "ruptura",
        "formula_version": "v1",
        "confidence": 0.9,
        "states": [
            {"state": "ACUMULANDO", "ts_enter": 1000.0, "trigger_raw": 0.1,
             "trigger_norm": 0.2, "trigger_confidence": 0.8, "trigger_formula": "f1"},
            {"state": "RESUELTO", "ts_enter": 1500.0, "trigger_raw": 0.5,
             "trigger_norm": 0.7, "trigger_confidence": 0.95, "trigger_formula": "f2"},
        ],
        "pressure_points": [
            {"ts": 1100.0, "direction": 1, "net_advance_raw": 0.01,
             "net_advance_norm": 0.3, "continuity": 0.5, "confidence": 0.7,
             "formula_version": "v1"},
            {"ts": 1200.0, "direction": -1, "net_advance_raw": -0.02,
             "net_advance_norm": -0.4, "continuity": 0.6, "confidence": 0.75,
             "formula_version": "v1"},
            {"ts": 1300.0, "direction": 1, "net_advance_raw": 0.03,
             "net_advance_norm": 0.5, "continuity": 0.7, "confidence": 0.8,
             "formula_version": "v1"},
        ],
    }


def test_save_and_read_full_episode(tmp_path):
    db = str(tmp_path / "obs.db")
    ep = make_episode()
    with EpisodeStore(db) as store:
        eid = store.save_episode(ep)
        assert isinstance(eid, int)
        got = store.get_episode("EURUSD", 1000.0, "live")
    assert got is not None
    for k in ("asset", "source", "ts_open", "ts_close", "state_final",
              "resolution_type", "formula_version", "confidence"):
        assert got[k] == ep[k], k
    assert len(got["states"]) == 2
    for saved, orig in zip(got["states"], ep["states"]):
        assert saved == orig
    assert len(got["pressure_points"]) == 3
    for saved, orig in zip(got["pressure_points"], ep["pressure_points"]):
        assert saved == orig


def test_idempotent_save(tmp_path):
    db = str(tmp_path / "obs.db")
    with EpisodeStore(db) as store:
        id1 = store.save_episode(make_episode())
        id2 = store.save_episode(make_episode())
        assert id1 == id2
        assert store.count_episodes() == 1
        got = store.get_episode("EURUSD", 1000.0, "live")
        assert len(got["states"]) == 2
        assert len(got["pressure_points"]) == 3


def test_missing_episode_returns_none(tmp_path):
    with EpisodeStore(str(tmp_path / "obs.db")) as store:
        assert store.get_episode("GBPUSD", 1.0, "live") is None


def test_schema_version_is_1(tmp_path):
    db = str(tmp_path / "obs.db")
    EpisodeStore(db).close()
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute("SELECT schema_version FROM meta").fetchall()
        assert rows == [(1,)]
    finally:
        conn.close()


def test_reopen_does_not_duplicate_meta(tmp_path):
    db = str(tmp_path / "obs.db")
    EpisodeStore(db).close()
    EpisodeStore(db).close()
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM meta").fetchone()[0] == 1
    finally:
        conn.close()


def test_wal_mode_active(tmp_path):
    db = str(tmp_path / "obs.db")
    store = EpisodeStore(db)
    try:
        mode = store._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
    finally:
        store.close()
