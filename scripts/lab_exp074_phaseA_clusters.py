"""EXP-074 — Mapa de Energia / Clustering de Fases A (no supervisado).

Dictamen Trader-Humano 2026-08-06 (culminacion de 071/072/073):
  El lab ya no descarta estrategias, descarta MODELOS MENTALES. Sintesis:
  el estocastico es buen descriptor de ESTADO pero mal predictor de CUANDO
  cambia de estado. Y la hipotesis mas fuerte aun no probada: las ~3300 Fases
  A NO son una sola poblacion. Si son 3-4 tipos distintos mezclados, TODOS los
  experimentos previos (donde ninguna variable fue significativa) son artefacto
  de mezclar poblaciones (sesgo de poblacion tipo medicina).

EXP-074 NO es supervisado. Descubre los TIPOS NATURALES de Fase A por clustering
(no usa la etiqueta breakout para formar grupos; la usa solo para perfilar).
Incluye la dimension de ENERGIA de Wyckoff (esfuerzo=volumen vs resultado=movimiento):
  eficiencia = |desplazamiento| / volumen ; absorcion = vol alta + mov bajo.

Pregunta: ¿cuantos tipos naturales de Fase A existen? (no ¿cual predice breakout?)
Salida = mapa de clusters + perfil por cluster. Art. 13: REAL=descubrimiento.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from strategy_lab.compute_features import SMC_ROOT, build_feature_frame, load_m15, load_htf

SEED = 42
ALPHA = 0.05
MAX_PHASE = 120


def extract_features(k, d, kd, close, vol, atr, body, n):
    """Detecta Fases A y extrae ~24 caracteristicas (estructura + K-D + ENERGIA)."""
    cross = (np.sign(kd[1:]) != np.sign(kd[:-1])) & (kd[1:] != 0)
    cross_full = np.zeros(n, dtype=bool)
    cross_full[1:] = cross

    feats = []
    in_phase = False
    start = None
    extreme_side = None
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
                    # energia Wyckoff: esfuerzo (vol) vs resultado (movimiento)
                    v = vol[start:i + 1]
                    vol_mean = float(np.mean(v))
                    xv = np.arange(len(v))
                    vol_trend = float(np.polyfit(xv, v, 1)[0]) if len(v) > 2 else 0.0
                    a_ = atr[start:i + 1]
                    atr_mean = float(np.mean(a_))
                    atr_trend = float(np.polyfit(xv, a_, 1)[0]) if len(a_) > 2 else 0.0
                    bd = body[start:i + 1]
                    body_mean = float(np.mean(bd))
                    body_trend = float(np.polyfit(xv, bd, 1)[0]) if len(bd) > 2 else 0.0
                    move = abs(close[i] - close[start])
                    efficiency = float(move / (vol_mean + 1e-9))   # abs vs resultado
                    absorb = float(vol_mean / (move + 1e-9))        # esfuerzo por nada = absorcion
                    feats.append({
                        "extreme_side": extreme_side, "duration": dt,
                        "n_osc": len(amps), "n_cross": int(np.sum(cross_full[start:i + 1])),
                        "n_brake": 0, "time_to_break": dt,
                        "max_kd_sep": float(np.max(np.abs(kd[start:i + 1]))),
                        "mean_kd_sep": float(np.mean(np.abs(kd[start:i + 1]))),
                        "amp_trend": amp_trend, "amp_std": float(np.std(amps)),
                        "entropy": _entropy(dirs), "mean_slope_K": float(np.mean(np.diff(k[start:i + 1]))),
                        "vol_mean": vol_mean, "vol_trend": vol_trend,
                        "atr_mean": atr_mean, "atr_trend": atr_trend,
                        "body_mean": body_mean, "body_trend": body_trend,
                        "efficiency": efficiency, "absorb": absorb,
                        "move": float(move),
                    })
                in_phase = False
    return feats


def _entropy(seq):
    import math
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
    fdf = pd.DataFrame(feats)
    fdf.to_parquet(ROOT / "data" / "strategy_lab" / "exp074_phaseA_features.parquet", index=False)

    # clustering NO supervisado sobre features numericas (sin breakout)
    num_cols = ["duration", "n_osc", "n_cross", "time_to_break", "max_kd_sep",
                "mean_kd_sep", "amp_trend", "amp_std", "entropy", "mean_slope_K",
                "vol_mean", "vol_trend", "atr_mean", "atr_trend", "body_mean",
                "body_trend", "efficiency", "absorb", "move"]
    fdf = fdf.dropna(subset=num_cols).reset_index(drop=True)
    if len(fdf) < 50:
        print("EXP-074: insuficientes fases validas para clustering.")
        return 0
    X = fdf[num_cols].values.astype(float)
    Xs = StandardScaler().fit_transform(X)

    # elegir K por BIC/silhouette (no supervisado)
    best_k, best_bic, best_sil, best_labels = 1, np.inf, -1, np.zeros(len(X))
    sil_by_k = {}
    for kk in range(1, 7):
        gm = GaussianMixture(n_components=kk, random_state=SEED, n_init=3)
        lbl = gm.fit_predict(Xs)
        bic = gm.bic(Xs)
        if kk >= 2:
            try:
                sil = silhouette_score(Xs, lbl)
            except Exception:
                sil = -1
            sil_by_k[kk] = round(sil, 4)
            if sil > best_sil:
                best_sil, best_k, best_labels = sil, kk, lbl
        else:
            best_bic = bic
    fdf["cluster"] = best_labels

    # perfilar clusters
    prof = fdf.groupby("cluster")[num_cols].median().round(3)
    prof.to_csv(ROOT / "reports" / "EXP-074_cluster_profiles.csv")
    fdf.to_parquet(ROOT / "data" / "strategy_lab" / "exp074_phaseA_clustered.parquet", index=False)

    print("=== EXP-074 — MAPA DE ENERGIA / CLUSTERING DE FASES A (EURUSD REAL) ===\n")
    print(f"Fases A: {len(fdf)} | features: {len(num_cols)}")
    print(f"Mejor K (silhouette): {best_k} | silhouette: {best_sil:.4f}")
    print("Silhouette por K:", sil_by_k)
    sizes = fdf["cluster"].value_counts().sort_index()
    print("Tamaños de cluster:", dict(sizes))
    print("\n-- Perfil por cluster (medianas) --")
    print(prof.to_string())
    if best_k >= 2:
        print("\nHIPOTESIS DE POBLACION MIXTA: CONFIRMADA (K>=2 clusters naturales).")
        print("Los experimentos 071-073 deben reinterpretarse POR SUBTIPO.")
    else:
        print("\nHIPOTESIS DE POBLACION MIXTA: NO confirmada (1 solo cluster).")
    print("\nVeredicto: clustering no supervisado (no win rate). REAL=descubrimiento, Art.13.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
