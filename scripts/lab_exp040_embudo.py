"""EXP-040 — embudo del Edificio sobre EURUSD REAL, vía laboratorio.

Toma los eventos del motor de secuencia libre (ya corrido y persistido en
data/strategy_lab/exp040_events_eurusd.parquet) y los evalúa con el tribunal
del lab (run_experiment) para obtener un veredicto inmutable y reproducible
(Art. 5/6 Charter).

Uso:
    python scripts/lab_exp040_embudo.py
Genera reports/EXP-040/ con seed.txt, environment.txt, dataset_hash.txt,
protocol_frozen.json, lifecycle.json, summary.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd

PAYOUT = 0.85  # asuncion de costo operacional (Quotex tipico)


def main() -> int:
    from strategy_lab.experiment_runner import run_experiment

    events_path = ROOT / "data" / "strategy_lab" / "exp040_events_eurusd.parquet"
    if not events_path.exists():
        print(f"[EXP-040] ERROR: falta {events_path}. Corre primero el motor de secuencia libre.", file=sys.stderr)
        return 2

    ev = pd.read_parquet(events_path)

    # Construir columnas que el runner del lab espera.
    # Solo expedientes COMPLETOS entran al analisis de promocion (tienen win real).
    ev = ev[ev["win"] >= 0].copy()
    ev["timestamp"] = pd.to_datetime(ev["birth_time"], errors="coerce")
    # profit binario neto: win=1 -> +payout-1 ; win=0 -> -1
    ev["profit"] = ev["win"].apply(lambda w: (PAYOUT - 1.0) if w == 1 else -1.0)
    ev["expected_value"] = ev["profit"]  # por evento, el runner agrega

    protocol = {
        "domain": "REAL",
        "alpha": 0.05,
        "fdr_method": "fdr_bh",
        "poder_min": 0.80,
        "n_min": 100,
        "baseline_wr": 0.50,
        "payout": PAYOUT,
        "seed": 42,
        "hypothesis": "specs/lab_protocolo_cientifico/hypothesis_exp040.md",
        "note": "EXP-040: embudo Edificio sobre EURUSD REAL. Busca firma de secuencia con edge neto positivo.",
    }

    artifacts = run_experiment(
        "EXP-040",
        ev,
        seed=42,
        dataset_manifest=str(ROOT / "datasets" / "dataset_v001" / "manifest.json"),
        protocol=protocol,
        report_dir=ROOT / "reports",
    )

    print(f"[EXP-040] verdict={artifacts.gate_decision.verdict if artifacts.gate_decision else 'n/a'}")
    print(f"[EXP-040] report={artifacts.report_path}")
    print(f"[EXP-040] seed={artifacts.seed} dataset_hash={artifacts.dataset_hash}")

    # --- Analisis por firma con FDR (Art. 9): el embudo se salva por secuencia ---
    from strategy_lab.multiple_comparisons import adjust_pvalues
    import numpy as np

    rep_dir = Path(artifacts.report_path).parent
    rows = []
    for firma, sub in ev.groupby("firma"):
        n = len(sub)
        if n < 100:  # n minimo congelado (Art. 6)
            continue
        wins = int(sub["win"].sum())
        wr = wins / n
        # p de binomial vs baseline 0.50
        from scipy import stats
        p = stats.binomtest(wins, n, 0.50).pvalue
        # effect size: lift sobre baseline (Odds Ratio simplificado = wr/(1-wr) / (0.5/0.5))
        odds = (wr / (1 - wr)) / 1.0 if 0 < wr < 1 else (np.inf if wr >= 1 else 0.0)
        # expected value neto con payout
        ev_net = wr * (PAYOUT - 1.0) + (1 - wr) * (-1.0)
        rows.append({
            "firma": firma, "n": n, "wins": wins, "wr": round(wr, 4),
            "p_value": p, "odds_ratio": round(float(odds), 3),
            "expected_value": round(float(ev_net), 4),
        })
    fdf = pd.DataFrame(rows)
    if not fdf.empty:
        res = adjust_pvalues(fdf["p_value"].tolist(), method="fdr_bh")
        fdf["p_adj_fdr"] = [round(x, 6) for x in res.adj_p]
        # promovibles: p_adj < alpha Y ev_net > 0 Y n>=100
        fdf["promovible"] = (fdf["p_adj_fdr"] < protocol["alpha"]) & (fdf["expected_value"] > 0)
        fdf = fdf.sort_values("expected_value", ascending=False)
        fdf.to_csv(rep_dir / "firma_analysis.csv", index=False)
        print("\n[EXP-040] === FIRMAS (FDR ajustado, n>=100) ===")
        print(fdf.round(4).to_string(index=False))
        n_prom = int(fdf["promovible"].sum())
        print(f"\n[EXP-040] firmas promovibles (edge neto + FDR + n>=100): {n_prom}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
