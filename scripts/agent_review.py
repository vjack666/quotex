"""Agente OFFLINE de aprendizaje de posiciones buenas/malas (STRAT-F).

Lee todos los trades STRAT-F resueltos (WIN/LOSS) de los DBs
(``data/db/trade_journal-*.db`` y ``data/db/black_box_strat*.db``),
APRENDE patrones de éxito/fracaso de forma determinista, y:

  1. Calcula estadística descriptiva (winrate global, por direction,
     por stoch_zone, por bucket de payout).
  2. Rankea las features que más DISCRIMINAN entre WIN y LOSS
     (separación de medias normalizada).
  3. Detecta "bad patterns" (combos de feature-values con winrate
     anormalmente bajo y volumen suficiente) -> reglas de EVITAR.
  4. Detecta "good patterns" (winrate alto) -> reglas de FAVORECER.
  5. Detecta features MUERTAS (varianza 0 en todo el dataset).
  6. Memoria durable: compara contra la corrida anterior y reporta
     DRIFT (winrate y ranking que cambiaron).
  7. Opcionalmente orquesta el re-entrenamiento del modelo LightGBM
     (flag --retrain) cuando hay suficientes trades NUEVOS.

El agente NO toca el hot path del scanner: es un analizador fuera de
linea que produce un reporte legible, reglas sugeridas (machine-readable
para que el humano/dashboard las apruebe) y, de tener masa crítica,
re-entrena el scorer para tenerlo listo.

No depende de ``lightgbm`` en su import: la carga de trades se
reimplementa aca (lightgbm-free) para que el analizador corra aunque
falte la dependencia de training. El re-entrenamiento se delega al
trainer via subprocess con el venv.

Uso:
    .venv/Scripts/python.exe scripts/agent_review.py
    .venv/Scripts/python.exe scripts/agent_review.py --retrain
    .venv/Scripts/python.exe scripts/agent_review.py --min-support 8
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

# Path bootstrap: que src/ sea importable como script.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SRC = os.path.join(_ROOT, "src")
for _p in (_SRC, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ml_features import FEATURE_NAMES, extract_features  # noqa: E402

AGENT_DIR = os.path.join(_ROOT, "data", "agent")
MEMORY_PATH = os.path.join(AGENT_DIR, "memory.json")
REPORT_GLOB = os.path.join(AGENT_DIR, "report-*.md")
SUGGESTIONS_PATH = os.path.join(AGENT_DIR, "suggestions.json")
DB_GLOB_CANDIDATES = os.path.join(_ROOT, "data", "db", "trade_journal-*.db")
DB_GLOB_BLACKBOX = os.path.join(_ROOT, "data", "db", "black_box_strat*.db")

# Umbrales por defecto (ajustables via CLI).
DEFAULT_MIN_SUPPORT = 10      # volumen minimo para que un patron sea confiable
DEFAULT_GOOD_WR = 0.62        # winrate >= -> buen patron
DEFAULT_BAD_WR = 0.38         # winrate <= -> mal patron
DEFAULT_MIN_TRADES_RETRAIN = 500


# ── Carga de trades (lightgbm-free, copiada de train_lightgbm) ──────────────
def discover_db_paths() -> list[str]:
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


def _to_epoch(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
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
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _blackbox_row_to_strategy_json(row: dict) -> dict:
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
    """Devuelve [{features, target(1=WIN), ts, source}, ...] (lightgbm-free)."""
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
                if not r.get("strategy_json"):
                    continue
                sj = r["strategy_json"]
                if isinstance(sj, str):
                    try:
                        sj = json.loads(sj)
                    except (json.JSONDecodeError, TypeError):
                        continue
                if r.get("spring_margin") is not None:
                    sj["spring_margin"] = r["spring_margin"]
                features = extract_features(sj)
                ts = _to_epoch(r.get("scanned_at"))
                rows.append({"features": features, "target": 1 if str(r["outcome"]).upper() == "WIN" else 0,
                             "ts": ts, "source": os.path.basename(db)})
        except sqlite3.Error:
            pass

        try:
            cur.execute(
                """
                SELECT order_result, strategy, strategy_details, stoch_m15,
                       direction, payout, duration_sec, ts
                FROM scan_candidates
                WHERE order_result IN ('WIN','LOSS') AND strategy = 'STRAT-F'
                """
            )
            for r in cur.fetchall():
                r = dict(r)
                sj = _blackbox_row_to_strategy_json(r)
                features = extract_features(sj)
                ts = _to_epoch(r.get("ts"))
                rows.append({"features": features, "target": 1 if str(r["order_result"]).upper() == "WIN" else 0,
                             "ts": ts, "source": os.path.basename(db)})
        except sqlite3.Error:
            pass

        conn.close()

    rows.sort(key=lambda x: (x["ts"] if x["ts"] is not None else float("inf"),))
    return rows


# ── Analisis ────────────────────────────────────────────────────────────────
def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def analyze(trades: list[dict]) -> dict:
    n = len(trades)
    n_win = sum(t["target"] for t in trades)
    winrate = n_win / n if n else 0.0

    # Features por clase
    win_feats = defaultdict(list)
    loss_feats = defaultdict(list)
    for t in trades:
        bucket = win_feats if t["target"] == 1 else loss_feats
        for f, v in t["features"].items():
            bucket[f].append(v)

    # Discriminacion: separacion de medias normalizada (Cohen-ish)
    discrimination = []
    dead_features = []
    for f in FEATURE_NAMES:
        wv, lv = win_feats[f], loss_feats[f]
        sd = _std(wv + lv)
        if sd == 0.0:
            dead_features.append(f)
            sep = 0.0
        else:
            sep = abs(_mean(wv) - _mean(lv)) / sd
        discrimination.append({
            "feature": f,
            "mean_win": round(_mean(wv), 4),
            "mean_loss": round(_mean(lv), 4),
            "separation": round(sep, 4),
            "fill": round((len(wv) + len(lv)) / n, 3) if n else 0.0,
        })
    discrimination.sort(key=lambda d: d["separation"], reverse=True)

    # Por direction
    by_dir = defaultdict(lambda: [0, 0])
    for t in trades:
        d = "CALL" if t["features"].get("direction") == 1.0 else "PUT"
        by_dir[d][0] += 1
        by_dir[d][1] += t["target"]

    # Por stoch_zone
    by_zone = defaultdict(lambda: [0, 0])
    for t in trades:
        z = int(t["features"].get("stoch_zone", 0))
        by_zone[z][0] += 1
        by_zone[z][1] += t["target"]

    # Por bucket de payout
    def payout_bucket(p: float) -> str:
        if p < 80:
            return "<80"
        if p < 85:
            return "80-85"
        if p < 90:
            return "85-90"
        return ">=90"
    by_payout = defaultdict(lambda: [0, 0])
    for t in trades:
        b = payout_bucket(t["features"].get("payout", 85))
        by_payout[b][0] += 1
        by_payout[b][1] += t["target"]

    return {
        "n": n,
        "n_win": n_win,
        "n_loss": n - n_win,
        "winrate": round(winrate, 4),
        "discrimination": discrimination,
        "dead_features": dead_features,
        "by_direction": {k: {"n": v[0], "win": v[1], "wr": round(v[1] / v[0], 3) if v[0] else 0.0} for k, v in by_dir.items()},
        "by_zone": {str(k): {"n": v[0], "win": v[1], "wr": round(v[1] / v[0], 3) if v[0] else 0.0} for k, v in by_zone.items()},
        "by_payout": {k: {"n": v[0], "win": v[1], "wr": round(v[1] / v[0], 3) if v[0] else 0.0} for k, v in by_payout.items()},
    }


def detect_patterns(trades: list[dict], min_support: int, good_wr: float, bad_wr: float) -> dict:
    """Detecta combos (direction + stoch_zone) con winrate extremo."""
    groups: dict[tuple, list[int]] = defaultdict(list)
    for t in trades:
        d = "CALL" if t["features"].get("direction") == 1.0 else "PUT"
        z = int(t["features"].get("stoch_zone", 0))
        groups[(d, z)].append(t["target"])

    good, bad = [], []
    for (d, z), targets in groups.items():
        n = len(targets)
        if n < min_support:
            continue
        w = sum(targets)
        wr = w / n
        entry = {"direction": d, "stoch_zone": z, "n": n, "win": w, "wr": round(wr, 3)}
        if wr >= good_wr:
            good.append(entry)
        elif wr <= bad_wr:
            bad.append(entry)
    good.sort(key=lambda e: e["wr"], reverse=True)
    bad.sort(key=lambda e: e["wr"])
    return {"good": good, "bad": bad}


# ── Memoria durable (drift entre corridas) ───────────────────────────────────
def load_memory() -> dict:
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_memory(mem: dict) -> None:
    os.makedirs(AGENT_DIR, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as fh:
        json.dump(mem, fh, indent=2)


def compute_drift(prev: dict, cur: dict) -> dict:
    drift: dict[str, Any] = {}
    pw = prev.get("winrate")
    cw = cur.get("winrate")
    if pw is not None and cw is not None:
        drift["winrate_delta"] = round(cw - pw, 4)
    prev_top = [d["feature"] for d in prev.get("discrimination", [])[:5]]
    cur_top = [d["feature"] for d in cur.get("discrimination", [])[:5]]
    if prev_top and cur_top:
        drift["top_features_changed"] = prev_top != cur_top
        drift["prev_top5"] = prev_top
        drift["cur_top5"] = cur_top
    return drift


# ── Reporte ──────────────────────────────────────────────────────────────────
def render_report(analysis: dict, patterns: dict, drift: dict, retrain: dict | None) -> str:
    lines: list[str] = []
    a = analysis
    lines.append("# Agente — Reporte de posiciones buenas/malas (STRAT-F)")
    lines.append(f"\nGenerado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"Trades resueltos analizados: **{a['n']}** (WIN={a['n_win']}, LOSS={a['n_loss']})")
    lines.append(f"Winrate global: **{a['winrate']*100:.1f}%**")
    if drift.get("winrate_delta") is not None:
        d = drift["winrate_delta"]
        sign = "+" if d >= 0 else ""
        lines.append(f"Drift vs corrida anterior: {sign}{d*100:.1f} pp")
    if drift.get("top_features_changed"):
        lines.append(f"Top features cambiaron: antes {drift['prev_top5']} -> ahora {drift['cur_top5']}")

    lines.append("\n## Features que mas discriminan WIN/LOSS")
    lines.append("| feature | mean_WIN | mean_LOSS | separacion | fill |")
    lines.append("|---|---|---|---|---|")
    for d in a["discrimination"][:8]:
        lines.append(f"| {d['feature']} | {d['mean_win']} | {d['mean_loss']} | {d['separation']} | {d['fill']} |")

    if a["dead_features"]:
        lines.append("\n## Features MUERTAS (varianza 0 en todo el dataset) — descartar del modelo")
        lines.append(", ".join(a["dead_features"]))

    lines.append("\n## Winrate por direction")
    for k, v in a["by_direction"].items():
        lines.append(f"- {k}: n={v['n']} winrate={v['wr']*100:.1f}%")

    lines.append("\n## Winrate por stoch_zone")
    for k, v in sorted(a["by_zone"].items()):
        lines.append(f"- Z{k}: n={v['n']} winrate={v['wr']*100:.1f}%")

    lines.append("\n## Winrate por bucket de payout")
    for k, v in sorted(a["by_payout"].items()):
        lines.append(f"- {k}: n={v['n']} winrate={v['wr']*100:.1f}%")

    if patterns["bad"]:
        lines.append("\n## BAD patterns (evitar — winrate anormalmente bajo)")
        lines.append("| direction | stoch_zone | n | winrate |")
        lines.append("|---|---|---|---|")
        for e in patterns["bad"]:
            lines.append(f"| {e['direction']} | Z{e['stoch_zone']} | {e['n']} | {e['wr']*100:.1f}% |")

    if patterns["good"]:
        lines.append("\n## GOOD patterns (favorecer — winrate alto)")
        lines.append("| direction | stoch_zone | n | winrate |")
        lines.append("|---|---|---|---|")
        for e in patterns["good"]:
            lines.append(f"| {e['direction']} | Z{e['stoch_zone']} | {e['n']} | {e['wr']*100:.1f}% |")

    if retrain:
        lines.append("\n## Re-entrenamiento")
        if retrain.get("trained"):
            m = retrain.get("metrics", {})
            lines.append(f"- Modelo re-entrenado. accuracy={m.get('accuracy')} f1={m.get('f1')} auc={m.get('auc')}")
        elif retrain.get("skipped"):
            lines.append(f"- Skip: {retrain.get('reason')}")
        else:
            lines.append(f"- Resultado: {retrain}")

    lines.append("\n---\nReporte generado por scripts/agent_review.py (agente offline, determinista).")
    return "\n".join(lines)


# ── Orquestador de re-entrenamiento ──────────────────────────────────────────
def maybe_retrain(n_trades: int, min_trades: int, venv_python: str | None) -> dict:
    mem = load_memory()
    last_n = mem.get("last_trained_n", 0)
    if n_trades < min_trades:
        return {"skipped": True, "reason": f"faltan {min_trades - n_trades} trades para re-entrenar (actual={n_trades})"}
    if n_trades <= last_n:
        return {"skipped": True, "reason": f"sin trades nuevos desde ultimo train (ultimo={last_n}, actual={n_trades})"}
    if not venv_python or not os.path.exists(venv_python):
        return {"skipped": True, "reason": f"venv python no encontrado: {venv_python}"}
    try:
        out = subprocess.run(
            [venv_python, os.path.join(_ROOT, "scripts", "train_lightgbm.py"),
             "--min-trades", str(min_trades)],
            capture_output=True, text=True, timeout=600,
        )
        meta_path = os.path.join(_ROOT, "data", "models", "lightgbm_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
            meta["trained"] = True
            return meta
        return {"trained": False, "stdout": out.stdout[-500:], "stderr": out.stderr[-500:]}
    except Exception as e:  # noqa: BLE001
        return {"trained": False, "error": str(e)}


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Agente offline de aprendizaje buenas/malas STRAT-F.")
    ap.add_argument("--retrain", action="store_true", help="Re-entrenar LightGBM si hay masa critica.")
    ap.add_argument("--min-trades", type=int, default=DEFAULT_MIN_TRADES_RETRAIN)
    ap.add_argument("--min-support", type=int, default=DEFAULT_MIN_SUPPORT)
    ap.add_argument("--good-wr", type=float, default=DEFAULT_GOOD_WR)
    ap.add_argument("--bad-wr", type=float, default=DEFAULT_BAD_WR)
    ap.add_argument("--venv-python", type=str, default=os.path.join(_ROOT, ".venv", "Scripts", "python.exe"))
    ap.add_argument("--digest", action="store_true", help="Imprimir solo resumen corto (para cron/notificacion).")
    args = ap.parse_args()

    trades = load_resolved_trades()
    analysis = analyze(trades)
    patterns = detect_patterns(trades, args.min_support, args.good_wr, args.bad_wr)

    prev = load_memory()
    drift = compute_drift(prev, analysis)

    retrain_result = None
    if args.retrain:
        retrain_result = maybe_retrain(len(trades), args.min_trades, args.venv_python)

    report = render_report(analysis, patterns, drift, retrain_result)

    os.makedirs(AGENT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report_path = os.path.join(AGENT_DIR, f"report-{stamp}.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    # Sugerencias machine-readable (para que el humano/dashboard apruebe).
    suggestions = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_trades": len(trades),
        "winrate": analysis["winrate"],
        "dead_features_to_drop": analysis["dead_features"],
        "avoid_rules": [
            {"direction": e["direction"], "stoch_zone": e["stoch_zone"],
             "reason": f"winrate={e['wr']*100:.1f}% en n={e['n']}"}
            for e in patterns["bad"]
        ],
        "favor_rules": [
            {"direction": e["direction"], "stoch_zone": e["stoch_zone"],
             "reason": f"winrate={e['wr']*100:.1f}% en n={e['n']}"}
            for e in patterns["good"]
        ],
        "top_discriminating_features": [d["feature"] for d in analysis["discrimination"][:5]],
    }
    with open(SUGGESTIONS_PATH, "w", encoding="utf-8") as fh:
        json.dump(suggestions, fh, indent=2)

    # Actualizar memoria.
    mem = {
        "winrate": analysis["winrate"],
        "n": len(trades),
        "discrimination": analysis["discrimination"],
        "last_report": report_path,
        "last_run": datetime.now(timezone.utc).isoformat(),
        "last_trained_n": (retrain_result or {}).get("n_trades", prev.get("last_trained_n", 0)),
    }
    save_memory(mem)

    if args.digest:
        digest = _build_digest(analysis, patterns, drift, retrain_result, report_path)
        print(digest)
    else:
        print(report)
        print(f"\n[AGENT] reporte -> {report_path}")
    print(f"[AGENT] sugerencias -> {SUGGESTIONS_PATH}")
    return 0


def _build_digest(analysis: dict, patterns: dict, drift: dict,
                  retrain: dict | None, report_path: str) -> str:
    """Resumen corto para notificacion/cron (drift + mejor patron + retrain)."""
    a = analysis
    lines: list[str] = []
    lines.append(f"QUOTEX agent digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"trades={a['n']} winrate={a['winrate']*100:.1f}%")
    if drift.get("winrate_delta") is not None:
        d = drift["winrate_delta"]
        s = "+" if d >= 0 else ""
        lines.append(f"drift winrate: {s}{d*100:.1f}pp")
    if drift.get("top_features_changed"):
        lines.append(f"top features: {drift['cur_top5']}")
    best = patterns["good"][0] if patterns["good"] else None
    if best:
        lines.append(f"MEJOR patron GOOD: {best['direction']} Z{best['stoch_zone']} "
                     f"n={best['n']} wr={best['wr']*100:.1f}%")
    else:
        lines.append("MEJOR patron GOOD: ninguno con volumen suficiente")
    worst = patterns["bad"][0] if patterns["bad"] else None
    if worst:
        lines.append(f"PEOR patron BAD: {worst['direction']} Z{worst['stoch_zone']} "
                     f"n={worst['n']} wr={worst['wr']*100:.1f}%")
    if retrain:
        if retrain.get("trained"):
            m = retrain.get("metrics", {})
            lines.append(f"RETREINADO OK acc={m.get('accuracy')} f1={m.get('f1')} auc={m.get('auc')}")
        elif retrain.get("skipped"):
            lines.append(f"retrain skip: {retrain.get('reason')}")
    lines.append(f"reporte completo: {report_path}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
