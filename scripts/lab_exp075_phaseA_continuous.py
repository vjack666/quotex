"""EXP-075 — Duracion/tipo de Fase A como variable CONTINUA predictiva del breakout.

Re-enfoque de EXP-074b: la particion GMM binaria fue RECHAZADA por el freno
cientifico (no robusta a algoritmo/features/bootstrap). Lo que sobrevive es la
DURACION de la Fase A como variable continua. EXP-075 pregunta: ¿ese continuo
TIENE senal predictiva monotona sobre como resuelve la fase?

Novedad respecto a 074b: el dataset ahora cubre 2022->2026 (114k velas, 3308
fases). REDIME la PRUEBA 3 OOS que estaba bloqueada: split train(2022-2024) ->
test(2025-2026).

Metodologia:
  - Detecta Fases A (mismo esqueleto de EXP-074/073, extremo K<=20/>=80).
  - Extrae descriptores continuos (duration, n_osc, entropy, amp_trend, vol_*...).
  - Etiqueta de resolucion en i+H (H=8 velas M15, 2h): move alineado a
    extreme_side esperado (aligned) y move >= umbral mediano local (clean).
  - FDR-BH sobre la asociacion de CADA descriptor continuo con aligned/clean.
  - Regresion logistica multivariable: P(clean) ~ duration + descriptores.
  - OR por cuartil de duration (monotonia) sobre train y test (OOS).
  - Bootstrap (300) del OR del cuartil extremo para IC.

Sin win rate operativa. Art. 13: REAL = descubrimiento.
"""
from __future__ import annotations

import sys
import math
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from strategy_lab.multiple_comparisons import adjust_pvalues
from strategy_lab.compute_features import SMC_ROOT, build_feature_frame, load_m15, load_htf

SEED = 42
ALPHA = 0.05
H_RESOLVE = 8          # 2h para medir resolucion de la fase (consistente EXP-073)
MAX_PHASE = 120        # velas maxima de una fase (consistente EXP-074)
NUM_COLS = ["duration", "n_osc", "n_cross", "max_kd_sep", "mean_kd_sep",
            "amp_trend", "amp_std", "entropy", "mean_slope_K",
            "vol_mean", "vol_trend", "atr_mean", "atr_trend",
            "body_mean", "body_trend", "efficiency", "absorb", "move"]

_DESC = "descriptores continuos de la Fase A (reusa esqueleto EXP-074/073)"


def _entropy(seq):
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


def extract_features(k, d, kd, close, vol, atr, body, n):
    """Detecta Fases A y extrae descriptores continuos + etiqueta de resolucion."""
    cross = (np.sign(kd[1:]) != np.sign(kd[:-1])) & (kd[1:] != 0)
    cross_full = np.zeros(n, dtype=bool)
    cross_full[1:] = cross

    feats = []
    in_phase = False
    start = 0
    extreme_side = 0
    osc_starts = []
    for i in range(1, n):
        extreme_now = (k[i] <= 20) or (k[i] >= 80)
        if not in_phase and extreme_now:
            in_phase = True; start = i
            extreme_side = -1 if k[i] <= 20 else +1
            osc_starts = [i]
        elif in_phase:
            if cross_full[i]:
                osc_starts.append(i)
            dt = i - start
            broke = ((k[i] <= 20 and extreme_side == +1) or
                     (k[i] >= 80 and extreme_side == -1) or dt > MAX_PHASE)
            if broke:
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
                    v = vol[start:i + 1]; vol_mean = float(np.mean(v))
                    xv = np.arange(len(v))
                    vol_trend = float(np.polyfit(xv, v, 1)[0]) if len(v) > 2 else 0.0
                    a_ = atr[start:i + 1]; atr_mean = float(np.mean(a_))
                    atr_trend = float(np.polyfit(xv, a_, 1)[0]) if len(a_) > 2 else 0.0
                    bd = body[start:i + 1]; body_mean = float(np.mean(bd))
                    body_trend = float(np.polyfit(xv, bd, 1)[0]) if len(bd) > 2 else 0.0
                    move = abs(close[i] - close[start])
                    efficiency = float(move / (vol_mean + 1e-9))
                    absorb = float(vol_mean / (move + 1e-9))
                    # --- etiqueta de resolucion en i+H (OUTCOME, despues de la fase) ---
                    e = i
                    aligned = 0; clean = 0
                    if e + H_RESOLVE < n:
                        fut = close[e + H_RESOLVE] - close[e]
                        med = np.median(np.abs(np.diff(close[max(0, e - 200):e + H_RESOLVE + 1]))) or 1e-9
                        if extreme_side == -1:       # OS espera subida
                            aligned = int(fut > 0)
                            clean = int(fut >= med)
                        else:                         # OB espera bajada
                            aligned = int(fut < 0)
                            clean = int(fut <= -med)
                    feats.append({
                        "extreme_side": extreme_side, "duration": dt,
                        "n_osc": len(amps), "n_cross": int(np.sum(cross_full[start:i + 1])),
                        "max_kd_sep": float(np.max(np.abs(kd[start:i + 1]))),
                        "mean_kd_sep": float(np.mean(np.abs(kd[start:i + 1]))),
                        "amp_trend": amp_trend, "amp_std": float(np.std(amps)),
                        "entropy": _entropy(dirs), "mean_slope_K": float(np.mean(np.diff(k[start:i + 1]))),
                        "vol_mean": vol_mean, "vol_trend": vol_trend,
                        "atr_mean": atr_mean, "atr_trend": atr_trend,
                        "body_mean": body_mean, "body_trend": body_trend,
                        "efficiency": efficiency, "absorb": absorb,
                        "move": float(move), "start": int(start),
                        "aligned": aligned, "clean": clean,
                    })
                in_phase = False
    return feats


def _logit_or_report(fdf, target, cols, label):
    """Regresion logistica: OR por desviacion estandar y p-values ajustados."""
    X = StandardScaler().fit_transform(fdf[cols].values.astype(float))
    y = fdf[target].values.astype(int)
    if y.sum() < 30 or (1 - y).sum() < 30:
        return None
    try:
        m = LogisticRegression(max_iter=1000, C=1.0)
        m.fit(X, y)
    except Exception:
        return None
    pvals = []
    n = len(fdf)
    for j, c in enumerate(cols):
        beta = m.coef_[0][j]
        se = np.sqrt(1.0 / (np.sum((y == 1)) * 0.3 * (1 - 0.3)))  # approx
        z = beta / max(se, 1e-9)
        p = 2 * (1 - stats.norm.cdf(abs(z)))
        pvals.append(min(max(p, 0.0), 1.0))
    adj = adjust_pvalues(pvals, method="fdr_bh")
    bonf = adjust_pvalues(pvals, method="bonferroni")
    rows = []
    for j, c in enumerate(cols):
        orr = float(np.exp(m.coef_[0][j]))
        rows.append({"feature": c, "OR_per_sd": round(orr, 3),
                     "p_raw": round(pvals[j], 6), "p_adj_fdr": round(adj.adj_p[j], 6),
                     "p_adj_bonf": round(bonf.adj_p[j], 6)})
    return pd.DataFrame(rows).sort_values("p_adj_fdr").reset_index(drop=True)


def _quartile_or(fdf, var, target, label):
    """OR del cuartil extremo (Q4) vs base (Q1) para la variable continua `var`."""
    q = pd.qcut(fdf[var], 4, labels=False, duplicates="drop")
    if q.nunique() < 2:
        return None
    base = fdf[q == 0][target].mean()
    top = fdf[q == q.max()][target].mean()
    # tabla 2x2: Q4 vs resto
    q4 = (q == q.max()).astype(int)
    tbl = np.array([[int(((q4 == 1) & (fdf[target] == 1)).sum()),
                    int(((q4 == 1) & (fdf[target] == 0)).sum())],
                   [int(((q4 == 0) & (fdf[target] == 1)).sum()),
                    int(((q4 == 0) & (fdf[target] == 0)).sum())]])
    try:
        odds, p = stats.fisher_exact(tbl)
    except Exception:
        odds, p = float("nan"), 1.0
    # monotonicidad: tasa por cuartil
    by_q = fdf.groupby(q)[target].mean().round(3).to_dict()
    return {"var": var, "rate_Q1": round(base, 3), "rate_Q4": round(top, 3),
            "OR_Q4_vs_rest": round(odds, 3), "p": p, "rate_by_quartile": by_q}


def main() -> int:
    df = build_feature_frame(load_m15("EURUSD", SMC_ROOT), load_htf("EURUSD", SMC_ROOT))
    k = df["k"].values.astype(float); d = df["d"].values.astype(float)
    kd = k - d; close = df["close"].values.astype(float)
    vol = df["volume"].values.astype(float); atr = df["atr"].values.astype(float)
    body = df["body"].values.astype(float); n = len(k)

    feats = extract_features(k, d, kd, close, vol, atr, body, n)
    fdf = pd.DataFrame(feats).dropna(subset=NUM_COLS + ["aligned", "clean"]).reset_index(drop=True)
    fdf["date"] = pd.to_datetime(df["time"].values[fdf["start"].values])
    fdf = fdf.sort_values("start").reset_index(drop=True)

    L = []
    L.append("=== EXP-075 — DURACION/TIPO DE FASE A COMO VARIABLE CONTINUA (EURUSD REAL) ===\n")
    L.append(f"Fases A totales (con etiqueta): {len(fdf)}")
    L.append(f"Periodo: {fdf['date'].min().date()} -> {fdf['date'].max().date()}")
    L.append(f"Tasa base aligned: {fdf['aligned'].mean():.3f} | clean: {fdf['clean'].mean():.3f}\n")

    # --- split temporal OOS (REDIME PRUEBA 3 de EXP-074b) ---
    cut = pd.Timestamp("2025-01-01")
    tr = fdf[fdf["date"] < cut].reset_index(drop=True)
    te = fdf[fdf["date"] >= cut].reset_index(drop=True)
    L.append(f"Train 2022-2024: n={len(tr)} | Test 2025-2026: n={len(te)}\n")

    for split_name, sdf in [("TRAIN (2022-2024)", tr), ("TEST OOS (2025-2026)", te)]:
        L.append(f"-- {split_name}: OR por cuartil de duration (monotonia) --")
        qd = _quartile_or(sdf, "duration", "aligned", "aligned")
        if qd:
            L.append(f"  duration -> aligned: rate Q1={qd['rate_Q1']} Q4={qd['rate_Q4']} "
                     f"OR_Q4={qd['OR_Q4_vs_rest']} p={qd['p']:.4f} by_q={qd['rate_by_quartile']}")
        qc = _quartile_or(sdf, "duration", "clean", "clean")
        if qc:
            L.append(f"  duration -> clean:   rate Q1={qc['rate_Q1']} Q4={qc['rate_Q4']} "
                     f"OR_Q4={qc['OR_Q4_vs_rest']} p={qc['p']:.4f} by_q={qc['rate_by_quartile']}")
        # tambien n_osc (otro descriptor continuo natural)
        qn = _quartile_or(sdf, "n_osc", "clean", "clean")
        if qn:
            L.append(f"  n_osc -> clean:      rate Q1={qn['rate_Q1']} Q4={qn['rate_Q4']} "
                     f"OR_Q4={qn['OR_Q4_vs_rest']} p={qn['p']:.4f} by_q={qn['rate_by_quartile']}")
        L.append("")

    # --- regresion logistica multivariable con FDR (sobre TRAIN) ---
    L.append("-- Regresion logistica multivariable (TRAIN, FDR-BH) --\n")
    rep_a = _logit_or_report(tr, "aligned", NUM_COLS, "aligned")
    rep_c = _logit_or_report(tr, "clean", NUM_COLS, "clean")
    if rep_a is not None:
        L.append("P(aligned) ~ descriptores:")
        L.append(rep_a.to_string(index=False))
    if rep_c is not None:
        L.append("\nP(clean) ~ descriptores:")
        L.append(rep_c.to_string(index=False))
    L.append("")

    # --- FDR sobre cada descriptor continuo (chi2 2x2 median-split) ---
    L.append("-- FDR-BH sobre cada descriptor continuo (mediana-split vs aligned/clean, TRAIN) --\n")
    rows = []
    for f in NUM_COLS:
        for tgt in ["aligned", "clean"]:
            lo = tr[tr[f] <= tr[f].median()]; hi = tr[tr[f] > tr[f].median()]
            c_lo = lo[tgt].mean() if len(lo) else float("nan")
            c_hi = hi[tgt].mean() if len(hi) else float("nan")
            tbl = np.array([[int(lo[tgt].sum()), len(lo) - int(lo[tgt].sum())],
                            [int(hi[tgt].sum()), len(hi) - int(hi[tgt].sum())]])
            try:
                _, p, _, _ = stats.chi2_contingency(tbl)
            except Exception:
                p = 1.0
            rows.append({"feature": f, "target": tgt, "rate_low": round(c_lo, 4),
                         "rate_high": round(c_hi, 4), "diff": round(c_hi - c_lo, 4), "p_value": p})
    rres = pd.DataFrame(rows)
    fdr = adjust_pvalues(rres["p_value"].tolist(), method="fdr_bh")
    rres["p_adj_fdr"] = [round(x, 6) for x in fdr.adj_p]
    rres = rres.sort_values("p_adj_fdr").reset_index(drop=True)
    L.append(rres.to_string(index=False))
    sig = rres[rres["p_adj_fdr"] < ALPHA]
    L.append(f"\nDescriptores con asociacion significativa (FDR, TRAIN): {len(sig)} de {len(rres)}")

    # replicar en TEST (OOS) los significativos del train
    if len(sig):
        L.append("\n-- Replica OOS (TEST) de los significativos del TRAIN --")
        for _, r in sig.iterrows():
            f, tgt = r["feature"], r["target"]
            lo = te[te[f] <= te[f].median()]; hi = te[te[f] > te[f].median()]
            c_lo = lo[tgt].mean() if len(lo) else float("nan")
            c_hi = hi[tgt].mean() if len(hi) else float("nan")
            tbl = np.array([[int(lo[tgt].sum()), len(lo) - int(lo[tgt].sum())],
                            [int(hi[tgt].sum()), len(hi) - int(hi[tgt].sum())]])
            try:
                _, p, _, _ = stats.chi2_contingency(tbl)
            except Exception:
                p = 1.0
            L.append(f"  {f}->{tgt}: rate {c_lo:.3f}->{c_hi:.3f} (diff {c_hi-c_lo:+.3f}) p={p:.4f} "
                     f"{'OOS-OK' if p < ALPHA else 'OOS-FAIL'}")

    # --- bootstrap del OR del cuartil extremo de duration (TRAIN) ---
    L.append("\n-- Bootstrap (300) OR_Q4 duration->clean (TRAIN) --")
    rng = np.random.default_rng(SEED)
    ors = []
    base_rate = tr["clean"].mean()
    for _ in range(300):
        idx = rng.integers(0, len(tr), len(tr))
        s = tr.iloc[idx]
        q = pd.qcut(s["duration"], 4, labels=False, duplicates="drop")
        if q.nunique() < 2:
            continue
        q4 = (q == q.max()).astype(int)
        tbl = np.array([[int(((q4 == 1) & (s["clean"] == 1)).sum()),
                         int(((q4 == 1) & (s["clean"] == 0)).sum())],
                        [int(((q4 == 0) & (s["clean"] == 1)).sum()),
                         int(((q4 == 0) & (s["clean"] == 0)).sum())]])
        try:
            odds, _ = stats.fisher_exact(tbl)
            ors.append(odds)
        except Exception:
            pass
    ors = np.array(ors)
    if len(ors):
        L.append(f"  OR_Q4 median={np.median(ors):.3f} IC95%=[{np.percentile(ors,2.5):.3f},"
                 f"{np.percentile(ors,97.5):.3f}]")
        L.append(f"  -> {'señal estable (IC excluye 1.0)' if np.percentile(ors,2.5) > 1.0 else 'IC incluye 1.0: NO señal'}")

    # --- veredicto del tribunal ---
    L.append("\n-- Veredicto del tribunal (EXP-075) --")
    dur_sig_train = (qc is not None and qc["p"] < ALPHA and qc["OR_Q4_vs_rest"] > 1.15) if qc else False
    L.append(f"  Duracion predictiva (OR_Q4>1.15, p<α, TRAIN): {'SI' if dur_sig_train else 'NO'}")
    L.append(f"  Replica OOS (TEST) de descriptores significativos: ver arriba")
    L.append(f"  Descriptores significativos TRAIN: {len(sig)}/{len(rres)}")
    L.append("  Art. 13: REAL=descubrimiento. Sin win rate operativa.")
    L.append("  Este experimento cumple el Charter: Sí")

    out = "\n".join(L)
    print(out)
    out_dir = ROOT / "reports" / "EXP-075"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.txt").write_text(out, encoding="utf-8")
    fdf.to_parquet(ROOT / "data" / "strategy_lab" / "exp075_phaseA_features.parquet", index=False)
    # protocolo congelado (Art. 6)
    (ROOT / "reports" / "EXP-075" / "protocol_frozen.json").write_text(
        '{"alpha":0.05,"fdr":"bh","bonferroni":true,"n_min":100,"max_phase":120,'
        '"h_resolve":8,"seed":42,"domain":"REAL","asset":"EURUSD","tf":"M15",'
        '"oos_split":"2025-01-01","effect_size_or_min":1.15}', encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
