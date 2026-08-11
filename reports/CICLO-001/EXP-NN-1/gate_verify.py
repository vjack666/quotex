"""gate_verify.py — Verificación: ¿la reconstrucción del gate reproduce el EXP-076?

Flujo fiel al audit_exp_edf.py (P3 -> CONTRATADO):
  1. Señal: vela i donde la dirección del Edificio está activa (k<=20&&d<=20 -> CALL,
     k>=80&&d>=80 -> PUT). (derive_direction)
  2. Confirmación: buscar la vela j en (i, i+MAX_HOLD] donde el gate compuesto se abre:
     arcoíris 7-EMA alineado a favor + válvula (K salió del extremo + |K-D|>=DESVIO
     + separación creciente en ventana EVOLVE).
  3. Timing: señal en j -> entry = open de la vela 60s que contiene t_j+300;
     exit = open de la vela 60s que contiene t_j+1200. WIN = close[exit] del lado.
  Objetivo EXP-076: CALL n=1962 WR=74.6% | PUT n=1695 WR=67.0%.
  Barre MAX_HOLD y EVOLVE para documentar la mejor coincidencia (o su ausencia).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import exp_common as ec  # noqa: E402


def run_flow(feats, n, max_hold, evol_velas, señal_en_cierre=True):
    """Señal por extremo -> confirmación compuesta -> timing broker."""
    wins_c = wins_p = n_c = n_p = 0
    n_sig_c = n_sig_p = 0
    for i in range(n):
        k, d = feats["k"][i], feats["d"][i]
        if k != k or d != d:
            continue
        direction = ec.derive_direction(k, d)
        if direction is None:
            continue
        n_sig_c += (direction == "CALL")
        n_sig_p += (direction == "PUT")
        opened = False
        for j in range(i + 1, min(i + 1 + max_hold, n)):
            kj, dj = feats["k"][j], feats["d"][j]
            if kj != kj or dj != dj:
                continue
            # válvula: K salió del extremo en dirección del trade
            if direction == "CALL":
                salio = kj > ec.EXTREME_LO
            else:
                salio = kj < ec.EXTREME_HI
            if not salio:
                continue
            sep = abs(kj - dj)
            if sep < ec.DESVIO:
                continue
            kd_hist = [abs(feats["k"][t] - feats["d"][t])
                       for t in range(max(0, j - evol_velas), j + 1)
                       if not (feats["k"][t] != feats["k"][t] or feats["d"][t] != feats["d"][t])]
            if len(kd_hist) >= 2 and not all(kd_hist[t] <= kd_hist[t + 1] for t in range(len(kd_hist) - 1)):
                continue
            # arcoíris alineado a favor en j
            ema_vals = [feats[f"ema{p}"][j] for p in ec.EMA_PERIODS]
            if not ec.arcoiris_alineado(feats["close"][j], ema_vals, direction):
                continue
            # gate compuesto abierto -> trade
            win, *_ = ec.resolve_trade(feats, j, direction, señal_en_cierre=señal_en_cierre)
            if win is None:
                opened = True
                break
            opened = True
            if direction == "CALL":
                n_c += 1
                wins_c += int(win)
            else:
                n_p += 1
                wins_p += int(win)
            break
        # (si no abre en max_hold, la señal se descarta -> n señal > n trade)
    return {"call": ec.wr_stats(wins_c, n_c), "put": ec.wr_stats(wins_p, n_p),
            "sig_call": n_sig_c, "sig_put": n_sig_p}


def main():
    df = ec.load_otc_60s()
    print(f"Velas: {len(df)}  ({df['datetime'].iloc[0]} -> {df['datetime'].iloc[-1]})")
    feats, n = ec.build_features(df)
    print("\n=== Verificación vs EXP-076 (CALL 74.6% n=1962 | PUT 67.0% n=1695) ===\n")

    for señal_en_cierre in (True, False):
        tag = "cierre(+60)" if señal_en_cierre else "open"
        print(f"--- Señal evaluada al {tag} ---")
        for max_hold in (10, 15, 20, 30):
            for evol in (3, 5):
                r = run_flow(feats, n, max_hold, evol, señal_en_cierre)
                c, p = r["call"], r["put"]
                print(f"  MAX_HOLD={max_hold:2d} EVOLVE={evol}: "
                      f"CALL n={c['n']:5d} WR={c['wr']}% | PUT n={p['n']:5d} WR={p['wr']}%  "
                      f"(señales {r['sig_call']}/{r['sig_put']})")
        print()

    print("Objetivo EXP-076: CALL n=1962 WR=74.6% | PUT n=1695 WR=67.0%")


if __name__ == "__main__":
    main()
