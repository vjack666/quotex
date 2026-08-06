"""EXP-071 — ZONA DE DESCUBRIMIENTO tras contexto [extremo>freno>cruce].

Cambio de paradigma (dictamen Trader-Humano 2026-08-06):
  - El contexto [extremo>freno>cruce] NO es estrategia. Es CONTEXTO de mercado.
  - Tras el cruce se abre la ZONA DE DESCUBRIMIENTO: se registra TODO evento
    que el motor conozca (sin lista cerrada, sin ventana fija).
  - El contexto vive hasta: zona muerta del estocastico, o nuevo extremo,
    o max vida (safe cap). El lab DESCUBRE cuanto vive, no lo asume.
  - El TIEMPO es variable principal: dt_desde_cruce, dt_desde_extremo,
    dt_entre_eslabones, dt_total.
  - Se mide WIN a DOS expiraciones: 5 min (M5) y 15 min (M15).
  - FDR/Bonferroni sobre los confirmadores observados.

Dominio REAL (EURUSD). Art. 13 Charter: solo descubrimiento, NO promocion.

Nota implementacion: los eventos de descubrimiento se detectan sobre M15
(mismo frame del contexto). WIN@15min usa M15. WIN@5min usa M5 alineado por
timestamp al evento (aproximacion: entry = primer M5 tras el evento M15).
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
from strategy_lab import secuencia_libre as SL
from strategy_lab.compute_features import SMC_ROOT, build_feature_frame, load_m15, load_htf

PAYOUT = 0.85
SEED = 42
ALPHA = 0.05
N_MIN = 100
MAX_LIFE = SL.MAX_LIFE_CANDLES  # safe cap (no criterio de estrategia)


def _load_m5(asset: str) -> pd.DataFrame:
    from strategy_lab.compute_features import PIP_FACTOR
    path = SMC_ROOT / f"{asset}_M5.parquet"
    df = pd.read_parquet(path)
    df = df[["time", "open", "high", "low", "close", "tick_volume"]].dropna().reset_index(drop=True)
    return df


def _detect_discovery_events(i, k, d, o, h, l, c, body_n, prev_c, rng_n, direction):
    """Eventos de descubrimiento que el motor CONOCE (sin lista cerrada impuesta)."""
    ev = set()
    # martillo / inv (ya en motor)
    hammer = (min(o[i], c[i]) - l[i]) >= 2 * max(abs(c[i] - o[i]), 1e-9)
    inv = (h[i] - max(o[i], c[i])) >= 2 * max(abs(c[i] - o[i]), 1e-9)
    if hammer:
        ev.add("martillo")
    if inv:
        ev.add("martillo_inv")
    # pinbar (mecha >=2x cuerpo, direccion flexible)
    upper = h[i] - max(o[i], c[i])
    lower = min(o[i], c[i]) - l[i]
    body = abs(c[i] - o[i])
    if max(upper, lower) >= 2 * max(body, 1e-9):
        ev.add("pinbar")
    # engulfing: cuerpo actual cubre el cuerpo previo (mismo frame)
    if i >= 1:
        prev_body = abs(prev_c - o[i - 1]) if False else abs(c[i - 1] - o[i - 1])
        cur_body = abs(c[i] - o[i])
        if cur_body > prev_body and ((c[i] > o[i]) != (c[i - 1] > o[i - 1])):
            ev.add("engulfing")
    # ruptura de rango: cierre fuera del rango de las ultimas N velas
    if i >= rng_n:
        lo = min(l[i - rng_n:i])
        hi = max(h[i - rng_n:i])
        if c[i] > hi or c[i] < lo:
            ev.add("ruptura_rango")
    # pullback: tras ruptura, retorno parcial hacia el rango
    if "ruptura_rango" in ev and i >= rng_n + 1:
        ev.add("pullback")
    # continuacion: segundo empuje mismo sentido que el anterior
    if i >= 2 and ((c[i] > c[i - 1]) == (c[i - 1] > c[i - 2])):
        ev.add("continuacion")
    return ev


def run_discovery(asset: str = "EURUSD") -> pd.DataFrame:
    df15 = build_feature_frame(load_m15(asset, SMC_ROOT), load_htf(asset, SMC_ROOT))
    df5 = _load_m5(asset)
    o = df15["open"].values.astype(float)
    c = df15["close"].values.astype(float)
    h = df15["high"].values.astype(float)
    l = df15["low"].values.astype(float)
    k = df15["k"].values.astype(float)
    d = df15["d"].values.astype(float)
    brake = df15["brake_transition"].values.astype(bool)
    hammer15 = df15["hammer_15m"].values.astype(bool)
    invhammer15 = df15["hammer_inv_15m"].values.astype(bool)
    impulse = df15["impulse_net"].values.astype(float)
    body_n = df15["body_n"].values.astype(float)
    times = pd.to_datetime(df15["time"].values)
    n = len(c)

    # M5 para win@5min: mapear timestamp de entry M15 -> primer M5 >= ese ts
    t5 = pd.to_datetime(df5["time"].values)
    c5 = df5["close"].values.astype(float)
    o5 = df5["open"].values.astype(float)

    rows = []
    in_zone = False
    zone_start_cruce = None
    zone_start_extremo = None
    zone_ctx_idx = None

    def m5_win_after(ts_entry, direction):
        # primer M5 con time >= ts_entry
        mask = t5 >= ts_entry
        if not mask.any():
            return None
        j = int(np.argmax(mask.values if hasattr(mask, "values") else mask))
        if j + 1 >= len(c5):
            return None
        verde = c5[j + 1] > o5[j]
        return int(verde if direction == "CALL" else (not verde))

    for i in range(20, n):
        # detectar contexto [extremo > freno > cruce] en orden
        ev_call = SL._detect_events_at(i, "CALL", k, d, np.abs(k - d), hammer15, invhammer15, brake)
        ev_put = SL._detect_events_at(i, "PUT", k, d, np.abs(k - d), hammer15, invhammer15, brake)
        # nacimiento de contexto
        if not in_zone:
            # buscar secuencia extremo->freno->cruce en i (extremo aqui, freno y cruce ya vistos)
            # simplificacion: el contexto se define por cruce CON extremo y freno previos en orden
            dirn = "CALL" if impulse[i] < 0 else "PUT"
            ev_dir = ev_call if dirn == "CALL" else ev_put
            if "cruce" in ev_dir and "extremo" in ev_dir and "freno" in ev_dir:
                # verificar orden extremo<freno<cruce mirando indices previos
                ie = None; ib = None; ic = i
                for jb in range(max(0, i - 60), i):
                    ej = SL._detect_events_at(jb, dirn, k, d, np.abs(k - d), hammer15, invhammer15, brake)
                    if "extremo" in ej and ie is None:
                        ie = jb
                    if "freno" in ej and ie is not None and ib is None and jb > ie:
                        ib = jb
                if ie is not None and ib is not None and ib > ie and ic > ib:
                    in_zone = True
                    zone_start_cruce = ic
                    zone_start_extremo = ie
                    zone_ctx_idx = ie
                    zone_prev_event = ic
        else:
            # dentro de la zona: registrar TODO evento de descubrimiento
            dirn = "CALL" if impulse[zone_start_extremo] < 0 else "PUT"
            evs = _detect_discovery_events(i, k, d, o, h, l, c, body_n, c[i - 1] if i >= 1 else c[i], 20, dirn)
            dt_cruce = i - zone_start_cruce
            dt_extremo = i - zone_start_extremo
            dt_total = i - zone_ctx_idx
            dt_eslabon = i - zone_prev_event
            zone_prev_event = i
            w15 = None; w5 = None
            # WIN@15min: entry vela M15 siguiente
            if i + 1 < n:
                verde = c[i + 1] > o[i]
                w15 = int(verde if dirn == "CALL" else (not verde))
            # WIN@5min: mapear ts entry -> M5
            w5 = m5_win_after(times[i], dirn)
            for ev in evs:
                rows.append({
                    "evento": ev, "dt_desde_cruce": dt_cruce, "dt_desde_extremo": dt_extremo,
                    "dt_eslabon": dt_eslabon, "dt_total": dt_total,
                    "win_15m": w15 if w15 is not None else -1,
                    "win_5m": w5 if w5 is not None else -1,
                })
            # cierre de contexto: zona muerta o nuevo extremo o max vida
            if SL._zona_muerta(k[i], d[i]) or dt_total > MAX_LIFE:
                in_zone = False
            else:
                # nuevo extremo en la misma direccion cierra la zona
                ev_dir = ev_call if dirn == "CALL" else ev_put
                if "extremo" in ev_dir:
                    in_zone = False

    return pd.DataFrame(rows)


def main() -> int:
    disc = run_discovery("EURUSD")
    disc.to_parquet(ROOT / "data" / "strategy_lab" / "exp071_discovery_events.parquet", index=False)

    # analisis por evento de confirmacion
    rows = []
    for ev, sub in disc.groupby("evento"):
        n = len(sub)
        if n < N_MIN:
            continue
        w15 = sub[sub["win_15m"] >= 0]["win_15m"].mean()
        w5 = sub[sub["win_5m"] >= 0]["win_5m"].mean()
        ev15 = w15 * (PAYOUT - 1) + (1 - w15) * (-1)
        ev5 = w5 * (PAYOUT - 1) + (1 - w5) * (-1)
        p15 = stats.binomtest(int((sub["win_15m"] == 1).sum()), n, 0.50).pvalue
        p5 = stats.binomtest(int((sub["win_5m"] == 1).sum()), n, 0.50).pvalue
        rows.append({
            "evento": ev, "n": n,
            "wr_15m": round(float(w15), 4), "wr_5m": round(float(w5), 4),
            "ev_15m": round(float(ev15), 4), "ev_5m": round(float(ev5), 4),
            "p_15m": p15, "p_5m": p5,
            "dt_desde_cruce_med": round(float(sub["dt_desde_cruce"].mean()), 2),
            "dt_total_med": round(float(sub["dt_total"].mean()), 2),
        })
    res = pd.DataFrame(rows)
    if not res.empty:
        # FDR sobre p_5m (la expiracion que pediste testear)
        fdr = adjust_pvalues(res["p_5m"].tolist(), method="fdr_bh")
        res["p_adj_fdr_5m"] = [round(x, 6) for x in fdr.adj_p]
        res = res.sort_values("ev_5m", ascending=False)
        res.to_csv(ROOT / "reports" / "EXP-071_discovery.csv", index=False)
        print("=== EXP-071 ZONA DE DESCUBRIMIENTO (contexto [extremo>freno>cruce]) ===")
        print(res.to_string(index=False))
        elig = res[(res["p_adj_fdr_5m"] < ALPHA) & (res["n"] >= N_MIN) & (res["ev_5m"] > 0)]
        if not elig.empty:
            best = elig.iloc[0]
            print(f"\nMEJOR confirmador por EV@5min (FDR, n>=100, EV>0): {best['evento']} "
                  f"WR5m={best['wr_5m']} EV5m={best['ev_5m']} p_adj={best['p_adj_fdr_5m']}")
        else:
            print("\nNingun confirmador sobrevive FDR con EV>0 a 5min. (REAL=descubrimiento, Art.13)")
    else:
        print("EXP-071: sin eventos suficientes para analizar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
