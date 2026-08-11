"""VISUAL-ESTRATEGIA — gráfica paso a paso de la estrategia (EXP-076/Edificio).

Genera una secuencia de 7 PNG: cada paso de la estrategia sobre la MISMA
señal real (gate compuesto + POI), con el estocástico FULL y el arcoíris 7-EMA.

Paso 1: Estocástico FULL 14,3,3 -> zona extremo (dirección)
Paso 2: K-D saludable (separación >= DESVIO, creciente)
Paso 3: K sale del extremo (válvula abierta)
Paso 4: Arcoíris 7-EMA alineado a favor
Paso 5: Gate compuesto completo -> SEÑAL
Paso 6: Timing broker: entry open[i+6] (t+300s) -> exit close[i+21] (t+1200s)
Paso 7: Resultado del trade + contexto POI

Requiere matplotlib. Determinista (seed fija).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import exp_common as ec  # noqa: E402

OUT = Path(__file__).resolve().parent
EMA_COLORS = ["#d62728", "#ff7f0e", "#ffd700", "#2ca02c", "#1f77b4", "#9467bd", "#8c564b"]
POI_CFG = dict(min_touches=2, tol_pips=5.0, swing_k=2, lookback=100)

PASOS = [
    ("01_estocastico_extremo", "Paso 1 - Estocastico FULL 14,3,3: zona de extremo (direccion)"),
    ("02_kd_separacion", "Paso 2 - Separacion K-D >= DESVIO y creciente (presion)"),
    ("03_valvula_sale", "Paso 3 - Valvula: K sale del extremo en direccion del trade"),
    ("04_arcoiris_alineado", "Paso 4 - Arcoiris 7-EMA alineado a favor"),
    ("05_senal_gate", "Paso 5 - Gate compuesto completo: SENAL"),
    ("06_timing_broker", "Paso 6 - Timing broker: entry open[t+300] -> exit close[t+1200]"),
    ("07_resultado_poi", "Paso 7 - Resultado del trade + contexto POI"),
]


def find_signal(feats, n, min_kd_sep=5.0, hold=15, evol=3, within_poi=True):
    """Busca la primera señal del gate compuesto (opcionalmente dentro de POI)."""
    floors, ceilings, act_from, act_to = ec.swing_levels_causal(
        feats["high"], feats["low"], **POI_CFG)
    for i in range(200, n - 30):
        k, d = feats["k"][i], feats["d"][i]
        if k != k or d != d:
            continue
        direction = ec.derive_direction(k, d)
        if direction is None:
            continue
        for j in range(i + 1, min(i + 1 + hold, n)):
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
                       for t in range(max(0, j - evol), j + 1)
                       if not (feats["k"][t] != feats["k"][t] or feats["d"][t] != feats["d"][t])]
            if len(kd_hist) >= 2 and not all(kd_hist[t] <= kd_hist[t + 1] for t in range(len(kd_hist) - 1)):
                continue
            ema_vals = [feats[f"ema{p}"][j] for p in ec.EMA_PERIODS]
            if not ec.arcoiris_alineado(feats["close"][j], ema_vals, direction):
                continue
            if within_poi:
                lo, hi = feats["low"][j], feats["high"][j]
                if not ec.in_poi_band(floors, ceilings, act_from, act_to, j, lo, hi):
                    continue
            return i, j, direction, (floors, ceilings, act_from, act_to)
    return None


def setup_ax(ax, feats, ts, title):
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_ylabel("Precio")
    ax.set_xlabel("Hora (UTC)")
    ax.grid(alpha=0.3, ls=":")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    return ax


def draw_kd(ax, feats, i0, i1, mark=None, label=""):
    k, d = feats["k"][i0:i1 + 1], feats["d"][i0:i1 + 1]
    x = np.arange(i0, i1 + 1)
    ax.plot(x, k, color="#1f77b4", lw=1.5, label=f"K  {label}")
    ax.plot(x, d, color="#ff7f0e", lw=1.5, label=f"D  {label}")
    ax.axhline(20, color="gray", lw=0.8, ls=":")
    ax.axhline(80, color="gray", lw=0.8, ls=":")
    if mark is not None:
        ax.axvline(mark, color="green", lw=1.2, ls="--", alpha=0.8)


def main():
    df = ec.load_otc_60s()
    feats, n = ec.build_features(df)
    dt = df["datetime"].to_numpy()

    found = find_signal(feats, n, within_poi=True)
    if found is None:
        print("No se encontró señal del gate dentro de POI")
        return
    i_sig, j_ent, direction, (floors, ceilings, act_from, act_to) = found
    win, e_idx, x_idx, entry, exit_open, exit_close = ec.resolve_trade(feats, j_ent, direction)
    print(f"Señal encontrada: dirección={direction} vela_signal={i_sig} vela_gate={j_ent} "
          f"entry_idx={e_idx} exit_idx={x_idx} win={win}")
    print(f"  Tiempo señal: {dt[j_ent]} | entry: {dt[e_idx]} | exit: {dt[x_idx]}")

    # ventana de graficado
    i0 = max(0, j_ent - 90)
    i1 = min(n - 1, x_idx + 15)
    x = np.arange(i0, i1 + 1)
    o, h, l, c = feats["open"], feats["high"], feats["low"], feats["close"]

    # ---- banda POI activa en la entrada ----
    poi_lo = poi_hi = None
    for f, ce, a, b in zip(floors, ceilings, act_from, act_to):
        if a <= e_idx < b and l[e_idx] <= ce and h[e_idx] >= f:
            poi_lo, poi_hi = f, ce
            break

    plt.rcParams["font.size"] = 9
    for k_png, (fname, title) in enumerate(PASOS, start=1):
        fig, (axp, axk) = plt.subplots(2, 1, figsize=(13, 7), sharex=True,
                                       gridspec_kw={"height_ratios": [3, 1]})
        fig.subplots_adjust(hspace=0.08)

        # --- precio (candlestick simplificado) ---
        colors = ["#2ca02c" if c[i] >= o[i] else "#d62728" for i in x]
        for t, i in enumerate(x):
            axp.vlines(t, l[i], h[i], color=colors[t], lw=0.7)
            axp.vlines(t, min(o[i], c[i]), max(o[i], c[i]), color=colors[t], lw=2.2)
        # EMAs
        for pidx, p in enumerate(ec.EMA_PERIODS):
            axp.plot(x - i0, feats[f"ema{p}"][x], color=EMA_COLORS[pidx], lw=0.8, alpha=0.9,
                     label=f"EMA{p}")
        # banda POI
        if poi_lo is not None:
            axp.axhspan(poi_lo, poi_hi, color="orange", alpha=0.18)
            axp.text(i1 - i0 - 2, (poi_lo + poi_hi) / 2, "POI", fontsize=9, color="#b3540a",
                     ha="right", va="center", bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.8))

        # marcadores según el paso
        if k_png >= 1:
            axp.scatter(j_ent - i0, c[j_ent], marker="o", s=80, color="blue", zorder=5,
                        label="Señal (vela gate)")
        if k_png >= 5:
            axp.scatter(j_ent - i0, c[j_ent], marker="*", s=260, color="magenta", zorder=6,
                        label="SEÑAL COMPUESTA")
        if k_png >= 6:
            axp.scatter(e_idx - i0, entry, marker="^", s=110, color="#00a2ff", zorder=6,
                        label=f"ENTRY open (t+300)")
            axp.scatter(x_idx - i0, exit_close, marker="v", s=110, color="#ff5722", zorder=6,
                        label=f"EXIT close (t+1200)")
            axp.axvspan(e_idx - i0, x_idx - i0, color="gold", alpha=0.12)
        if k_png >= 7:
            lbl = "WIN" if win else "LOSS"
            col = "#2ca02c" if win else "#d62728"
            axp.text(x_idx - i0 + 1, exit_close, f"{lbl}", color=col, fontsize=12, fontweight="bold")
            axp.annotate("", xy=(x_idx - i0, exit_close), xytext=(e_idx - i0, entry),
                         arrowprops=dict(arrowstyle="-|>", color=col, lw=1.8))
        setup_ax(axp, feats, dt, f"[{direction}] {title}")
        axp.legend(fontsize=7, loc="upper left", ncol=4)

        # --- estocástico ---
        draw_kd(axk, feats, i0, i1)
        axk.axhline(50, color="gray", lw=0.6, ls=":")
        axk.set_ylabel("K/D 14,3,3")
        axk.legend(fontsize=7, loc="upper left")
        axk.set_ylim(-5, 105)
        if k_png >= 6:
            axk.axvline(e_idx - i0, color="#00a2ff", lw=1.2, ls="--")
            axk.axvline(x_idx - i0, color="#ff5722", lw=1.2, ls="--")

        # ticks de fecha real
        ticks = np.linspace(i0, i1, min(8, i1 - i0 + 1)).astype(int)
        axk.set_xticks(ticks - i0)
        axk.set_xticklabels([pd_to_str(dt[t]) for t in ticks], rotation=0)

        png = OUT / f"paso_{k_png}_{fname}.png"
        fig.savefig(png, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"  [{k_png}/7] {png.name}")


def pd_to_str(ts):
    s = str(ts)
    return s[11:16] if len(s) > 16 else s


if __name__ == "__main__":
    import pandas as pd
    main()
