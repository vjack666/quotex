"""EW / 6E diario — ADQUISICIÓN gratuita desde Yahoo Finance (FASE 1 GRATIS; AUTORIZADO A 2026-08-07).

Instrumento: CME Euro FX Futures continuous `6E=F` (Yahoo). Volumen = contratos negociados reales
(en exchange), NO tick volume. Escala: DIARIO (D1) — adaptación formal de EW-1 M15->D1 autorizada.

Objetivo de este script: SOLO adquirir y guardar el raw. NO construye features ni ejecuta EW-1.
La congelación y ejecución de EW-1 permanece en su propio gate (autorización del Trader-Humano).

Salida: data/strategy_lab/ew_6e_daily.parquet (gitignored). Columnas: open,high,low,close,volume.
Índice: DatetimeIndex (Yahoo devuelve tz-aware; se convierte a UTC naive para consistencia).
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

SYM = "6E=F"
START = "2022-01-01"
END = "2026-08-01"
OUT = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\ew_6e_daily.parquet")


def main() -> int:
    print(f"[acquire] {SYM} diario {START}..{END}")
    t = yf.Ticker(SYM)
    df = t.history(interval="1d", start=START, end=END, auto_adjust=False)
    if df is None or len(df) == 0:
        print("[acquire] ERROR: sin datos (¿símbolo o rango no disponible en Yahoo?)")
        return 1
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["open", "high", "low", "close", "volume"]
    # Yahoo devuelve índice tz-aware (America/New_York). Convertir a UTC naive.
    df.index = pd.to_datetime(df.index, utc=True).tz_convert("UTC").tz_localize(None)
    df.index.name = "time"
    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT)
    print(f"[acquire] OK: {len(df):,} barras  rango {df.index.min().date()}..{df.index.max().date()}")
    print(f"[acquire] guardado: {OUT}")
    print(f"[acquire] vol: min={df.volume.min():.0f} mean={df.volume.mean():.0f} "
          f"max={df.volume.max():.0f} %ceros={ (df.volume==0).mean():.2%} %missing={df.volume.isna().mean():.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
