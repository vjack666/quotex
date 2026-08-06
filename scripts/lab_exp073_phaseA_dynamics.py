"""EXP-073 — Dinamica de la Fase A (energia, no eventos).

Dictamen Trader-Humano 2026-08-06: tres experimentos (070/071/072) convergen en
"ningun confirmador tiene edge". Eso no es falta de poder estadistico: es la
pregunta equivocada. Wyckoff no pregunta "que viene despues?", sino "quien tiene
el control?" — ENERGIA/DINAMICA, no posicion. El estocastico describe posicion;
no mide quien absorbe, empuja o se agota.

EXP-073 NO opera la reversion. Estudia la DINAMICA de la Fase A para responder:
  "¿Que cambia justo antes de que termine una acumulacion/distribucion?"
Es decir: que variable dinamica separa las fases que RESUELVEN (clean breakout)
de las que se desinflan (fizzle).

Salida = tabla de dinamica x asociacion con resolucion, NO win rate.
Dominio REAL (EURUSD). Art. 13 Charter: solo descubrimiento.
"""
from __future__ import annotations

import sys
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
from scipy import stats
from strategy_lab.multiple_comparisons import adjust_pvalues
from strategy_lab.compute_features import SMC_ROOT, build_feature_frame, load_m15, load_htf

SEED = 42
ALPHA = 0.05
H_RESOLVE = 8          # 2h para medir resolucion de la fase
MAX_PHASE = 120        # velas maxima de una fase (safe cap)


def _shannon_entropy(seq):
    """Entropia de la secuencia de direcciones {-1,0,+1} (normalizada 0..1).
    Alternancia perfecta -> baja; agrupada/caotica -> alta."""
    vals = [int(s) for s in seq if s != 0]
    if len(vals) < 2:
        return 0.0
    counts = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    n = len(vals)
    H = 0.0
    for c in counts.values():
        p = c / n
        H -= p * math.log2(p)
    return H / math.log2(len(counts)) if len(counts) > 1 else 0.0


def extract_phases(k, d, kd, close, n):
    """Detecta Fases A y extrae dinamica por oscilacion + resolucion."""
    # cruces de K-D (inicio de cada oscilacion)
    cross = (np.sign(kd[1:]) != np.sign(kd[:-1])) & (kd[1:] != 0)
    cross_full = np.zeros(n, dtype=bool)
    cross_full[1:] = cross

    phases = []
    in_phase = False
    start = None
    extreme_side = None
    osc_starts = []
    for i in range(1, n):
        extreme_now = (k[i] <= 20) or (k[i] >= 80)
        if not in_phase and extreme_now:
            in_phase = True; start = i
            extreme_side = -1 if k[i] <= 20 else +1  # OS->espera up, OB->espera down
            osc_starts = [i]
        elif in_phase:
            if cross_full[i]:
                osc_starts.append(i)
            dt = i - start
            broke = ((k[i] <= 20 and extreme_side == +1) or
                     (k[i] >= 80 and extreme_side == -1) or dt > MAX_PHASE)
            if broke:
                # cerrar fase: oscilaciones = segmentos entre osc_starts
                segs = osc_starts + [i]
                amps, durs, dirs = [], [], []
                for s in range(len(segs) - 1):
                    a, b = segs[s], segs[s + 1]
                    if b <= a:
                        continue
                    amps.append(float(np.max(np.abs(kd[a:b + 1]))))
                    durs.append(b - a)
                    dirs.append(int(np.sign(k[b] - k[a])))
                if len(amps) >= 2:
                    xs = np.arange(len(amps))
                    amp_trend = float(np.polyfit(xs, amps, 1)[0]) if len(amps) > 2 else 0.0
                    dur_trend = float(np.polyfit(xs, durs, 1)[0]) if len(durs) > 2 else 0.0
                    ent = _shannon_entropy(dirs)
                    # resolucion: movimiento de precio en H velas tras el cierre
                    e = i
                    if e + H_RESOLVE < n:
                        move = close[e + H_RESOLVE] - close[e]
                        med = np.median(np.abs(np.diff(close[max(0, e - 200):e + H_RESOLVE + 1]))) or 1e-9
                        thr = med
                        if extreme_side == -1:      # OS -> espera subida
                            clean = (move >= thr)
                            fake = (move <= -thr)
                        else:                        # OB -> espera bajada
                            clean = (move <= -thr)
                            fake = (move >= thr)
                        phases.append({
                            "extreme_side": extreme_side, "n_osc": len(amps),
                            "amp_trend": amp_trend, "amp_std": float(np.std(amps)),
                            "dur_trend": dur_trend, "entropy": ent,
                            "mean_slope_K": float(np.mean(np.diff(k[start:i + 1]))),
                            "max_kd_sep": float(np.max(np.abs(kd[start:i + 1]))),
                            "time_to_break": dt, "clean": int(clean), "fake": int(fake),
                            "amp_seq": ",".join(f"{a:.1f}" for a in amps[:8]),
                        })
                in_phase = False
    return phases


def main() -> int:
    df = build_feature_frame(load_m15("EURUSD", SMC_ROOT), load_htf("EURUSD", SMC_ROOT))
    k = df["k"].values.astype(float)
    d = df["d"].values.astype(float)
    kd = k - d
    close = df["close"].values.astype(float)
    n = len(k)

    phases = extract_phases(k, d, kd, close, n)
    pdf = pd.DataFrame(phases)
    pdf.to_parquet(ROOT / "data" / "strategy_lab" / "exp073_phaseA_dynamics.parquet", index=False)

    n_clean = int(pdf["clean"].sum())
    base_rate = n_clean / len(pdf)
    print("=== EXP-073 — DINAMICA DE LA FASE A (EURUSD REAL, descubrimiento) ===\n")
    print(f"Fases A analizadas: {len(pdf)} | tasa base clean breakout: {base_rate:.3f}")
    print("\nMedias de variables dinamicas:")
    print(pdf[["n_osc", "amp_trend", "amp_std", "dur_trend", "entropy",
               "mean_slope_K", "max_kd_sep", "time_to_break"]].median().round(3).to_string())

    # DESCUBRIMIENTO: que feature dinamica separa clean de no-clean?
    feats = ["n_osc", "amp_trend", "amp_std", "dur_trend", "entropy",
             "mean_slope_K", "max_kd_sep", "time_to_break"]
    rows = []
    for f in feats:
        lo = pdf[pdf[f] <= pdf[f].median()]
        hi = pdf[pdf[f] > pdf[f].median()]
        c_lo = lo["clean"].mean() if len(lo) else float("nan")
        c_hi = hi["clean"].mean() if len(hi) else float("nan")
        # chi-cuadrado 2x2 (clean vs grupo)
        tbl = np.array([[int(lo["clean"].sum()), len(lo) - int(lo["clean"].sum())],
                        [int(hi["clean"].sum()), len(hi) - int(hi["clean"].sum())]])
        try:
            chi2, p, _, _ = stats.chi2_contingency(tbl)
        except Exception:
            p = 1.0
        rows.append({"feature": f, "clean_rate_low": round(c_lo, 4),
                     "clean_rate_high": round(c_hi, 4),
                     "diff": round(c_hi - c_lo, 4), "p_value": p})
    res = pd.DataFrame(rows)
    if not res.empty:
        fdr = adjust_pvalues(res["p_value"].tolist(), method="fdr_bh")
        res["p_adj_fdr"] = [round(x, 6) for x in fdr.adj_p]
        res = res.sort_values("diff", key=lambda s: s.abs(), ascending=False)
        res.to_csv(ROOT / "reports" / "EXP-073_dynamics_resolution.csv", index=False)
        print("\n-- Dinamica vs RESOLUCION de la fase (FDR sobre features) --")
        print(res.to_string(index=False))
        sig = res[res["p_adj_fdr"] < ALPHA]
        print(f"\nFeatures con asociacion significativa (FDR): {len(sig)}")
        if len(sig):
            print("La firma de 'lo que rompe el equilibrio' es:")
            for _, r in sig.iterrows():
                print(f"  {r['feature']}: clean {r['clean_rate_low']:.2f}->{r['clean_rate_high']:.2f} "
                      f"(diff {r['diff']:+.2f}, p_adj={r['p_adj_fdr']})")
    print("\nVeredicto: dinamica (no eventos). REAL=descubrimiento, Art.13.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
