"""Grilla 5x4 (EXP-041..EXP-060) — embudo del Edificio sobre EURUSD REAL.

Eje A (EXTREMO): OVERSOLD/OVERBOUGHT en 20/80, 25/75, 30/70, 35/65, 40/60
Eje B (SEPARACION): MIN_SEPARATION en 1, 2, 3, 4

Cada celda = un experimento. Mismo motor secuencia_libre, mismo dominio
REAL, mismo payout 0.85, seed 42. Se inyectan los umbrales al modulo antes
de correr (sin tocar secuencia_libre.py).

Al final aplica FDR/Bonferroni sobre los 20 p-values y declara el mejor
por tribunal: maximo EV neto que sobrevive FDR (p_adj < alpha) y n>=100.

Genera reports/EXP-04X/ con reporte inmutable por cada experimento.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import numpy as np
from scipy import stats
from strategy_lab.multiple_comparisons import adjust_pvalues

PAYOUT = 0.85
SEED = 42
ALPHA = 0.05
N_MIN = 100

EXTREMOS = [(20, 80), (25, 75), (30, 70), (35, 65), (40, 60)]
SEPARACIONES = [1, 2, 3, 4]

from strategy_lab import secuencia_libre as SL


def run_one(oversold: int, overbought: int, min_sep: int) -> dict:
    """Corre el motor con umbrales inyectados; devuelve metricas del embudo."""
    # inyectar constantes (sin editar el modulo original)
    SL.OVERSOLD = float(oversold)
    SL.OVERBOUGHT = float(overbought)
    SL.MIN_SEPARATION = float(min_sep)

    events, funnel = SL.run_secuencia_libre(pairs=["EURUSD"], verbose=False)
    comp = events[events["win"] >= 0]
    n_comp = len(comp)
    if n_comp == 0:
        return {
            "oversold": oversold, "overbought": overbought, "min_sep": min_sep,
            "nacidos": int(funnel["nacidos"].iloc[0]),
            "completas": 0, "wr": float("nan"), "ev": float("nan"),
            "p": 1.0, "n": 0,
        }
    wins = int(comp["win"].sum())
    wr = wins / n_comp
    ev_net = wr * (PAYOUT - 1.0) + (1 - wr) * (-1.0)
    p = stats.binomtest(wins, n_comp, 0.50).pvalue
    return {
        "oversold": oversold, "overbought": overbought, "min_sep": min_sep,
        "nacidos": int(funnel["nacidos"].iloc[0]),
        "completas": n_comp, "wr": round(wr, 4), "ev": round(float(ev_net), 4),
        "p": p, "n": n_comp,
    }


def main() -> int:
    from strategy_lab.experiment_runner import run_experiment

    rows = []
    exp_idx = 41
    for (os_, ob_) in EXTREMOS:
        for ms in SEPARACIONES:
            m = run_one(os_, ob_, ms)
            m["exp"] = f"EXP-{exp_idx:03d}"
            rows.append(m)
            # reporte inmutable por experimento
            ev = SL.run_secuencia_libre(pairs=["EURUSD"], verbose=False)[0]
            ev = ev[ev["win"] >= 0].copy()
            ev["timestamp"] = pd.to_datetime(ev["birth_time"], errors="coerce")
            ev["profit"] = ev["win"].apply(lambda w: (PAYOUT - 1.0) if w == 1 else -1.0)
            ev["expected_value"] = ev["profit"]
            protocol = {
                "domain": "REAL", "alpha": ALPHA, "fdr_method": "fdr_bh",
                "poder_min": 0.80, "n_min": N_MIN, "baseline_wr": 0.50,
                "payout": PAYOUT, "seed": SEED,
                "oversold": os_, "overbought": ob_, "min_separation": ms,
                "grid": "5x4 extremo x separacion",
                "hypothesis": "specs/lab_protocolo_cientifico/hypothesis_exp040.md",
            }
            try:
                art = run_experiment(
                    f"EXP-{exp_idx:03d}", ev, seed=SEED,
                    dataset_manifest=str(ROOT / "datasets" / "dataset_v001" / "manifest.json"),
                    protocol=protocol, report_dir=ROOT / "reports",
                )
                m["report"] = str(art.report_path)
            except Exception as exc:  # no debe fallar, pero no matamos la grilla
                m["report"] = f"ERROR: {exc}"
            print(f"[{m['exp']}] extremo={os_}/{ob_} sep={ms} "
                  f"completas={m['completas']} WR={m['wr']} EV={m['ev']} p={m['p']:.4f}")
            exp_idx += 1

    grid = pd.DataFrame(rows)

    # FDR/Bonferroni sobre los 20 p-values (Art. 9)
    fdr = adjust_pvalues(grid["p"].tolist(), method="fdr_bh")
    grid["p_adj_fdr"] = [round(x, 6) for x in fdr.adj_p]
    bonf = adjust_pvalues(grid["p"].tolist(), method="bonferroni")
    grid["p_adj_bonf"] = [round(x, 6) for x in bonf.adj_p]

    # mejor por tribunal: EV neto maximo que sobrevive FDR y n>=100
    elig = grid[(grid["p_adj_fdr"] < ALPHA) & (grid["n"] >= N_MIN)]
    if not elig.empty:
        best = elig.sort_values("ev", ascending=False).iloc[0]
        best_tag = f"{best['exp']} (extremo={int(best['oversold'])}/{int(best['overbought'])}, sep={int(best['min_sep'])})"
    else:
        # ninguno sobrevive FDR: reportamos el de mayor EV igual (con advertencia)
        best = grid.sort_values("ev", ascending=False).iloc[0]
        best_tag = f"{best['exp']} (extremo={int(best['oversold'])}/{int(best['overbought'])}, sep={int(best['min_sep'])}) — NO sobrevive FDR"

    grid_path = ROOT / "reports" / "EXP-041-060_grid.csv"
    grid.to_csv(grid_path, index=False)
    print("\n=== GRILLA COMPLETA (20 exp) ===")
    print(grid[["exp", "oversold", "overbought", "min_sep", "completas", "wr", "ev", "p", "p_adj_fdr", "p_adj_bonf"]].to_string(index=False))
    print(f"\n=== MEJOR POR TRIBUNAL (FDR, n>=100) ===\n{best_tag}")
    print(f"WR={best['wr']}  EV={best['ev']}  p={best['p']:.4f}  p_adj_fdr={best['p_adj_fdr']}")
    print(f"\nGuardado: {grid_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
