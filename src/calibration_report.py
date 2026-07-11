"""Reporte de calibracion STRAT-F.

Lee las decisiones STRAT-F del diario (trade_journal.db) y sugiere
ajustes de umbrales basados en datos reales: que filtros estan
matando senales, y si el win rate de aceptadas justifica apretar o
aflojar. Es heuristico — no una garantia de rentabilidad.

Uso:  python -m calibration_report [dias]
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from trade_journal import Journal  # noqa: E402


# Mapeo de skip_reason -> codigo de filtro (debe coincidir con
# src/strat_fractal.py: los textos son los que emite evaluate_strat_f).
def classify_skip(reason: str) -> str:
    r = reason.lower()
    if "payout" in r and "minimo" in r:
        return "R2 payout"
    if "rango roto" in r:
        return "CTX M15 roto"
    if "m5 insuficiente" in r:
        return "DATA M5"
    if "sin fractal m5" in r:
        return "DATA M5"
    if "zona muy joven" in r:
        return "R3 edad zona"
    if "contra tendencia m15" in r:
        return "R1 tendencia"
    if "m1 no rechaza" in r:
        return "R4 banda M1"
    if "score" in r and "minimo" in r:
        return "R6 score"
    return "OTRO"


# Texto humano de cada filtro para las sugerencias.
SUGGESTIONS = {
    "R2 payout": (
        "Fijado por el broker, no ajustable. Si domina, restringe la "
        "lista de pares a los que paguen >=80%."
    ),
    "R3 edad zona": (
        "STRAT_F_ZONE_MIN_AGE (ahora 3 velas M5). Si mata mucho, bajar a 2 "
        "da mas volumen pero mas ruido recien formado. Solo bajar si el win "
        "rate de aceptadas es alto."
    ),
    "R4 banda M1": (
        "Filtro de calidad clave (el precio debe rechazar la banda). Si "
        "domina (>50%), revisar la logica de banda en M1 antes de relajar; "
        "no es ruido barato."
    ),
    "R1 tendencia": (
        "Contexto M15. Si domina, el mercado esta direccional y STRAT-F "
        "(rebotes) no aplica; no aflojar."
    ),
    "R6 score": (
        "STRAT_F_MIN_SCORE (ahora 60). Bajar da volumen; subir da pureza. "
        "Ajustar segun win rate de aceptadas."
    ),
    "CTX M15 roto": "No operar rebotes en rango roto. Correcto, no tocar.",
    "DATA M5": "Falta de velas M5 para fractal. Ruido de datos, no umbral.",
    "OTRO": "Revisar a mano.",
}


def build_calibration(days: int = 90, journal: Optional[Journal] = None) -> dict:
    j = journal or Journal()
    rows = j.query_strat_f(days)
    total = len(rows)
    accepted = [r for r in rows if r["decision"] == "ACCEPTED"]
    rejected = [r for r in rows if r["decision"] != "ACCEPTED"]
    wins = [r for r in accepted if r["outcome"] == "WIN"]
    losses = [r for r in accepted if r["outcome"] == "LOSS"]
    pending = [r for r in accepted if r["outcome"] in ("PENDING", "DRY_RUN")]

    reasons = Counter(classify_skip((r["reject_reason"] or "sin motivo")) for r in rejected)
    resolved = len(wins) + len(losses)
    win_rate = (len(wins) / resolved * 100.0) if resolved else 0.0
    acc_rate = (len(accepted) / total * 100.0) if total else 0.0

    # Sugerencia global basada en win rate de aceptadas resueltas.
    if resolved == 0:
        global_hint = "Sin trades resueltas aun: no ajustar umbrales todavia."
    elif win_rate < 50.0:
        global_hint = (
            f"Win rate {win_rate:.0f}% < 50%: APRETAR umbrales "
            "(subir STRAT_F_MIN_SCORE o STRAT_F_ZONE_MIN_AGE)."
        )
    elif win_rate >= 60.0 and acc_rate < 10.0:
        global_hint = (
            f"Win rate {win_rate:.0f}% alto pero pocas senales ({acc_rate:.0f}%): "
            "considerar RELAJAR un poco (bajar R3/R6) para mas volumen."
        )
    else:
        global_hint = (
            f"Win rate {win_rate:.0f}% y volumen {acc_rate:.0f}%: umbrales "
            "actuales razonables, monitorear."
        )

    return {
        "total": total,
        "accepted": len(accepted),
        "rejected": len(rejected),
        "wins": len(wins),
        "losses": len(losses),
        "pending": len(pending),
        "win_rate": win_rate,
        "acc_rate": acc_rate,
        "reasons": dict(reasons),
        "global_hint": global_hint,
    }


def print_calibration(days: int = 90) -> None:
    c = build_calibration(days)
    print(f"\n{'═'*70}")
    print(f"  STRAT-F — CALIBRACION (ultimos {days} dias)")
    print(f"{'═'*70}")
    if c["total"] == 0:
        print("  (sin datos STRAT-F en el diario todavia)")
        print("  Corre run_strat_f_panel.bat para alimentarlo.")
        print()
        return
    print(f"  Evaluados : {c['total']}")
    print(f"  Aceptadas : {c['accepted']}  ({c['acc_rate']:.1f}%)")
    print(f"  Rechazadas: {c['rejected']}")
    print(f"  Resueltas : WIN={c['wins']} LOSS={c['losses']} PEND={c['pending']}")
    print(f"  Win rate  : {c['win_rate']:.1f}%")
    print(f"\n  Motivos de rechazo (para calibrar):")
    for motive, cnt in Counter(c["reasons"]).most_common():
        pct = cnt / max(c["rejected"], 1) * 100.0
        print(f"    {cnt:>4}  ({pct:5.1f}%)  [{motive}]")
        print(f"           -> {SUGGESTIONS.get(motive, 'revisar')}")
    print(f"\n  Sugerencia global: {c['global_hint']}")
    print()


if __name__ == "__main__":
    _days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    print_calibration(days=_days)
