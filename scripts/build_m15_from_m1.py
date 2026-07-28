"""Agrega EURUSD M1 -> M15 usando los datos Dukascopy prestados de SMC-SYSTEMS.

READ-ONLY sobre la fuente: NO se copia ni modifica el parquet de SMC.
El resultado se guarda en data/smc_borrowed/EURUSD_M15.parquet (prestamo
registrado, separado del repo SMC). Esto da M15 de 14 anos sin re-descargar.

Uso:
  PYTHONPATH=src .venv/Scripts/python.exe scripts/build_m15_from_m1.py
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SRC = "C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw/EURUSD_M1.parquet"
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "smc_borrowed")
OUT = os.path.join(OUT_DIR, "EURUSD_M15.parquet")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"[build] leyendo {SRC}")
    df = pq.read_table(SRC).to_pandas()
    df = df.sort_values("time").reset_index(drop=True)
    # time viene como datetime64[ms, UTC]; pasamos a tz-naive para agrupar por 15min.
    t = df["time"].dt.tz_localize(None) if df["time"].dt.tz is not None else df["time"]
    df["bucket"] = t.dt.floor("15min")
    g = df.groupby("bucket", sort=True)
    out = pd.DataFrame({
        "time": g["time"].min(),
        "open": g["open"].first(),
        "high": g["high"].max(),
        "low": g["low"].min(),
        "close": g["close"].last(),
        "tick_volume": g["tick_volume"].sum(),
        "volume": g["volume"].sum() if "volume" in df.columns else g["tick_volume"].sum(),
    }).reset_index(drop=True)
    out = out.rename(columns={"bucket": "time"})
    # descartar velas incompletas al inicio/fin (bucket sin 15min completos)
    out = out.dropna(subset=["open", "high", "low", "close"])
    print(f"[build] M15 filas: {len(out)}  rango: {out['time'].min()} -> {out['time'].max()}")
    span = (out["time"].max() - out["time"].min()).days / 365.0
    print(f"[build] ~{span:.1f} anos")
    out.to_parquet(OUT, index=False)
    print(f"[build] guardado en {OUT}")


if __name__ == "__main__":
    main()
