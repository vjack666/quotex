"""Genera M15 desde M1 (Dukascopy prestado de SMC, read-only).

Agrega velas M1 a M15 por ventana de 15 min alineada al reloj. Reutilizable
para cualquier par. Salida: data/smc_borrowed/<PAR>_M15.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
DST = ROOT / "data" / "smc_borrowed"


def m1_to_m15(src: Path, dst: Path) -> None:
    df = pd.read_parquet(src)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time").sort_index()
    vol = "tick_volume" if "tick_volume" in df.columns else "volume"
    agg = df.resample("15min").agg({
        "open": "first", "high": "max", "low": "min", "close": "last",
        vol: "sum",
    }).dropna()
    agg = agg.reset_index().rename(columns={vol: "volume"})
    dst.parent.mkdir(parents=True, exist_ok=True)
    agg.to_parquet(dst, index=False)
    print(f"[OK] {src.name} -> {dst.name}: {len(agg):,} velas M15 "
          f"({agg['time'].min()} .. {agg['time'].max()})")


def main() -> int:
    pairs = sys.argv[1:] or ["EURUSD", "XAUUSD"]
    for p in pairs:
        s = SRC / f"{p}_M1.parquet"
        d = DST / f"{p}_M15.parquet"
        if not s.exists():
            print(f"[SKIP] {s} no existe")
            continue
        m1_to_m15(s, d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
