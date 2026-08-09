"""AUDITORÍA MULTI-TF — Arcoíris M15 (tendencia) + señal/trigger M5.

Hipótesis: el arcoíris de 7 EMAs en M15 captura la tendencia real (71% WR en
EXP-EDF-04 como gate P3). El M5 es ruidoso solo. Combinar: la dirección la da el
arcoíris M15; el timing de entrada lo da el M5 (freno + salida estocástica).
Expiración = 15min (3 velas M5 tras entry).

Modos:
  arc_signal     : señal cuando el arcoíris M15 alinea (CALL/PUT); entry M5 +1, exit +3.
  arc_filter_m5  : trigger M5 (freno + stoch exit_ext) SOLO si coincide con arcoíris M15.
  arc_filter_m5k : igual pero exige arcoíris alineado en K velas M15 consecutivas.
  arc_bias_m5dir : arcoíris da bias (CALL/PUT/None); M5 stoch da dirección; requiere acuerdo.

Uso:
  python scripts/audit_multitf.py <AÑO> <PAR> [modo] [k_persist] [entry_off] [exit_off]
  modo "grid" corre todos los modos y offsets.
"""
from __future__ import annotations
import sys, math
from pathlib import Path

try:
    import logging
    logging.disable(logging.CRITICAL)
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from audit_edificio_funnel import compute_stoch_full, load_csv_year

DATA_ROOT = Path(r"C:\Users\v_jac\Desktop\backtest quotex\datos de velas\data")
if not DATA_ROOT.exists():
    DATA_ROOT = Path(r"C:\Users\v_jac\Desktop\backtest quotex\datos de velas\data")

EMA_PERIODS = [5, 10, 20, 40, 80, 160, 320]


def compute_emas(closes, periods=EMA_PERIODS):
    out = []
    for p in periods:
        alpha = 2.0 / (p + 1.0)
        ema = [0.0] * len(closes)
        for t in range(len(closes)):
            ema[t] = closes[t] if t == 0 else alpha * closes[t] + (1 - alpha) * ema[t - 1]
        out.append(ema)
    return out


def arcoiris_direction(close, ema_vals):
    """CALL si close>EMA5>...>EMA320; PUT si close<EMA5<...<EMA320; None si mixto."""
    e = list(ema_vals)
    up = all(close >= e[i] and e[i] >= e[i + 1] for i in range(len(e) - 1))
    if up:
        return "CALL"
    dn = all(close <= e[i] and e[i] <= e[i + 1] for i in range(len(e) - 1))
    if dn:
        return "PUT"
    return None


def load_m(par, tf, year):
    df = load_csv_year(DATA_ROOT / par / tf, year).reset_index(drop=True)
    return [{"ts": str(r.timestamp), "o": float(r.open), "h": float(r.high),
             "l": float(r.low), "c": float(r.close)} for r in df.itertuples()]


def build_m15_arc(m15):
    closes = [r["c"] for r in m15]
    emas = compute_emas(closes)
    n = len(m15)
    dirs = []
    for i in range(n):
        ev = [emas[k][i] for k in range(len(emas))]
        dirs.append(arcoiris_direction(m15[i]["c"], ev))
    return dirs, emas


def m15_index_for_m5(m5row_ts, m15_ts_list):
    """Índice M15 cuyo ts es el bucket de 15min que contiene el ts M5."""
    # ts son strings ISO; tomamos los primeros 15 chars (YYYY-MM-DDTHH:MM)
    bucket = m5row_ts[:16]
    # ajustar a múltiplo de 15 min
    mm = int(bucket[14:16])
    mm = (mm // 15) * 15
    target = bucket[:14] + f"{mm:02d}"
    # búsqueda binaria simple
    lo, hi = 0, len(m15_ts_list) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if m15_ts_list[mid] == target:
            return mid
        elif m15_ts_list[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return max(0, min(hi if hi >= 0 else 0, len(m15_ts_list) - 1))


def build_m5_ctx(m5):
    n = len(m5)
    highs = [r["h"] for r in m5]
    lows = [r["l"] for r in m5]
    closes = [r["c"] for r in m5]
    k_list, d_list = compute_stoch_full(highs, lows, closes)
    ctx = []
    for i in range(n):
        rng = (m5[i]["h"] - m5[i]["l"]) if (m5[i]["h"] - m5[i]["l"]) > 0 else 0.0
        prev_rng = (m5[i - 1]["h"] - m5[i - 1]["l"]) if i > 0 else 0.0
        brake = (prev_rng > 0) and (rng < prev_rng * 0.6)
        ctx.append({"k": k_list[i], "d": d_list[i], "brake": brake,
                    "close": closes[i],
                    "k_prev": k_list[i - 1] if i > 0 else k_list[i]})
    return ctx, k_list, d_list


def run_mode(m5, m5ctx, m15_dirs, m15_ts_list, mode, k_persist=1, entry_off=1, exit_off=3,
              ema5_m=None):
    n = len(m5)
    signals = []
    for i in range(1, n):
        c = m5ctx[i]
        k, d = c["k"], c["d"]
        if k != k or d != d:
            continue
        midx = m15_index_for_m5(m5[i]["ts"], m15_ts_list)
        arc_dir = m15_dirs[midx]
        # persistencia de arcoíris
        if k_persist > 1:
            ok_persist = True
            for pp in range(k_persist):
                jj = midx - pp
                if jj < 0 or m15_dirs[jj] != arc_dir or arc_dir is None:
                    ok_persist = False
                    break
            if not ok_persist:
                arc_dir = None
        direction = None
        if mode == "arc_signal":
            direction = arc_dir
        elif mode == "arc_filter_m5":
            if not c["brake"]:
                continue
            if arc_dir is None:
                continue
            if k > 20.0 and k >= c["k_prev"]:
                m5dir = "CALL"
            elif k < 80.0 and k <= c["k_prev"]:
                m5dir = "PUT"
            else:
                continue
            if m5dir == arc_dir:
                direction = m5dir
        elif mode == "arc_bias_m5dir":
            if arc_dir is None:
                continue
            m5dir = "CALL" if k >= d else "PUT"
            if m5dir == arc_dir:
                direction = m5dir
        elif mode == "mtf_both":
            # arcoíris M15 alineado Y arcoíris M5 fast alineado, misma dir
            if arc_dir is None:
                continue
            e = [ema5_m[kk][i] for kk in range(len(ema5_m))]
            if arc_dir == "CALL" and not (e[0] > e[2] > e[6]):
                continue
            if arc_dir == "PUT" and not (e[0] < e[2] < e[6]):
                continue
            direction = arc_dir
        elif mode == "mtf_pull":
            # arcoíris M15 da bias; M5 entry en pullback: precio tocó EMA20 M5 y rebota
            if arc_dir is None:
                continue
            e20 = ema5_m[2][i]
            prev_c = m5[i - 1]["c"] if i > 0 else c["close"]
            if arc_dir == "CALL":
                if not (prev_c <= e20 * 1.0005 and c["close"] > e20):
                    continue
            else:
                if not (prev_c >= e20 * 0.9995 and c["close"] < e20):
                    continue
            direction = arc_dir
        elif mode == "mtf_cross_ema":
            # arcoíris M15 alineado + M5 cruza EMA20 en dir del arcoíris
            if arc_dir is None:
                continue
            e20 = ema5_m[2][i]
            e20p = ema5_m[2][i - 1] if i > 0 else e20
            if arc_dir == "CALL" and not (m5[i - 1]["c"] <= e20p and c["close"] > e20):
                continue
            if arc_dir == "PUT" and not (m5[i - 1]["c"] >= e20p and c["close"] < e20):
                continue
            direction = arc_dir
        elif mode == "mtf_cross_ema_s":
            # mtf_cross_ema + estocástico M5 saliendo de extremo
            if arc_dir is None:
                continue
            e20 = ema5_m[2][i]
            e20p = ema5_m[2][i - 1] if i > 0 else e20
            if arc_dir == "CALL" and not (m5[i - 1]["c"] <= e20p and c["close"] > e20):
                continue
            if arc_dir == "PUT" and not (m5[i - 1]["c"] >= e20p and c["close"] < e20):
                continue
            if arc_dir == "CALL" and not (k > 20.0 and k >= c["k_prev"]):
                continue
            if arc_dir == "PUT" and not (k < 80.0 and k <= c["k_prev"]):
                continue
            direction = arc_dir
        elif mode == "mtf_cross_ema_strong":
            # mtf_cross_ema pero cruce "fuerte": close X% sobre EMA20
            if arc_dir is None:
                continue
            e20 = ema5_m[2][i]
            e20p = ema5_m[2][i - 1] if i > 0 else e20
            if arc_dir == "CALL":
                if not (m5[i - 1]["c"] <= e20p and c["close"] > e20 * 1.0003):
                    continue
            else:
                if not (m5[i - 1]["c"] >= e20p and c["close"] < e20 * 0.9997):
                    continue
            direction = arc_dir
        if direction is None:
            continue
        signals.append((i, direction))
    w = l = 0
    for (i, direction) in signals:
        ei = i + entry_off
        xi = i + exit_off
        if xi >= n:
            continue
        entry = m5[ei]["c"]
        exitp = m5[xi]["c"]
        if (direction == "CALL" and exitp > entry) or (direction == "PUT" and exitp < entry):
            w += 1
        else:
            l += 1
    return len(signals), w, l


def binom_p(n, k, p=0.5):
    if n == 0:
        return 1.0
    if n > 1000:
        from math import erf, sqrt
        p_hat = k / n
        se = sqrt(0.25 / n)
        if se == 0:
            return 0.0
        z = abs(p_hat - 0.5) / se
        return 2.0 * (1.0 - 0.5 * (1.0 + erf(z / sqrt(2.0))))
    from math import comb
    pe = lambda x: comb(n, x) * (0.5 ** n)
    pk = pe(k)
    return min(1.0, sum(pe(x) for x in range(n + 1) if pe(x) <= pk + 1e-12))


MODES = ["arc_signal", "arc_filter_m5", "arc_bias_m5dir", "mtf_both", "mtf_pull", "mtf_cross_ema", "mtf_cross_ema_b", "mtf_cross_ema_s", "mtf_cross_ema_strong"]
OFFS = [(1, 3), (1, 2), (2, 4), (1, 4)]


def main():
    year = sys.argv[1] if len(sys.argv) > 1 else "2024"
    par = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
    mode = sys.argv[3] if len(sys.argv) > 3 else "grid"
    kp = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    eo = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    xo = int(sys.argv[6]) if len(sys.argv) > 6 else 3

    m15 = load_m(par, "M15", year)
    m5 = load_m(par, "M5", year)
    m15_dirs, _ = build_m15_arc(m15)
    m15_ts_list = [r["ts"][:16] for r in m15]
    m5ctx, _, _ = build_m5_ctx(m5)
    ema5_m = compute_emas([r["c"] for r in m5])

    if mode != "grid":
        n, w, l = run_mode(m5, m5ctx, m15_dirs, m15_ts_list, mode, kp, eo, xo, ema5_m)
        wr = w / (w + l) * 100 if (w + l) else 0.0
        print(f"mode={mode} kp={kp} eo={eo} xo={xo}: n={n} w={w} l={l} WR={wr:.1f}% p={binom_p(w+l,w):.4f}")
        return

    print(f"{'MODE':16} {'kp':>2} {'eo':>2} {'xo':>2} {'N':>6} {'WR%':>6} {'p':>8}")
    print("-" * 52)
    for m in MODES:
        for kpers in (1, 3):
            for (eo, xo) in OFFS:
                n, w, l = run_mode(m5, m5ctx, m15_dirs, m15_ts_list, m, kpers, eo, xo, ema5_m)
                wr = w / (w + l) * 100 if (w + l) else 0.0
                print(f"{m:16} {kpers:>2} {eo:>2} {xo:>2} {n:>6} {wr:>6.1f} {binom_p(w+l,w):>8.4f}")


if __name__ == "__main__":
    main()
