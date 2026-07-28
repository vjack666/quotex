"""Lector de episodios del Atlas para el Discovery Engine (CONTRATO T2).

Carga episodios YA grabados por el Observador (Fase B) desde la DB SQLite
del Atlas. NO toca el bot ni el feed. Cero imports a scanner/strat_fractal/bot.

Regla R8: el conjunto PREDICTOR excluye ``end_reason``/``mfe``/``mae`` del
summary. El Episode conserva el summary completo (para miner/reporter) pero
``enumerate_features`` (space.py) NO los usa como feature.
"""

from __future__ import annotations

import sqlite3
from typing import Iterator

from .types import Episode

# Campos del summary que NO deben usarse como features del predictor (R8).
# Se mantienen en Episode.summary para auditoría/miner, pero space.py los omite.
_NON_PREDICTOR_SUMMARY = ("end_reason", "mfe", "mae")

# Columnas de la tabla episodes que mapean directamente al Episode.
_EPISODE_COLS = (
    "id",
    "asset",
    "source",
    "ts_open",
    "ts_close",
    "state_final",
)


def classify_source(source_str: str) -> tuple[str, str]:
    """Deriva (market, source) a partir del string ``source`` del Atlas (R9b).

    - contiene 'parquet' y no '_otc' -> ('forex', 'Dukascopy')
    - contiene '_otc' -> ('otc', 'Quotex OTC')
    """
    s = source_str or ""
    if "_otc" in s:
        return ("otc", "Quotex OTC")
    if "parquet" in s:
        return ("forex", "Dukascopy")
    # Por defecto: sin clasificación conocida, se deja sin mercado explícito.
    return ("unknown", s)


def _row_to_episode(conn: sqlite3.Connection, row: sqlite3.Row) -> Episode:
    episode_id = row["id"]
    asset = row["asset"] or ""
    source_raw = row["source"] or ""
    market, source = classify_source(source_raw)

    evolution = _load_evolution(conn, episode_id)
    summary = _load_summary(conn, episode_id)

    return Episode(
        episode_id=episode_id,
        asset=asset,
        market=market,
        source=source,
        ts_open=float(row["ts_open"] or 0.0),
        ts_close=float(row["ts_close"] or 0.0),
        state_final=row["state_final"] or "",
        evolution=evolution,
        summary=summary,
    )


def _load_evolution(conn: sqlite3.Connection, episode_id: int) -> list[dict]:
    cur = conn.execute(
        """
        SELECT bar_index, ts, price, distance_pips, mfe, mae, state,
               vars_json, vars_version
        FROM episode_evolution
        WHERE episode_id = ?
        ORDER BY bar_index ASC
        """,
        (episode_id,),
    )
    out: list[dict] = []
    for r in cur:
        out.append(
            {
                "bar_index": r["bar_index"],
                "ts": r["ts"],
                "price": r["price"],
                "distance_pips": r["distance_pips"],
                "mfe": r["mfe"],
                "mae": r["mae"],
                "state": r["state"],
                "vars_json": r["vars_json"],
                "vars_version": r["vars_version"],
            }
        )
    return out


def _load_summary(conn: sqlite3.Connection, episode_id: int) -> dict:
    cur = conn.execute(
        "SELECT * FROM episode_summary WHERE episode_id = ?", (episode_id,)
    )
    row = cur.fetchone()
    if row is None:
        return {}
    return {k: row[k] for k in row.keys()}


def load_episodes(db_path: str, asset: str | None = None,
                 limit: int | None = None, offset: int = 0) -> Iterator[Episode]:
    """Itera episodios del Atlas como ``Episode``.

    Args:
        db_path: ruta a la DB SQLite del Atlas.
        asset: si se indica, filtra por ese asset.
        limit: si se indica, limita el número de episodios cargados (útil para
            smoke tests sobre Atlas poblado sin cargar 125k episodios).
        offset: si se indica, salta los primeros N episodios (ordenados por
            ts_open). Permite cargar un slice que cruce el split_year de
            walk-forward sin leer todo el Atlas.

    Yields:
        Episode con evolution y summary poblados.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        sql = "SELECT id FROM episodes"
        args: tuple = ()
        if asset is not None:
            sql += " WHERE asset = ?"
            args = (asset,)
        sql += " ORDER BY ts_open"
        if limit is not None:
            sql += " LIMIT ?"
            args = args + (limit,)
            if offset:
                sql += " OFFSET ?"
                args = args + (offset,)
        id_rows = conn.execute(sql, args).fetchall()

        for (ep_id,) in id_rows:
            row = conn.execute(
                f"SELECT {','.join(_EPISODE_COLS)} FROM episodes WHERE id = ?",
                (ep_id,),
            ).fetchone()
            if row is None:
                continue
            yield _row_to_episode(conn, row)
    finally:
        conn.close()
