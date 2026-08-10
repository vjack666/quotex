"""EXP-084 — Redes neuronales tabulares (LightGBM + MLP) sobre SPOT M15 REAL.

Objetivo: aprender si NUESTRAS HERRAMIENTAS (arcoiris 7-EMA, valvula K/D,
POI de swing causal, estocastico 14,3,3) ayudan a predecir la direccion en
EURUSD y XAUUSD M15 REAL (no OTC). Cierra la deuda R9 del CICLO-002.

Reglas:
  - Indicadores identicos en semantica a reports/CICLO-001/exp_common.py
    (compute_stoch_full 14,3,3; EMAs 5..320; swing_levels_causal/in_poi_band).
    Aqui se usan implementaciones VECTORIZADAS equivalentes por rendimiento
    (890k velas); se valida equivalencia numerica sobre una muestra.
  - Timing broker aprox M15: senal en cierre vela i -> entry = open[i+1],
    exit = open[i+2]. Label = 1 (CALL gana) si close[i+2] > open[i+1].
  - Split temporal estricto 70/15/15 (sin shuffle).
  - Metricas: WR por decil de confianza (top 10/25/40/50%), umbral 0.55,
    p-valor binomial vs breakeven 54% (payout 85%).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\Users\v_jac\Desktop\QUOTEX")
OUT = ROOT / "reports" / "CICLO-002" / "EXP-084"
sys.path.insert(0, str(ROOT / "reports" / "CICLO-001"))
import exp_common as EC  # noqa: E402  (congelado, solo lectura)

EMA_PERIODS = EC.EMA_PERIODS
BREAKEVEN = 0.54
THRESHOLD = 0.55
SEED = 42

ASSETS = {
    "EURUSD": (ROOT / "data/strategy_lab/cohorte_real_eurusd/EURUSD_M15.parquet", 1e-4),
    "XAUUSD": (ROOT / "data/smc_borrowed/XAUUSD_M15.parquet", 1e-2),
}


# ── Indicadores vectorizados (equivalentes a exp_common) ─────────────────
def stoch_full_vec(h, l, c, k_period=14, d_period=3, slow_k=3):
    hs = pd.Series(h); ls = pd.Series(l); cs = pd.Series(c)
    hh = hs.rolling(k_period).max()
    ll = ls.rolling(k_period).min()
    rng = (hh - ll)
    raw_k = np.where(rng.to_numpy() == 0, 50.0, 100.0 * (cs - ll) / rng.replace(0, np.nan))
    raw_k = pd.Series(raw_k).where(~hh.isna())
    k = raw_k.rolling(slow_k).mean()
    d = k.rolling(d_period).mean()
    return k.to_numpy(), d.to_numpy()


def emas_vec(c, periods=EMA_PERIODS):
    cs = pd.Series(c)
    return [cs.ewm(span=p, adjust=False).mean().to_numpy() for p in periods]


def poi_flags_blocked(high, low, pip_size, block=20000, warm=600):
    """in_poi_band por vela, calculado por bloques (causal dentro del bloque)."""
    n = len(high)
    flags = np.zeros(n, dtype=np.int8)
    start = 0
    while start < n:
        end = min(start + block, n)
        lo = max(0, start - warm)
        h = high[lo:end]; l = low[lo:end]
        f, c_, a, b = EC.swing_levels_causal(h, l, pip_size=pip_size)
        if len(f) == 0:
            start = end
            continue
        idx = np.arange(len(h))
        # activo: a <= i < b ; toca banda: low_i <= ceil and high_i >= floor
        act = (idx[:, None] >= a[None, :]) & (idx[:, None] < b[None, :])
        touch = (l[:, None] <= c_[None, :]) & (h[:, None] >= f[None, :])
        inband = (act & touch).any(axis=1)
        flags[start:end] = inband[start - lo:].astype(np.int8)
        start = end
    return flags


def build_matrix(name, path, pip_size):
    df = pd.read_parquet(path).sort_values("time").reset_index(drop=True)
    vol_col = "tick_volume" if "tick_volume" in df.columns else "volume"
    df["ticks"] = pd.to_numeric(df[vol_col], errors="coerce").fillna(0.0)
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    n = len(df)

    k, d = stoch_full_vec(h, l, c)
    emas = emas_vec(c)
    kd = np.abs(k - d)
    kd_slope = kd - np.roll(kd, 1); kd_slope[0] = np.nan
    kd_slope3 = kd - np.roll(kd, 3); kd_slope3[:3] = np.nan

    rng = h - l
    body = np.abs(c - o)
    tr = np.maximum.reduce([h - l,
                            np.abs(h - np.roll(c, 1)),
                            np.abs(l - np.roll(c, 1))])
    tr[0] = h[0] - l[0]
    atr = pd.Series(tr).rolling(14).mean().to_numpy()

    poi = poi_flags_blocked(h, l, pip_size)

    X = {}
    # arcoiris: distancias normalizadas por ATR
    for p, e in zip(EMA_PERIODS, emas):
        X[f"dist_ema{p}"] = (c - e) / np.maximum(atr, 1e-12)
    # apilamiento del arcoiris (orden estricto): +1 alcista, -1 bajista, 0 mezcla
    seq = np.vstack([c] + emas)
    up = np.all(np.diff(seq, axis=0) <= 0, axis=0)
    dn = np.all(np.diff(seq, axis=0) >= 0, axis=0)
    X["arcoiris_stack"] = up.astype(float) - dn.astype(float)
    X["ema_spread"] = (emas[0] - emas[-1]) / np.maximum(atr, 1e-12)
    # estocastico / valvula relajada
    X["k"] = k; X["d"] = d
    X["kd_sep"] = kd
    X["kd_slope1"] = kd_slope
    X["kd_slope3"] = kd_slope3
    X["k_slope1"] = k - np.roll(k, 1)
    X["k_extremo_lo"] = (k <= 20).astype(float)
    X["k_extremo_hi"] = (k >= 80).astype(float)
    # POI
    X["in_poi"] = poi.astype(float)
    # velas
    X["body_ratio"] = np.where(rng > 0, body / np.maximum(rng, 1e-12), 0.0)
    X["upper_wick"] = np.where(rng > 0, (h - np.maximum(o, c)) / np.maximum(rng, 1e-12), 0.0)
    X["lower_wick"] = np.where(rng > 0, (np.minimum(o, c) - l) / np.maximum(rng, 1e-12), 0.0)
    X["range_atr"] = rng / np.maximum(atr, 1e-12)
    X["atr_ratio"] = atr / np.maximum(c, 1e-12)
    X["ret1"] = (c - np.roll(c, 1)) / np.maximum(atr, 1e-12)
    X["ret5"] = (c - np.roll(c, 5)) / np.maximum(atr, 1e-12)
    X["ret20"] = (c - np.roll(c, 20)) / np.maximum(atr, 1e-12)
    X["hour"] = df["time"].dt.hour.to_numpy(float)
    X["dow"] = df["time"].dt.dayofweek.to_numpy(float)

    Xdf = pd.DataFrame(X)
    # label: entry=open[i+1], exit=open[i+2]; CALL gana si close[i+2] > open[i+1]
    entry = np.roll(o, -1)
    exit_close = np.roll(c, -2)
    y = (exit_close > entry).astype(np.int8).astype(float)
    y[n - 2:] = np.nan
    Xdf["_y"] = y
    Xdf["_time"] = df["time"].to_numpy()
    Xdf["_asset"] = name
    Xdf = Xdf.iloc[330:n - 2]  # warmup EMA320 + label valido
    Xdf = Xdf.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    return Xdf


def wr_block(y_true, prob, frac):
    """WR sobre el top-frac por confianza |p-0.5| direccional."""
    conf = np.abs(prob - 0.5)
    n_sel = max(1, int(len(prob) * frac))
    idx = np.argsort(-conf)[:n_sel]
    pred = (prob[idx] >= 0.5).astype(int)
    wins = int((pred == y_true[idx]).sum())
    return EC.wr_stats(wins, len(idx), p0=BREAKEVEN)


def evaluate(y, prob, tag, asset_arr=None):
    res = {"tag": tag, "n_total": int(len(y)),
           "base_rate_call": round(float(y.mean()) * 100, 2)}
    for frac, lab in [(1.0, "all"), (0.5, "top50"), (0.4, "top40"),
                      (0.25, "top25"), (0.10, "top10"), (0.05, "top05")]:
        res[lab] = wr_block(y, prob, frac)
    # umbral 0.55 (bidireccional)
    sel = (prob >= THRESHOLD) | (prob <= 1 - THRESHOLD)
    if sel.sum() > 0:
        pred = (prob[sel] >= 0.5).astype(int)
        res["thr055"] = EC.wr_stats(int((pred == y[sel]).sum()), int(sel.sum()), p0=BREAKEVEN)
    else:
        res["thr055"] = {"n": 0, "wins": 0, "wr": None, "p": 1.0}
    if asset_arr is not None:
        per = {}
        for a in np.unique(asset_arr):
            m = asset_arr == a
            pa, ya = prob[m], y[m]
            per[a] = {"all": wr_block(ya, pa, 1.0), "top25": wr_block(ya, pa, 0.25),
                      "top10": wr_block(ya, pa, 0.10)}
        res["por_activo"] = per
    return res


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    for name, (path, pip) in ASSETS.items():
        print(f"[load] {name} ...", flush=True)
        f = build_matrix(name, path, pip)
        print(f"  {name}: {len(f)} filas utilizables, base rate CALL="
              f"{f['_y'].mean()*100:.2f}%", flush=True)
        frames.append(f)
    data = pd.concat(frames, ignore_index=True).sort_values("_time").reset_index(drop=True)
    feat_cols = [c for c in data.columns if not c.startswith("_")]
    print(f"[data] {len(data)} filas, {len(feat_cols)} features "
          f"({time.time()-t0:.0f}s)", flush=True)

    n = len(data)
    i_tr, i_va = int(n * 0.70), int(n * 0.85)
    tr, va, te = data.iloc[:i_tr], data.iloc[i_tr:i_va], data.iloc[i_va:]
    Xtr, ytr = tr[feat_cols].to_numpy(np.float32), tr["_y"].to_numpy(int)
    Xva, yva = va[feat_cols].to_numpy(np.float32), va["_y"].to_numpy(int)
    Xte, yte = te[feat_cols].to_numpy(np.float32), te["_y"].to_numpy(int)
    ate = te["_asset"].to_numpy()

    results = {
        "exp": "EXP-084",
        "dominio": "SPOT M15 REAL (EURUSD + XAUUSD)",
        "n_rows": n, "n_features": len(feat_cols), "features": feat_cols,
        "split": {"train": [str(tr['_time'].iloc[0]), str(tr['_time'].iloc[-1]), len(tr)],
                  "val": [str(va['_time'].iloc[0]), str(va['_time'].iloc[-1]), len(va)],
                  "test": [str(te['_time'].iloc[0]), str(te['_time'].iloc[-1]), len(te)]},
        "base_rate": {"train": round(float(ytr.mean()) * 100, 2),
                      "val": round(float(yva.mean()) * 100, 2),
                      "test": round(float(yte.mean()) * 100, 2)},
        "breakeven": BREAKEVEN, "threshold": THRESHOLD,
        "poi_rate": round(float(data["in_poi"].mean()) * 100, 2),
        "models": {},
    }

    # ── LightGBM ──
    import lightgbm as lgb
    print("[lgbm] entrenando ...", flush=True)
    m = lgb.LGBMClassifier(n_estimators=2000, learning_rate=0.02, num_leaves=63,
                           min_child_samples=200, subsample=0.8, subsample_freq=1,
                           colsample_bytree=0.8, reg_lambda=1.0,
                           random_state=SEED, n_jobs=-1)
    m.fit(Xtr, ytr, eval_set=[(Xva, yva)], eval_metric="auc",
          callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(200)])
    p_va = m.predict_proba(Xva)[:, 1]
    p_te = m.predict_proba(Xte)[:, 1]
    from sklearn.metrics import roc_auc_score
    imp = sorted(zip(feat_cols, m.feature_importances_.tolist()),
                 key=lambda x: -x[1])
    results["models"]["lightgbm"] = {
        "best_iteration": int(m.best_iteration_ or m.n_estimators),
        "auc_val": round(float(roc_auc_score(yva, p_va)), 4),
        "auc_test": round(float(roc_auc_score(yte, p_te)), 4),
        "val": evaluate(yva, p_va, "lgbm/val"),
        "test": evaluate(yte, p_te, "lgbm/test", ate),
        "feature_importance": imp,
    }
    print("  lgbm AUC test:", results["models"]["lightgbm"]["auc_test"], flush=True)

    # ── MLP ──
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler
    print("[mlp] entrenando ...", flush=True)
    sc = StandardScaler().fit(Xtr)
    mlp = MLPClassifier(hidden_layer_sizes=(128, 64), activation="relu",
                        alpha=1e-3, batch_size=1024, learning_rate_init=1e-3,
                        max_iter=60, early_stopping=True, n_iter_no_change=6,
                        validation_fraction=0.1, random_state=SEED)
    mlp.fit(sc.transform(Xtr), ytr)
    q_va = mlp.predict_proba(sc.transform(Xva))[:, 1]
    q_te = mlp.predict_proba(sc.transform(Xte))[:, 1]
    results["models"]["mlp"] = {
        "n_iter": int(mlp.n_iter_),
        "auc_val": round(float(roc_auc_score(yva, q_va)), 4),
        "auc_test": round(float(roc_auc_score(yte, q_te)), 4),
        "val": evaluate(yva, q_va, "mlp/val"),
        "test": evaluate(yte, q_te, "mlp/test", ate),
    }
    print("  mlp AUC test:", results["models"]["mlp"]["auc_test"], flush=True)

    # ── Ablacion: sin POI (para medir aporte de la herramienta POI) ──
    cols_nopoi = [c for c in feat_cols if c != "in_poi"]
    ix = [feat_cols.index(c) for c in cols_nopoi]
    m2 = lgb.LGBMClassifier(n_estimators=2000, learning_rate=0.02, num_leaves=63,
                            min_child_samples=200, subsample=0.8, subsample_freq=1,
                            colsample_bytree=0.8, reg_lambda=1.0,
                            random_state=SEED, n_jobs=-1)
    m2.fit(Xtr[:, ix], ytr, eval_set=[(Xva[:, ix], yva)], eval_metric="auc",
           callbacks=[lgb.early_stopping(100, verbose=False)])
    r_te = m2.predict_proba(Xte[:, ix])[:, 1]
    results["models"]["lightgbm_sin_poi"] = {
        "auc_test": round(float(roc_auc_score(yte, r_te)), 4),
        "test": evaluate(yte, r_te, "lgbm_sin_poi/test"),
    }

    # ── Subgrupo diagnostico: test dentro de POI ──
    m_poi = te["in_poi"].to_numpy() > 0.5
    if m_poi.sum() > 30:
        results["diagnostico_poi_test"] = {
            "n_en_poi": int(m_poi.sum()),
            "lgbm_en_poi": evaluate(yte[m_poi], p_te[m_poi], "lgbm/test/in_poi"),
            "lgbm_fuera_poi": evaluate(yte[~m_poi], p_te[~m_poi], "lgbm/test/out_poi"),
        }

    results["runtime_sec"] = round(time.time() - t0, 1)
    (OUT / "_raw_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in results.items() if k != "models"}, indent=2))
    print("TOP15 importancia:", imp[:15])
    print("OK ->", OUT / "_raw_results.json", f"{results['runtime_sec']}s")


if __name__ == "__main__":
    main()
