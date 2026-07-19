"""Deep dive into the largest black box DBs for STRAT-F analysis."""
import sys
import io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import sqlite3
import json
from pathlib import Path

for db_name in ["black_box_strat_2026-07-13.db", "black_box_strat_2026-07-14.db", "black_box_strat_2026-07-15.db"]:
    db_path = Path("data/db") / db_name
    if not db_path.exists():
        continue

    print(f"\n{'=' * 70}")
    print(f"  DEEP DIVE: {db_name}")
    print("=" * 70)

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row

    # All STRAT-F rows (including pending)
    total_all = con.execute(
        "SELECT COUNT(*) FROM scan_candidates WHERE strategy='STRAT-F'"
    ).fetchone()[0]
    total_resolved = con.execute(
        "SELECT COUNT(*) FROM scan_candidates WHERE strategy='STRAT-F' AND order_result IN ('WIN','LOSS')"
    ).fetchone()[0]
    total_pending = con.execute(
        "SELECT COUNT(*) FROM scan_candidates WHERE strategy='STRAT-F' AND order_result IS NULL"
    ).fetchone()[0]

    print(f"\n  Total STRAT-F candidates: {total_all}")
    print(f"    Resolved (WIN/LOSS):    {total_resolved}")
    print(f"    Pending:                {total_pending}")

    if total_resolved == 0:
        con.close()
        continue

    # Win rate by estado
    print(f"\n  WIN RATE BY ESTADO:")
    for row in con.execute("""
        SELECT
            json_extract(stoch_m15, '$.estado') as estado,
            COUNT(*) as total,
            SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
        FROM scan_candidates
        WHERE strategy='STRAT-F' AND order_result IN ('WIN','LOSS')
        GROUP BY estado
    """).fetchall():
        print(f"    {row['estado']:15s}: {row['wins']}/{row['total']} = {row['win_rate']}%")

    # Win rate by cruce
    print(f"\n  WIN RATE BY CRUCE:")
    for row in con.execute("""
        SELECT
            json_extract(stoch_m15, '$.cruce') as cruce,
            COUNT(*) as total,
            SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
        FROM scan_candidates
        WHERE strategy='STRAT-F' AND order_result IN ('WIN','LOSS')
        GROUP BY cruce
    """).fetchall():
        print(f"    {str(row['cruce']):15s}: {row['wins']}/{row['total']} = {row['win_rate']}%")

    # Win rate by contradicts
    print(f"\n  WIN RATE BY CONTRADICTS:")
    for row in con.execute("""
        SELECT
            stoch_contradicts,
            COUNT(*) as total,
            SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
        FROM scan_candidates
        WHERE strategy='STRAT-F' AND order_result IN ('WIN','LOSS')
        GROUP BY stoch_contradicts
    """).fetchall():
        print(f"    contradicts={row['stoch_contradicts']}: {row['wins']}/{row['total']} = {row['win_rate']}%")

    # Win rate by direction + estado combo
    print(f"\n  WIN RATE BY DIRECTION + ESTADO:")
    for row in con.execute("""
        SELECT
            direction,
            json_extract(stoch_m15, '$.estado') as estado,
            COUNT(*) as total,
            SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
        FROM scan_candidates
        WHERE strategy='STRAT-F' AND order_result IN ('WIN','LOSS')
        GROUP BY direction, estado
        ORDER BY total DESC
    """).fetchall():
        print(f"    {row['direction']:5s} + {str(row['estado']):15s}: {row['wins']}/{row['total']} = {row['win_rate']}%")

    # Win rate by divergencia
    print(f"\n  WIN RATE BY DIVERGENCIA:")
    for row in con.execute("""
        SELECT
            json_extract(stoch_m15, '$.divergencia') as divergencia,
            COUNT(*) as total,
            SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
        FROM scan_candidates
        WHERE strategy='STRAT-F' AND order_result IN ('WIN','LOSS')
        GROUP BY divergencia
    """).fetchall():
        print(f"    {str(row['divergencia']):15s}: {row['wins']}/{row['total']} = {row['win_rate']}%")

    # Sample of stoch_m15 JSON to see full structure
    print(f"\n  SAMPLE stoch_m15 JSON (first 3):")
    for row in con.execute("""
        SELECT stoch_m15 FROM scan_candidates
        WHERE strategy='STRAT-F' AND stoch_m15 IS NOT NULL
        LIMIT 3
    """).fetchall():
        stoch = json.loads(row["stoch_m15"]) if isinstance(row["stoch_m15"], str) else row["stoch_m15"]
        print(f"    {json.dumps(stoch, indent=6)}")

    # Candle count distribution
    print(f"\n  CANDLES_15m COUNT DISTRIBUTION:")
    candle_counts = []
    for row in con.execute("""
        SELECT candles_15m FROM scan_candidates
        WHERE strategy='STRAT-F' AND candles_15m IS NOT NULL
    """).fetchall():
        try:
            c = json.loads(row["candles_15m"]) if isinstance(row["candles_15m"], str) else row["candles_15m"]
            if isinstance(c, list):
                candle_counts.append(len(c))
        except Exception:
            pass

    if candle_counts:
        print(f"    Min: {min(candle_counts)}, Max: {max(candle_counts)}, Avg: {sum(candle_counts)/len(candle_counts):.1f}")
        # Buckets
        buckets = {"<10": 0, "10-14": 0, "15-19": 0, "20-29": 0, "30+": 0}
        for c in candle_counts:
            if c < 10: buckets["<10"] += 1
            elif c < 15: buckets["10-14"] += 1
            elif c < 20: buckets["15-19"] += 1
            elif c < 30: buckets["20-29"] += 1
            else: buckets["30+"] += 1
        for bucket, count in buckets.items():
            print(f"    {bucket:8s}: {count}")

    con.close()
