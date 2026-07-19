"""Count resolved trades across all black box DBs."""
import sqlite3
from pathlib import Path

DB_DIR = Path("data/db")
for db_file in sorted(DB_DIR.glob("black_box_strat_*.db")):
    con = sqlite3.connect(db_file)
    total = con.execute("SELECT COUNT(*) FROM scan_candidates WHERE order_result IS NOT NULL").fetchone()[0]
    wins = con.execute("SELECT COUNT(*) FROM scan_candidates WHERE order_result='WIN'").fetchone()[0]
    losses = con.execute("SELECT COUNT(*) FROM scan_candidates WHERE order_result='LOSS'").fetchone()[0]
    con.close()
    if total > 0:
        wr = wins / total * 100 if total > 0 else 0
        print(f"{db_file.name}: {total} trades ({wins}W/{losses}L) WR={wr:.1f}%")
