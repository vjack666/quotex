"""EXP-072 — Mapa de Transiciones de Mercado (Market State Transition Graph).

Cambio de paradigma Wyckoff (dictamen Trader-Humano 2026-08-06):
  El mercado NO es "contexto -> confirmador -> entrada" (vela magica).
  Es "estado -> transicion de estado -> confirmacion -> operacion".
  El estocastico ES el indicador de fase; el freno es la 1a reaccion (Spring/
  secondary test de la Fase A de Wyckoff). No buscamos el evento ganador:
  descubrimos la cadena de Markov de estados y que rutas llevan a movimientos
  favorables.

Salida = GRAFO de transiciones + descriptores de Fase A. NO un unico win rate.

Dominio REAL (EURUSD). Art. 13 Charter: solo descubrimiento, NO promocion.
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
from strategy_lab.compute_features import SMC_ROOT, build_feature_frame, load_m15, load_htf

SEED = 42
ALPHA = 0.05
H_FORWARD = 4  # ventana de "movimiento favorable" = 1h (4 velas M15)
IMP_TH = 0.4   # umbral de impulso para call/put


# ---------- estado ----------
def _k_regime(k):
    if k <= 20: return "OS"
    if k >= 80: return "OB"
    if k <= 40: return "LO"
    if k >= 60: return "HI"
    return "MID"

def _k_trend(dk):
    if dk > 1.0: return "up"
    if dk < -1.0: return "dn"
    return "flat"

def _impulse(x):
    if x > IMP_TH: return "call"
    if x < -IMP_TH: return "put"
    return "flat"

def _state_tuple(k, dk, imp):
    return (_k_regime(k), _k_trend(dk), _impulse(imp))

def _state_id(t):
    regs = {"OS":0,"OB":1,"LO":2,"HI":3,"MID":4}
    tr = {"up":0,"dn":1,"flat":2}
    im = {"call":0,"put":1,"flat":2}
    return (regs[t[0]]*3 + tr[t[1]])*3 + im[t[2]]

def _state_label(sid):
    regs = ["OS","OB","LO","HI","MID"]
    tr = ["up","dn","flat"]
    im = ["call","put","flat"]
    r = sid // 9; rest = sid % 9
    t = rest // 3; i = rest % 3
    return f"{regs[r]}.{tr[t]}.{im[i]}"


def build_graph(asset: str = "EURUSD"):
    df = build_feature_frame(load_m15(asset, SMC_ROOT), load_htf(asset, SMC_ROOT))
    k = df["k"].values.astype(float)
    d = df["d"].values.astype(float)
    imp = df["impulse_net"].values.astype(float)
    close = df["close"].values.astype(float)
    brake = df["brake_transition"].values.astype(bool)
    n = len(k)

    dk = np.zeros(n); dk[1:] = np.diff(k)
    kd = k - d
    kd_prev = np.concatenate([[kd[0]], kd[:-1]])
    cross = (np.sign(kd) != np.sign(kd_prev)) & (kd != 0)

    # secuencia de estados
    states = np.array([_state_id(_state_tuple(k[i], dk[i], imp[i])) for i in range(n)], dtype=int)

    # transiciones
    T = np.zeros((45, 45), dtype=int)
    for i in range(n - 1):
        T[states[i], states[i+1]] += 1
    probs = T / T.sum(axis=1, keepdims=True)
    probs = np.nan_to_num(probs)

    # favorable: impulso del estado se realiza en H velas?
    fav = np.zeros(n)
    for i in range(n - H_FORWARD):
        ret = close[i + H_FORWARD] - close[i]
        s = states[i]
        lab = _state_label(s)
        impc = lab.split(".")[2]
        if impc == "call":
            fav[i] = 1.0 if ret > 0 else 0.0
        elif impc == "put":
            fav[i] = 1.0 if ret < 0 else 0.0
        else:
            fav[i] = 1.0 if abs(ret) <= np.median(np.abs(np.diff(close[:n-H_FORWARD]))) else 0.0

    # por estado: n, favorable_rate, p (vs 0.5), FDR
    rows = []
    for s in range(45):
        idx = np.where(states[:-H_FORWARD] == s)[0]
        if len(idx) < 50:
            continue
        f = fav[idx].mean()
        p = stats.binomtest(int(fav[idx].sum()), len(idx), 0.50).pvalue
        rows.append({"state": s, "label": _state_label(s), "n": len(idx),
                     "favorable_rate": round(float(f), 4), "p_value": p})
    sf = pd.DataFrame(rows)
    if not sf.empty:
        fdr = adjust_pvalues(sf["p_value"].tolist(), method="fdr_bh")
        sf["p_adj_fdr"] = [round(x, 6) for x in fdr.adj_p]
        sf = sf.sort_values("favorable_rate", ascending=False)

    # grafo de transiciones (top por from_state)
    trows = []
    for a in range(45):
        tot = T[a].sum()
        if tot == 0:
            continue
        for b in range(45):
            if T[a, b] > 0:
                trows.append({"from_state": a, "from_label": _state_label(a),
                              "to_state": b, "to_label": _state_label(b),
                              "count": int(T[a, b]), "prob": round(float(probs[a, b]), 5)})
    tg = pd.DataFrame(trows)

    # descriptores de Fase A (tras cada extremo)
    desc = []
    in_phase = False
    start = None
    for i in range(1, n):
        extreme_now = (k[i] <= 20) or (k[i] >= 80)
        if not in_phase and extreme_now:
            in_phase = True; start = i
            t_fb = t_fc = t_be = None
            n_c = 0; n_b = 0; seps = []; slopes = []
        elif in_phase:
            dt = i - start
            if t_fb is None and brake[i]:
                t_fb = dt
            if t_fc is None and cross[i]:
                t_fc = dt
            if t_be is None and (k[i] <= 20 or k[i] >= 80) and i > start + 1:
                t_be = dt
            if cross[i]:
                n_c += 1
            if brake[i]:
                n_b += 1
            seps.append(abs(kd[i])); slopes.append(dk[i])
            # cierre de fase: nuevo extremo lejano o salida clara (cruce a banda opuesta)
            if (k[i] <= 20 and k[start] >= 80) or (k[i] >= 80 and k[start] <= 20) or dt > 120:
                desc.append({"duration": dt, "t_first_brake": t_fb, "t_first_cross": t_fc,
                             "t_back_extreme": t_be, "n_cross": n_c, "n_brake": n_b,
                             "max_kd_sep": round(float(np.max(seps)), 2),
                             "mean_kd_sep": round(float(np.mean(seps)), 2),
                             "mean_slope": round(float(np.mean(slopes)), 3)})
                in_phase = False
    desc_df = pd.DataFrame(desc)

    return tg, sf, desc_df


def main() -> int:
    tg, sf, desc_df = build_graph("EURUSD")
    tg.to_csv(ROOT / "reports" / "EXP-072_transitions.csv", index=False)
    sf.to_csv(ROOT / "reports" / "EXP-072_state_favorable.csv", index=False)
    desc_df.to_csv(ROOT / "reports" / "EXP-072_phaseA_descriptors.csv", index=False)

    print("=== EXP-072 — MAPA DE TRANSICIONES DE MERCADO (EURUSD REAL, descubrimiento) ===\n")
    print(f"Estados activos: {tg['from_state'].nunique()} | transiciones: {len(tg)}")
    print("\n-- Top 12 transiciones mas probables (desde estado -> siguiente) --")
    print(tg.sort_values("prob", ascending=False).head(12).to_string(index=False))
    print("\n-- Top 10 estados por tasa de movimiento favorable (H=4 velas) --")
    if not sf.empty:
        print(sf.head(10).to_string(index=False))
        sig = sf[(sf["p_adj_fdr"] < ALPHA) & (sf["favorable_rate"] > 0.55)]
        print(f"\nEstados con sesgo favorable significativo (FDR, rate>0.55): {len(sig)}")
    print("\n-- Descriptores de Fase A (tras cada extremo) --")
    if not desc_df.empty:
        print(f"Eventos de Fase A: {len(desc_df)}")
        print(desc_df.median(numeric_only=True).round(2).to_string())
    print("\nVeredicto: grafo de transiciones (no win rate unico). REAL=descubrimiento, Art.13.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
