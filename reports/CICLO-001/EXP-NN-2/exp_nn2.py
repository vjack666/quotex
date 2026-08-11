"""EXP-NN-2 — El juez del gate: red neuronal con features del gate vs gate puro.

Pregunta: si el gate compuesto (arcoíris + válvula) codifica el edge del 74.6%,
¿una red neuronal entrenada con ESAS MISMAS features lo recupera mejor o peor?

  - Features del gate: 7 EMAs (niveles), K, D, |K-D|, posición del close vs EMAs,
    distancia del K al extremo, body/range, ticks.
  - Target: dirección ganadora a +900s (timing real broker: entry open[i+6],
    exit close[i+21]; señal al cierre).
  - Split temporal estricto 70/15/15 cronológico (sin shuffle, sin leak).
  - Baseline: WR del mercado (≈49%), breakeven 54%.
  - Métricas: WR en test (umbral 0.55), p-valor binomial vs 54%, lift sobre base.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import exp_common as ec  # noqa: E402

BREAKEVEN = 0.54
SEED = 42

GATE_FEATURES = [
    "ema5", "ema10", "ema20", "ema40", "ema80", "ema160", "ema320",
    "k", "d", "kd_sep",
    "dist_close_ema5", "dist_close_ema20", "dist_close_ema320",
    "k_extreme_dist", "body_ratio", "rng_ratio20", "ticks_ratio20", "ret1", "ret5", "ret20",
]


def build_matrix(feats, n):
    """Matriz de features del gate + targets, alineada por vela (NaN -> dropeadas)."""
    close = feats["close"]
    atr20 = np.convolve(feats["rng"], np.ones(20) / 20, mode="same")
    ticks20 = np.convolve(feats["ticks"], np.ones(20) / 20, mode="same")

    cols = {}
    for p in (5, 10, 20, 40, 80, 160, 320):
        cols[f"ema{p}"] = feats[f"ema{p}"]
    cols["k"] = feats["k"]
    cols["d"] = feats["d"]
    cols["kd_sep"] = feats["kd_sep"]
    cols["dist_close_ema5"] = (close - feats["ema5"]) / np.maximum(feats["ema5"], 1e-12)
    cols["dist_close_ema20"] = (close - feats["ema20"]) / np.maximum(feats["ema20"], 1e-12)
    cols["dist_close_ema320"] = (close - feats["ema320"]) / np.maximum(feats["ema320"], 1e-12)
    cols["k_extreme_dist"] = np.where(feats["k"] >= 50, feats["k"] - 80.0, 20.0 - feats["k"])
    cols["body_ratio"] = feats["body_ratio"]
    cols["rng_ratio20"] = feats["rng"] / np.maximum(atr20, 1e-12)
    cols["ticks_ratio20"] = feats["ticks"] / np.maximum(ticks20, 1e-12)
    cols["ret1"] = feats["ret1"]
    cols["ret5"] = feats["ret5"]
    cols["ret20"] = feats["ret20"]

    X = np.column_stack([cols[f] for f in GATE_FEATURES])
    y = np.full(n, np.nan)  # 1 = CALL gana (close[i+21] > open[i+6])
    valid = np.ones(n, dtype=bool)
    for i in range(n):
        win, *_ = ec.resolve_trade(feats, i, "CALL")
        if win is None:
            valid[i] = False
            continue
        y[i] = float(win)
        # descartar filas con features NaN (arranque de indicadores)
        if np.isnan(X[i]).any() or np.isinf(X[i]).any():
            valid[i] = False
    return X, y, valid


def pval_binom(w, n, p0=BREAKEVEN):
    if n == 0:
        return 1.0
    return float(stats.binom.sf(w - 1, n, p0))


def report(tag, dec, y):
    n = int(dec.sum())
    if n == 0:
        print(f"  {tag}: ops=0")
        return None
    w = int(y[dec].sum())
    wr = 100.0 * w / n
    p = pval_binom(w, n)
    print(f"  {tag}: ops={n:5d}  WR={wr:.1f}%  wins={w}  p_vs54={p:.4f}")
    return {"n": n, "wr": wr, "w": w, "p": p}


def main():
    df = ec.load_otc_60s()
    feats, n = ec.build_features(df)
    print(f"Velas: {n}  ({df['datetime'].iloc[0]} -> {df['datetime'].iloc[-1]})")

    X, y, valid = build_matrix(feats, n)
    idx = np.where(valid)[0]
    print(f"Velas válidas (features + target): {len(idx)}")
    if len(idx) == 0:
        print("ERROR: sin velas válidas")
        return

    # split temporal cronológico
    t_tr, t_va = int(len(idx) * 0.70), int(len(idx) * 0.85)
    i_tr, i_va, i_te = idx[:t_tr], idx[t_tr:t_va], idx[t_va:]
    Xtr, Xva, Xte = X[i_tr], X[i_va], X[i_te]
    ytr, yva, yte = y[i_tr], y[i_va], y[i_te]
    print(f"Split temporal: train={len(i_tr)} val={len(i_va)} test={len(i_te)}")
    print(f"Rango test: {df['datetime'].iloc[i_te[0]]} -> {df['datetime'].iloc[i_te[-1]]}")
    print(f"Base rate test (CALL gana): {yte.mean()*100:.2f}%  (breakeven {BREAKEVEN*100}%)")

    # ---- Modelo 1: MLP ----
    print("\n=== MLP (features del gate) ===")
    sc = StandardScaler().fit(Xtr)
    mlp = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=400, random_state=SEED,
                        early_stopping=True, n_iter_no_change=20, validation_fraction=0.1)
    mlp.fit(sc.transform(Xtr), ytr)
    prob = mlp.predict_proba(sc.transform(Xte))[:, 1]
    r_mlp = report("MLP test (umbral 0.55)", prob >= 0.55, yte)
    # curva: WR por decil de confianza
    order = np.argsort(prob)[::-1]
    print("  WR por decil de confianza (test):")
    for q in (0.10, 0.25, 0.40, 0.50):
        k = int(len(yte) * q)
        sel = order[:k]
        print(f"    top {int(q*100)}%: ops={k} WR={yte[sel].mean()*100:.1f}%  p={pval_binom(int(yte[sel].sum()), k):.4f}")

    # ---- Modelo 2: LightGBM ----
    print("\n=== LightGBM (features del gate) ===")
    lgbm = lgb.LGBMClassifier(n_estimators=500, learning_rate=0.05, num_leaves=31,
                              random_state=SEED, verbose=-1)
    lgbm.fit(Xtr, ytr, eval_set=[(Xva, yva)], eval_metric="binary_logloss")
    prob = lgbm.predict_proba(Xte)[:, 1]
    r_lgbm = report("LGBM test (umbral 0.55)", prob >= 0.55, yte)
    order = np.argsort(prob)[::-1]
    print("  WR por decil de confianza (test):")
    for q in (0.10, 0.25, 0.40, 0.50):
        k = int(len(yte) * q)
        sel = order[:k]
        print(f"    top {int(q*100)}%: ops={k} WR={yte[sel].mean()*100:.1f}%  p={pval_binom(int(yte[sel].sum()), k):.4f}")

    # feature importances
    imp = sorted(zip(GATE_FEATURES, lgbm.feature_importances_), key=lambda t: -t[1])[:8]
    print("\nTop features LGBM:")
    for name, v in imp:
        print(f"  {name}: {v}")

    # guardar
    np.savez(Path(__file__).resolve().parent / "resultados_nn2.npz",
             base_test=yte.mean(),
             mlp_n=r_mlp["n"] if r_mlp else 0, mlp_wr=r_mlp["wr"] if r_mlp else np.nan,
             mlp_p=r_mlp["p"] if r_mlp else np.nan,
             lgbm_n=r_lgbm["n"] if r_lgbm else 0, lgbm_wr=r_lgbm["wr"] if r_lgbm else np.nan,
             lgbm_p=r_lgbm["p"] if r_lgbm else np.nan)
    print("\nGuardado resultados_nn2.npz")


if __name__ == "__main__":
    main()
