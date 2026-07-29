"""Agente OFFLINE dedicado al comportamiento del ESTOCASTICO en las 3 TFs.

Este agente es INDEPENDIENTE de agent_review.py: se especializa en
aprender como se comporta el estocastico (M15 / M5 / M1) en el momento
de la entrada, y si eso predice exito o fracaso.

Hipotesis que el agente valida (Ruben 2026-07-24):
  - El bot entra CALL con el estocastico M15 apuntando PARA ABAJO y
    eso pierde.
  - Cuando entra en la direccion del estocastico que SALE de la zona
    20 hacia la 80 (va para ARRIBA), da mejores resultados.

El agente NO asume la hipotesis: la EVALUA contra los datos y reporta
el winrate por celda con intervalo de Wilson (para no vender ruido de
n=11 como 'mejor patron').

Salida:
  - reporte data/agent/stoch-report-<ts>.md
  - sugerencias data/agent/stoch-suggestions.json (machine-readable)
  - memoria data/agent/stoch-memory.json (drift entre corridas)
  - --digest: resumen corto para cron

Uso:
  .venv/Scripts/python.exe scripts/agent_stoch.py
  .venv/Scripts/python.exe scripts/agent_stoch.py --digest
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import agent_common as ac

STOCH_DIR = os.path.join(ac.AGENT_DIR, "stoch")
MEMORY_PATH = os.path.join(STOCH_DIR, "memory.json")
SUGGESTIONS_PATH = os.path.join(STOCH_DIR, "suggestions.json")

DEFAULT_MIN_SUPPORT = 10
DEFAULT_GOOD_WR = 0.60
DEFAULT_BAD_WR = 0.40


# ── Analisis por TF ──────────────────────────────────────────────────────────
def _cell_stats(rows: list[dict], key_fn) -> dict:
    """Agrupa filas por key_fn(row) y devuelve estadistica por celda."""
    groups: dict[Any, list[int]] = defaultdict(list)
    for t in rows:
        k = key_fn(t)
        groups[k].append(t["target"])
    out = {}
    for k, targets in groups.items():
        n = len(targets)
        w = sum(targets)
        lo, center, hi = ac.wilson_interval(w, n)
        out[k] = {
            "n": n,
            "win": w,
            "wr": round(center, 4),
            "wilson_lower": round(lo, 4),
            "wilson_upper": round(hi, 4),
        }
    return out


def analyze_stoch(rows: list[dict]) -> dict:
    n = len(rows)
    n_win = sum(t["target"] for t in rows)

    def tf_trend(tf: str):
        def f(t: dict) -> str:
            return ac.stoch_trend(t["stoch"].get(tf, {}))
        return f

    def tf_zone(tf: str):
        def f(t: dict) -> str:
            return ac.stoch_zone_label(t["stoch"].get(tf, {}))
        return f

    def dir_cross_trend(t: dict, tf: str):
        d = t["direction"]
        tr = ac.stoch_trend(t["stoch"].get(tf, {}))
        return f"{d}|{tf.upper()}:{tr}"

    def exit_zone_up(t: dict):
        # "sale de 20 hacia 80" = sobreventa y subiendo (en M15).
        s = t["stoch"].get("m15", {})
        z = ac.stoch_zone_label(s)
        tr = ac.stoch_trend(s)
        return f"{z}|{tr}"

    result = {
        "n": n,
        "n_win": n_win,
        "winrate": round(n_win / n, 4) if n else 0.0,
        "m15_trend": _cell_stats(rows, tf_trend("m15")),
        "m5_trend": _cell_stats(rows, tf_trend("m5")),
        "m1_trend": _cell_stats(rows, tf_trend("m1")),
        "m15_zone": _cell_stats(rows, tf_zone("m15")),
        "m5_zone": _cell_stats(rows, tf_zone("m5")),
        "m1_zone": _cell_stats(rows, tf_zone("m1")),
        "direction_x_m15_trend": _cell_stats(rows, lambda t: dir_cross_trend(t, "m15")),
        "direction_x_m5_trend": _cell_stats(rows, lambda t: dir_cross_trend(t, "m5")),
        "direction_x_m1_trend": _cell_stats(rows, lambda t: dir_cross_trend(t, "m1")),
        "m15_exit_zone": _cell_stats(rows, exit_zone_up),
    }
    return result


def detect_rules(analysis: dict, min_support: int, good_wr: float, bad_wr: float) -> dict:
    """Convierte celdas extremas en reglas sugeridas, usando Wilson lower."""
    good, bad = [], []

    def scan(group: dict, label: str):
        for k, st in group.items():
            if st["n"] < min_support:
                continue
            # Solo consideramos 'bueno' si el lower bound supera el umbral.
            if st["wilson_lower"] >= good_wr:
                good.append({"group": label, "key": str(k), **st})
            elif st["wilson_upper"] <= bad_wr:
                bad.append({"group": label, "key": str(k), **st})

    for grp in (
        "m15_trend", "m5_trend", "m1_trend",
        "direction_x_m15_trend", "direction_x_m5_trend", "direction_x_m1_trend",
        "m15_exit_zone",
    ):
        scan(analysis.get(grp, {}), grp)

    good.sort(key=lambda e: e["wilson_lower"], reverse=True)
    bad.sort(key=lambda e: e["wilson_lower"])
    return {"good": good, "bad": bad}


# ── Memoria / drift ──────────────────────────────────────────────────────────
def load_memory() -> dict:
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_memory(mem: dict) -> None:
    os.makedirs(STOCH_DIR, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as fh:
        json.dump(mem, fh, indent=2)


def compute_drift(prev: dict, cur: dict) -> dict:
    drift: dict[str, Any] = {}
    pw = prev.get("winrate")
    cw = cur.get("winrate")
    if pw is not None and cw is not None:
        drift["winrate_delta"] = round(cw - pw, 4)
    # Drift de la hipotesis clave: CALL+M15 bajando.
    pk = (prev.get("direction_x_m15_trend") or {}).get("CALL|M15:bajando")
    ck = (cur.get("direction_x_m15_trend") or {}).get("CALL|M15:bajando")
    if pk and ck:
        drift["call_m15_down_wr_delta"] = round(ck["wr"] - pk["wr"], 4)
    return drift


# ── Render ───────────────────────────────────────────────────────────────────
def _fmt_cell(k: str, st: dict) -> str:
    return (f"- {k}: n={st['n']} wr={st['wr']*100:.1f}% "
            f"(Wilson {st['wilson_lower']*100:.1f}–{st['wilson_upper']*100:.1f}%)")


def render_report(analysis: dict, rules: dict, drift: dict) -> str:
    a = analysis
    L: list[str] = []
    L.append("# Agente Estocastico — comportamiento por TF (STRAT-F)")
    L.append(f"\nGenerado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    L.append(f"Trades analizados: **{a['n']}** (WIN={a['n_win']}, winrate={a['winrate']*100:.1f}%)")
    if drift.get("winrate_delta") is not None:
        d = drift["winrate_delta"]
        s = "+" if d >= 0 else ""
        L.append(f"Drift winrate vs corrida anterior: {s}{d*100:.1f}pp")
    if drift.get("call_m15_down_wr_delta") is not None:
        d = drift["call_m15_down_wr_delta"]
        s = "+" if d >= 0 else ""
        L.append(f"Drift CALL+M15-bajando winrate: {s}{d*100:.1f}pp")

    L.append("\n## Estocastico M15 — tendencia al entrar")
    for k, st in sorted(a["m15_trend"].items()):
        L.append(_fmt_cell(k, st))
    L.append("\n## Estocastico M5 — tendencia al entrar")
    for k, st in sorted(a["m5_trend"].items()):
        L.append(_fmt_cell(k, st))
    L.append("\n## Estocastico M1 — tendencia al entrar")
    for k, st in sorted(a["m1_trend"].items()):
        L.append(_fmt_cell(k, st))
    L.append("\n## M15 — zona al entrar")
    for k, st in sorted(a["m15_zone"].items()):
        L.append(_fmt_cell(k, st))
    L.append("\n## M5 — zona al entrar")
    for k, st in sorted(a["m5_zone"].items()):
        L.append(_fmt_cell(k, st))
    L.append("\n## M1 — zona al entrar")
    for k, st in sorted(a["m1_zone"].items()):
        L.append(_fmt_cell(k, st))
    L.append("\n## Direction x M15 tendencia (celda clave de la hipotesis)")
    for k, st in sorted(a["direction_x_m15_trend"].items()):
        L.append(_fmt_cell(k, st))
    L.append("\n## Direction x M5 tendencia")
    for k, st in sorted(a["direction_x_m5_trend"].items()):
        L.append(_fmt_cell(k, st))
    L.append("\n## Direction x M1 tendencia")
    for k, st in sorted(a["direction_x_m1_trend"].items()):
        L.append(_fmt_cell(k, st))
    L.append("\n## M15 — salida de zona (sobreventa+subiendo = 'sale de 20 hacia 80')")
    for k, st in sorted(a["m15_exit_zone"].items()):
        L.append(_fmt_cell(k, st))

    if rules["bad"]:
        L.append("\n## BAD rules sugeridas (evitar — Wilson upper <= 40%)")
        for e in rules["bad"]:
            L.append(f"- [{e['group']}] {e['key']}: n={e['n']} wr={e['wr']*100:.1f}%")
    if rules["good"]:
        L.append("\n## GOOD rules sugeridas (favorecer — Wilson lower >= 60%)")
        for e in rules["good"]:
            L.append(f"- [{e['group']}] {e['key']}: n={e['n']} wr={e['wr']*100:.1f}%")

    L.append("\n---\nAgente scripts/agent_stoch.py (offline, determinista).")
    return "\n".join(L)


def build_digest(analysis: dict, rules: dict, drift: dict, report_path: str) -> str:
    a = analysis
    L: list[str] = []
    L.append(f"QUOTEX stoch-agent digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    L.append(f"trades={a['n']} winrate={a['winrate']*100:.1f}%")
    if drift.get("winrate_delta") is not None:
        d = drift["winrate_delta"]
        s = "+" if d >= 0 else ""
        L.append(f"drift winrate: {s}{d*100:.1f}pp")
    # Celdas clave de la hipotesis (M15 y M1).
    for tf in ("m15", "m1"):
        cell = a[f"direction_x_{tf}_trend"].get(f"CALL|{tf.upper()}:bajando")
        if cell:
            L.append(f"HIPOTESIS CALL+{tf.upper()}-bajando: n={cell['n']} wr={cell['wr']*100:.1f}% "
                     f"(Wilson lo={cell['wilson_lower']*100:.1f}%)")
    best = rules["good"][0] if rules["good"] else None
    worst = rules["bad"][0] if rules["bad"] else None
    if best:
        L.append(f"GOOD: [{best['group']}] {best['key']} n={best['n']} wr={best['wr']*100:.1f}%")
    if worst:
        L.append(f"BAD: [{worst['group']}] {worst['key']} n={worst['n']} wr={worst['wr']*100:.1f}%")
    L.append(f"reporte: {report_path}")
    return "\n".join(L)


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Agente estocastico STRAT-F (3 TFs).")
    ap.add_argument("--digest", action="store_true", help="Resumen corto para cron.")
    ap.add_argument("--min-support", type=int, default=DEFAULT_MIN_SUPPORT)
    ap.add_argument("--good-wr", type=float, default=DEFAULT_GOOD_WR)
    ap.add_argument("--bad-wr", type=float, default=DEFAULT_BAD_WR)
    args = ap.parse_args()

    rows = ac.load_resolved_trades()
    analysis = analyze_stoch(rows)
    rules = detect_rules(analysis, args.min_support, args.good_wr, args.bad_wr)

    prev = load_memory()
    drift = compute_drift(prev, analysis)

    report = render_report(analysis, rules, drift)

    os.makedirs(STOCH_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report_path = os.path.join(STOCH_DIR, f"stoch-report-{stamp}.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    suggestions = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_trades": analysis["n"],
        "winrate": analysis["winrate"],
        "hypothesis_call_m15_down": analysis["direction_x_m15_trend"].get("CALL|M15:bajando"),
        "good_rules": rules["good"],
        "bad_rules": rules["bad"],
    }
    with open(SUGGESTIONS_PATH, "w", encoding="utf-8") as fh:
        json.dump(suggestions, fh, indent=2)

    save_memory({
        "winrate": analysis["winrate"],
        "n": analysis["n"],
        "direction_x_m15_trend": analysis["direction_x_m15_trend"],
        "last_report": report_path,
        "last_run": datetime.now(timezone.utc).isoformat(),
    })

    if args.digest:
        print(build_digest(analysis, rules, drift, report_path))
    else:
        print(report)
        print(f"\n[STOCH] reporte -> {report_path}")
    print(f"[STOCH] sugerencias -> {SUGGESTIONS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
