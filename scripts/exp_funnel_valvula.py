"""EXP — VÁLVULA P3→CONTRATADO medida SOBRE el embudo ya validado.

Arquitectura desacoplada (lo que pidió el consejo científico):
  1) Embudo P1→P2→P3 = MISMA máquina validada de exp_funnel_b.py
     (return_to_extreme). Importamos Sim/run de ahí y registramos los
     eventos P3 para no reescribir la máquina (evita divergencias).
  2) VÁLVULA P3→CONTRATADO = forward-scan desde cada evento P3:
     la válvula se ABRE cuando K sale del extremo en dirección del trade
     Y |K-D| abre con presión acumulada (viene subiendo en las últimas
     VELAS_EVOLVE velas). Si no abre en MAX_HOLD_VELAS → bloqueado.
  3) WR por semestre (H1 = primeras velas, H2 = resto) con definición
     fiel al bot REAL: entry≈señal+5min, exit≈+15min; en M15 se aproxima
     entry=i+1, exit=i+2 (LIMITACIÓN: no reconstruye openPrice intravela).

Barrido de umbral {1,3,5}. NO se optimiza fuera de ese barrido.

Uso:
  python scripts/exp_funnel_valvula.py [AÑO] [PAR] [umbral_opcional]
  Sin umbral → barre {1,3,5}.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

# Reusamos la máquina YA validada de exp_funnel_b.py (no la reescribimos).
from exp_funnel_b import (  # noqa: E402
    Sim as _BaseSim,
    run as _base_run,
    MAX_HOLD_VELAS,
    STICKY_DESCARTE,
    BRAKE_RATIO,
)
from audit_edificio_funnel import (  # noqa: E402
    EXT_ROOT,
    compute_stoch_full,
    load_csv_year,
)

VELAS_EVOLVE = 3            # EDIFICIO_P3_EVOLVE_WINDOW
ENTRY_OFFSET = 1            # EDIFICIO_P3_PAPER_ENTRY_OFFSET (M15)
EXIT_OFFSET = 2            # EDIFICIO_P3_PAPER_EXIT_OFFSET (M15)


class Sim(_BaseSim):
    """Igual que exp_funnel_b.Sim pero registra los eventos P3 para la válvula."""

    def __init__(self, modo: str):
        super().__init__(modo)
        self.p3_events = []   # (i, direction)

    def _to_p3(self, i, ts, k, d, motivo):
        self.piso = 3
        self.entries[3] += 1
        self.p3_events.append((i, self.direction))
        self.eventos.append({
            "i": i, "ts": ts, "evento": "P2→P3", "dir": self.direction,
            "extremo": self.extreme, "k": round(float(k), 2),
            "d": round(float(d), 2), "motivo": motivo,
        })
        self._reset_p2()
        self.piso = 1  # ciclo cerrado: la tarjeta vuelve a competir desde P1


def run(m15: pd.DataFrame, modo: str = "base") -> Sim:
    sim = Sim(modo)
    n = len(m15)
    ks = m15["k"].tolist()
    ds = m15["d"].tolist()
    hi = m15["high"].tolist()
    lo = m15["low"].tolist()
    ts = m15["ts"].tolist()
    for i in range(1, n):
        k, d = ks[i], ds[i]
        if pd.isna(k) or pd.isna(d):
            continue
        k_prev, d_prev = ks[i - 1], ds[i - 1]
        flags = _base_flags(k, d, k_prev, d_prev)
        if flags is None:
            continue
        direction, _cross_ok, extreme_ok = flags
        cross_sticky = _is_sticky(k, d, STICKY_DESCARTE)
        rng = hi[i] - lo[i]
        rng_prev = hi[i - 1] - lo[i - 1]
        brake_ok = rng_prev > 0 and rng < rng_prev * BRAKE_RATIO
        sim.step(i, ts[i], k, d, k_prev, direction, cross_sticky, brake_ok, extreme_ok, None, k)
    return sim


# Reusamos las funciones puras de exp_funnel_b vía import interno
import exp_funnel_b as _bfun  # noqa: E402
_base_flags = _bfun.derive_flags
_is_sticky = _bfun.is_sticky_cross


def apply_valve(m15: pd.DataFrame, p3_events: list, umbral: float) -> dict:
    """Forward-scan de la válvula sobre cada evento P3.

    Devuelve contratados=[(i, direction)] y conteo de bloqueados.
    """
    ks = m15["k"].tolist()
    ds = m15["d"].tolist()
    n = len(m15)
    contratados = []
    bloqueados = 0
    for (i0, direction) in p3_events:
        extreme = 20.0 if direction == "CALL" else 80.0
        kd_hist: list = []
        abrio = False
        for j in range(i0 + 1, min(i0 + 1 + MAX_HOLD_VELAS + 1, n)):
            k, d = ks[j], ds[j]
            if pd.isna(k) or pd.isna(d):
                continue
            k_prev_v = ks[j - 1] if j - 1 >= 0 else k
            # (a) salida del extremo en dirección del trade
            if extreme == 20.0:  # CALL
                if not (float(k) > 20.0 and float(k) >= float(k_prev_v)):
                    continue
            else:  # PUT
                if not (float(k) < 80.0 and float(k) <= float(k_prev_v)):
                    continue
            # (b) separación K-D con presión acumulada
            sep = abs(float(k) - float(d))
            kd_hist.append(sep)
            if len(kd_hist) > VELAS_EVOLVE + 1:
                kd_hist.pop(0)
            if sep < umbral:
                continue
            if len(kd_hist) >= 2:
                recent = kd_hist[-VELAS_EVOLVE:]
                if not all(recent[t] <= recent[t + 1] for t in range(len(recent) - 1)):
                    continue
            contratados.append((j, direction))
            abrio = True
            break
        if not abrio:
            bloqueados += 1
    return {"contratados": contratados, "bloqueados": bloqueados}


def wr(closes: list, contratados: list, nt: int) -> tuple:
    h1 = {"n": 0, "w": 0, "l": 0}
    h2 = {"n": 0, "w": 0, "l": 0}
    mid = nt // 2
    for (i, direc) in contratados:
        ei, xi = i + ENTRY_OFFSET, i + EXIT_OFFSET
        if ei >= nt or xi >= nt:
            continue
        entry, exit_p = closes[ei], closes[xi]
        win = (exit_p > entry) if direc == "CALL" else (exit_p < entry)
        bk = h1 if i < mid else h2
        bk["n"] += 1
        bk["w" if win else "l"] += 1
    return h1, h2


def fmt(bk: dict) -> str:
    if bk["n"] == 0:
        return "n=0"
    return f"n={bk['n']} WR={100.0*bk['w']/bk['n']:.1f}% (W{bk['w']}/L{bk['l']})"


def main() -> int:
    year = sys.argv[1] if len(sys.argv) > 1 else "2024"
    par = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
    if len(sys.argv) > 3 and sys.argv[3].replace(".", "", 1).isdigit():
        umbrales = [float(sys.argv[3])]
    else:
        umbrales = [1.0, 3.0, 5.0]

    m15 = load_csv_year(EXT_ROOT / par / "M15", year)
    ks, ds = compute_stoch_full(m15["high"].tolist(), m15["low"].tolist(), m15["close"].tolist())
    m15["k"] = ks
    m15["d"] = ds
    nt = len(m15)
    closes = m15["close"].tolist()

    sim = run(m15, "base")
    print("=" * 70)
    print(f"VÁLVULA P3→CONTRATADO — {par} {year}")
    print(f"Embudo validado (exp_funnel_b): P1→P2={sim.entries[2]}  P2→P3={sim.entries[3]}")
    print("Definición WIN fiel a REAL (entry≈señal+5min, exit≈+15min, M15 i+1/i+2)")
    print("=" * 70)

    for u in umbrales:
        r = apply_valve(m15, sim.p3_events, u)
        h1, h2 = wr(closes, r["contratados"], nt)
        print(f"\n--- VÁLVULA |K-D| >= {u:.0f} ---")
        print(f"  P1→P2={sim.entries[2]}  P2→P3={sim.entries[3]}  "
              f"CONTRATADO={len(r['contratados'])}  BLOQUEADOS={r['bloqueados']}")
        print(f"  WR H1 (descubrimiento): {fmt(h1)}")
        print(f"  WR H2 (holdout)       : {fmt(h2)}")
        if sim.entries[3]:
            print(f"  Tasa P3→CONTRATADO: {100.0*len(r['contratados'])/sim.entries[3]:.1f}%")

    print("\n" + "-" * 70)
    print("LIMITACIÓN: entry/exit aproximados con close M15 (i+1/i+2). El bot real")
    print("entra ~300s tras la señal (openPrice intravela); el CSV M15 no reconstruye")
    print("ese precio. WR es aproximación temporal, no réplica del broker. H2 = holdout")
    print("del mismo año (mitades), no datos externos; detecta sobreajuste, no garantiza edge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
