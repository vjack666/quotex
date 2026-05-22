#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple


def latest_journal_db(db_dir: Path) -> Path:
    dbs = sorted(db_dir.glob("trade_journal-*.db"))
    if not dbs:
        raise FileNotFoundError(f"No trade_journal DB files found in {db_dir}")
    return dbs[-1]


def fetch_rows(conn: sqlite3.Connection, sql: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
    cur = conn.execute(sql, params)
    return cur.fetchall()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def safe_wr(wins: int, losses: int) -> float:
    total = int(wins) + int(losses)
    return round((100.0 * float(wins) / float(total)), 4) if total > 0 else 0.0


def outcome_counts(rows: List[sqlite3.Row]) -> Dict[str, Any]:
    wins = int(sum(int(r["wins"] or 0) for r in rows))
    losses = int(sum(int(r["losses"] or 0) for r in rows))
    total = wins + losses
    return {
        "wins": wins,
        "losses": losses,
        "total": total,
        "winrate_pct": safe_wr(wins, losses),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Performance report from trade_journal DB")
    parser.add_argument("--db", default="", help="Path to trade_journal DB (default: latest in data/db)")
    parser.add_argument("--db-dir", default="data/db", help="DB directory used when --db is omitted")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days")
    parser.add_argument("--top", type=int, default=5, help="Top/bottom assets to display")
    parser.add_argument("--json-out", default="", help="Optional output JSON path")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else latest_journal_db(Path(args.db_dir))
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    report: Dict[str, Any] = {
        "db_path": str(db_path),
        "lookback_days": int(args.days),
        "summary": {},
        "shadow_coverage": {},
        "by_category": [],
        "by_htf_alignment": [],
        "by_pattern": [],
        "by_score_range": [],
        "by_strategy_origin": [],
        "by_veto_count": [],
        "by_hour": [],
        "assets_top": [],
        "assets_bottom": [],
        "notes": [],
    }

    outcomes_sql = """
    SELECT
        SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) AS losses,
        SUM(CASE WHEN outcome='WIN' THEN profit ELSE 0 END) AS profit_wins,
        SUM(CASE WHEN outcome='LOSS' THEN ABS(profit) ELSE 0 END) AS loss_abs,
        AVG(CASE WHEN outcome IN ('WIN','LOSS') THEN profit END) AS expectancy
    FROM candidates
    WHERE decision='ACCEPTED'
      AND outcome IN ('WIN','LOSS')
      AND scanned_at >= datetime('now', ?)
    """
    outcome_row = fetch_rows(conn, outcomes_sql, (f"-{int(args.days)} days",))
    base = row_to_dict(outcome_row[0]) if outcome_row else {}
    wins = int(base.get("wins") or 0)
    losses = int(base.get("losses") or 0)
    profit_wins = float(base.get("profit_wins") or 0.0)
    loss_abs = float(base.get("loss_abs") or 0.0)
    expectancy = float(base.get("expectancy") or 0.0)
    pf = round((profit_wins / loss_abs), 6) if loss_abs > 0 else None
    report["summary"] = {
        "wins": wins,
        "losses": losses,
        "total": wins + losses,
        "winrate_pct": safe_wr(wins, losses),
        "profit_factor": pf,
        "expectancy": round(expectancy, 6),
    }

    coverage_sql = """
    SELECT
        COUNT(*) AS shadow_rows_total,
        SUM(CASE WHEN candidate_id IS NOT NULL THEN 1 ELSE 0 END) AS with_candidate,
        SUM(CASE WHEN trade_outcome != 'NO_TRADE' THEN 1 ELSE 0 END) AS with_any_outcome,
        SUM(CASE WHEN trade_outcome IN ('WIN','LOSS') THEN 1 ELSE 0 END) AS with_resolved_outcome
    FROM shadow_decision_audit
    WHERE created_at >= datetime('now', ?)
    """
    cov_row = fetch_rows(conn, coverage_sql, (f"-{int(args.days)} days",))
    cov = row_to_dict(cov_row[0]) if cov_row else {}
    shadow_rows_total = int(cov.get("shadow_rows_total") or 0)
    with_candidate = int(cov.get("with_candidate") or 0)
    with_any_outcome = int(cov.get("with_any_outcome") or 0)
    with_resolved_outcome = int(cov.get("with_resolved_outcome") or 0)
    linkage_pct_any = round((100.0 * float(with_any_outcome) / float(with_candidate)), 4) if with_candidate > 0 else 0.0
    linkage_pct_resolved = round((100.0 * float(with_resolved_outcome) / float(with_candidate)), 4) if with_candidate > 0 else 0.0
    report["shadow_coverage"] = {
        "shadow_rows_total": shadow_rows_total,
        "with_candidate": with_candidate,
        "with_any_outcome": with_any_outcome,
        "with_resolved_outcome": with_resolved_outcome,
        "linkage_pct_any": linkage_pct_any,
        "linkage_pct_resolved": linkage_pct_resolved,
    }

    shadow_window = f"-{int(args.days)} days"
    grouped_sql = """
    WITH latest_shadow AS (
        SELECT s.*
        FROM shadow_decision_audit s
        INNER JOIN (
            SELECT candidate_id, MAX(id) AS max_id
            FROM shadow_decision_audit
            WHERE candidate_id IS NOT NULL
            GROUP BY candidate_id
        ) x ON x.max_id = s.id
        WHERE s.trade_outcome IN ('WIN','LOSS')
          AND s.created_at >= datetime('now', ?)
    )
    SELECT
        {group_expr} AS bucket,
        SUM(CASE WHEN trade_outcome='WIN' THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN trade_outcome='LOSS' THEN 1 ELSE 0 END) AS losses
    FROM latest_shadow
    GROUP BY bucket
    HAVING bucket IS NOT NULL
    ORDER BY (wins + losses) DESC, bucket
    """

    def run_group(group_expr: str) -> List[Dict[str, Any]]:
        rows = fetch_rows(conn, grouped_sql.format(group_expr=group_expr), (shadow_window,))
        out: List[Dict[str, Any]] = []
        for r in rows:
            wins_i = int(r["wins"] or 0)
            losses_i = int(r["losses"] or 0)
            out.append(
                {
                    "bucket": r["bucket"],
                    "wins": wins_i,
                    "losses": losses_i,
                    "total": wins_i + losses_i,
                    "winrate_pct": safe_wr(wins_i, losses_i),
                }
            )
        return out

    report["by_category"] = run_group("new_category")
    report["by_htf_alignment"] = run_group("CASE WHEN new_htf_aligned=1 THEN 'aligned' WHEN new_htf_aligned=0 THEN 'contra_or_flat' ELSE 'unknown' END")
    report["by_pattern"] = run_group("COALESCE(NULLIF(TRIM(pattern_name),''),'none')")
    report["by_score_range"] = run_group(
        "CASE "
        "WHEN score_original IS NULL THEN 'unknown' "
        "WHEN score_original < 70 THEN '<70' "
        "WHEN score_original < 73 THEN '70-72.99' "
        "WHEN score_original < 80 THEN '73-79.99' "
        "ELSE '80+' END"
    )
    report["by_strategy_origin"] = run_group("COALESCE(NULLIF(TRIM(strategy_origin),''), 'UNKNOWN')")
    report["by_veto_count"] = run_group(
        "CASE "
        "WHEN new_veto_count IS NULL THEN 'unknown' "
        "WHEN new_veto_count >= 5 THEN '5+' "
        "ELSE CAST(new_veto_count AS TEXT) END"
    )

    report["by_hour"] = run_group("printf('%02d', CAST(strftime('%H', created_at) AS INTEGER))")

    assets_sql = """
    WITH latest_shadow AS (
        SELECT s.*
        FROM shadow_decision_audit s
        INNER JOIN (
            SELECT candidate_id, MAX(id) AS max_id
            FROM shadow_decision_audit
            WHERE candidate_id IS NOT NULL
            GROUP BY candidate_id
        ) x ON x.max_id = s.id
        WHERE s.trade_outcome IN ('WIN','LOSS')
          AND s.created_at >= datetime('now', ?)
    ), by_asset AS (
        SELECT
            asset,
            SUM(CASE WHEN trade_outcome='WIN' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN trade_outcome='LOSS' THEN 1 ELSE 0 END) AS losses
        FROM latest_shadow
        GROUP BY asset
        HAVING (wins + losses) >= 3
    )
    SELECT asset, wins, losses, (wins + losses) AS total,
           ROUND((100.0 * wins) / (wins + losses), 4) AS winrate_pct
    FROM by_asset
    ORDER BY winrate_pct DESC, total DESC
    """
    asset_rows = fetch_rows(conn, assets_sql, (shadow_window,))
    report["assets_top"] = [row_to_dict(r) for r in asset_rows[: int(args.top)]]
    report["assets_bottom"] = [row_to_dict(r) for r in list(asset_rows[-int(args.top):])[::-1]]

    if report["summary"]["total"] == 0:
        report["notes"].append("No WIN/LOSS rows in candidates for selected window")
    if not report["by_category"]:
        report["notes"].append("No WIN/LOSS rows in shadow_decision_audit for selected window")
    if report["shadow_coverage"].get("with_candidate", 0) > 0 and report["shadow_coverage"].get("with_resolved_outcome", 0) == 0:
        report["notes"].append("Shadow rows existen pero no tienen outcomes resueltos WIN/LOSS (linkage resolved 0%)")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
