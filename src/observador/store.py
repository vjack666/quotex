"""EpisodeStore — persistencia SQLite (WAL) de episodios del Observador (D4)."""
from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    schema_version INTEGER,
    created_ts REAL
);
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY,
    asset TEXT,
    source TEXT,
    ts_open REAL,
    ts_close REAL,
    state_final TEXT,
    resolution_type TEXT,
    formula_version TEXT,
    confidence REAL,
    UNIQUE(asset, ts_open, source)
);
CREATE TABLE IF NOT EXISTS episode_states (
    episode_id INT,
    state TEXT,
    ts_enter REAL,
    trigger_raw REAL,
    trigger_norm REAL,
    trigger_confidence REAL,
    trigger_formula TEXT
);
CREATE TABLE IF NOT EXISTS pressure_points (
    episode_id INT,
    ts REAL,
    direction INT,
    net_advance_raw REAL,
    net_advance_norm REAL,
    continuity REAL,
    confidence REAL,
    formula_version TEXT
);
"""

_STATE_FIELDS = ("state", "ts_enter", "trigger_raw", "trigger_norm",
                 "trigger_confidence", "trigger_formula")
_POINT_FIELDS = ("ts", "direction", "net_advance_raw", "net_advance_norm",
                 "continuity", "confidence", "formula_version")


class EpisodeStore:
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        cur = self._conn.execute("SELECT COUNT(*) FROM meta")
        if cur.fetchone()[0] == 0:
            # created_ts lo pone SQLite: prohibido reloj de pared en Python
            # dentro de src/observador/ (test adversarial T8).
            self._conn.execute(
                "INSERT INTO meta (schema_version, created_ts) "
                "VALUES (?, strftime('%s','now'))",
                (SCHEMA_VERSION,),
            )
        self._conn.commit()

    # -- API ----------------------------------------------------------------
    def save_episode(self, episode: dict) -> int:
        """Guarda un episodio de forma idempotente por (asset, ts_open, source)."""
        key = (episode["asset"], episode["ts_open"], episode["source"])
        try:
            self._conn.execute("BEGIN")
            row = self._conn.execute(
                "SELECT id FROM episodes WHERE asset=? AND ts_open=? AND source=?",
                key,
            ).fetchone()
            if row is None:
                cur = self._conn.execute(
                    "INSERT INTO episodes (asset, source, ts_open, ts_close, "
                    "state_final, resolution_type, formula_version, confidence) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (episode["asset"], episode["source"], episode["ts_open"],
                     episode["ts_close"], episode["state_final"],
                     episode["resolution_type"], episode["formula_version"],
                     episode["confidence"]),
                )
                episode_id = cur.lastrowid
            else:
                episode_id = row["id"]
                self._conn.execute(
                    "UPDATE episodes SET ts_close=?, state_final=?, "
                    "resolution_type=?, formula_version=?, confidence=? WHERE id=?",
                    (episode["ts_close"], episode["state_final"],
                     episode["resolution_type"], episode["formula_version"],
                     episode["confidence"], episode_id),
                )
                self._conn.execute(
                    "DELETE FROM episode_states WHERE episode_id=?", (episode_id,))
                self._conn.execute(
                    "DELETE FROM pressure_points WHERE episode_id=?", (episode_id,))
            self._conn.executemany(
                "INSERT INTO episode_states (episode_id, state, ts_enter, "
                "trigger_raw, trigger_norm, trigger_confidence, trigger_formula) "
                "VALUES (?,?,?,?,?,?,?)",
                [(episode_id,) + tuple(s[f] for f in _STATE_FIELDS)
                 for s in episode.get("states", [])],
            )
            self._conn.executemany(
                "INSERT INTO pressure_points (episode_id, ts, direction, "
                "net_advance_raw, net_advance_norm, continuity, confidence, "
                "formula_version) VALUES (?,?,?,?,?,?,?,?)",
                [(episode_id,) + tuple(p[f] for f in _POINT_FIELDS)
                 for p in episode.get("pressure_points", [])],
            )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        return episode_id

    def get_episode(self, asset: str, ts_open: float, source: str):
        row = self._conn.execute(
            "SELECT * FROM episodes WHERE asset=? AND ts_open=? AND source=?",
            (asset, ts_open, source),
        ).fetchone()
        if row is None:
            return None
        episode = {k: row[k] for k in ("asset", "source", "ts_open", "ts_close",
                                       "state_final", "resolution_type",
                                       "formula_version", "confidence")}
        episode["id"] = row["id"]
        episode["states"] = [
            {f: r[f] for f in _STATE_FIELDS}
            for r in self._conn.execute(
                "SELECT * FROM episode_states WHERE episode_id=? ORDER BY rowid",
                (row["id"],))
        ]
        episode["pressure_points"] = [
            {f: r[f] for f in _POINT_FIELDS}
            for r in self._conn.execute(
                "SELECT * FROM pressure_points WHERE episode_id=? ORDER BY rowid",
                (row["id"],))
        ]
        return episode

    def count_episodes(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
