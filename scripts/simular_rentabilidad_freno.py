"""simular_rentabilidad_freno.py — rentabilidad del edge del freno vs costos Quotex.

Carga los 8 pares M15 prestados (SMC-SYSTEMS), usa brake_eval para generar
señales del freno, y simula PnL con payout configurable. Reporta expectancy,
break-even WR, ROI y si el edge aguanta tras costos reales.

Candado: cero import del bot (scanner/strat_fractal/pyquotex/consolidation_bot/
connection/caffeine/loop_utils). Solo time.perf_counter para log de duración.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# root del proyecto (scripts/ -> QUOTEX)
ROOT = Path(__file__).resolve().parents[1]
SRC = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
BORROWED = ROOT / "data" / "smc_borrowed"
PAIRS = ["EURUSD", "XAUUSD", "GBPUSD", "AUDUSD",
         "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]

# cfg compartido del CONTRATO
BRAKE_CFG = {
    "stochastic": {},
    "impulse": {"window": 8, "min_pips": 30},
    "brake": {"fwd": 3, "max_advance_frac": 0.10, "require_alternation": True},
    "rebote": {"fwd": 3, "min_pips": 8},
}

ROWS_LIMIT = 200_000


def _resolve_path(name: str) -> Path:
    local = BORROWED / f"{name}_M15.parquet"
    smc = SRC / f"{name}_M15.parquet"
    return local if local.exists() else smc


def load_pair(name: str) -> pd.DataFrame:
    p = _resolve_path(name)
    df = pd.read_parquet(p)
    df = df.sort_values("time")
    return df.iloc[-ROWS_LIMIT:]


def signals_from_pair(df: pd.DataFrame):
    """Devuelve lista de aciertos (bool) de señales del freno para el par."""
    from strategy_lab.brake_eval import (
        brake_winrate,
        compute_brake_and_rebote,
    )
    feat = compute_brake_and_rebote(
        df["open"].to_numpy(), df["high"].to_numpy(),
        df["low"].to_numpy(), df["close"].to_numpy(), BRAKE_CFG,
    )
    brake = feat["brake_mask"].astype(bool)
    net = feat["impulse_net"]
    up = feat["rebote_up"].astype(bool)
    dn = feat["rebote_dn"].astype(bool)
    # señal alcista: impulso bajista frenó -> acierto si rebota al alza
    br_up = brake & (net < 0)
    # señal bajista: impulso alcista frenó -> acierto si rebota a la baja
    br_dn = brake & (net > 0)
    entries = np.concatenate([up[br_up], dn[br_dn]])
    return entries.astype(bool)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payout", type=float, default=0.85,
                    help="payout ratio de Quotex (p.ej. 0.85 = 85%)")
    ap.add_argument("--stake", type=float, default=100.0,
                    help="capital por señal")
    ap.add_argument("--limit", type=int, default=ROWS_LIMIT,
                    help="máx filas por par (perf)")
    args = ap.parse_args(argv)

    from strategy_lab import pnl_sim

    t0 = time.perf_counter()
    all_entries: list[bool] = []
    per_pair_wr = {}
    for name in PAIRS:
        df = load_pair(name)
        if args.limit:
            df = df.iloc[-args.limit:]
        entries = signals_from_pair(df)
        if entries.size:
            per_pair_wr[name] = float(entries.mean())
        all_entries.extend(entries.tolist())
        print(f"  {name:7s}: señales={entries.size:6d}  wr={per_pair_wr.get(name, 0):.4f}",
              file=sys.stderr)

    entries = np.asarray(all_entries, dtype=bool)
    n = int(entries.size)
    wr = float(entries.mean()) if n else 0.0

    exp = pnl_sim.expectancy_per_signal(wr, args.payout)
    be = pnl_sim.break_even_wr(args.payout)
    sim = pnl_sim.simulate(entries, payout=args.payout, stake=args.stake)

    edge_holds = exp > 0.0
    elapsed = time.perf_counter() - t0

    print("=" * 60)
    print(f"EDGE DEL FRENO — simulación de rentabilidad (payout={args.payout:.0%})")
    print("=" * 60)
    print(f"Señales totales      : {n}")
    print(f"Win-rate realizado   : {wr:.4f}  ({sim['wins']} aciertos)")
    print(f"Expectancy/señal     : {exp:+.4f}  (por $1 apostado)")
    print(f"Break-even WR        : {be:.4f}")
    print(f"ROI (sin reinversión): {sim['roi']:.4f}")
    print(f"PnL total            : {sim['total_return']:+.2f} ({args.stake}/señal)")
    print(f"Margen sobre BE      : {wr - be:+.4f}  "
          f"({'EDGE AGUANTA' if edge_holds else 'EDGE NO AGUANTA'} tras costos)")
    print(f"Duración             : {elapsed:.2f}s")
    print("=" * 60)

    # código de salida: 0 si el edge aguanta, 1 si no
    return 0 if edge_holds else 1


if __name__ == "__main__":
    raise SystemExit(main())
