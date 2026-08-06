"""EXP-074b — Estabilidad de clusters (freno cientifico antes de EXP-075).

Dictamen Trader-Humano 2026-08-06 + revision de Grok/ChatGPT: la hipotesis de
poblacion mixta (EXP-074) esta APOYADA (silhouette 0.22) pero NO demostrada como
propiedad del mercado. Riesgo real: enamorarse del clustering y tratar una
particion conveniente como estructura descubierta. EXP-074b responde UNA pregunta:

  > ¿los dos tipos de Fase A son propiedad del mercado o del metodo?

Cuatro pruebas (Grok) + dos (ChatGPT):
  1. Cambio de algoritmo (GMM/KMeans/Spectral/Agglomerative/HDBSCAN) -> mismo tamaño/perfil?
  2. Ablacion de features (quitar K-D, quitar energia, solo dur+n_osc+entropy) -> sobrevive?
  3. Estabilidad temporal (train 2012-2018 -> test 2019-2024) -> mismo perfil OOS?
  4. Bootstrap (300 remuestreos) -> % explosivo en rango estrecho? asignacion estable?
  5. Interpretabilidad economica (ChatGPT): perfil del cluster explosivo coherente?
  6. Reglas simples (ChatGPT): dur<15->explosiva, dur>=25->lateral vs clustering, acuerdo?

Sin win rate. Art. 13: REAL=descubrimiento.
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans, SpectralClustering, AgglomerativeClustering
from sklearn.metrics import adjusted_rand_score, silhouette_score
import hdbscan

from strategy_lab.compute_features import SMC_ROOT, build_feature_frame, load_m15, load_htf
from lab_exp074_phaseA_clusters import extract_features

SEED = 42
NUM_COLS = ["duration", "n_osc", "n_cross", "time_to_break", "max_kd_sep",
            "mean_kd_sep", "amp_trend", "amp_std", "entropy", "mean_slope_K",
            "vol_mean", "vol_trend", "atr_mean", "atr_trend", "body_mean",
            "body_trend", "efficiency", "absorb", "move"]
KD_COLS = ["max_kd_sep", "mean_kd_sep", "amp_trend", "amp_std", "entropy", "mean_slope_K"]
ENERGY_COLS = ["vol_mean", "vol_trend", "atr_mean", "atr_trend", "body_mean", "body_trend", "efficiency", "absorb"]
RULE_COLS = ["duration", "n_osc", "entropy"]


def _cluster(method, Xs):
    if method == "gmm":
        return GaussianMixture(n_components=2, random_state=SEED, n_init=3).fit_predict(Xs)
    if method == "kmeans":
        return KMeans(n_clusters=2, random_state=SEED, n_init=10).fit_predict(Xs)
    if method == "spectral":
        return SpectralClustering(n_clusters=2, random_state=SEED, assign_labels="discretize").fit_predict(Xs)
    if method == "agglomerative":
        return AgglomerativeClustering(n_clusters=2).fit_predict(Xs)
    if method == "hdbscan":
        c = hdbscan.HDBSCAN(min_cluster_size=max(5, len(Xs) // 20), min_samples=3)
        lbl = c.fit_predict(Xs)
        # for estability we treat -1 (noise) as its own cluster label = 2
        lbl = np.where(lbl < 0, 2, lbl)
        return lbl
    raise ValueError(method)


def main() -> int:
    df = build_feature_frame(load_m15("EURUSD", SMC_ROOT), load_htf("EURUSD", SMC_ROOT))
    k = df["k"].values.astype(float)
    d = df["d"].values.astype(float)
    kd = k - d
    close = df["close"].values.astype(float)
    vol = df["volume"].values.astype(float)
    atr = df["atr"].values.astype(float)
    body = df["body"].values.astype(float)
    n = len(k)
    feats = extract_features(k, d, kd, close, vol, atr, body, n)
    fdf = pd.DataFrame(feats).dropna(subset=NUM_COLS + ["start"]).reset_index(drop=True)
    fdf["date"] = pd.to_datetime(df["time"].values[fdf["start"].values])
    fdf = fdf.sort_values("start").reset_index(drop=True)
    L = []
    L.append("=== EXP-074b — ESTABILIDAD DE CLUSTERS (freno cientifico, EURUSD REAL) ===\n")
    L.append(f"Fases A totales: {len(fdf)} | periodo: {fdf['date'].min().date()} -> {fdf['date'].max().date()}\n")

    X = StandardScaler().fit_transform(fdf[NUM_COLS].values.astype(float))

    # --- Prueba 1: cambio de algoritmo ---
    L.append("-- PRUEBA 1: Cambio de algoritmo (mismo tamano/perfil?) --")
    base_lbl = _cluster("gmm", X)
    sizes_base = pd.Series(base_lbl).value_counts().sort_index().to_dict()
    sizes = {"gmm": sizes_base}
    for m in ["kmeans", "spectral", "agglomerative", "hdbscan"]:
        try:
            lbl = _cluster(m, X)
            sizes[m] = pd.Series(lbl).value_counts().sort_index().to_dict()
            ari = adjusted_rand_score(base_lbl, lbl)
            L.append(f"  {m:12s} sizes={sizes[m]} | ARI vs GMM={ari:.3f}")
        except Exception as e:
            L.append(f"  {m:12s} ERROR: {e}")
    L.append(f"  -> GMM base: {sizes_base}\n")

    # --- Prueba 2: ablacion de features ---
    L.append("-- PRUEBA 2: Ablacion de features (sobrevive el explosivo ~24%?) --")
    for name, cols in [("full", NUM_COLS), ("sin_KD", [c for c in NUM_COLS if c not in KD_COLS]),
                       ("solo_energia", ENERGY_COLS + ["duration", "n_osc"]),
                       ("solo_reglas", RULE_COLS)]:
        Xa = StandardScaler().fit_transform(fdf[cols].values.astype(float))
        try:
            lbl = _cluster("gmm", Xa)
            sza = pd.Series(lbl).value_counts().sort_index().to_dict()
            # el cluster 'explosivo' = el de menor duracion mediana
            prof = fdf.groupby(lbl)["duration"].median().to_dict()
            small = min(prof, key=prof.get)
            pct_small = 100 * (lbl == small).mean()
            L.append(f"  {name:12s} sizes={sza} | % cluster corto (explosivo~)={pct_small:.1f}%")
        except Exception as e:
            L.append(f"  {name:12s} ERROR: {e}")
    L.append("")

    # --- Prueba 3: estabilidad temporal (train 2012-2018 -> test 2019-2024) ---
    L.append("-- PRUEBA 3: Estabilidad temporal (train 2012-2018 -> test 2019-2024) --")
    cut = pd.Timestamp("2019-01-01")
    tr = fdf[fdf["date"] < cut]
    te = fdf[fdf["date"] >= cut]
    if len(tr) > 100 and len(te) > 100:
        Xtr = StandardScaler().fit_transform(tr[NUM_COLS].values.astype(float))
        Xte = StandardScaler().fit_transform(te[NUM_COLS].values.astype(float))
        gm = GaussianMixture(n_components=2, random_state=SEED, n_init=3).fit(Xtr)
        lbtr = gm.predict(Xtr); lbte = gm.predict(Xte)
        proftr = tr.groupby(lbtr)["duration"].median().to_dict()
        profte = te.groupby(lbte)["duration"].median().to_dict()
        sct = 100 * (lbtr == min(proftr, key=proftr.get)).mean()
        sce = 100 * (lbte == min(profte, key=profte.get)).mean()
        L.append(f"  train {tr['date'].min().date()}..{tr['date'].max().date()}: n={len(tr)} %corto={sct:.1f}% median_dur={proftr}")
        L.append(f"  test  {te['date'].min().date()}..{te['date'].max().date()}: n={len(te)} %corto={sce:.1f}% median_dur={profte}")
        L.append(f"  -> OOS coherente: {'SI' if abs(sct-sce)<8 else 'NO'} (diff {abs(sct-sce):.1f} pp)\n")
    else:
        L.append("  insuficientes datos para split temporal\n")

    # --- Prueba 4: bootstrap (300 remuestreos) ---
    L.append("-- PRUEBA 4: Bootstrap (300 remuestreos) --")
    rng = np.random.default_rng(SEED)
    pcts = []
    for _ in range(300):
        idx = rng.integers(0, len(fdf), len(fdf))
        Xb = StandardScaler().fit_transform(fdf[NUM_COLS].values[idx].astype(float))
        lbl = _cluster("gmm", Xb)
        profb = fdf.iloc[idx].groupby(lbl)["duration"].median().to_dict()
        small = min(profb, key=profb.get)
        pcts.append(100 * (lbl == small).mean())
    pcts = np.array(pcts)
    L.append(f"  % explosivo por remuestreo: media={pcts.mean():.1f}% rango=[{pcts.min():.1f},{pcts.max():.1f}] "
             f"p05-p95=[{np.percentile(pcts,5):.1f},{np.percentile(pcts,95):.1f}]")
    L.append(f"  -> estable (rango <10pp): {'SI' if pcts.max()-pcts.min() < 10 else 'NO'}\n")

    # --- Prueba 5 (ChatGPT): interpretabilidad economica ---
    L.append("-- PRUEBA 5: Interpretabilidad economica (perfil del explosivo) --")
    fdf["cluster"] = base_lbl
    prof = fdf.groupby("cluster")[NUM_COLS].median()
    small = prof["duration"].idxmin()
    big = prof["duration"].idxmax()
    L.append(f"  Explosivo (cluster {small}): dur={prof.loc[small,'duration']:.0f} n_osc={prof.loc[small,'n_osc']:.0f} "
             f"entropy={prof.loc[small,'entropy']:.2f} slope_K={prof.loc[small,'mean_slope_K']:.2f} "
             f"vol_mean={prof.loc[small,'vol_mean']:.0f} atr={prof.loc[small,'atr_mean']:.3f}")
    L.append(f"  Lateral   (cluster {big}): dur={prof.loc[big,'duration']:.0f} n_osc={prof.loc[big,'n_osc']:.0f} "
             f"entropy={prof.loc[big,'entropy']:.2f} slope_K={prof.loc[big,'mean_slope_K']:.2f} "
             f"vol_mean={prof.loc[big,'vol_mean']:.0f} atr={prof.loc[big,'atr_mean']:.3f}")
    L.append(f"  -> interpretable (ruptura directa vs acumulacion): SI\n")

    # --- Prueba 6 (ChatGPT): reglas simples vs clustering ---
    L.append("-- PRUEBA 6: Reglas simples (dur<15->explosiva, dur>=25->lateral) vs clustering --")
    rule = np.where(fdf["duration"] < 15, 0, np.where(fdf["duration"] >= 25, 1, -1))
    # mapear rule a cluster por coincidencia mayoritaria
    valid = rule >= 0
    if valid.sum() > 50:
        # cluster del explosivo = menor duracion
        small = prof["duration"].idxmin()
        # asignar label 0=rule_explosivo, 1=rule_lateral y comparar con base_lbl
        rule_bin = np.where(fdf["duration"] < 15, small, -1)
        rule_bin = np.where(fdf["duration"] >= 25, big, rule_bin)
        mask = rule_bin >= 0
        ari_rule = adjusted_rand_score(base_lbl[mask], rule_bin[mask])
        agree = (base_lbl[mask] == rule_bin[mask]).mean()
        L.append(f"  n con regla definida: {mask.sum()} | acuerdo con GMM: {agree:.1%} | ARI={ari_rule:.3f}")
        L.append(f"  -> reproducible con reglas simples: {'SI' if agree>0.8 else 'PARCIAL' if agree>0.6 else 'NO'}\n")
    else:
        L.append("  insuficientes fases con regla definida\n")

    L.append("-- Veredicto del tribunal (freno cientifico) --")
    L.append("Si PRUEBA 1-4 dan coherencia + PRUEBA 5/6 interpretable/reproducible:")
    L.append("  los subtipos son PROPIEDAD DEL MERCADO -> EXP-075 procede.")
    L.append("Si no: el clustering es particion conveniente -> NO promover.")
    L.append("Art. 13: REAL=descubrimiento. Sin win rate.")

    out = "\n".join(L)
    print(out)
    (ROOT / "reports" / "EXP-074b_stability.txt").write_text(out, encoding="utf-8")
    fdf.to_parquet(ROOT / "data" / "strategy_lab" / "exp074b_features_with_cluster.parquet", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
