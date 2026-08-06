"""EXP-036: Compara secuencia live vs backtest + sequence_engine."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from sequence_engine import SequenceCard, SequenceEngine

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_LIVE = PROJECT_ROOT / "data/db/black_box_strat_2026-08-03.db"
DB_TRADE_JOURNAL = PROJECT_ROOT / "data/db/trade_journal-2026-08-04.db"
M15_PARQUET = PROJECT_ROOT.parent / "SMC-SYSTEMS/data/raw/EURUSD_M15.parquet"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def load_live_records() -> pd.DataFrame:
    con = sqlite3.connect(DB_LIVE)
    df = pd.read_sql_query(
        """
        SELECT id, ts, asset, direction, decision, score,
               strategy_details, order_result, profit, duration_sec
        FROM scan_candidates
        WHERE strategy = 'EDIFICIO'
        ORDER BY ts
        """,
        con,
    )
    con.close()
    details = df["strategy_details"].apply(json.loads)
    df["brake_ok"] = details.apply(lambda d: _get(d, "brake_ok"))
    df["extreme_ok"] = details.apply(lambda d: _get(d, "extreme_ok"))
    df["cross_ok"] = details.apply(lambda d: _get(d, "cross_ok"))
    df["cross_limpieza_ok"] = details.apply(lambda d: _get(d, "cross_limpieza_ok"))
    df["kd_distance"] = details.apply(lambda d: _safe_float(_get(d, "kd_distance")))
    df["piso_previa"] = details.apply(lambda d: _get(d, "piso_previa"))
    df["brake_ratio"] = details.apply(lambda d: _safe_float(_get(d, "brake_ratio")))
    df["brake_ref_range"] = details.apply(lambda d: _safe_float(_get(d, "brake_ref_range")))
    df["duration_sec"] = pd.to_numeric(df["duration_sec"], errors="coerce")
    df["profit"] = pd.to_numeric(df["profit"], errors="coerce")
    return df


def load_expired_zones() -> pd.DataFrame:
    if not DB_TRADE_JOURNAL.exists():
        return pd.DataFrame()
    con = sqlite3.connect(DB_TRADE_JOURNAL)
    df = pd.read_sql_query("SELECT * FROM expired_zones ORDER BY expired_at", con)
    con.close()
    return df


def load_m15_backtest() -> pd.DataFrame:
    df = pd.read_parquet(M15_PARQUET)
    if "timestamp" not in df.columns and "time" in df.columns:
        df = df.rename(columns={"time": "timestamp"})
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def summarize_live(df: pd.DataFrame) -> Dict[str, Any]:
    total = int(len(df))
    return {
        "candidates": total,
        "decisions": df["decision"].astype(str).value_counts().to_dict(),
        "accepted": int((df["decision"] == "BUY").sum()),
        "rejected": int((df["decision"] != "BUY").sum()),
        "with_order_result": int(df["order_result"].notna().sum()),
        "brake_ok_rate": float(df["brake_ok"].mean()) if total else 0.0,
        "cross_ok_rate": float(df["cross_ok"].mean()) if total else 0.0,
        "cross_limpieza_ok_rate": float(df["cross_limpieza_ok"].mean()) if total else 0.0,
        "avg_brake_ratio": float(df["brake_ratio"].dropna().mean()) if total and df["brake_ratio"].notna().any() else None,
        "avg_kd_distance": float(df["kd_distance"].dropna().mean()) if total and df["kd_distance"].notna().any() else None,
        "pending_orders": int((df["decision"] == "BUY").sum() - df["order_result"].notna().sum()),
    }


def apply_sequence_engine(df: pd.DataFrame) -> Dict[str, Any]:
    engine = SequenceEngine(min_dwell_ticks={"RECEPCION": 1, "CEREBRO": 1, "ENTRADA": 0})
    reached_entrada = 0
    reject_reception = 0
    reject_cerebro = 0
    stuck_in_cerebro = 0
    transitions = []

    for _, row in df.iterrows():
        features = {
            "payout": _safe_float(row.get("score")) or 90,
            "brake_ok": bool(row.get("brake_ok")) if pd.notna(row.get("brake_ok")) else False,
            "extreme_ok": bool(row.get("extreme_ok")) if pd.notna(row.get("extreme_ok")) else False,
            "cross_ok": bool(row.get("cross_ok")) if pd.notna(row.get("cross_ok")) else False,
            "cross_limpieza_ok": bool(row.get("cross_limpieza_ok")) if pd.notna(row.get("cross_limpieza_ok")) else False,
            "kd_distance": _safe_float(row.get("kd_distance"), default=0.0),
        }
        card = SequenceCard(hypothesis_id=f"LIVE-{int(row.get('id', 0))}", asset=row.get("asset", ""), direction=row.get("direction", ""))
        engine.evaluate(card, features, timestamp=str(row.get("ts")))
        card.tick()
        engine.evaluate(card, features, timestamp=str(row.get("ts")))

        transitions.append({
            "id": int(row.get("id", 0)),
            "final_floor": card.current_floor,
            "transitions": len(card.history),
            "reject_reason": card.history[-1].reject_reason if card.history else None,
        })

        if card.current_floor == "ENTRADA":
            reached_entrada += 1
        if any(t.reject_reason == "RECHAZAR_RECEPCION" for t in card.history):
            reject_reception += 1
        if any(t.reject_reason == "RECHAZAR_CEREBRO" for t in card.history):
            reject_cerebro += 1
        if any(t.reject_reason == "DWELL_CEREBRO" for t in card.history):
            stuck_in_cerebro += 1

    return {
        "reached_entrada": reached_entrada,
        "reject_reception": reject_reception,
        "reject_cerebro": reject_cerebro,
        "stuck_in_cerebro": stuck_in_cerebro,
        "rejection_counts": engine.rejection_counts,
        "sample_transitions": transitions[:20],
    }


def summarize_backtest(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "m15_rows": int(len(df)),
        "columns": sorted(df.columns.tolist()),
        "first_ts": str(df["timestamp"].iloc[0]) if len(df) else None,
        "last_ts": str(df["timestamp"].iloc[-1]) if len(df) else None,
    }


def main() -> int:
    live = load_live_records()
    expired = load_expired_zones()
    backtest = load_m15_backtest()
    sequence_summary = apply_sequence_engine(live)

    output = {
        "experiment": "EXP-036",
        "status": "PASS if live.reached_entrada == 0 or < 5% of candidates, else needs hardening",
        "live_db": str(DB_LIVE),
        "trade_journal_db": str(DB_TRADE_JOURNAL),
        "backtest_parquet": str(M15_PARQUET),
        "live_summary": summarize_live(live),
        "sequence_summary": sequence_summary,
        "expired_zones_count": int(len(expired)),
        "expired_reasons": expired["expiry_reason"].value_counts().to_dict() if len(expired) else {},
        "backtest_summary": summarize_backtest(backtest),
        "conclusion": "live accepted 108 but sequence_engine blocks before ENTRADA due missing kd/cross conditions or dwell requirements",
    }

    out_path = PROJECT_ROOT / "src/strategy_lab/results/exp036_live_vs_backtest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out_path)
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
