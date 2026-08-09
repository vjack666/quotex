"""AUDITORÍA M15 PURA — Arcoíris M15 + freno M15 + cruce EMA20 M15 (señal M15).

Hipótesis: el edge de EXP-EDF-04 (arcoíris M15 = 71% WR) puede MEJORARSE añadiendo
filtros de timing M15: freno (compresión de rango) + cruce de precio sobre EMA20 M15.
Entry/exit EN M15 (eo=1 = +15min, xo=2 = +30min).
Esto es la "señal en M15" que el usuario pidió originalmente pero con el arcoíris como
puerta estricta (la lección de EXP-EDF-04).

Uso:
  python scripts/audit_m15_pure.py <AÑO> <PAR> [grid|modo] [kp]
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
from audit_multitf import compute_emas, arcoiris_direction

DATA_ROOT = Path(r"C:\Users\v_jac\Desktop\backtest quotex\datos de velas\data")
if not DATA_ROOT.exists():
    DATA_ROOT = Path(r"C:\Users\v_jac\Desktop\backtest quotex\datos de velas\data")

EMA_PERIODS = [5, 10, 20, 40, 80, 160, 320]


def load_m(par, tf, year):
    df = load_csv_year(DATA_ROOT / par / tf, year).reset_index(drop=True)
    return [{"ts": str(r.timestamp), "o": float(r.open), "h": float(r.high),
             "l": float(r.low), "c": float(r.close)} for r in df.itertuples()]


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


def run(m15, m15_dirs, ema15, brake15, mode, kp=1, eo=1, xo=2):
    n = len(m15)
    signals = []
    for i in range(2, n):
        arc_dir = m15_dirs[i]
        if kp > 1:
            ok = True
            for pp in range(kp):
                jj = i - pp
                if jj < 0 or m15_dirs[jj] != arc_dir or arc_dir is None:
                    ok = False
                    break
            if not ok:
                continue
        if arc_dir is None:
            continue
        direction = None
        if mode == "arc_only":
            direction = arc_dir
        elif mode == "arc_freno":
            if not brake15[i]:
                continue
            direction = arc_dir
        elif mode == "arc_cross_ema":
            e20 = ema15[2][i]
            e20p = ema15[2][i - 1]
            if arc_dir == "CALL" and not (m15[i - 1]["c"] <= e20p and m15[i]["c"] > e20):
                continue
            if arc_dir == "PUT" and not (m15[i - 1]["c"] >= e20p and m15[i]["c"] < e20):
                continue
            direction = arc_dir
        elif mode == "arc_freno_cross":
            if not brake15[i]:
                continue
            e20 = ema15[2][i]
            e20p = ema15[2][i - 1]
            if arc_dir == "CALL" and not (m15[i - 1]["c"] <= e20p and m15[i]["c"] > e20):
                continue
            if arc_dir == "PUT" and not (m15[i - 1]["c"] >= e20p and m15[i]["c"] < e20):
                continue
            direction = arc_dir
        if direction is None:
            continue
        signals.append((i, direction))
    w = l = 0
    for (i, direction) in signals:
        ei = i + eo
        xi = i + xo
        if xi >= n:
            continue
        entry = m15[ei]["c"]
        exitp = m15[xi]["c"]
        if (direction == "CALL" and exitp > entry) or (direction == "PUT" and exitp < entry):
            w += 1
        else:
            l += 1
    return len(signals), w, l


def main():
    year = sys.argv[1] if len(sys.argv) > 1 else "2024"
    par = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
    mode = sys.argv[3] if len(sys.argv) > 3 else "grid"
    kp = int(sys.argv[4]) if len(sys.argv) > 4 else 1

    m15 = load_m(par, "M15", year)
    n = len(m15)
    closes = [r["c"] for r in m15]
    ema15 = compute_emas(closes)
    m15_dirs = [arcoiris_direction(m15[i]["c"], [ema15[k][i] for k in range(len(ema15))]) for i in range(n)]
    brake15 = []
    for i in range(n):
        rng = (m15[i]["h"] - m15[i]["l"]) if (m15[i]["h"] - m15[i]["l"]) > 0 else 0.0
        prev_rng = (m15[i - 1]["h"] - m15[i - 1]["l"]) if i > 0 else 0.0
        brake15.append((prev_rng > 0) and (rng < prev_rng * 0.6))

    MODES = ["arc_only", "arc_freno", "arc_cross_ema", "arc_freno_cross"]
    OFFS = [(1, 2), (1, 3), (2, 4)]
    if mode != "grid":
        nn, w, l = run(m15, m15_dirs, ema15, brake15, mode, kp)
        wr = w / (w + l) * 100 if (w + l) else 0.0
        print(f"mode={mode} kp={kp}: n={nn} w={w} l={l} WR={wr:.1f}% p={binom_p(w+l,w):.4f}")
        return
    print(f"{'MODE':16} {'kp':>2} {'eo':>2} {'xo':>2} {'N':>6} {'WR%':>6} {'p':>8}")
    print("-" * 52)
    for m in MODES:
        for kpers in (1, 3):
            for (eo, xo) in OFFS:
                nn, w, l = run(m15, m15_dirs, ema15, brake15, m, kpers, eo, xo)
                wr = w / (w + l) * 100 if (w + l) else 0.0
                print(f"{m:16} {kpers:>2} {eo:>2} {xo:>2} {nn:>6} {wr:>6.1f} {binom_p(w+l,w):>8.4f}")


if __name__ == "__main__":
    main()
