"""Universalidad de LAB-001 (muerte del empuje) y LAB-002 (tamano de zona).

PARALELO / SOLO LECTURA: lee parquets SMC-SYSTEMS directamente y re-implementa
la logica transitions_v1 localmente (NO importa src/observador a proposito,
para no pisar el frente paralelo de la Fase B).

Reproducir: .venv/Scripts/python.exe scripts/universalidad_lab.py [PAR ...]
Sin args corre todos. Pares: XAUUSD_M1 y los 8 M5.

Metodo identico a scripts/lab_001_muerte_empuje.py y lab_002_tamano_zona.py:
- maquina de estados D2/D3 (quiet_exit_v1 + transitions_v1), mismas constantes
- LAB-001: muerte total = adv_tail<=tercil inf AND ultimo/pico<0.10 AND
  cont_tail<=tercil inf (episodios con >=8 puntos de presion)
- LAB-002: terciles del tamano de zona BRAKE->RESOLUTION en pips
- walk-forward split 2020-01-01, placebo 1000 barajadas (solo pares marcados)
"""
import random
import statistics as st
import sys
import time
from collections import deque

import numpy as np
import pandas as pd

RAW = r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw"
SPLIT_2020 = 1577836800.0
PCT_PEAK_DEAD, PCT_PEAK_ALIVE = 0.10, 0.60
SEED, N_SHUFFLES = 7, 1000

# constantes transitions_v1 (src/observador/state_machine.py, copiadas adrede)
ROLLING_WINDOW = 30
QUIET_BODY_FACTOR = 2.0
QUIET_MIN_CONSECUTIVE = 3
PRESSURE_CONTINUITY = 0.7
BRAKE_PEAK_FRACTION = 0.30
BRAKE_MIN_CANDLES = 2
TRANSITION_CANDLES = 5
REBOUND_BODY_FACTOR = 2.0
STATE_TIMEOUT = 60
CONTINUITY_WINDOW = 5

# (nombre_archivo, pip, ts_start, placebo?)
PAIRS = [
    ("XAUUSD_M1", 0.1, "2019-01-01", True),
    ("AUDUSD_M5", 0.0001, None, True),
    ("EURUSD_M5", 0.0001, None, False),
    ("GBPUSD_M5", 0.0001, None, False),
    ("NZDUSD_M5", 0.0001, None, False),
    ("USDCAD_M5", 0.0001, None, False),
    ("USDCHF_M5", 0.0001, None, False),
    ("USDJPY_M5", 0.01, None, False),
    ("XAUUSD_M5", 0.1, None, False),
]


def run_machine(ts, op, hi, lo, cl):
    """Reimplementacion local de transitions_v1. Devuelve lista de episodios:
    (res_type, ts_open, adv_tail, cont_tail, last_over_peak, zone_pips_raw)."""
    episodes = []
    state = "QUIET"
    direction = 0
    window_bodies = deque(maxlen=ROLLING_WINDOW)
    sign_win = deque(maxlen=CONTINUITY_WINDOW)  # signos de cuerpo para continuidad
    streak_dir, streak_len = 0, 0
    peak_adv = 0.0
    brake_count = 0
    trans_count = 0
    trans_entry_close = 0.0
    candles_in_state = 0
    prev_close = None
    ep_open_ts = 0.0
    points = []          # (adv_norm, cont) por vela con episodio activo
    brake_ts = None
    zone_hi = -1e18
    zone_lo = 1e18

    n = len(ts)
    for i in range(n):
        o, h, l, c = op[i], hi[i], lo[i], cl[i]
        body = c - o
        sign = 1 if body > 0 else (-1 if body < 0 else 0)
        if sign != 0 and sign == streak_dir:
            streak_len += 1
        else:
            streak_dir = sign
            streak_len = 1 if sign != 0 else 0

        window_bodies.append(abs(body))
        sign_win.append(sign)
        candles_in_state += 1
        med = st.median(window_bodies)

        advance = 0.0
        if direction != 0 and prev_close is not None:
            advance = (c - prev_close) * direction
            if advance > peak_adv:
                peak_adv = advance

        # punto de presion (pressure_v1) mientras hay episodio activo
        if direction != 0 and prev_close is not None:
            norm = min(1.0, max(0.0, advance / (2.0 * med))) if med > 0 else 0.0
            cont = sum(1 for s in sign_win if s == direction) / len(sign_win)
            points.append((norm, cont))

        if state in ("BRAKE", "TRANSITION"):
            zone_hi = max(zone_hi, h)
            zone_lo = min(zone_lo, l)

        resolved = None
        if state == "QUIET":
            if med > 0.0 and abs(body) > QUIET_BODY_FACTOR * med and streak_len >= QUIET_MIN_CONSECUTIVE:
                direction = streak_dir
                state = "EXPANSION"
                candles_in_state = 0
                brake_count = 0
                peak_adv = 0.0
                ep_open_ts = ts[i]
                points = []
                brake_ts = None
                zone_hi, zone_lo = -1e18, 1e18
        elif state == "EXPANSION":
            cont = sum(1 for s in sign_win if s == direction) / len(sign_win)
            if cont >= PRESSURE_CONTINUITY:
                state = "PRESSURE"
                candles_in_state = 0
                brake_count = 0
        elif state == "PRESSURE":
            if peak_adv > 0.0 and advance < BRAKE_PEAK_FRACTION * peak_adv:
                brake_count += 1
            else:
                brake_count = 0
            if brake_count >= BRAKE_MIN_CANDLES:
                state = "BRAKE"
                candles_in_state = 0
                brake_count = 0
                brake_ts = ts[i]
                zone_hi, zone_lo = h, l
        elif state == "BRAKE":
            if body * direction < 0:
                state = "TRANSITION"
                candles_in_state = 0
                trans_count = 0
                trans_entry_close = c
        elif state == "TRANSITION":
            trans_count += 1
            if trans_count >= TRANSITION_CANDLES:
                net = (c - trans_entry_close) * direction
                contrary = -net if net < 0 else 0.0
                if med > 0.0 and contrary >= REBOUND_BODY_FACTOR * med:
                    resolved = "REBOUND"
                elif net > 0:
                    resolved = "CONTINUATION"
                else:
                    resolved = "CHAOS"

        if resolved is None and state != "QUIET" and candles_in_state >= STATE_TIMEOUT:
            resolved = "NEUTRALIZATION"

        if resolved is not None:
            if resolved != "NEUTRALIZATION" and len(points) >= 8:
                tail = points[-5:]
                adv_tail = sum(p[0] for p in tail) / 5
                cont_tail = sum(p[1] for p in tail) / 5
                peak = max(p[0] for p in points) or 1e-9
                zone = (zone_hi - zone_lo) if (brake_ts is not None and zone_hi > zone_lo) else None
                episodes.append((resolved, ep_open_ts, adv_tail, cont_tail,
                                 points[-1][0] / peak, zone))
            state = "QUIET"
            direction = 0
            peak_adv = 0.0
            trans_count = 0
            candles_in_state = 0
            points = []
            brake_ts = None

        prev_close = c
    return episodes


def rb(g):
    return 100 * sum(1 for d in g if d[0] == "REBOUND") / len(g) if g else float("nan")


def placebo(data, subset_n, diff, seed):
    labels = [d[0] for d in data]
    random.seed(seed)
    worse = 0
    for _ in range(N_SHUFFLES):
        random.shuffle(labels)
        dl = (sum(1 for x in labels[:subset_n] if x == "REBOUND") / subset_n
              - sum(1 for x in labels[subset_n:] if x == "REBOUND") / (len(labels) - subset_n))
        worse += abs(dl) >= abs(diff)
    return worse / N_SHUFFLES


def analyze(name, pip, start, do_placebo):
    t0 = time.time()
    df = pd.read_parquet(f"{RAW}\\{name}.parquet")
    t = pd.to_datetime(df["time"], utc=True)
    if start:
        df = df[t >= pd.Timestamp(start, tz="UTC")]
        t = t[t >= pd.Timestamp(start, tz="UTC")]
    tsec = (t - pd.Timestamp(0, tz="UTC")).dt.total_seconds().to_numpy()
    order = np.argsort(tsec)
    ts = tsec[order]
    op = df["open"].to_numpy()[order]
    hi = df["high"].to_numpy()[order]
    lo = df["low"].to_numpy()[order]
    cl = df["close"].to_numpy()[order]

    eps = run_machine(ts, op, hi, lo, cl)
    if not eps:
        print(f"{name}: SIN episodios analizables")
        return

    print(f"\n=== {name} (pip={pip}, velas={len(ts)}, episodios={len(eps)}, "
          f"{time.time()-t0:.0f}s) ===")
    print(f"  %REBOUND global: {rb(eps):.1f}%")

    # --- LAB-001: muerte del empuje ---
    advs = sorted(d[2] for d in eps)
    conts = sorted(d[3] for d in eps)
    adv_lo, cont_lo = advs[len(advs) // 3], conts[len(conts) // 3]
    is_dead = lambda d: d[2] <= adv_lo and d[4] < PCT_PEAK_DEAD and d[3] <= cont_lo
    dead = [d for d in eps if is_dead(d)]
    rest = [d for d in eps if not is_dead(d)]
    alive = [d for d in eps if d[4] > PCT_PEAK_ALIVE]
    print(f"  LAB-001 MUERTE n={len(dead)}: REBOUND {rb(dead):.1f}% "
          f"(resto {rb(rest):.1f}%, vivo {rb(alive):.1f}%)")
    for era, lo_, hi_ in [("pre2020", 0, SPLIT_2020), ("2020+", SPLIT_2020, 9e18)]:
        g = [d for d in dead if lo_ <= d[1] < hi_]
        print(f"    walk-forward {era}: n={len(g)}, REBOUND {rb(g):.1f}%")
    if do_placebo and dead:
        p = placebo(eps, len(dead), rb(dead) / 100 - rb(rest) / 100, SEED)
        print(f"    placebo LAB-001: p={p:.3f}")

    # --- LAB-002: tamano de zona ---
    zdata = [(d[0], d[1], d[5] / pip) for d in eps if d[5] is not None]
    if len(zdata) < 100:
        print(f"  LAB-002: insuficientes zonas (n={len(zdata)})")
        return
    q1, q2 = np.percentile([z for _, _, z in zdata], [33, 66])
    print(f"  LAB-002 zonas n={len(zdata)}, terciles <{q1:.1f}/{q2:.1f}> pips")
    for nm, cond in [("CHICA", lambda s: s < q1), ("MEDIA", lambda s: q1 <= s <= q2),
                     ("GRANDE", lambda s: s > q2)]:
        g = [d for d in zdata if cond(d[2])]
        g1 = [d for d in g if d[1] < SPLIT_2020]
        g2 = [d for d in g if d[1] >= SPLIT_2020]
        print(f"    {nm}: n={len(g)}, REBOUND {rb(g):.1f}% | eras {rb(g1):.1f}/{rb(g2):.1f}")
    if do_placebo:
        grande = [d for d in zdata if d[2] > q2]
        resto = [d for d in zdata if d[2] <= q2]
        p = placebo(zdata, len(grande), rb(grande) / 100 - rb(resto) / 100, 11)
        print(f"    placebo LAB-002 GRANDE vs resto: p={p:.3f}")


if __name__ == "__main__":
    wanted = set(a.upper() for a in sys.argv[1:])
    for name, pip, start, plc in PAIRS:
        if wanted and name not in wanted:
            continue
        try:
            analyze(name, pip, start, plc)
        except Exception as e:  # noqa: BLE001
            print(f"{name}: FALLO ({type(e).__name__}: {e})")
