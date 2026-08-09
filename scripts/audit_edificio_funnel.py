"""AUDITORÍA FUNNEL del Edificio de Contratación (modo paper, SOLO embudo + WR).

NO es backtest de win rate de producción: es AUDITORÍA DE EMBUDO + medición de
WIN/LOSS en datos históricos con la definición FIEL al bot REAL:
  entry_price = openPrice de la orden; duration = DURATION_SEC (900s = 15min)
  CALL gana si exit > entry; PUT gana si exit < entry; empate NO es WIN.
APROXIMACIÓN TEMPORAL (documentada): el bot real entra ~300s tras la señal y
expíra 15min después. Con velas M15 no reconstruimos el precio intravela exacto,
así que usamos señal i → entry = close[i+ENTRY_OFFSET] → exit = close[i+EXIT_OFFSET].
Esto reproduce la ESTRUCTURA temporal REAL (señal→+5min→+15min) pero NO el precio
exacto de entrada del broker. Ver reporte para la limitación.

Puerta P3 configurable:
  EDIFICIO_P3_GATE_MODE = "cruce_limpio" | "valvula"
  "valvula": P3 = cámara de presión; CONTRATADO cuando K sale del extremo en
  dirección del trade Y |K-D| abre (presión acumulada, no salto aislado).

Barrido de válvula: para cada umbral en {1,3,5} se corre un pase completo del
edificio y se reporta P1→P2→P3→CONTRATADO y WR, separado por semestre
(H1 = primeras velas del año, H2 = resto) — holdout metodológico.

Uso:
  python scripts/audit_edificio_funnel.py <AÑO> <PAR> [valvula|cruce_limpio] [no5m] [umbral]
  Si no se pasa umbral, barre {1,3,5}.

Datos SOLO LECTURA: <EXT_ROOT>/<PAR>/M15, M5
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from config import (  # noqa: E402
    EDIFICIO_P3_NO_5M_GATE,
    EDIFICIO_P3_GATE_MODE,
    EDIFICIO_P3_DESVIO_K,
    EDIFICIO_P3_EVOLVE_WINDOW,
    EDIFICIO_P3_PAPER_ENTRY_OFFSET,
    EDIFICIO_P3_PAPER_EXIT_OFFSET,
)
from edificio_contratacion import (  # noqa: E402
    EdificioContratacion,
    PISO_FUERA,
    PISO_1,
    PISO_2,
    PISO_3,
    CONTRATADO,
)

EXT_ROOT = Path(r"C:\Users\v_jac\Desktop\backtest quotex\datos de velas\data")


# ── Funciones puras (fieles al cálculo del bot: estocástico FULL 14,3,3) ──
def compute_stoch_full(highs, lows, closes, k_period=14, d_period=3, slow_k=3):
    """Estocástico FULL 14,3,3 (Lane clásico). Devuelve (k_list, d_list)."""
    import numpy as np
    n = len(closes)
    raw_k = [float("nan")] * n
    for i in range(k_period - 1, n):
        hh = max(highs[i - k_period + 1:i + 1])
        ll = min(lows[i - k_period + 1:i + 1])
        if hh == ll:
            raw_k[i] = 50.0
        else:
            raw_k[i] = 100.0 * (closes[i] - ll) / (hh - ll)
    raw_k = np.array(raw_k, dtype=float)
    # %K suavizado SMA slow_k
    k_list = np.full(n, float("nan"))
    for i in range(k_period - 1 + slow_k - 1, n):
        k_list[i] = float(np.nanmean(raw_k[i - slow_k + 1:i + 1]))
    # %D = SMA d_period de %K
    d_list = np.full(n, float("nan"))
    for i in range(k_period - 1 + slow_k - 1 + d_period - 1, n):
        d_list[i] = float(np.nanmean(k_list[i - d_period + 1:i + 1]))
    return k_list.tolist(), d_list.tolist()


def derive_flags(k, d, k_prev, d_prev):
    """Dirección + flags de cruce/extremo según la lógica del Edificio."""
    if k is None or d is None:
        return None
    if k <= 20.0 and d <= 20.0:           # sobreventa -> CALL
        if k_prev is None or d_prev is None:
            return ("CALL", False, True)
        cross_ok = bool(k > d and k_prev <= d_prev)
        return ("CALL", cross_ok, True)
    if k >= 80.0 and d >= 80.0:           # sobrecompra -> PUT
        if k_prev is None or d_prev is None:
            return ("PUT", False, True)
        cross_ok = bool(k < d and k_prev >= d_prev)
        return ("PUT", cross_ok, True)
    return None


def is_sticky_cross(k, d, threshold=3.0):
    return abs(k - d) < threshold
PISO_LABELS = {
    PISO_FUERA: "FUERA", PISO_1: "P1", PISO_2: "P2", PISO_3: "P3", CONTRATADO: "CONTRATADO",
}


def load_csv_year(folder: Path, year: str) -> pd.DataFrame:
    p = folder / f"{year}.csv"
    if not p.exists():
        raise FileNotFoundError(f"falta {p}")
    df = pd.read_csv(p)
    df.columns = [c.strip().lower() for c in df.columns]
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    return df


def run_year(par: str, year: str, gate_mode: str, no_5m: bool, desvio_k: float, limit: Optional[int] = None):
    """Corre un pase completo del Edificio y devuelve embudo + señales contratadas."""
    import config as _cfg
    import logging as _logging
    _logging.disable(_logging.CRITICAL)  # silencia el logger del Edificio (auditoría paper)
    from config import EDIFICIO_STICKY_THRESHOLD, EDIFICIO_BRAKE_CONFIRM_RATIO
    _cfg.EDIFICIO_P3_MODE = "return_to_extreme"  # embudo P2→P3 validado (retorno al extremo)
    _cfg.EDIFICIO_P3_GATE_MODE = gate_mode
    _cfg.EDIFICIO_P3_DESVIO_K = desvio_k
    _cfg.EDIFICIO_P3_EVOLVE_WINDOW = EDIFICIO_P3_EVOLVE_WINDOW
    _cfg.EDIFICIO_P3_NO_5M_GATE = no_5m

    m15 = load_csv_year(EXT_ROOT / par / "M15", year)
    m5 = load_csv_year(EXT_ROOT / par / "M5", year)
    ks, ds = compute_stoch_full(m15["high"].tolist(), m15["low"].tolist(), m15["close"].tolist())
    m15["k"] = ks
    m15["d"] = ds
    nt = len(m15)
    if limit is not None:
        nt = min(nt, limit)

    ed = EdificioContratacion()
    ASSET = f"{par}_audit"

    piso_counts = Counter()
    entries_piso = Counter()
    transitions = Counter()
    sig = Counter()
    descartes = Counter()
    max_piso_reached = 0
    contratados_idx = []  # (i, direction) donde el edificio marcó CONTRATADO

    closes = m15["close"].tolist()
    m5_idx = 0

    for i in range(nt):
        row = m15.iloc[i]
        ts = row["ts"].timestamp()
        k = row["k"]
        d = row["d"]
        if pd.isna(k) or pd.isna(d):
            continue
        k_prev = m15.iloc[i - 1]["k"] if i > 0 else None
        d_prev = m15.iloc[i - 1]["d"] if i > 0 else None

        # ── Flags FIELES al scanner real (scanner.py:1488-1531) ──
        if pd.isna(k_prev) or pd.isna(d_prev):
            k_prev0 = d_prev0 = None
        else:
            k_prev0, d_prev0 = float(k_prev), float(d_prev)
        kf, df = float(k), float(d)
        # dirección estable (no vacía): mantiene el último no-vacío para no
        # romper el estado de p2_entry_extreme en el Edificio.
        if kf >= 80.0:
            direction = "PUT"
        elif kf <= 20.0:
            direction = "CALL"
        elif kf > df and kf < 50:
            direction = "CALL"
        elif kf < df and kf > 50:
            direction = "PUT"
        else:
            direction = getattr(run_year, "_last_dir", "CALL")
        run_year._last_dir = direction
        _cross_up = k_prev0 is not None and d_prev0 is not None and (k_prev0 < d_prev0 and kf >= df)
        _cross_down = k_prev0 is not None and d_prev0 is not None and (k_prev0 > d_prev0 and kf <= df)
        cross_ok = bool((_cross_up and direction == "CALL") or (_cross_down and direction == "PUT"))
        cross_sticky = is_sticky_cross(kf, df, EDIFICIO_STICKY_THRESHOLD)
        extreme_ok = bool((kf <= 20.0 and direction == "CALL") or (kf >= 80.0 and direction == "PUT"))
        # brake_ok: compresión de rango de la vela actual vs la PREVIA (emp A/B: rng<0.7*rng_prev)
        rng_prev = float(m15.iloc[i - 1]["high"] - m15.iloc[i - 1]["low"]) if i >= 1 else 0.0
        last_range = float(row["high"]) - float(row["low"])
        brake_ok = bool(rng_prev > 0 and last_range < rng_prev * EDIFICIO_BRAKE_CONFIRM_RATIO)

        sig["cross_ok"] += int(cross_ok)
        sig["cross_sticky"] += int(cross_sticky)
        sig["extreme_ok"] += int(extreme_ok)
        sig["brake_ok"] += int(brake_ok)

        # vela M5 cerrada más reciente
        while m5_idx < len(m5) and m5.iloc[m5_idx]["ts"].timestamp() <= ts:
            m5_idx += 1
        close_candle_5m = None
        if m5_idx > 0:
            c5 = m5.iloc[m5_idx - 1]
            close_candle_5m = {
                "open": float(c5["open"]), "high": float(c5["high"]),
                "low": float(c5["low"]), "close": float(c5["close"]), "name": "m5",
            }
        candles_15m = [
            {"ts": m15.iloc[j]["ts"].timestamp(),
             "open": float(m15.iloc[j]["open"]), "high": float(m15.iloc[j]["high"]),
             "low": float(m15.iloc[j]["low"]), "close": float(m15.iloc[j]["close"])}
            for j in range(max(0, i - 5), i + 1)
        ]

        prev = ed.get_card(ASSET)
        prev_piso = prev.piso if prev else PISO_FUERA
        res = ed.evaluate(
            asset=ASSET, direction=direction or "CALL", payout=90, payout_ok=True,
            brake_ok=brake_ok, extreme_ok=extreme_ok, cross_ok=cross_ok,
            cross_sticky=cross_sticky, stoch_k=kf, stoch_d=df if not pd.isna(df) else None,
            candles_15m=candles_15m, close_candle_5m=close_candle_5m,
        )
        card = ed.get_card(ASSET)
        piso = card.piso
        piso_counts[piso] += 1
        if piso > prev_piso:
            entries_piso[piso] += 1
            transitions[(prev_piso, piso)] += 1
        max_piso_reached = max(max_piso_reached, piso)
        if getattr(card, "p2_descartado", False):
            descartes[card.p2_descartado_motivo or "desconocido"] += 1
        if res == "contratado":
            contratados_idx.append((i, card.direction or direction))

    # WR por semestre (aproximación entry=i+ENTRY_OFFSET, exit=i+EXIT_OFFSET)
    entry_off = EDIFICIO_P3_PAPER_ENTRY_OFFSET
    exit_off = EDIFICIO_P3_PAPER_EXIT_OFFSET
    mid = nt // 2
    h1 = {"n": 0, "w": 0, "l": 0, "t": 0}
    h2 = {"n": 0, "w": 0, "l": 0, "t": 0}
    for i, direc in contratados_idx:
        ei = i + entry_off
        xi = i + exit_off
        if ei >= nt or xi >= nt:
            continue
        entry = closes[ei]
        exit_p = closes[xi]
        if direc == "CALL":
            win = exit_p > entry
        else:
            win = exit_p < entry
        bucket = h1 if i < mid else h2
        bucket["n"] += 1
        if win:
            bucket["w"] += 1
        else:
            bucket["l"] += 1

    return {
        "max_piso": max_piso_reached,
        "entries": entries_piso,
        "piso_counts": piso_counts,
        "transitions": transitions,
        "descartes": descartes,
        "sig": sig,
        "contratados": len(contratados_idx),
        "h1": h1, "h2": h2,
        "nt": nt,
    }


def wr(bucket: dict) -> str:
    n = bucket["n"]
    if n == 0:
        return "n=0"
    return f"n={n} WR={100.0*bucket['w']/n:.1f}% (W{bucket['w']}/L{bucket['l']})"


def main() -> int:
    year = sys.argv[1] if len(sys.argv) > 1 else "2024"
    par = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
    gate = sys.argv[3] if len(sys.argv) > 3 else "valvula"
    no_5m = sys.argv[4] == "no5m" if len(sys.argv) > 4 else True
    umbral_arg = sys.argv[5] if len(sys.argv) > 5 else None
    limit = int(sys.argv[6]) if len(sys.argv) > 6 else None  # depuración: solo primeras N velas
    if umbral_arg and umbral_arg.replace(".", "", 1).isdigit():
        umbrales = [float(umbral_arg)]
    else:
        umbrales = [1.0, 3.0, 5.0]  # barrido acordado (no optimizar a ojo)

    print("=" * 70)
    print(f"AUDITORÍA FUNNEL + WR — {par} {year} | gate={gate} no5m={no_5m}")
    print("Definición WIN fiel a REAL (entry≈señal+5min, exit≈+15min, M15 approx)")
    print("=" * 70)

    for u in umbrales:
        r = run_year(par, year, gate, no_5m, u, limit)
        print(f"\n--- VÁLVULA |K-D| >= {u:.0f} ---")
        print(f"  P1→P2={r['entries'][PISO_2]}  P2→P3={r['entries'][PISO_3]}  "
              f"CONTRATADO={r['contratados']}")
        print(f"  Piso máx: {PISO_LABELS.get(r['max_piso'])}")
        print(f"  WR H1 (descubrimiento): {wr(r['h1'])}")
        print(f"  WR H2 (holdout)       : {wr(r['h2'])}")
        print(f"  Descartes: {sum(r['descartes'].values())} "
              f"-> {dict(r['descartes'].most_common(3))}")

    # Nota metodológica
    print("\n" + "-" * 70)
    print("LIMITACIÓN: entry/exit aproximados con close de velas M15 (i+1/i+2).")
    print("El bot real entra ~300s tras la señal (precio openPrice intravela); el")
    print("CSV M15 no reconstruye ese precio exacto. WR es aproximación temporal,")
    print("no réplica del broker. H2 es holdout del mismo año (primeras vs segundas")
    print("mitad), NO datos externos; sirve para detectar sobreajuste, no para")
    print("garantizar edge fuera de muestra global.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
