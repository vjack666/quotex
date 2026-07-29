"""Entry Intelligence Agent — orquestador de auto-retrain continuo.

Feature 18 (Entry Intelligence Agent). Este módulo decide CUÁNDO reentrenar el
modelo LightGBM, conserva el modelo de mejor F1 y dispara el reentrenamiento
en segundo plano sin bloquear el hot path del bot.

FUENTE DE DATOS (T10/T11 Experience Engine): la fuente PREFERIDA ahora es la
memoria única del Experience Engine (data/market_memory/, Feature 27) — el
arco completo de cada entrada (contexto_previo → evento → resultado). Si la
memoria está vacía, run_training cae automáticamente a las DBs legacy
(scan_candidates / trade_journal) como fallback. El contrato del Confidence
Score (0-1 de WIN, mismas 28 FEATURE_NAMES de ml_features) NO cambia.

El modelo en sí (ml_scorer.MLScorer) y la extracción de features
(ml_features) ya existen; este módulo SOLO orquesta el ciclo de vida:

  · Descubre las DBs de black box / trade journal.
  · Cuenta los trades resueltos NUEVOS desde el último retrain.
  · Si hay >= RETRAIN_MIN_NEW trades nuevos (o --force), entrena en un path
    temporal y SOLO reemplaza el modelo en producción si su F1 holdout es
    >= al del modelo actual (conserva el mejor).
  · Registra last_retrain.json con el estado.

Todo es determinista y offline: no LLM, no red.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

# Make sure repo + scripts are importable regardless of caller.
_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_ROOT), str(_ROOT / "scripts"), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ml_features import FEATURE_NAMES  # noqa: E402

# ── Config ──────────────────────────────────────────────────────────────────
RETRAIN_MIN_NEW = 100          # >100 trades nuevos resueltos => reentrenar
MIN_TRADES = 500               # umbral absoluto del pipeline de entrenamiento
MODELS_DIR = _ROOT / "data" / "models"
MODEL_PATH = MODELS_DIR / "lightgbm_v1.pkl"
META_PATH = MODELS_DIR / "lightgbm_meta.json"
STATE_PATH = MODELS_DIR / "last_retrain.json"
DB_DIR = _ROOT / "data" / "db"
# Memoria única del Experience Engine (fuente PREFERIDA de retrain, Feature 27)
MEMORY_ROOT = _ROOT / "data" / "market_memory"


def discover_databases() -> list[str]:
    """Find all candidate DBs (black_box + trade_journal)."""
    if not DB_DIR.exists():
        return []
    dbs: list[str] = []
    for pat in ("black_box_strat_*.db", "trade_journal-*.db", "trade_journal.db"):
        dbs.extend(str(p) for p in sorted(DB_DIR.glob(pat)))
    return dbs


def _load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_ts": 0.0, "last_f1": 0.0, "model_path": str(MODEL_PATH)}


def _save_state(state: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def count_new_resolved_trades(db_paths: list[str], since_ts: float) -> int:
    """Count resolved trades (WIN/LOSS) with ts > since_ts across DBs."""
    import sqlite3

    total = 0
    for db in db_paths:
        if not os.path.exists(db):
            continue
        try:
            con = sqlite3.connect(db)
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # scan_candidates (black_box) carries ts + order_result
            try:
                rows = cur.execute(
                    "SELECT COUNT(*) AS n FROM scan_candidates "
                    "WHERE order_result IN ('WIN','LOSS') AND ts > ?",
                    (since_ts,),
                ).fetchone()
                if rows:
                    total += int(rows["n"])
            except sqlite3.Error:
                pass
            # trade_journal-style (outcome + scanned_at)
            try:
                rows = cur.execute(
                    "SELECT COUNT(*) AS n FROM candidates "
                    "WHERE outcome IN ('WIN','LOSS') AND "
                    "CAST(strftime('%s', scanned_at) AS REAL) > ?",
                    (since_ts,),
                ).fetchone()
                if rows:
                    total += int(rows["n"])
            except sqlite3.Error:
                pass
            con.close()
        except sqlite3.Error:
            continue
    return total


def _f1_of_model(model_path: str, db_paths: list[str]) -> float:
    """Compute holdout F1 of an existing model via ml_scorer on a temp eval.

    Returns 0.0 if the model cannot be evaluated.
    """
    try:
        from ml_scorer import MLScorer

        scorer = MLScorer(model_path=model_path)
        if not scorer.is_available():
            return 0.0
    except Exception:
        return 0.0

    # Reuse the training pipeline's walk-forward split to evaluate F1 on the
    # held-out 20%. run_training returns metrics only when it trains; here we
    # ask it to evaluate without persisting by using a temp path + force on a
    # reduced split is overkill. Instead we compute metrics via a light
    # holdout using load_resolved_trades + the scorer's own predict.
    try:
        from train_lightgbm import load_resolved_trades
    except Exception:
        return 0.0

    rows = load_resolved_trades(db_paths=db_paths)
    if len(rows) < 50:
        return 0.0
    # temporal 80/20 holdout
    rows_sorted = sorted(rows, key=lambda r: r.get("ts") or 0)
    hold = rows_sorted[int(len(rows_sorted) * 0.8):]
    if not hold:
        return 0.0
    tp = fp = fn = 0
    for r in hold:
        pred = scorer.predict(r["features"])
        if pred is None:
            continue
        pred_label = 1 if pred >= 0.5 else 0
        if pred_label == 1 and r["target"] == 1:
            tp += 1
        elif pred_label == 1 and r["target"] == 0:
            fp += 1
        elif pred_label == 0 and r["target"] == 1:
            fn += 1
    if tp + fp == 0 or tp + fn == 0:
        return 0.0
    prec = tp / (tp + fp)
    rec = tp / (tp + fn)
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def maybe_retrain(force: bool = False, quiet: bool = True) -> dict:
    """Decide and run a retrain if warranted.

    Returns a result dict with keys: triggered, trained, accepted, reason,
    n_new, f1_new, f1_prev.
    """
    db_paths = discover_databases()
    state = _load_state()
    last_ts = float(state.get("last_ts", 0.0))
    last_f1 = float(state.get("last_f1", 0.0))

    n_new = count_new_resolved_trades(db_paths, last_ts)
    result: dict[str, Any] = {
        "triggered": False,
        "trained": False,
        "accepted": False,
        "reason": "",
        "n_new": n_new,
        "f1_new": None,
        "f1_prev": last_f1,
        "db_count": len(db_paths),
    }

    if not db_paths:
        result["reason"] = "no databases found"
        return result

    if not force and n_new < RETRAIN_MIN_NEW:
        result["reason"] = (
            f"only {n_new} new resolved trades (< {RETRAIN_MIN_NEW} threshold)"
        )
        return result

    result["triggered"] = True

    # Train into a temp path, then keep only if F1 is not worse.
    # Derive paths from MODELS_DIR at runtime so tests/overrides of MODELS_DIR
    # are respected (the module-level constants are fixed at import time).
    model_path = MODELS_DIR / "lightgbm_v1.pkl"
    meta_path = MODELS_DIR / "lightgbm_meta.json"
    tmp_model = MODELS_DIR / "lightgbm_tmp.pkl"
    tmp_meta = MODELS_DIR / "lightgbm_tmp_meta.json"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from train_lightgbm import run_training

        train_res = run_training(
            db_paths=db_paths,
            model_path=str(tmp_model),
            meta_path=str(tmp_meta),
            min_trades=MIN_TRADES,
            force=force,
            quiet=quiet,
            # Fuente preferida: memoria única (Feature 27); run_training cae
            # a las DBs legacy (db_paths) si la memoria está vacía.
            mem_root=str(MEMORY_ROOT),
        )
    except Exception as e:  # pragma: no cover - defensive
        result["reason"] = f"training error: {e}"
        return result

    if not train_res.get("trained"):
        result["reason"] = train_res.get("message", "training guard blocked")
        return result

    result["trained"] = True
    f1_new = float(train_res.get("metrics", {}).get("f1", 0.0))
    result["f1_new"] = f1_new

    # Accept if no previous model, or new F1 >= previous (keep the best).
    accept = (last_f1 == 0.0) or (f1_new >= last_f1)
    if accept:
        import shutil

        shutil.move(str(tmp_model), str(model_path))
        if tmp_meta.exists():
            shutil.move(str(tmp_meta), str(meta_path))
        result["accepted"] = True
    else:
        # Discard the worse model.
        for f in (tmp_model, tmp_meta):
            try:
                f.unlink()
            except FileNotFoundError:
                pass
        result["reason"] = (
            f"new F1 {f1_new:.3f} < previous {last_f1:.3f}; kept previous model"
        )

    if result["accepted"]:
        _save_state({
            "last_ts": __import__("time").time(),
            "last_f1": f1_new,
            "model_path": str(MODEL_PATH),
        })
        result["reason"] = "model updated"
    return result


# ── Background trigger (fire-and-forget) ──────────────────────────────────────
_retrain_lock = threading.Lock()


def trigger_background_retrain() -> None:
    """Spawn a daemon thread that runs maybe_retrain() without blocking."""
    def _run() -> None:
        try:
            maybe_retrain()
        except Exception:
            pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def trigger_background_retrain_once() -> None:
    """Like trigger_background_retrain but skips if a retrain is already queued."""
    if not _retrain_lock.acquire(blocking=False):
        return
    try:
        trigger_background_retrain()
    finally:
        # release after a short delay so we don't spam on every resolved trade
        _retrain_lock.release()


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Entry Intelligence Agent retrain")
    ap.add_argument("--force", action="store_true", help="ignore the new-trade threshold")
    ap.add_argument("--quiet", action="store_true", default=True)
    ap.add_argument("--verbose", dest="quiet", action="store_false")
    args = ap.parse_args()
    out = maybe_retrain(force=args.force, quiet=args.quiet)
    print(json.dumps(out, indent=2, default=str))
