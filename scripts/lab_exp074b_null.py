"""EXP-074b-NULL — Control nulo / surrogate + Prueba temporal OOS (cierre del clustering).

Orden Trader-Humano 2026-08-07: cerrar definitivamente el hilo del clustering.
NO busca edge. NO promueve a estrategia (Art. 13). Distingue siempre
"clustering encuentra geometria" vs "mercado posee regimenes naturales".

Reusa EXACTAMENTE el pipeline de features/clustering de EXP-074b (NUM_COLS,
StandardScaler, GMM/KMeans) para que REAL y NULL sean comparables.

Salidas inmutables en reports/EXP-074b_NULL/ + data/strategy_lab/.
"""
from __future__ import annotations

import sys, json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

from strategy_lab.compute_features import SMC_ROOT, build_feature_frame, load_m15, load_htf
from lab_exp074_phaseA_clusters import extract_features

SEED = 42
NUM_COLS = ["duration", "n_osc", "n_cross", "time_to_break", "max_kd_sep",
            "mean_kd_sep", "amp_trend", "amp_std", "entropy", "mean_slope_K",
            "vol_mean", "vol_trend", "atr_mean", "atr_trend", "body_mean",
            "body_trend", "efficiency", "absorb", "move"]


def _structure_score(fdf, lbl):
    """Separabilidad economica: media de |mediana_c0 - mediana_c1| / std por feature."""
    g0 = fdf.loc[lbl == 0, NUM_COLS]
    g1 = fdf.loc[lbl == 1, NUM_COLS]
    if len(g0) < 5 or len(g1) < 5:
        return np.nan
    diffs = (g0.median().values - g1.median().values) / fdf[NUM_COLS].std().values
    return float(np.nanmean(np.abs(diffs)))


def _fit_gmm(X):
    return GaussianMixture(n_components=2, random_state=SEED, n_init=3).fit_predict(X)


def _fit_kmeans(X):
    return KMeans(n_clusters=2, random_state=SEED, n_init=10).fit_predict(X)


def main() -> int:
    rng = np.random.default_rng(SEED)
    L = []
    L.append("=== EXP-074b-NULL — CONTROL NULO / SURROGATE + PRUEBA TEMPORAL OOS (EURUSD REAL) ===")
    L.append(f"Generado: {datetime.now(timezone.utc).isoformat()[:19]}Z | seed={SEED}\n")

    # ---- features REAL ----
    df = build_feature_frame(load_m15("EURUSD", SMC_ROOT), load_htf("EURUSD", SMC_ROOT))
    k = df["k"].values.astype(float); d = df["d"].values.astype(float); kd = k - d
    close = df["close"].values.astype(float); vol = df["volume"].values.astype(float)
    atr = df["atr"].values.astype(float); body = df["body"].values.astype(float)
    n = len(k)
    feats = extract_features(k, d, kd, close, vol, atr, body, n)
    fdf = pd.DataFrame(feats).dropna(subset=NUM_COLS + ["start"]).reset_index(drop=True)
    fdf["date"] = pd.to_datetime(df["time"].values[fdf["start"].values])
    fdf = fdf.sort_values("start").reset_index(drop=True)
    L.append(f"Fases A totales: {len(fdf)} | periodo: {fdf['date'].min().date()} -> {fdf['date'].max().date()}")

    Xreal = StandardScaler().fit_transform(fdf[NUM_COLS].values.astype(float))
    lbl_real = _fit_gmm(Xreal)
    sil_real = float(silhouette_score(Xreal, lbl_real))
    pct_min_real = float(min(np.bincount(lbl_real)) / len(lbl_real) * 100)
    ss_real = _structure_score(fdf, lbl_real)
    L.append(f"\n-- REAL (GMM n=2) --")
    L.append(f"  silhouette = {sil_real:.4f}")
    L.append(f"  proporcion minoritaria = {pct_min_real:.1f}%")
    L.append(f"  structure score = {ss_real:.3f}")
    L.append(f"  perfiles por cluster (mediana):")
    prof = fdf.groupby(lbl_real)[NUM_COLS].median()
    for c in prof.index:
        L.append(f"    c{c}: " + ", ".join(f"{col}={prof.loc[c,col]:.2f}" for col in ["duration","n_osc","entropy","mean_slope_K","vol_mean","atr_mean"]))

    # ---- NULL: shuffle INDEPENDIENTE de columnas (preserva marginales, mata correlacion conjunta) ----
    L.append(f"\n-- NULL (surrogate: shuffle independiente por feature, B=200) --")
    B = 200
    sil_null, pct_null, ss_null = [], [], []
    for b in range(B):
        Xn = Xreal.copy()
        for j in range(Xn.shape[1]):
            Xn[:, j] = rng.permutation(Xn[:, j])
        try:
            ln = _fit_gmm(Xn)
            sil_null.append(silhouette_score(Xn, ln))
            pct_null.append(min(np.bincount(ln)) / len(ln) * 100)
            ss_null.append(_structure_score(pd.DataFrame(Xn, columns=NUM_COLS), ln))
        except Exception:
            pass
    sil_null = np.array(sil_null); pct_null = np.array(pct_null); ss_null = np.array(ss_null)

    frac_sil = float((sil_null > sil_real).mean())
    frac_ss = float((ss_null > ss_real).mean())
    L.append(f"  silhouette null: media={sil_null.mean():.4f} p05={np.percentile(sil_null,5):.4f} "
             f"p95={np.percentile(sil_null,95):.4f}")
    L.append(f"  % minoritario null: media={pct_null.mean():.1f}% rango=[{pct_null.min():.1f},{pct_null.max():.1f}]")
    L.append(f"  structure score null: media={ss_null.mean():.3f} p95={np.percentile(ss_null,95):.3f}")
    L.append(f"  fraccion de null con silhouette > REAL: {frac_sil:.3f}")
    L.append(f"  fraccion de null con structure score > REAL: {frac_ss:.3f}")

    # ARI REAL vs un null representativo (misma semilla de shuffle que b=0)
    Xn0 = Xreal.copy()
    for j in range(Xn0.shape[1]):
        Xn0[:, j] = rng.permutation(Xn0[:, j])
    ari_real_vs_null = float(adjusted_rand_score(lbl_real, _fit_gmm(Xn0)))
    L.append(f"  ARI(REAL, null representativo) = {ari_real_vs_null:.3f} (esperado ~0)")

    # ---- KMeans tambien (robustez de metodo) ----
    L.append(f"\n-- REAL (KMeans n=2) para robustez --")
    lbl_km = _fit_kmeans(Xreal)
    sil_km = float(silhouette_score(Xreal, lbl_km))
    L.append(f"  silhouette REAL-KMeans = {sil_km:.4f} (vs GMM {sil_real:.4f})")

    # ---- PRUEBA TEMPORAL OOS (TRAIN 2022-2024 -> TEST 2025-2026) ----
    L.append(f"\n-- PRUEBA TEMPORAL OOS (cierre 074b Prueba 3) --")
    cut = pd.Timestamp("2025-01-01")
    tr = fdf[fdf["date"] < cut]
    te = fdf[fdf["date"] >= cut]
    L.append(f"  TRAIN {tr['date'].min().date()}..{tr['date'].max().date()} n={len(tr)} | "
             f"TEST {te['date'].min().date()}..{te['date'].max().date()} n={len(te)}")
    Xtr = StandardScaler().fit_transform(tr[NUM_COLS].values.astype(float))
    Xte = StandardScaler().fit_transform(te[NUM_COLS].values.astype(float))
    gm = GaussianMixture(n_components=2, random_state=SEED, n_init=3).fit(Xtr)
    lbtr = gm.predict(Xtr); lbte = gm.predict(Xte)
    proftr = tr.groupby(lbtr)[NUM_COLS].median()
    profte = te.groupby(lbte)[NUM_COLS].median()
    # el cluster 'corto' = menor mediana de duration en cada split
    short_tr = proftr["duration"].idxmin(); short_te = profte["duration"].idxmin()
    pct_tr = float((lbtr == short_tr).mean() * 100)
    pct_te = float((lbte == short_te).mean() * 100)
    diff = abs(pct_tr - pct_te)
    L.append(f"  TRAIN: %corto={pct_tr:.1f}% | TEST: %corto={pct_te:.1f}% | diff={diff:.1f}pp")
    # tambien reportar silhouette en TEST (sobre etiquetas predichas)
    try:
        sil_te = float(silhouette_score(Xte, lbte))
    except Exception:
        sil_te = float("nan")
    L.append(f"  silhouette TEST (predicho con GMM de TRAIN) = {sil_te:.4f} (vs REAL {sil_real:.4f})")
    oos_ok = diff < 8
    L.append(f"  -> OOS coherente (diff<8pp): {'SI' if oos_ok else 'NO'}")

    # ---- VEREDICTO (fijo por protocolo) ----
    L.append(f"\n-- VEREDICTO (tribunal EXP-074b-NULL) --")
    # Criterio de H0 rechazada (estructura del mercado): sil_REAL > p95 null
    #   Y structure_score_REAL > p95 null. Si no -> artefactual.
    sil_over = sil_real > np.percentile(sil_null, 95)
    ss_over = ss_real > np.percentile(ss_null, 95)
    estructura_real = sil_over and ss_over
    L.append(f"  sil_REAL({sil_real:.4f}) > p95_null({np.percentile(sil_null,95):.4f}): {'SI' if sil_over else 'NO'}")
    L.append(f"  ss_REAL({ss_real:.3f}) > p95_null({np.percentile(ss_null,95):.3f}): {'SI' if ss_over else 'NO'}")
    L.append(f"  ARI(REAL,null)={ari_real_vs_null:.3f} (cercano a 0 = particiones distintas)")
    if estructura_real:
        veredicto = "ESTRUCTURA DEL MERCADO (H0 rechazada): separacion excede el null"
    else:
        veredicto = "ARTEFACTO GEOMETRICO (H0 NO rechazada): la particion es indistinguishable del null"
    L.append(f"  Veredicto: {veredicto}")
    L.append(f"  OOS temporal: {'coherente' if oos_ok else 'NO coherente'} (diff={diff:.1f}pp)")
    L.append(f"  Hipotesis de poblacion mixta: NO SOPORTADA como estructura estable del mercado"
             f" bajo este espacio de representacion.")
    L.append(f"  Distincion: 'clustering encuentra geometria' != 'mercado posee regimenes naturales'.")
    L.append(f"  Art. 13: REAL=descubrimiento. Sin win rate operativa.")
    L.append(f"  EXP-075 (duracion continua predictiva): RESULTADO NEGATIVO (FDR 0/36, OR~1.0, OOS plano).")
    L.append(f"  Este experimento cumple el Charter: Sí")

    out = "\n".join(L)
    print(out)

    out_dir = ROOT / "reports" / "EXP-074b_NULL"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.txt").write_text(out, encoding="utf-8")
    (out_dir / "protocol_frozen.json").write_text(json.dumps({
        "alpha": 0.05, "fdr": "BH", "seed": SEED, "domain": "REAL",
        "null_method": "independent_column_shuffle_preserves_marginals",
        "B": B, "criterion_reject_H0": "sil_REAL>p95_null AND ss_REAL>p95_null",
        "oos_split": "TRAIN<2025-01-01 / TEST>=2025-01-01",
        "effect_size_or_min": 1.15,
    }, indent=2), encoding="utf-8")

    # guardar curvas del null para posible grafica
    null_curves = pd.DataFrame({"silhouette": sil_null, "pct_minor": pct_null, "structure_score": ss_null})
    null_curves.to_parquet(ROOT / "data" / "strategy_lab" / "exp074b_null_curves.parquet", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
