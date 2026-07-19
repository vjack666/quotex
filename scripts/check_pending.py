"""Check how many ACCEPTED candidates exist vs resolved trades."""
import sys
import io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import sqlite3
import json
from pathlib import Path

for db_name in ["black_box_strat_2026-07-14.db", "black_box_strat_2026-07-15.db"]:
    db_path = Path("data/db") / db_name
    if not db_path.exists():
        continue

    print(f"\n{'=' * 60}")
    print(f"  {db_name}")
    print("=" * 60)

    con = sqlite3.connect(str(db_path))

    # Decision distribution
    print("\n  DECISION distribution:")
    for row in con.execute("""
        SELECT decision, COUNT(*) as cnt
        FROM scan_candidates WHERE strategy='STRAT-F'
        GROUP BY decision
    """).fetchall():
        print(f"    {row[0]:25s}: {row[1]}")

    # ACCEPTED vs resolved
    accepted = con.execute(
        "SELECT COUNT(*) FROM scan_candidates WHERE strategy='STRAT-F' AND decision='ACCEPTED'"
    ).fetchone()[0]
    resolved = con.execute(
        "SELECT COUNT(*) FROM scan_candidates WHERE strategy='STRAT-F' AND order_result IN ('WIN','LOSS')"
    ).fetchone()[0]
    pending_accepted = con.execute(
        "SELECT COUNT(*) FROM scan_candidates WHERE strategy='STRAT-F' AND decision='ACCEPTED' AND order_result IS NULL"
    ).fetchone()[0]

    print(f"\n  ACCEPTED: {accepted}")
    print(f"  Resolved (WIN/LOSS): {resolved}")
    print(f"  ACCEPTED but PENDING: {pending_accepted}")

    # Check order_id on accepted candidates
    with_oid = con.execute(
        "SELECT COUNT(*) FROM scan_candidates WHERE strategy='STRAT-F' AND decision='ACCEPTED' AND order_id IS NOT NULL AND order_id != ''"
    ).fetchone()[0]
    without_oid = con.execute(
        "SELECT COUNT(*) FROM scan_candidates WHERE strategy='STRAT-F' AND decision='ACCEPTED' AND (order_id IS NULL OR order_id = '')"
    ).fetchone()[0]

    print(f"\n  ACCEPTED with order_id: {with_oid}")
    print(f"  ACCEPTED without order_id: {without_oid}")

    # Sample of accepted pending candidates
    print(f"\n  Sample ACCEPTED PENDING (first 3):")
    for row in con.execute("""
        SELECT id, asset, direction, score, order_id, order_result, decision, stoch_contradicts
        FROM scan_candidates
        WHERE strategy='STRAT-F' AND decision='ACCEPTED' AND order_result IS NULL
        LIMIT 3
    """).fetchall():
        print(f"    id={row[0]} asset={row[1]} dir={row[2]} score={row[3]} oid={row[4]} result={row[5]} decision={row[6]} contradicts={row[7]}")

    # Sample of resolved candidates
    print(f"\n  Sample RESOLVED (first 3):")
    for row in con.execute("""
        SELECT id, asset, direction, score, order_id, order_result, profit, stoch_contradicts
        FROM scan_candidates
        WHERE strategy='STRAT-F' AND order_result IN ('WIN','LOSS')
        LIMIT 3
    """).fetchall():
        print(f"    id={row[0]} asset={row[1]} dir={row[2]} score={row[3]} oid={row[4]} result={row[5]} profit={row[6]} contradicts={row[7]}")

    con.close()
