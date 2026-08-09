"""AUDITORÍA FUNNEL 5min — FRENO + ARCOÍRIS + ESTOCÁSTICO (teoría entry/exit 5m).

NUEVO funnel (NO el Edificio P3). Granularidad M5:
  - FRENO:      vela M5 cuyo rango < BRAKE_RATIO * rango de la vela previa (compressión).
  - ARCOÍRIS:   7 EMAs exponenciales sobre close M5; alineación a favor del trade.
  - ESTOCÁSTICO: %K/%D (compute_stoch_full sobre M5); salida de extremo = señal.
Entry/exit EN M5 (teoría del usuario): entry = close[i+ENTRY_OFF], exit = close[i+EXIT_OFF].
La SEÑAL se envía con expiración de 15min (3 velas M5) — parámetro de holdout.

Combina las 3 capas en ~30 configuraciones (ver COMBOS). Cada una reporta:
  n señales, WR% (entry/exit M5), y p-value binomial vs 50%.

Uso:
  python scripts/audit_funnel_5m.py <AÑO> <PAR> [indice_combo|all]
  combo "all" corre los 30 y vuelca tabla. Sin args: EURUSD 2024 all.
"""
from __future__ import annotations

import sys
import math
from pathlib import Path

logging_disabled = True
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

EMA_PERIODS = [5, 10, 20, 40, 80, 160, 320]  # arcoíris M5


def compute_emas(closes, periods=EMA_PERIODS):
    out = []
    for p in periods:
        alpha = 2.0 / (p + 1.0)
        ema = [0.0] * len(closes)
        for t in range(len(closes)):
            ema[t] = closes[t] if t == 0 else alpha * closes[t] + (1 - alpha) * ema[t - 1]
        out.append(ema)
    return out


def arcoiris_ok(close, ema_vals, direction):
    """True si el arcoíris (7 EMAs) está estrictamente alineado a favor del trade."""
    if direction == "CALL":
        seq = [close] + list(ema_vals)
        return all(seq[i] >= seq[i + 1] for i in range(len(seq) - 1))
    else:
        seq = [close] + list(ema_vals)
        return all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1))


def load_m5(year, par):
    df = load_csv_year(DATA_ROOT / par / "M5", year).reset_index(drop=True)
    rows = [{"ts": str(r.timestamp), "o": float(r.open), "h": float(r.high),
             "l": float(r.low), "c": float(r.close)} for r in df.itertuples()]
    return rows


def build_context(rows):
    """Precomputa stoch, EMAs, flags de freno por vela M5."""
    n = len(rows)
    highs = [r["h"] for r in rows]
    lows = [r["l"] for r in rows]
    closes = [r["c"] for r in rows]
    k_list, d_list = compute_stoch_full(highs, lows, closes)
    emas = compute_emas(closes)
    # freno: rango actual < BRAKE_RATIO * rango previo
    BRAKE_RATIO = 0.6
    ctx = []
    for i in range(n):
        rng = (rows[i]["h"] - rows[i]["l"]) if (rows[i]["h"] - rows[i]["l"]) > 0 else 0.0
        prev_rng = (rows[i - 1]["h"] - rows[i - 1]["l"]) if i > 0 else 0.0
        brake = (prev_rng > 0) and (rng < prev_rng * BRAKE_RATIO)
        ctx.append({
            "k": k_list[i], "d": d_list[i],
            "brake": brake,
            "ema": [emas[k][i] for k in range(len(emas))],
            "close": closes[i],
        })
    return ctx, k_list, d_list


# ── COMBINACIONES (~30) ────────────────────────────────────────────────
# Cada combo: nombre + dict de flags.
# freno:    requerir freno previo (True/False)
# arc:      nivel de alineación de arcoíris
#             "full" = 7 EMAs estrictas; "fast" = solo EMA5>EMA20>EMA320; "none" = no usar
# stoch:    condición estocástica
#             "exit_ext" = K sale de extremo (CALL K>20 / PUT K<80)
#             "cross"    = K cruza D en dirección
#             "sep"      = |K-D| >= sep_umbral
# sep_u:    umbral |K-D| para modo "sep"
# hold:     velas M5 de holdout de la señal (3 = 15min expiración)
# entry_off/exit_off: desplazamiento entry/exit en M5 desde la señal
COMBOS = []
# Generador sistemático de 30 combos
_freno_opts = [True, False]
_arc_opts = ["full", "fast", "none"]
_stoch_opts = ["exit_ext", "cross", "sep"]
_sep_opts = [2.0, 5.0]
for f in _freno_opts:
    for a in _arc_opts:
        for s in _stoch_opts:
            for su in _sep_opts:
                COMBOS.append({
                    "freno": f, "arc": a, "stoch": s, "sep_u": su,
                    "hold": 3, "entry_off": 1, "exit_off": 3,
                })
# Recorta a 30 exactos (hay 2*3*3*2 = 36; dejamos las 30 primeras variando sep)
COMBOS = COMBOS[:30]
for _i, _c in enumerate(COMBOS):
    _c["name"] = f"C{_i:02d}_f{int(_c['freno'])}_a{_c['arc']}_s{_c['stoch']}_u{_c['sep_u']}"


def gate_open(ctx_i, combo):
    """¿La vela i abre la señal según el combo?"""
    c = ctx_i
    k, d = c["k"], c["d"]
    if k != k or d != d:
        return None
    # dirección por estocástico: K>D -> CALL, K<D -> PUT (salida de extremo)
    if combo["stoch"] == "exit_ext":
        if k > 20.0 and k >= (c.get("k_prev", k)):
            direction = "CALL"
        elif k < 80.0 and k <= (c.get("k_prev", k)):
            direction = "PUT"
        else:
            return None
    elif combo["stoch"] == "cross":
        # dirección provisional por pendiente K vs D; run_combo re-valida el cruce real
        direction = "CALL" if k >= d else "PUT"
    else:  # sep
        direction = "CALL" if k >= d else "PUT"
        if abs(k - d) < combo["sep_u"]:
            return None
    if combo["freno"] and not c["brake"]:
        return None
    if combo["arc"] == "full" and not arcoiris_ok(c["close"], c["ema"], direction):
        return None
    if combo["arc"] == "fast":
        e = c["ema"]
        if direction == "CALL" and not (e[0] > e[2] > e[6]):
            return None
        if direction == "PUT" and not (e[0] < e[2] < e[6]):
            return None
    return direction


def run_combo(rows, ctx, combo, k_list, d_list):
    n = len(rows)
    signals = []
    for i in range(1, n):
        direction = gate_open(ctx[i], combo)
        if direction is None:
            continue
        # cruce estocástico requiere vela previa
        if combo["stoch"] == "cross":
            kp, dp = k_list[i - 1], d_list[i - 1]
            if kp != kp or dp != dp:
                continue
            if not ((k_list[i] > d_list[i] and kp <= dp) or (k_list[i] < d_list[i] and kp >= dp)):
                continue
            direction = "CALL" if k_list[i] > d_list[i] else "PUT"
        signals.append((i, direction))
    # WR entry/exit en M5
    w = l = 0
    for (i, direction) in signals:
        ei = i + combo["entry_off"]
        xi = i + combo["exit_off"]
        if xi >= n:
            continue
        entry = rows[ei]["c"]
        exitp = rows[xi]["c"]
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


def main():
    year = sys.argv[1] if len(sys.argv) > 1 else "2024"
    par = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
    which = sys.argv[3] if len(sys.argv) > 3 else "all"
    rows = load_m5(year, par)
    ctx, k_list, d_list = build_context(rows)
    # k_prev para exit_ext
    for i in range(len(ctx)):
        ctx[i]["k_prev"] = k_list[i - 1] if i > 0 else k_list[i]
    if which == "all":
        print(f"{'COMBO':28} {'N':>5} {'WR%':>6} {'p':>8}")
        print("-" * 52)
        for combo in COMBOS:
            n, w, l = run_combo(rows, ctx, combo, k_list, d_list)
            wr = w / (w + l) * 100 if (w + l) else 0.0
            p = binom_p(w + l, w)
            print(f"{combo['name']:28} {n:>5} {wr:>6.1f} {p:>8.4f}")
    else:
        idx = int(which)
        combo = COMBOS[idx]
        n, w, l = run_combo(rows, ctx, combo, k_list, d_list)
        wr = w / (w + l) * 100 if (w + l) else 0.0
        print(f"COMBO {combo['name']}: n={n} w={w} l={l} WR={wr:.1f}% p={binom_p(w+l,w):.4f}")


if __name__ == "__main__":
    main()
