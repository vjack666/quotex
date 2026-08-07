"""PHASEA-R5 — Estructura independiente del Edificio (no mira WIN/LOSS ni senal).

Feature: edificio_wyckoff_phasea (R5). Caja negra intacta. Sin volumen.
Diseno autorizado por Trader-Humano:
  R5-A: Phase_A_Score sobre TODO el mercado M15 (solo OHLC+tiempo).
  R5-B: score como TRAYECTORIA (persistencia/clusters), no solo numero.
  R5-C: consecuencia de mercado a H velas SIN Edificio (retorno/ruptura/reversion).
  Ablation: quitar cada componente y medir cuanto cae la predictividad de la
            estructura (descubrir que 2-3 piezas importan, el resto es ruido).
NO optimiza win rate del Edificio. Solo describe si la estructura tiene
comportamiento propio.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

M15_PATHS = [
    Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\cohorte_real_eurusd\EURUSD_M15.parquet"),
    Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\smc_borrowed\EURUSD_M15.parquet"),
]
REPORT_DIR = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\ew_reports\PHASEA-R5")
WINDOW = 20
STEP = 5          # ventana cada 5 velas (eficiencia; 543k/5 ~ 108k ventanas)
FWD = [1, 3, 5]   # horizonte en velas M15


def _load_m15() -> pd.DataFrame:
    for p in M15_PATHS:
        if p.exists():
            df = pd.read_parquet(p)
            df["ts"] = pd.to_datetime(df["time"])
            return df.sort_values("ts").reset_index(drop=True)
    raise FileNotFoundError("No hay EURUSD_M15 en disco.")


def _componentes(o, h, l, c) -> dict:
    n = len(c)
    if n < 10:
        return {}
    half = max(5, n // 2)
    x = np.arange(n)
    sf = np.polyfit(x[:half], c[:half], 1)[0]
    ss = np.polyfit(x[half:], c[half:], 1)[0]
    rng = (h - l)
    net_first = abs(c[half - 1] - c[0]); net_second = abs(c[-1] - c[half - 1])
    agot = net_first - net_second
    comp = (rng[:half].mean() / rng[half:].mean()) if rng[half:].mean() > 0 else np.nan
    overlap = float(np.mean([min(h[i + 1], h[i]) - max(l[i + 1], l[i]) for i in range(n - 1)]))
    bf, ph, pl = 0, h[0], l[0]
    for i in range(1, n):
        touch = (h[i] >= ph) or (l[i] <= pl)
        inside = (c[i] <= ph) and (c[i] >= pl)
        if touch and inside:
            bf += 1
        ph, pl = max(ph, h[i]), min(pl, l[i])
    break_fail = bf / (n - 1) if n > 1 else 0.0
    safe = np.where(rng > 0, rng, np.nan)
    wick_vals = ((h - np.maximum(o, c)) + (np.minimum(o, c) - l)) / safe
    wick = float(np.nanmean(wick_vals)) if np.any(np.isfinite(wick_vals)) else 0.0
    chg = np.sign(np.diff(c))
    pf = float(np.mean(chg[: half - 1] != 0)) if half > 1 else 0.0
    ps = float(np.mean(chg[half - 1:] != 0)) if n - half > 1 else 0.0
    reduc = pf - ps
    cambio = abs(sf - ss)
    return {"agotamiento": float(agot), "compression": float(comp), "overlap": overlap,
            "break_fail": float(break_fail), "rechazo": wick, "reduc_cont": float(reduc),
            "cambio_reg": float(cambio)}


def _corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = ~(np.isnan(a) | np.isnan(b))
    if m.sum() < 10:
        return np.nan
    return float(np.corrcoef(a[m], b[m])[0, 1])


def main() -> int:
    df = _load_m15()
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    N = len(c)
    comp_cols = ["agotamiento", "compression", "overlap", "break_fail", "rechazo", "reduc_cont", "cambio_reg"]
    recs = []
    # Ventanas móviles cada STEP, con contexto forward de FWD velas
    for s in range(0, N - WINDOW - max(FWD) - 1, STEP):
        e = s + WINDOW
        comp = _componentes(o[s:e], h[s:e], l[s:e], c[s:e])
        if not comp:
            continue
        fwd = {}
        for H in FWD:
            ee = e + H
            fwd[f"ret_{H}"] = float(c[ee] - c[e]) / c[e] if c[e] != 0 else np.nan
            rng_win = (h[s:e] - l[s:e]).max()
            rng_fwd = (h[e:ee] - l[e:ee]).max()
            fwd[f"break_{H}"] = float(rng_fwd / rng_win) if rng_win > 0 else np.nan
            # reversion respecto a direccion del impulso de la ventana
            imp = c[e - 1] - c[s]
            fwd[f"reversal_{H}"] = float(np.sign(imp) != np.sign(c[ee] - c[e])) if imp != 0 else np.nan
        rec = {"i": s, "ts": df["time"].iloc[s]}
        rec.update(comp); rec.update(fwd)
        recs.append(rec)
    m = pd.DataFrame(recs)
    if m.empty:
        print("[PHASEA-R5] sin ventanas"); return 1

    # R5-A: score normalizado por rank global (descriptivo de mercado, NO mira Edificio)
    for col in comp_cols:
        m[f"n_{col}"] = m[col].rank(pct=True)
    m["phase_a_score"] = m[[f"n_{col}" for col in comp_cols]].sum(axis=1)

    # R5-B: persistencia de la estructura (autocorrelacion del score en el tiempo)
    ac = {f"ac{l}": float(pd.Series(m["phase_a_score"].values).autocorr(lag=l)) for l in (1, 2, 3, 5)}
    # fraccion de ventanas con score alto que estan rodeadas de otras altas (cluster)
    hi = m["phase_a_score"] > m["phase_a_score"].quantile(0.8)
    cluster = float((hi & hi.shift(1).fillna(False)).mean()) if hi.sum() else np.nan

    # R5-C: consecuencia de mercado por tercil de score (TODO el mercado, no Edificio)
    m["tercil"] = pd.qcut(m["phase_a_score"], 3, labels=["bajo", "medio", "alto"])
    conse = {}
    for H in FWD:
        for met in [f"ret_{H}", f"break_{H}", f"reversal_{H}"]:
            conse[f"{met}"] = {t: float(m.loc[m["tercil"] == t, met].mean(skipna=True)) for t in ["bajo", "medio", "alto"]}

    # Ablation: quitar cada componente, medir caida de predictividad de la estructura
    # objetivo = break_3 (expansion posterior) y ret_3
    ablation = {}
    base_corr_break = _corr(m["phase_a_score"], m["break_3"])
    base_corr_ret = _corr(m["phase_a_score"], m["ret_3"])
    for drop in comp_cols:
        keep = [f"n_{col}" for col in comp_cols if col != drop]
        sc = m[keep].sum(axis=1)
        cb = _corr(sc, m["break_3"]); cr = _corr(sc, m["ret_3"])
        ablation[drop] = {"corr_break_drop": base_corr_break - cb, "corr_ret_drop": base_corr_ret - cr}

    # OOS temporal: 2a mitad del dataset
    mid = len(m) // 2
    m2 = m.iloc[mid:]
    oos = {"n": int(len(m2))}
    for H in FWD:
        oos[f"ret_{H}"] = {t: float(m2.loc[m2["tercil"] == t, f"ret_{H}"].mean(skipna=True)) for t in ["bajo", "medio", "alto"]}

    report = {
        "n_windows": int(len(m)), "window": WINDOW, "step": STEP,
        "R5A_score_range": [float(m["phase_a_score"].min()), float(m["phase_a_score"].max())],
        "R5B_persistencia": ac, "R5B_cluster_frac_alto": cluster,
        "R5C_consecuencia_por_tercil": conse,
        "ablation_vs_break3_base_corr": base_corr_break, "ablation_vs_ret3_base_corr": base_corr_ret,
        "ablation_drop_por_componente": ablation,
        "OOS_segunda_mitad": oos,
        "regla_oro": "sin volumen, sin Edificio, sin win/loss",
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    with open(REPORT_DIR / "summary.md", "w", encoding="utf-8") as f:
        f.write("# PHASEA-R5 — Estructura independiente del Edificio (R5)\n\n")
        f.write(f"- Ventanas M15: {len(m)} (step {STEP}, ventana {WINDOW}). NO Edificio, NO win/loss, NO volumen.\n")
        f.write("\n## R5-B Persistencia (trayectoria, no numero)\n")
        f.write(f"- Autocorrelacion score lag1..5: {ac}\n- Fraccion de altos en cluster: {cluster:.3f}\n")
        f.write("\n## R5-C Consecuencia de mercado por tercil de score (TODO el mercado)\n")
        for H in FWD:
            f.write(f"\n### H={H} velas\n")
            for met in [f"ret_{H}", f"break_{H}", f"reversal_{H}"]:
                row = conse[met]
                f.write(f"- {met}: bajo={row['bajo']:.5f} medio={row['medio']:.5f} alto={row['alto']:.5f}\n")
        f.write(f"\n## Ablation (caida de correlacion al quitar componente)\n- base break3 r={base_corr_break:.3f} | ret3 r={base_corr_ret:.3f}\n")
        for drop, v in sorted(ablation.items(), key=lambda kv: abs(kv[1]["corr_break_drop"]), reverse=True):
            f.write(f"- quitar {drop}: d_break={v['corr_break_drop']:.4f} d_ret={v['corr_ret_drop']:.4f}\n")
        f.write("\n## OOS (2a mitad del dataset)\n")
        for H in FWD:
            row = oos[f"ret_{H}"]
            f.write(f"- ret_{H}: bajo={row['bajo']:.5f} medio={row['medio']:.5f} alto={row['alto']:.5f}\n")
        f.write("\nRegla de oro: volumen NUNCA requisito. Edificio caja negra intacta. Charter: Sí\n")
    print(f"[PHASEA-R5] reporte: {REPORT_DIR} | ventanas={len(m)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
