"""Fase 4 del Laboratorio — Ranking de firmas con LightGBM (reutiliza la libreria,
no el MLScorer de produccion del bot).

Diseno honesto:
- El MLScorer de produccion (src/ml_scorer.py) se entrena con el Experience Engine
  del bot y usa FEATURE_NAMES del bot. NO es reutilizable tal cual para el lab.
  Por eso reutilizamos LightGBM COMO LIBRERIA, con features del motor libre.
- Objetivo: RANKEAR firmas por WR predicha / importancia de features. Nada mas.
  Ley 12 del motor de secuencias: el modelo SOLO rankea; no decide, no opera.
- El veredicto de PROMOCION lo dicta promotion_gate.py + tribunal_v1.yaml
  (incluido FDR, aun pendiente de redactar por §15). Este script NO promueve.

Dataset:
- Solo expedientes COMPLETOS con veredicto binario resuelto (win in {0,1}).
  win == -1 (completa pero sin cierre limpio) se DESCARTA: no se fabrican etiquetas.
- Features numericas del motor libre + firma codificada como categoria.
- Guard de muestra minima: respeta min_trades=500 (igual que ml_scorer) para entrenar
  el modelo global. El reporte por firma respeta los umbrales del tribunal
  (60 individual / 100 compuesta) y los marca explicitamente.

Uso:
    python src/strategy_lab/run_lab_fase4_rank.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Permite importar strategy_lab como paquete
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Fase 5 (tribunal) usara promotion_gate + evidence + robustness.
# En Fase 4 solo rankeamos; no los importamos para no arrastrar codigo muerto.

DATA = ROOT / "data" / "strategy_lab" / "secuencia_libre_events.parquet"
MIN_TRADES = 500  # igual que ml_scorer._MIN_TRADES_DEFAULT

# Features numericas del motor libre (sin columnas de identidad / leaky)
NUMERIC_FEATURES = [
    "n_eventos", "vida_velas", "lag_freno", "lag_extremo", "lag_cruce",
    "lag_separacion", "lag_martillo", "body_n", "brake_ratio", "rvol",
    "trend", "htf_bias", "k_birth", "d_birth", "hour",
]
CAT_FEATURES = ["firma", "asset", "direction"]


def load_clean() -> pd.DataFrame:
    df = pd.read_parquet(DATA)
    # Solo completas con veredicto resuelto
    mask = (df["completa"] == 1) & (df["win"].isin([0, 1]))
    clean = df[mask].copy()
    dropped = len(df) - len(clean)
    print(f"[load] filas totales={len(df)}  completas+resueltas={len(clean)}  "
          f"descartadas(win=-1/no completa)={dropped}")
    return clean


def train_lightgbm(X: pd.DataFrame, y: pd.Series):
    import lightgbm as lgb

    X = X.copy()
    # LightGBM requiere numericas; las categoricas van como dtype 'category'
    cat_cols = [c for c in CAT_FEATURES if c in X.columns]
    for c in cat_cols:
        X[c] = X[c].astype("category")

    model = lgb.LGBMClassifier(
        n_estimators=400,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(X, y, categorical_feature=cat_cols)
    return model


def firma_report(clean: pd.DataFrame) -> pd.DataFrame:
    g = (
        clean.groupby("firma")
        .agg(n=("win", "size"), wr=("win", "mean"), win_count=("win", "sum"))
        .sort_values("n", ascending=False)
    )
    g["cumple_min_individual_60"] = g["n"] >= 60
    g["cumple_min_compuesta_100"] = g["n"] >= 100
    g["cumple_min_500"] = g["n"] >= MIN_TRADES
    return g


def main() -> None:
    clean = load_clean()
    if len(clean) < MIN_TRADES:
        print(f"[WARN] muestra global {len(clean)} < min_trades {MIN_TRADES}; "
              "LightGBM no entrena (guard activo, igual que ml_scorer).")
        print("        Se reporta solo ranking observacional por firma.")
    else:
        feat = NUMERIC_FEATURES + CAT_FEATURES
        X = clean[feat].copy()
        y = clean["win"].astype(int)
        model = train_lightgbm(X, y)
        imp = pd.Series(model.feature_importances_, index=feat).sort_values(ascending=False)
        print("\n[model] LightGBM entrenado  n=%d  WR_base=%.4f" % (len(clean), y.mean()))
        print("[model] Top-12 importancia de features:")
        print(imp.head(12).to_string())

    rep = firma_report(clean)
    print("\n=== RANKING DE FIRMAS (observacional, completas resueltas) ===")
    print("total firmas:%d" % len(rep))
    print(rep.to_string())

    # Senalar candidatas que el tribunal consideraria por muestra
    candidatas = rep[rep["cumple_min_compuesta_100"]]
    print("\n=== CANDIDATAS POR MUESTRA (n>=100, umbral compuesta tribunal) ===")
    print("n_candidatas=%d" % len(candidatas))
    for firma, row in candidatas.iterrows():
        # Poder del §8.1 (aprox): mejora sobre baseline global
        base = clean["win"].mean()
        delta = row["wr"] - base
        print(f"  {firma:55s} n={int(row['n']):4d}  WR={row['wr']:.4f}  "
              f"delta_vs_base={delta:+.4f}")

    print("\n[NOTA] Este script NO promueve. El veredicto de promocion requiere")
    print("      promotion_gate.py + tribunal_v1.yaml (FDR aun pendiente, §15).")
    print("[NOTA] Ranking observacional != evidencia (jerarquia nivel 1 del tribunal).")


if __name__ == "__main__":
    main()
