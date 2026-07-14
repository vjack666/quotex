"""Estadísticas de la caja negra STRAT-F (Fase 5).

Lee scan_candidates de la caja negra (black_box_strat_*.db) y produce un
reporte medible:
- win_rate / expectancy por asset y por hora del día.
- ranking de loss_reason (qué falla más, para calibrar).
- A/B del estocástico M15: opera donde stoch indicaba extremo
  (sobrecompra/sobreventa) vs neutro, sin filtrar aún (modo medición).

No duplica calibration_report.py (que lee trade_journal); este módulo es la
capa de datos de la caja negra y alimenta tanto consola como un futuro LLM.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from black_box_recorder import get_black_box


def _parse_stoch(stoch_raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not stoch_raw:
        return None
    try:
        return json.loads(stoch_raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _stoch_bucket(stoch: Optional[Dict[str, Any]]) -> str:
    """Clasifica el estocástico en extremo vs neutro para el A/B."""
    if not stoch:
        return "sin_datos"
    estado = (stoch.get("estado") or "").upper()
    if estado in ("SOBRECOMPRA", "SOBREVENTA"):
        return "extremo"
    if estado in ("NEUTRO", ""):
        return "neutro"
    return "neutro"


def build_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Calcula todas las métricas desde la caja negra.

    Devuelve un dict serializable (listo para JSON / LLM).
    """
    bb = get_black_box()
    path = db_path or bb.db_path
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT asset, direction, decision, order_result, profit,
               loss_reason, improvement_hint, stoch_m15, created_at
        FROM scan_candidates
        WHERE strategy = 'STRAT-F'
        """
    ).fetchall()
    con.close()

    resolved = [r for r in rows if r["order_result"] in ("WIN", "LOSS")]

    # ── Global ──
    total = len(resolved)
    wins = sum(1 for r in resolved if r["order_result"] == "WIN")
    losses = total - wins
    pnl = sum((r["profit"] or 0.0) for r in resolved)
    win_rate = (wins / total * 100.0) if total else 0.0
    expectancy = (pnl / total) if total else 0.0

    # ── Por asset ──
    by_asset: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"n": 0, "w": 0, "pnl": 0.0})
    for r in resolved:
        a = by_asset[r["asset"]]
        a["n"] += 1
        a["w"] += 1 if r["order_result"] == "WIN" else 0
        a["pnl"] += (r["profit"] or 0.0)
    assets_stats = {
        a: {
            "n": v["n"],
            "win_rate": (v["w"] / v["n"] * 100.0) if v["n"] else 0.0,
            "expectancy": (v["pnl"] / v["n"]) if v["n"] else 0.0,
        }
        for a, v in sorted(by_asset.items(), key=lambda kv: kv[1]["pnl"], reverse=True)
    }

    # ── Por hora del día (UTC) ──
    by_hour: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"n": 0, "w": 0, "pnl": 0.0})
    for r in resolved:
        try:
            dt = datetime.fromisoformat(r["created_at"])
        except (ValueError, TypeError):
            continue
        h = dt.hour
        b = by_hour[h]
        b["n"] += 1
        b["w"] += 1 if r["order_result"] == "WIN" else 0
        b["pnl"] += (r["profit"] or 0.0)
    hour_stats = {
        str(h): {
            "n": v["n"],
            "win_rate": (v["w"] / v["n"] * 100.0) if v["n"] else 0.0,
            "expectancy": (v["pnl"] / v["n"]) if v["n"] else 0.0,
        }
        for h, v in sorted(by_hour.items())
    }

    # ── Ranking de loss_reason ──
    loss_counter: Dict[str, int] = defaultdict(int)
    hint_by_reason: Dict[str, str] = {}
    for r in resolved:
        if r["order_result"] == "LOSS" and r["loss_reason"]:
            loss_counter[r["loss_reason"]] += 1
            if r["improvement_hint"]:
                hint_by_reason[r["loss_reason"]] = r["improvement_hint"]
    loss_ranking = [
        {"reason": reason, "count": cnt, "hint": hint_by_reason.get(reason, "")}
        for reason, cnt in sorted(loss_counter.items(), key=lambda kv: kv[1], reverse=True)
    ]

    # ── A/B estocástico M15 ──
    ab: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"n": 0, "w": 0, "pnl": 0.0})
    for r in resolved:
        bucket = _stoch_bucket(_parse_stoch(r["stoch_m15"]))
        cell = ab[bucket]
        cell["n"] += 1
        cell["w"] += 1 if r["order_result"] == "WIN" else 0
        cell["pnl"] += (r["profit"] or 0.0)
    ab_stats = {
        k: {
            "n": v["n"],
            "win_rate": (v["w"] / v["n"] * 100.0) if v["n"] else 0.0,
            "expectancy": (v["pnl"] / v["n"]) if v["n"] else 0.0,
        }
        for k, v in ab.items()
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_resolved": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "expectancy": round(expectancy, 4),
        "pnl": round(pnl, 2),
        "by_asset": {a: {k: round(val, 2) for k, val in v.items()} for a, v in assets_stats.items()},
        "by_hour": {h: {k: round(val, 2) for k, val in v.items()} for h, v in hour_stats.items()},
        "loss_ranking": loss_ranking,
        "stoch_ab": {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in ab_stats.items()},
    }


def render_report(stats: Dict[str, Any]) -> str:
    """Formatea el dict a texto legible (consola / log)."""
    lines: List[str] = []
    lines.append("=== Caja Negra STRAT-F — Reporte ===")
    lines.append(f"Resueltas : {stats['total_resolved']} (WIN {stats['wins']} / LOSS {stats['losses']})")
    lines.append(f"Win rate : {stats['win_rate']:.1f}%")
    lines.append(f"Expectancy: {stats['expectancy']:.4f}")
    lines.append(f"PnL      : {stats['pnl']:.2f}")
    if stats["by_asset"]:
        lines.append("")
        lines.append("Por asset (PnL desc):")
        for a, v in stats["by_asset"].items():
            lines.append(f"  {a:14s} n={v['n']:3d} WR={v['win_rate']:.1f}% E={v['expectancy']:.4f}")
    if stats["by_hour"]:
        lines.append("")
        lines.append("Por hora UTC:")
        for h, v in stats["by_hour"].items():
            lines.append(f"  {h:>2s}h  n={v['n']:3d} WR={v['win_rate']:.1f}% E={v['expectancy']:.4f}")
    if stats["loss_ranking"]:
        lines.append("")
        lines.append("Ranking de pérdidas (loss_reason):")
        for item in stats["loss_ranking"]:
            lines.append(f"  {item['reason']:22s} x{item['count']}  -> {item['hint']}")
    if stats["stoch_ab"]:
        lines.append("")
        lines.append("A/B estocástico M15 (modo medición, aún no filtra):")
        for k, v in stats["stoch_ab"].items():
            lines.append(f"  {k:10s} n={v['n']:3d} WR={v['win_rate']:.1f}% E={v['expectancy']:.4f}")
    return "\n".join(lines)


def main() -> None:
    stats = build_stats()
    print(render_report(stats))


if __name__ == "__main__":
    main()
