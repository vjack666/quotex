"""EXP-EDF — SWEEP DEFINITIVO: ¿la válvula K/D aporta edge real P3->CONTRATADO?

Mide el motor real reparado (embudo P1->P2->P3 idéntico a la máquina validada de
exp_funnel_b) sobre TODOS los datasets disponibles (EURUSD 2023/2024, XAUUSD 2009-2025),
comparando 3 puertas distintas para el P3->CONTRATADO:

  A) valvula       = salir del extremo + |K-D|>=5 + presión 3 velas (hipótesis del usuario)
  B) cruce_limpio  = cruce limpio M15 + gate M5 body>=50% (puerta ORIGINAL del Edificio)
  C) ALL_P3        = entrar en TODOS los P3 (baseline: sin filtro de válvula)

Por cada dataset y puerta reporta: P3, CONTR, BLOCK, WR global, y p-value binomial vs 50%.
El dictamen se deriva de si la válvula bate consistentemente a ALL_P3 (su baseline propio)
en todos los datasets y la diferencia es significativa.

WR fiel al bot: entry=i+1 close, exit=i+2 close (aprox; bot real entra ~300s tras señal).
Stoch: compute_stoch_full (mismo de la sim validada). No modifica src/.
"""
import sys, csv, logging, math
from pathlib import Path

logging.disable(logging.CRITICAL)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from audit_edificio_funnel import compute_stoch_full, load_csv_year
from exp_funnel_b import (Sim, derive_flags, is_sticky_cross,
                          MAX_HOLD_VELAS, STICKY_DESCARTE, BRAKE_RATIO)

DATA_ROOT = Path(r"C:\Users\v_jacane\Desktop\backtest quotex\datos de velas\data")
if not DATA_ROOT.exists():
    DATA_ROOT = Path(r"C:\Users\v_jac\Desktop\backtest quotex\datos de velas\data")

EVOLVE = 3          # EDIFICIO_P3_EVOLVE_WINDOW
DESVIO = 5.0        # EDIFICIO_P3_DESVIO_K (default motor)
MAX_HOLD = 8        # ventanas M15 para que la puerta abra tras P3


def build_feed(m15, m5idx):
    """Precomputa stoch, flags y presión K/D por vela (fiel al motor real)."""
    highs = [r["h"] for r in m15]
    lows = [r["l"] for r in m15]
    closes = [r["c"] for r in m15]
    k_list, d_list = compute_stoch_full(highs, lows, closes)
    n = len(m15)
    kd_all = [abs(k_list[i] - d_list[i]) if (k_list[i] == k_list[i] and d_list[i] == d_list[i]) else None
              for i in range(n)]
    prev = None
    feed = []
    for i in range(n):
        sk, sd = k_list[i], d_list[i]
        if sk is None or sd is None or (sk != sk) or (sd != sd):
            feed.append(None); prev = (sk, sd); continue
        _flags = derive_flags(sk, sd, prev[0] if prev else sk, prev[1] if prev else sd)
        if _flags is None:
            feed.append(None); prev = (sk, sd); continue
        direction, _cross_ok, extreme_ok = _flags
        prev_range = m15[i - 1]["h"] - m15[i - 1]["l"] if i > 0 else 0.0
        last_range = m15[i]["h"] - m15[i]["l"]
        brake_ok = (prev_range > 0) and (last_range < prev_range * BRAKE_RATIO)
        cross_ok = _cross_ok
        cross_sticky = is_sticky_cross(sk, sd, STICKY_DESCARTE)
        m5row = m5idx.get(m15[i]["ts"])
        candle_5m = None
        if m5row is not None:
            h = float(m5row["high"]); l = float(m5row["low"])
            o = float(m5row["open"]); c = float(m5row["close"])
            rng = (h - l) if (h - l) > 0 else 0.0
            candle_5m = {"body_pct": (abs(c - o) / rng) if rng > 0 else 0.0}
        feed.append((sk, sd, direction, brake_ok, extreme_ok, cross_ok, cross_sticky, candle_5m))
        prev = (sk, sd)
    return k_list, d_list, kd_all, feed


EMA_PERIODS = [5, 10, 20, 40, 80, 160, 320]  # arcoíris de 7 EMAs exponenciales (M15)


def compute_emas(closes, periods=EMA_PERIODS):
    """Devuelve lista de 7 arrays (uno por periodo) con las EMAs exponenciales.
    EMA[t] = close[t] en t<period; luego alpha*close + (1-alpha)*EMA[t-1].
    """
    out = []
    for p in periods:
        alpha = 2.0 / (p + 1.0)
        ema = [0.0] * len(closes)
        for t in range(len(closes)):
            if t == 0:
                ema[t] = closes[t]
            else:
                ema[t] = alpha * closes[t] + (1 - alpha) * ema[t - 1]
        out.append(ema)
    return out


def arcoiris_alineado(close, emas, direction):
    """True si el arcoíris de 7 EMAs confirma tendencia a favor del trade.
    CALL: close > EMA5 > EMA10 > EMA20 > EMA40 > EMA80 > EMA160 > EMA320 (todos en orden).
    PUT : close < EMA5 < EMA10 < ... < EMA320.
    Orden estricto = tendencia limpia (rainbow alineado).
    """
    e = [emas[k][0] for k in range(len(emas))] if isinstance(emas[0], (list, tuple)) else emas
    # emas viene como lista de 7 arrays; tomamos el valor en el índice dado por caller
    # (el caller pasa los valores ya indexados). Aquí 'emas' = lista de 7 floats.
    if direction == "CALL":
        seq = [close] + list(e)
        return all(seq[i] >= seq[i + 1] for i in range(len(seq) - 1))
    else:  # PUT
        seq = [close] + list(e)
        return all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1))


def run_gates(m15, m5idx):
    k_list, d_list, kd_all, feed = build_feed(m15, m5idx)
    n = len(m15)
    p3_events = []  # indices i donde el motor promovió a P3
    sim = Sim(modo="base")
    for i in range(n):
        f = feed[i]
        if f is None or not f[2]:
            continue
        sk, sd, direction, brake_ok, extreme_ok, cross_ok, cross_sticky, _ = f
        k_prev = feed[i - 1][0] if i > 0 and feed[i - 1] else sk
        p3_before = sim.entries[3]
        sim.step(i, m15[i]["ts"], sk, sd, k_prev, direction, cross_sticky, brake_ok, extreme_ok, None, sk)
        if sim.entries[3] > p3_before:
            p3_events.append((i, direction))

    # Arcoíris de 7 EMAs exponenciales sobre el close M15 (paramétrica de tendencia)
    closes = [r["c"] for r in m15]
    ema_arrays = compute_emas(closes)  # 7 arrays de longitud n

    results = {}
    for gate in ("valvula", "cruce_limpio", "arcoiris", "all_p3"):
        contratados = []
        blocked = 0
        for (i, direction) in p3_events:
            if gate == "all_p3":
                contratados.append((i, direction))
                continue
            opened = False
            for j in range(i + 1, min(i + 1 + MAX_HOLD, n)):
                skj, sdj = k_list[j], d_list[j]
                if skj != skj or sdj != sdj:
                    continue
                ok = False
                if gate == "valvula":
                    salio = (skj > 20.0 and direction == "CALL") or (skj < 80.0 and direction == "PUT")
                    kd_now = abs(skj - sdj)
                    creciente = True
                    if j >= EVOLVE:
                        kds = [kd_all[t] for t in range(j - EVOLVE, j + 1)]
                        creciente = (None not in kds) and all(kds[t] <= kds[t + 1] for t in range(len(kds) - 1))
                    ok = salio and (kd_now >= DESVIO) and creciente
                elif gate == "arcoiris":
                    # Tendencia paramétrica: las 7 EMAs alineadas a favor del trade
                    ema_vals = [ema_arrays[k][j] for k in range(len(ema_arrays))]
                    ok = arcoiris_alineado(m15[j]["c"], ema_vals, direction)
                else:  # cruce_limpio + gate M5 real
                    fj = feed[j]
                    if fj is not None and fj[2]:
                        _sk, _sd, _dir, _b, _e, cjo, cst, m5j = fj
                        if cjo and not cst and _dir == direction:
                            ok = (m5j is not None and m5j["body_pct"] >= 0.5) or (m5j is None)
                if ok:
                    contratados.append((i, direction))
                    opened = True
                    break
            if not opened:
                blocked += 1
        results[gate] = (contratados, blocked)
    return len(p3_events), results


def winrate(contratados, m15, off_e=1, off_x=2):
    n = len(m15)
    w = l = 0
    for (i, direction) in contratados:
        if i + off_x >= n:
            continue
        entry = m15[i + off_e]["c"]
        exitp = m15[i + off_x]["c"]
        if (direction == "CALL" and exitp > entry) or (direction == "PUT" and exitp < entry):
            w += 1
        else:
            l += 1
    return w, l, (w / (w + l) * 100) if (w + l) else 0.0


def binom_p(n, k, p=0.5):
    """p-value two-sided binomial contra p=0.5.
    Para n grande usa aproximación normal (Z-test) para evitar overflow de comb().
    """
    if n == 0:
        return 1.0
    if n > 1000:
        # Z-test normal: p_hat vs 0.5, SE = sqrt(0.25/n)
        from math import erf, sqrt
        p_hat = k / n
        se = sqrt(0.25 / n)
        if se == 0:
            return 0.0
        z = abs(p_hat - 0.5) / se
        # two-sided p via error function
        return 2.0 * (1.0 - 0.5 * (1.0 + erf(z / sqrt(2.0))))
    from math import comb
    p_exact = lambda x: comb(n, x) * (0.5 ** n)
    p_k = p_exact(k)
    total = 0.0
    for x in range(n + 1):
        if p_exact(x) <= p_k + 1e-12:
            total += p_exact(x)
    return min(1.0, total)


def sweep():
    datasets = []
    # EURUSD: solo 2023/2024 disponibles
    for year in ("2023", "2024"):
        p = DATA_ROOT / "EURUSD" / "M15" / f"{year}.csv"
        if p.exists():
            datasets.append(("EURUSD", year))
    # XAUUSD: 2009-2025
    for year in [str(y) for y in range(2009, 2026)]:
        p = DATA_ROOT / "XAUUSD" / "M15" / f"{year}.csv"
        if p.exists():
            datasets.append(("XAUUSD", year))

    rows = []
    for instr, year in datasets:
        m15p = DATA_ROOT / instr / "M15" / f"{year}.csv"
        m5p = DATA_ROOT / instr / "M5" / f"{year}.csv"
        m15 = load_csv_year(DATA_ROOT / instr / "M15", year).reset_index(drop=True)
        m5 = load_csv_year(DATA_ROOT / instr / "M5", year).reset_index(drop=True)
        m15f = [{"ts": str(r.timestamp), "o": float(r.open), "h": float(r.high),
                 "l": float(r.low), "c": float(r.close)} for r in m15.itertuples()]
        m5idx = {str(r.timestamp): {"high": float(r.high), "low": float(r.low),
                                    "open": float(r.open), "close": float(r.close)}
                 for r in m5.itertuples()}
        n_p3, res = run_gates(m15f, m5idx)
        rec = {"instr": instr, "year": year, "p3": n_p3}
        for gate in ("valvula", "cruce_limpio", "arcoiris", "all_p3"):
            cont, blk = res[gate]
            w, l, wr_ = winrate(cont, m15f)
            rec[gate] = {"n": len(cont), "blk": blk, "w": w, "l": l, "wr": wr_,
                         "p": binom_p(w + l, w)}
        rows.append(rec)
    return rows


def main():
    rows = sweep()
    gates = ("valvula", "arcoiris", "cruce_limpio", "all_p3")
    print(f"{'INSTR':7} {'YEAR':5} {'P3':>5} | {'GATE':11} {'N':>5} {'BLOCK':>6} {'WR%':>6} {'p-value':>9}")
    print("-" * 62)
    for r in rows:
        for gate in gates:
            g = r[gate]
            print(f"{r['instr']:7} {r['year']:5} {r['p3']:>5} | {gate:11} {g['n']:>5} {g['blk']:>6} "
                  f"{g['wr']:>6.1f} {g['p']:>9.4f}")
        print("-" * 62)

    # Dictamen por gate vs baseline ALL_P3
    for gate, label in (("valvula", "VÁLVULA K/D"), ("arcoiris", "ARCOÍRIS 7-EMA")):
        print(f"\n=== DICTAMEN: {label} vs baseline ALL_P3 ===")
        beats = 0
        total = 0
        for r in rows:
            v = r[gate]; a = r["all_p3"]
            total += 1
            delta = v["wr"] - a["wr"]
            sig = "SIG" if v["p"] < 0.05 else "ns"
            mark = "VENCE" if (v["wr"] > a["wr"] and v["p"] < 0.05) else ("+edge" if v["wr"] > a["wr"] else "PIERDE")
            if v["wr"] > a["wr"]:
                beats += 1
            print(f"{r['instr']:7} {r['year']:5}: {gate:9} WR={v['wr']:.1f}% (p={v['p']:.3f}) "
                  f"vs ALL_P3 WR={a['wr']:.1f}%  Δ={delta:+.1f}pp  [{mark}/{sig}]")

    # Pooled para cada gate
    print("\n=== POOLED (todos los datasets) ===")
    pooled_v = pv = None
    for gate, label in (("valvula", "válvula"), ("arcoiris", "arcoiris"), ("all_p3", "ALL_P3"), ("cruce_limpio", "cruce_limpio")):
        n = sum(r[gate]["n"] for r in rows)
        w = sum(r[gate]["w"] for r in rows)
        l = sum(r[gate]["l"] for r in rows)
        wr_ = w / (w + l) * 100 if (w + l) else 0
        p_ = binom_p(w + l, w)
        if gate == "valvula":
            pooled_v, pv = wr_, p_
        print(f"{label:13}: n={n:>5}  WR={wr_:.1f}%  p={p_:.4f}")

    # Comparación directa arcoiris vs válvula (¿cuál mejor?)
    print("\n=== ARCOÍRIS vs VÁLVULA (cuál da más WR) ===")
    arc_wins = val_wins = 0
    for r in rows:
        if r["arcoiris"]["wr"] > r["valvula"]["wr"]:
            arc_wins += 1
        else:
            val_wins += 1
        print(f"{r['instr']:7} {r['year']:5}: arcoiris={r['arcoiris']['wr']:.1f}%  válvula={r['valvula']['wr']:.1f}%")

    n_a = sum(r["arcoiris"]["n"] for r in rows)
    w_a = sum(r["arcoiris"]["w"] for r in rows)
    l_a = sum(r["arcoiris"]["l"] for r in rows)
    pooled_a = w_a / (w_a + l_a) * 100 if (w_a + l_a) else 0
    pa = binom_p(w_a + l_a, w_a)
    print(f"\narcoiris pooled: n={n_a} WR={pooled_a:.1f}% p={pa:.4f} | datasets donde arcoiris>válvula: {arc_wins}/{arc_wins+val_wins}")

    print("\n=== VEREICTO ===")
    print(f"Válvula K/D: WR pooled {pooled_v:.1f}% (p={pv:.4f}), vence a ALL_P3 en {beats}/{total}.")
    print(f"Arcoíris 7-EMA: WR pooled {pooled_a:.1f}% (p={pa:.4f}), vence a ALL_P3 en {arc_wins+val_wins - val_wins}/{arc_wins+val_wins}.")
    if pooled_a > pooled_v and pa < 0.05:
        print("ARCOÍRIS 7-EMA SUPERA a la válvula K/D como puerta P3->CONTRATADO.")
    elif pooled_v > pooled_a and pv < 0.05:
        print("VÁLVULA K/D sigue siendo superior al arcoíris como puerta P3->CONTRATADO.")
    else:
        print("Ambas por encima de baseline; diferencia entre ellas no concluyente.")


if __name__ == "__main__":
    main()
