"""Serie PIPELINE (EXP-061..EXP-070) — construye la estrategia como SECUENCIA.

Diferencia con la grilla 5x4: aqui cada experimento NO varia umbrales de
eventos sueltos. Define un PIPELINE (orden requerido de eventos) y lo trata
como una estrategia completa:
  - nace con el PRIMER evento del pipeline,
  - exige los siguientes EN ESE ORDEN (ignora fuera de orden, no invalida),
  - al completar el orden, ENTRA en la vela siguiente,
  - win = vela M15 de expiracion (1 vela) despues de la entrada.

Fase 1 (ablacion hacia adelante): pipelines crecientes desde [freno].
Fase 2 (gramatica): las top firmas de EXP-040 como orden exacto.

Dominio REAL (EURUSD M15), payout 0.85, seed 42, reporte inmutable por EXP.
FDR/Bonferroni al final sobre los 10 p-values (Art. 9).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
from scipy import stats
from strategy_lab.multiple_comparisons import adjust_pvalues
from strategy_lab import secuencia_libre as SL
from strategy_lab.compute_features import SMC_ROOT, build_feature_frame, load_m15, load_htf

PAYOUT = 0.85
SEED = 42
ALPHA = 0.05
N_MIN = 100
EXPIRY = 1  # 1 vela M15


def _build_df(asset: str = "EURUSD") -> pd.DataFrame:
    df = build_feature_frame(load_m15(asset, SMC_ROOT), load_htf(asset, SMC_ROOT))
    return df


def _detect_at(i, direction, k, d, kd_dist, hammer, inv_hammer, brake_transition):
    return SL._detect_events_at(i, direction, k, d, kd_dist, hammer, inv_hammer, brake_transition)


def run_pipeline(pipeline: list[str], df: pd.DataFrame) -> dict:
    """Corre UN pipeline como estrategia. Devuelve metricas."""
    o = df["open"].values.astype(float)
    c = df["close"].values.astype(float)
    k = df["k"].values.astype(float)
    d = df["d"].values.astype(float)
    kd_dist = df["kd_dist"].values.astype(float)
    hammer = np.asarray(df["hammer_15m"].values)
    inv_hammer = np.asarray(df["hammer_inv_15m"].values)
    brake = df["brake_transition"].values.astype(bool)
    impulse = df["impulse_net"].values.astype(float)
    times = df["time"].values
    n = len(c)

    first_ev = pipeline[0]
    nacidos = 0
    entries = 0
    wins = 0
    entry_idxs: list[int] = []

    for i in range(20, n - EXPIRY - 1):
        # detectar eventos en esta vela para ambas direcciones
        ev_call = _detect_at(i, "CALL", k, d, kd_dist, hammer, inv_hammer, brake)
        ev_put = _detect_at(i, "PUT", k, d, kd_dist, hammer, inv_hammer, brake)
        # nacimiento: el PRIMER evento del pipeline aparece
        born = None
        direction = None
        if first_ev in ev_call:
            born = "CALL"
        elif first_ev in ev_put:
            born = "PUT"
        if born is None:
            continue
        direction = born
        ev_dir = ev_call if direction == "CALL" else ev_put
        # verificar que el primer evento efectivamente esta
        if pipeline[0] not in ev_dir:
            continue
        nacidos += 1
        seen = 1
        completed_at = None
        # pipeline de 1 evento: completa en el nacimiento
        if len(pipeline) == 1:
            completed_at = i
        else:
            # avanzar desde i+1 buscando el resto en orden
            for j in range(i + 1, n - EXPIRY - 1):
                ej_call = _detect_at(j, "CALL", k, d, kd_dist, hammer, inv_hammer, brake)
                ej_put = _detect_at(j, "PUT", k, d, kd_dist, hammer, inv_hammer, brake)
                ej = ej_call if direction == "CALL" else ej_put
                need = pipeline[seen]
                if need in ej:
                    seen += 1
                    if seen == len(pipeline):
                        completed_at = j
                        break
                # invalidacion estructural: zona muerta
                if SL._zona_muerta(k[j], d[j]):
                    break
                if j - i > SL.MAX_LIFE_CANDLES:
                    break
        if completed_at is not None:
            entry = completed_at + 1
            if entry + EXPIRY - 1 < n:
                entries += 1
                entry_idxs.append(entry)
                verde = c[entry + EXPIRY - 1] > o[entry]
                w = int(verde if direction == "CALL" else (not verde))
                wins += w

    wr = (wins / entries) if entries else float("nan")
    ev_net = wr * (PAYOUT - 1.0) + (1 - wr) * (-1.0) if entries else float("nan")
    p = stats.binomtest(wins, entries, 0.50).pvalue if entries else 1.0
    return {
        "pipeline": ">".join(pipeline), "nacidos": nacidos, "entradas": entries,
        "wins": wins, "wr": round(wr, 4), "ev": round(float(ev_net), 4), "p": p,
    }


def main() -> int:
    from strategy_lab.experiment_runner import run_experiment

    df = _build_df("EURUSD")
    # (exp_id, pipeline)
    plans = [
        ("EXP-061", ["freno"]),
        ("EXP-062", ["freno", "extremo"]),
        ("EXP-063", ["freno", "extremo", "cruce"]),
        ("EXP-064", ["freno", "extremo", "cruce", "separacion"]),
        ("EXP-065", ["freno", "extremo", "cruce", "separacion", "martillo"]),
        # Fase 2: firmas top de EXP-040 como orden exacto
        ("EXP-066", ["extremo", "freno", "separacion", "martillo", "cruce"]),
        ("EXP-067", ["freno", "separacion", "extremo", "martillo", "cruce"]),
        ("EXP-068", ["extremo", "freno", "martillo", "cruce"]),
        ("EXP-069", ["extremo", "freno", "cruce", "martillo"]),
        ("EXP-070", ["freno", "separacion", "extremo", "cruce", "martillo"]),
    ]

    rows = []
    for exp_id, pl in plans:
        m = run_pipeline(pl, df)
        m["exp"] = exp_id
        rows.append(m)
        # reporte inmutable: construir events-like df para el runner
        ev = pd.DataFrame([{
            "win": 1 if k < (m["wins"]) else 0,  # placeholder; runner usa win global
        }] ) if False else pd.DataFrame({"win": [1] * m["wins"] + [0] * (m["entradas"] - m["wins"])})
        ev["timestamp"] = pd.Timestamp.now()
        ev["profit"] = ev["win"].apply(lambda w: (PAYOUT - 1.0) if w == 1 else -1.0)
        ev["expected_value"] = ev["profit"]
        protocol = {
            "domain": "REAL", "alpha": ALPHA, "fdr_method": "fdr_bh",
            "poder_min": 0.80, "n_min": N_MIN, "baseline_wr": 0.50,
            "payout": PAYOUT, "seed": SEED, "pipeline": ">".join(pl),
            "series": "PIPELINE (secuencia como estrategia)",
            "hypothesis": "specs/lab_protocolo_cientifico/hypothesis_exp061_070.md",
        }
        try:
            art = run_experiment(
                exp_id, ev, seed=SEED,
                dataset_manifest=str(ROOT / "datasets" / "dataset_v001" / "manifest.json"),
                protocol=protocol, report_dir=ROOT / "reports",
            )
            m["report"] = str(art.report_path)
        except Exception as exc:
            m["report"] = f"ERROR: {exc}"
        print(f"[{exp_id}] {m['pipeline']:55s} nac={m['nacidos']:6d} ent={m['entradas']:5d} "
              f"WR={m['wr']} EV={m['ev']} p={m['p']:.4f}")

    grid = pd.DataFrame(rows)
    fdr = adjust_pvalues(grid["p"].tolist(), method="fdr_bh")
    grid["p_adj_fdr"] = [round(x, 6) for x in fdr.adj_p]
    bonf = adjust_pvalues(grid["p"].tolist(), method="bonferroni")
    grid["p_adj_bonf"] = [round(x, 6) for x in bonf.adj_p]

    grid_path = ROOT / "reports" / "EXP-061-070_pipeline.csv"
    grid.to_csv(grid_path, index=False)
    print("\n=== SERIE PIPELINE (10 exp) ===")
    print(grid[["exp", "pipeline", "nacidos", "entradas", "wr", "ev", "p", "p_adj_fdr"]].to_string(index=False))
    elig = grid[(grid["p_adj_fdr"] < ALPHA) & (grid["entradas"] >= N_MIN)]
    if not elig.empty:
        best = elig.sort_values("ev", ascending=False).iloc[0]
        tag = f"{best['exp']} ({best['pipeline']})"
    else:
        best = grid.sort_values("ev", ascending=False).iloc[0]
        tag = f"{best['exp']} ({best['pipeline']}) -- NO sobrevive FDR"
    print(f"\n=== MEJOR PIPELINE POR TRIBUNAL (FDR, n>=100) ===\n{tag}")
    print(f"WR={best['wr']} EV={best['ev']} p={best['p']:.4f} p_adj_fdr={best['p_adj_fdr']}")
    print(f"\nGuardado: {grid_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
