#!/usr/bin/env python3
"""Forense EDIFICIO: diagnóstico WIN/LOSS del 2026-07-31."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\db\black_box_strat_2026-07-31.db")


def con():
    return sqlite3.connect(str(DB_PATH))


def section(title):
    print(f"\n{'='*72}\n{title}\n{'='*72}")


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: no existe {DB_PATH}")
        return 2
    print(f"DB: {DB_PATH}  size={DB_PATH.stat().st_size:,} bytes")

    c = con()
    cur = c.cursor()

    # 1) Esquema y columnas clave
    section("ESQUEMA scan_candidates")
    cur.execute("PRAGMA table_info(scan_candidates)")
    cols = {row[1]: row for row in cur.fetchall()}
    for col in ["order_id", "order_result", "profit", "duration_sec", "decision_reason", "strategy_details", "created_at", "updated_at", "close_candle_15m", "close_candle_5m", "close_stoch_m15"]:
        print(col, cols.get(col))

    # 2) Conteo por estrategia y order_result
    section("CONTEOS strategy / order_result")
    cur.execute("""
        SELECT strategy, order_result, COUNT(*) AS n
        FROM scan_candidates
        GROUP BY strategy, order_result
        ORDER BY strategy, order_result
    """)
    for row in cur.fetchall():
        print(row)

    # 3) Foco EDIFICIO: órdenes enviadas
    section("EDIFICIO: filas con order_id no nulo")
    cur.execute("""
        SELECT id, asset, direction, order_id, order_result, profit,
               decision, decision_reason, duration_sec, ts, created_at, updated_at
        FROM scan_candidates
        WHERE strategy = 'EDIFICIO' AND order_id IS NOT NULL AND order_id <> ''
        ORDER BY id
    """)
    sent = cur.fetchall()
    print(f"total={len(sent)}")
    for row in sent:
        print(row)

    # 4) Diagnóstico específico EDIFICIO
    section("DIAGNÓSTICO EDIFICIO: desglose de order_result")
    cur.execute("""
        SELECT order_result, COUNT(*) AS n
        FROM scan_candidates
        WHERE strategy = 'EDIFICIO' AND order_id IS NOT NULL AND order_id <> ''
        GROUP BY order_result
        ORDER BY COUNT(*) DESC
    """)
    for row in cur.fetchall():
        print(row)

    # 5) Fila representativa: ¿cuántas tienen close_candle_15m/5m/stoch?
    section("EDIFICIO: métricas de cierre para filas pendientes")
    pending = [r for r in sent if r[4] is None]
    print(f"pendientes={len(pending)}")
    if pending:
        c15 = cur.execute("""
            SELECT COUNT(*) FROM scan_candidates
            WHERE strategy='EDIFICIO' AND order_result IS NULL
              AND close_candle_15m IS NOT NULL
        """).fetchone()[0]
        c5 = cur.execute("""
            SELECT COUNT(*) FROM scan_candidates
            WHERE strategy='EDIFICIO' AND order_result IS NULL
              AND close_candle_5m IS NOT NULL
        """).fetchone()[0]
        cs = cur.execute("""
            SELECT COUNT(*) FROM scan_candidates
            WHERE strategy='EDIFICIO' AND order_result IS NULL
              AND close_stoch_m15 IS NOT NULL
        """).fetchone()[0]
        print("close_candle_15m not null:", c15)
        print("close_candle_5m not null:", c5)
        print("close_stoch_m15 not null:", cs)

    # 6) Detectar si hay alguna fila STRAT-F resuelta (si todas son NULL, el resolvedor no ha corrido en absoluto)
    section("CONTROL: STRAT-F ¿tiene alguna fila resuelta hoy?")
    cur.execute("""
        SELECT order_result, COUNT(*) FROM scan_candidates
        WHERE strategy='STRAT-F' AND order_id IS NOT NULL AND order_id <> ''
        GROUP BY order_result ORDER BY COUNT(*) DESC
    """)
    for row in cur.fetchall():
        print(row)

    # 7) Detectar órdenes duplicadas por order_id en EDIFICIO
    section("EDIFICIO: order_id duplicados")
    cur.execute("""
        SELECT order_id, COUNT(*) AS n
        FROM scan_candidates
        WHERE strategy='EDIFICIO' AND order_id IS NOT NULL AND order_id <> ''
        GROUP BY order_id HAVING n > 1 ORDER BY n DESC
    """)
    dups = cur.fetchall()
    print(f"duplicados={len(dups)}")
    for row in dups[:20]:
        print(row)

    # 8) Revisar JSON strategy_details para detectar order_ref=0 en curso de envío
    section("EDIFICIO: inspección de strategy_details para pendientes")
    cur.execute("""
        SELECT id, asset, direction, order_id, strategy_details
        FROM scan_candidates
        WHERE strategy='EDIFICIO' AND order_result IS NULL
        ORDER BY id LIMIT 20
    """)
    for row in cur.fetchall():
        try:
            details = json.loads(row[4]) if row[4] else {}
        except Exception:
            details = {"raw": row[4]}
        print(f"id={row[0]} asset={row[1]} dir={row[2]} order_id={row[3]} details={details}")

    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
