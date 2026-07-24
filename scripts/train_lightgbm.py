"""LightGBM training pipeline for Feature 18 (lightgbm_scorer).

Reads ALL resolved STRAT-F trades from the black-box DBs
(``data/db/trade_journal-*.db`` and ``data/db/black_box_strat-*.db``),
extracts the 18 ML features via :func:`src.ml_features.extract_features`,
performs a temporal (walk-forward) 80/20 split, trains a LightGBM
classifier (target 1=WIN, 0=LOSS), and persists:

    data/models/lightgbm_v1.pkl      (joblib: {"model":..., "meta":...})
    data/models/lightgbm_meta.json   (feature_importances, metrics, n_trades)

**HARD GUARD:** training only runs when the total number of resolved
STRAT-F trades >= MIN_TRADES (500). Otherwise it prints how many trades
are still missing and exits WITHOUT training. This prevents blind
training on an insufficient dataset.

This script is safe to run anytime — it performs no data collection,
does not start the bot/server, and never overwrites a model once the
guard blocks training.

Usage:
    python scripts/train_lightgbm.py            # uses data/db/* and guard
    python scripts/train_lightgbm.py --force     # ignore guard (NOT recommended)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any

import joblib
import lightgbm as lgb
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# ── Path bootstrap: make src/ importable when run as a script ──────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SRC = os.path.join(_ROOT, "src")
for _p in (_SRC, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ml_features import (  # noqa: E402
    FEATURE_NAMES,
    extract_features,
    extract_from_db_row,
    extract_features_full,
)

# ── Constants ─────────────────────────────────────────────────────────────
MIN_TRADES = 500
MODEL_PATH = os.path.join(_ROOT, "data", "models", "lightgbm_v1.pkl")
META_PATH = os.path.join(_ROOT, "data", "models", "lightgbm_meta.json")
DB_GLOB_CANDIDATES = os.path.join(_ROOT, "data", "db", "trade_journal-*.db")
DB_GLOB_BLACKBOX = os.path.join(_ROOT, "data", "db", "black_box_strat*.db")


# ── DB discovery ──────────────────────────────────────────────────────────
def discover_db_paths() -> list[str]:
    """Return unique, existing DB paths that hold black-box trades.

    Excludes the empty ``data/trade_journal.db`` and de-duplicates the
    corrupt duplicate ``black_box_strat-2026-07-18.db`` (dash variant
    that lacks the expected tables).
    """
    paths: list[str] = []
    seen = set()
    for pattern in (DB_GLOB_CANDIDATES, DB_GLOB_BLACKBOX):
        for p in sorted(glob.glob(pattern)):
            ap = os.path.abspath(p)
            if ap in seen:
                continue
            seen.add(ap)
            paths.append(p)
    return paths


# ── Row loading ───────────────────────────────────────────────────────────
def _to_epoch(value: Any) -> float | None:
    """Best-effort conversion of a timestamp column to a float epoch."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # heuristic: ms vs s
        if value > 1e12:
            return float(value) / 1000.0
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(
                tzinfo=timezone.utc
            ).timestamp()
        except ValueError:
            continue
    # ISO with timezone / nanoseconds — fall back to fromisoformat
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _blackbox_row_to_strategy_json(row: dict) -> dict:
    """Build a ``strategy_json``-compatible dict from a scan_candidates row."""
    sj: dict[str, Any] = {}
    if row.get("direction"):
        sj["direction"] = row["direction"]
    if row.get("payout") is not None:
        sj["payout"] = float(row["payout"])
    if row.get("duration_sec") is not None:
        sj["duration_sec"] = float(row["duration_sec"])

    stoch = row.get("stoch_m15")
    if isinstance(stoch, str):
        try:
            stoch = json.loads(stoch)
        except (json.JSONDecodeError, TypeError):
            stoch = None
    if isinstance(stoch, dict) and stoch:
        sj["stoch_m15"] = stoch

    sd = row.get("strategy_details")
    if isinstance(sd, str):
        try:
            sd = json.loads(sd)
        except (json.JSONDecodeError, TypeError):
            sd = None
    if isinstance(sd, dict) and sd:
        ps: dict[str, Any] = {}
        if sd.get("math_quality") is not None:
            ps["math_quality"] = sd["math_quality"]
        if sd.get("score_breakdown") is not None:
            ps["score_breakdown"] = sd["score_breakdown"]
        if ps:
            sj["pattern_snapshot"] = ps
    return sj


def load_resolved_trades(db_paths: list[str] | None = None) -> list[dict]:
    """Load every resolved STRAT-F trade as ``{features, target, ts}``.

    Sources:
      * ``trade_journal-*.db`` → table ``candidates`` (outcome WIN/LOSS,
        strategy_origin='STRAT-F') with a rich ``strategy_json`` column.
      * ``black_box_strat*.db`` → table ``scan_candidates`` (order_result
        WIN/LOSS, strategy='STRAT-F') with a slimmer ``strategy_details``.

    Rows whose DB does not contain the expected table are skipped.
    """
    if db_paths is None:
        db_paths = discover_db_paths()

    rows: list[dict] = []
    for db in db_paths:
        try:
            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
        except sqlite3.Error:
            continue

        # ── Source 1: trade_journal candidates ──
        try:
            cur.execute(
                """
                SELECT outcome, strategy_origin, strategy_json, spring_margin,
                       direction, payout, scanned_at, ticket_duration_sec,
                       entry_duration_sec
                FROM candidates
                WHERE outcome IN ('WIN','LOSS') AND strategy_origin = 'STRAT-F'
                """
            )
            for r in cur.fetchall():
                r = dict(r)
                # Pass the FULL row so extract_features_full can read raw
                # candles_1m/5m/15m + stoch_m5/m1 + timestamp for OFFLINE
                # OHLC-geometry computation (Entry Intelligence Agent).
                features = extract_features_full(r)
                ts = _to_epoch(r.get("scanned_at"))
                rows.append(
                    {
                        "features": features,
                        "target": 1 if str(r["outcome"]).upper() == "WIN" else 0,
                        "ts": ts,
                        "source": os.path.basename(db),
                    }
                )
        except sqlite3.Error:
            conn.rollback()  # release aborted txn so the next source can run

        # ── Source 2: black_box scan_candidates ──
        try:
            cur.execute(
                """
                SELECT order_result, strategy, strategy_details, stoch_m15,
                       stoch_m5, stoch_m1, candles_1m, candles_5m, candles_15m,
                       direction, payout, duration_sec, ts, asset
                FROM scan_candidates
                WHERE order_result IN ('WIN','LOSS') AND strategy = 'STRAT-F'
                """
            )
            for r in cur.fetchall():
                r = dict(r)
                # Full row → extract_features_full reads raw candles + 3-TF
                # stochastic + context for OFFLINE OHLC-geometry features.
                features = extract_features_full(r)
                ts = _to_epoch(r.get("ts"))
                rows.append(
                    {
                        "features": features,
                        "target": 1 if str(r["order_result"]).upper() == "WIN" else 0,
                        "ts": ts,
                        "source": os.path.basename(db),
                    }
                )
        except sqlite3.Error:
            conn.rollback()  # release aborted txn so the next source can run

        conn.close()

    # Stable sort: by timestamp when known, else keep insertion order.
    rows.sort(key=lambda x: (x["ts"] if x["ts"] is not None else float("inf"),))
    return rows


# ── Fuente preferida (Feature 27): memoria única del Experience Engine ─────
MEMORY_ROOT = os.path.join(_ROOT, "data", "market_memory")


def load_experiences_as_rows(mem_root: str | None = None) -> list[dict]:
    """Lee la memoria única (data/market_memory/) y devuelve rows entrenables.

    Cada experiencia CERRADA (arco con resultado WIN/LOSS) se mapea a un dict
    con las MISMAS claves que ``extract_features_full`` ya consume desde
    ``scan_candidates`` — así NO cambian ml_features ni FEATURE_NAMES (las 28
    features siguen idénticas). Devuelve la misma forma que
    ``load_resolved_trades``: ``{features, target, ts, source}``.
    """
    from pathlib import Path

    try:
        from experience_engine import ExperienceMemory
    except Exception:
        return []

    root = Path(mem_root or MEMORY_ROOT)
    if not root.exists():
        return []

    try:
        experiences = ExperienceMemory(root=root).all_experiences()
    except Exception:
        return []

    rows: list[dict] = []
    for exp in experiences:
        if not exp.is_closed():
            continue
        ctx = exp.contexto_previo or {}
        ev = exp.evento or {}
        res = exp.resultado or {}
        raw = exp.raw or {}
        # Mapear el arco a la forma de fila scan_candidates que
        # extract_features_full ya sabe leer (KISS: sin tocar el extractor).
        row = {
            "candles_1m": raw.get("candles_1m"),
            "candles_5m": raw.get("candles_5m"),
            "candles_15m": raw.get("candles_15m"),
            "stoch_m15": ctx.get("stoch_m15"),
            "stoch_m5": ctx.get("stoch_m5"),
            "stoch_m1": ctx.get("stoch_m1"),
            "direction": ev.get("direccion") or ev.get("direction"),
            "payout": ev.get("payout"),
            "duration_sec": ev.get("duration_sec"),
            "asset": exp.asset,
            "ts": exp.ts,
            "order_result": res.get("decision"),
            "profit": res.get("profit"),
            "entry_price": ev.get("nivel"),
            "exit_price": res.get("exit_price"),
            "loss_reason": res.get("loss_reason"),
            "strategy_details": None,
        }
        features = extract_features_full(row)
        rows.append(
            {
                "features": features,
                "target": 1 if str(res.get("decision")).upper() == "WIN" else 0,
                "ts": float(exp.ts) if exp.ts else None,
                "source": "market_memory",
            }
        )

    rows.sort(key=lambda x: (x["ts"] if x["ts"] is not None else float("inf"),))
    return rows


# ── Training core ───────────────────────────────────────────────────────────
def train_model(X: pd.DataFrame, y: pd.Series, random_state: int = 42) -> dict:
    """Walk-forward (temporal 80/20) LightGBM training.

    Returns a dict with the fitted model and evaluation metrics.
    """
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    model = lgb.LGBMClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        random_state=random_state,
        verbose=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    try:
        y_proba = model.predict_proba(X_test)[:, 1]
        auc = float(roc_auc_score(y_test, y_proba)) if len(set(y_test)) > 1 else None
    except Exception:
        auc = None

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "auc": auc,
    }

    raw_imp = model.feature_importances_
    names = list(X.columns)
    feature_importances = {
        name: float(imp) for name, imp in zip(names, raw_imp)
    }

    return {
        "model": model,
        "metrics": metrics,
        "feature_importances": feature_importances,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "split_idx": split_idx,
        "feature_names": list(names),
    }


def run_training(
    db_paths: list[str] | None = None,
    model_path: str = MODEL_PATH,
    meta_path: str = META_PATH,
    min_trades: int = MIN_TRADES,
    force: bool = False,
    quiet: bool = False,
    mem_root: str | None = None,
) -> dict:
    """Orchestrate the full pipeline WITH the 500-trade guard.

    Fuente de datos (T10/T11 Experience Engine):
      1. PREFERIDA: memoria única (data/market_memory/, Feature 27) — solo
         cuando NO se pasan ``db_paths`` explícitos (uso de producción) o
         cuando se pasa ``mem_root`` explícito.
      2. FALLBACK: DBs legacy (scan_candidates / trade_journal), para no
         romper el entrenamiento actual si la memoria aún no está poblada.

    Returns a dict. If the guard blocks training, the dict has
    ``{"trained": False, "actual": M, "min": min_trades, "missing": N}``
    and nothing is written to disk. If training succeeds, the dict is the
    metadata (with ``trained=True``) and both files are persisted.
    """
    rows: list[dict] = []
    if mem_root is not None or db_paths is None:
        rows = load_experiences_as_rows(mem_root)
        if rows and not quiet:
            print(
                f"[ML] fuente: memoria única (Feature 27) — "
                f"{len(rows)} experiencias cerradas"
            )
    if not rows:
        # Fallback: DBs legacy si la memoria única aún no está poblada.
        rows = load_resolved_trades(db_paths)
    actual = len(rows)

    if actual < min_trades and not force:
        missing = min_trades - actual
        msg = (
            f"Faltan {missing} trades para entrenar "
            f"(actual={actual}, minimo={min_trades})"
        )
        if not quiet:
            print(msg)
        return {
            "trained": False,
            "actual": actual,
            "min": min_trades,
            "missing": missing,
            "message": msg,
        }

    if not quiet:
        print(f"[ML] {actual} trades resueltos — entrenando LightGBM...")

    X = pd.DataFrame([r["features"] for r in rows], columns=FEATURE_NAMES)
    y = pd.Series([r["target"] for r in rows], name="target")

    result = train_model(X, y)

    # Persist model + meta (structure compatible with MLScorer.load)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    meta = {
        "trained": True,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_trades": actual,
        "n_train": result["n_train"],
        "n_test": result["n_test"],
        "split_idx": result["split_idx"],
        "min_trades_required": min_trades,
        "feature_names": result["feature_names"],
        "feature_importances": result["feature_importances"],
        "metrics": result["metrics"],
        "lightgbm_version": lgb.__version__,
    }
    joblib.dump({"model": result["model"], "meta": meta}, model_path)
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    if not quiet:
        m = meta["metrics"]
        print(
            f"[ML] modelo guardado en {model_path}\n"
            f"[ML] accuracy={m['accuracy']:.3f} f1={m['f1']:.3f} "
            f"auc={m['auc'] if m['auc'] is not None else 'n/a'}"
        )
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Train LightGBM STRAT-F scorer.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the 500-trade guard (NOT recommended).",
    )
    parser.add_argument(
        "--min-trades",
        type=int,
        default=MIN_TRADES,
        help="Override the minimum resolved-trade guard (default 500).",
    )
    args = parser.parse_args()

    result = run_training(
        db_paths=None,
        model_path=MODEL_PATH,
        meta_path=META_PATH,
        min_trades=args.min_trades,
        force=args.force,
    )

    # Guard blocked training → exit cleanly, no model written.
    if not result.get("trained"):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
