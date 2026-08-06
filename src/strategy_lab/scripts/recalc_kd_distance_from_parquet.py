"""Recalcula kd_distance y stochastics desde parquet M15 para backtest offline.

Usa:
- EURUSD_M15.parquet como fuente de velas M15
- `src/stochastic_m15.py::compute_stoch` para reproducir la feature del bot

Genera CSV listo para EXP-037 con columnas:
ts, direction, kd_distance, stoch_k, stoch_d, state
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from models import Candle
from stochastic_m15 import compute_stoch


M15_PARQUET = Path(r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\EURUSD_M15.parquet")
OUT_CSV = PROJECT_ROOT / "data" / "exports" / "exp037_kd_distance_dataset.csv"
FAST = True  # filtra solo zonas de posible interés


def load_m15(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)
    return df


def row_to_candle(row: pd.Series) -> Candle:
    return Candle(
        ts=int(row["time"].timestamp()),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        ticks=int(row.get("tick_volume", 0) or 0),
    )


def evaluate_slice(candles: list[Candle]) -> dict:
    st = compute_stoch(candles)
    k = st.get("k")
    d = st.get("d")
    kd = None
    if k is not None and d is not None:
        try:
            kd = abs(float(k) - float(d))
        except (TypeError, ValueError):
            kd = None
    return {
        "stoch_k": k,
        "stoch_d": d,
        "kd_distance": kd,
        "state": st.get("estado"),
        "cruce": st.get("cruce"),
    }


def build_dataset(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    closes = df["close"].tolist()
    need = 30 if FAST else 60
    for i in range(need, len(df) - 10):
        window = df.iloc[i - need : i]
        candles = [row_to_candle(r) for _, r in window.iterrows()]
        info = evaluate_slice(candles)
        if FAST and info["kd_distance"] is None:
            continue
        rows.append(
            {
                "ts": df.iloc[i]["time"],
                "direction": "call" if closes[i] > closes[i - 1] else "put",
                "kd_distance": info["kd_distance"],
                "stoch_k": info["stoch_k"],
                "stoch_d": info["stoch_d"],
                "state": info["state"],
                "cruce": info["cruce"],
            }
        )
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> None:
    print("rows=", len(df), sep="")
    print("kd_distance stats:")
    print(df["kd_distance"].describe().to_string())
    print("state counts:")
    print(df["state"].value_counts(dropna=False).to_string())


def main() -> int:
    print("m15=", M15_PARQUET, sep="")
    if not M15_PARQUET.exists():
        raise SystemExit(f"missing parquet: {M15_PARQUET}")
    raw = load_m15(M15_PARQUET)
    print("raw_rows=", len(raw), sep="")
    dataset = build_dataset(raw)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(OUT_CSV, index=False)
    print("out=", OUT_CSV, sep="")
    summarize(dataset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
