"""EXP-POI — Evaluación del POI de la estrategia (EXP-076 / Edificio).

Pregunta: ¿las señales del gate compuesto que entran DENTRO de una zona POI
(swing_levels_causal) tienen mejor WR que las que entran fuera?

El POI es un filtro de contexto (M3 del freno): una entrada en un nivel donde
el precio ya reaccionó >= min_touches veces debería tener más probabilidad de
rebote que una entrada en zona neutra.

Evaluaciones:
  1. POI sobre el universo de DIRECCIÓN (k<=20/d<=20 CALL | k>=80/d>=80 PUT)
     -> comparación dentro/fuera con n grande.
  2. POI sobre el GATE COMPUESTO (dirección + confirmación arcoíris+válvula)
     -> el filtro de contexto aplicado a la estrategia final.
  3. POI evaluado en la vela de SEÑAL y en la vela de ENTRY.

Todo con timing real del broker (entry open[i+6], exit close[i+21]).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import exp_common as ec  # noqa: E402

BREAKEVEN = 0.54
POI_CFG = dict(min_touches=2, tol_pips=5.0, swing_k=2, lookback=100)  # defaults del módulo


def pval_binom(w, n, p0=BREAKEVEN):
    if n == 0:
        return 1.0
    return float(stats.binom.sf(w - 1, n, p0))


def trade_at(feats, j, direction):
    win, e_idx, x_idx, entry, exit_open, exit_close = ec.resolve_trade(feats, j, direction)
    return win, e_idx


def evaluate(feats, n, events, floors, ceilings, act_from, act_to):
    """events: lista de (idx_vela, direction). Compara WR dentro vs fuera del POI."""
    rows = []  # (dentro, win)
    for j, direction in events:
        win, e_idx = trade_at(feats, j, direction)
        if win is None:
            continue
        if e_idx is None:
            e_idx = j
        low, high = feats["low"][e_idx], feats["high"][e_idx]
        dentro = ec.in_poi_band(floors, ceilings, act_from, act_to, e_idx, low, high)
        rows.append((int(dentro), int(win)))
    if not rows:
        return None
    arr = np.array(rows)
    dentro = arr[:, 0] == 1
    n_d, n_f = int(dentro.sum()), int((~dentro).sum())
    w_d = int(arr[dentro, 1].sum())
    w_f = int(arr[~dentro, 1].sum())
    wr_d = 100.0 * w_d / n_d if n_d else float("nan")
    wr_f = 100.0 * w_f / n_f if n_f else float("nan")
    # test de diferencia de proporciones (una cola: dentro > fuera)
    p_diff = float(stats.binomtest(w_d, n_d, wr_f / 100.0, alternative="greater").pvalue) if (n_d and n_f and wr_f > 0) else 1.0
    return {"n_dentro": n_d, "n_fuera": n_f, "wr_dentro": round(wr_d, 1), "wr_fuera": round(wr_f, 1),
            "wins_dentro": w_d, "wins_fuera": w_f, "p_dentro_vs54": pval_binom(w_d, n_d),
            "p_dentro_vs_fuera": p_diff}


def universo_direccion(feats, n):
    """Todas las velas con dirección de extremo (universo de la señal)."""
    events = []
    for i in range(n):
        k, d = feats["k"][i], feats["d"][i]
        if k != k or d != d:
            continue
        direction = ec.derive_direction(k, d)
        if direction is not None:
            events.append((i, direction))
    return events


def universo_gate(feats, n, max_hold=15, evol_velas=3):
    """Señales del gate compuesto: dirección + confirmación arcoíris+válvula en (i, i+hold]."""
    events = []
    for i in range(n):
        k, d = feats["k"][i], feats["d"][i]
        if k != k or d != d:
            continue
        direction = ec.derive_direction(k, d)
        if direction is None:
            continue
        for j in range(i + 1, min(i + 1 + max_hold, n)):
            kj, dj = feats["k"][j], feats["d"][j]
            if kj != kj or dj != dj:
                continue
            if direction == "CALL":
                salio = kj > ec.EXTREME_LO
            else:
                salio = kj < ec.EXTREME_HI
            if not salio or abs(kj - dj) < ec.DESVIO:
                continue
            kd_hist = [abs(feats["k"][t] - feats["d"][t])
                       for t in range(max(0, j - evol_velas), j + 1)
                       if not (feats["k"][t] != feats["k"][t] or feats["d"][t] != feats["d"][t])]
            if len(kd_hist) >= 2 and not all(kd_hist[t] <= kd_hist[t + 1] for t in range(len(kd_hist) - 1)):
                continue
            ema_vals = [feats[f"ema{p}"][j] for p in ec.EMA_PERIODS]
            if not ec.arcoiris_alineado(feats["close"][j], ema_vals, direction):
                continue
            events.append((j, direction))
            break
    return events


def main():
    df = ec.load_otc_60s()
    feats, n = ec.build_features(df)
    print(f"Velas: {n}  ({df['datetime'].iloc[0]} -> {df['datetime'].iloc[-1]})")

    # POIs causales sobre 60s
    floors, ceilings, act_from, act_to = ec.swing_levels_causal(
        feats["high"], feats["low"], **POI_CFG)
    print(f"Bandas POI (60s): {floors.size}  | velas dentro de alguna zona activa: "
          f"{sum(1 for i in range(n) if ec.in_poi_band(floors, ceilings, act_from, act_to, i, feats['low'][i], feats['high'][i]))}")

    universos = {
        "UNIVERSO DIRECCIÓN (extremo K/D)": universo_direccion(feats, n),
        "GATE COMPUESTO (dir+arcoíris+válvula)": universo_gate(feats, n),
    }
    print(f"\n=== Evaluación POI (bandas 60s, tol=5 pips, min_touches=2, lookback=100) ===\n")
    for name, events in universos.items():
        r = evaluate(feats, n, events, floors, ceilings, act_from, act_to)
        print(f"{name}:  eventos={len(events)}")
        if r is None:
            print("   (sin trades válidos)")
            continue
        print(f"   DENTRO : n={r['n_dentro']:6d}  WR={r['wr_dentro']}%  wins={r['wins_dentro']}  "
              f"p_vs54={r['p_dentro_vs54']:.4f}")
        print(f"   FUERA  : n={r['n_fuera']:6d}  WR={r['wr_fuera']}%  wins={r['wins_fuera']}")
        print(f"   p(dentro > fuera)={r['p_dentro_vs_fuera']:.4f}")
        print()

    # Sensibilidad: POI con parámetros más estrictos (más toques, menos tol)
    print("=== Sensibilidad de parámetros POI sobre el GATE COMPUESTO ===")
    events_gate = universos["GATE COMPUESTO (dir+arcoíris+válvula)"]
    for cfg in (dict(min_touches=2, tol_pips=3.0, swing_k=2, lookback=100),
                dict(min_touches=3, tol_pips=5.0, swing_k=2, lookback=100),
                dict(min_touches=2, tol_pips=5.0, swing_k=2, lookback=200)):
        fl, ce, af, at = ec.swing_levels_causal(feats["high"], feats["low"], **cfg)
        r = evaluate(feats, n, events_gate, fl, ce, af, at)
        tag = f"touches={cfg['min_touches']} tol={cfg['tol_pips']} lookback={cfg['lookback']}"
        if r:
            print(f"  {tag}: bandas={fl.size}  DENTRO n={r['n_dentro']} WR={r['wr_dentro']}%  "
                  f"FUERA n={r['n_fuera']} WR={r['wr_fuera']}%  p_diff={r['p_dentro_vs_fuera']:.4f}")
        else:
            print(f"  {tag}: sin trades")


if __name__ == "__main__":
    main()
