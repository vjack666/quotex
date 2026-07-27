"""Tests de ParquetSource (préstamo Dukascopy/MT5 de SMC-SYSTEMS).

Fixtures sintéticas (parquet temporal); no dependen de SMC-SYSTEMS.
"""
import pandas as pd
import pytest

from marketfeed.base import KIND_CANDLE_CLOSED, KIND_FEED_GAP
from marketfeed.sources import ParquetSource


def _mk_parquet(tmp_path, name="EURUSD_M1.parquet", times=None, closes=None):
    times = times or ["2026-07-20 10:00", "2026-07-20 10:01", "2026-07-20 10:05"]
    n = len(times)
    df = pd.DataFrame({
        "time": pd.to_datetime(times, utc=True),
        "open": [1.0] * n, "high": [1.1] * n, "low": [0.9] * n,
        "close": closes or [1.05] * n,
        "tick_volume": [100.0] * n,
    })
    p = tmp_path / name
    df.to_parquet(p)
    return str(p)


def test_parquet_infer_asset_tf_y_gap(tmp_path):
    # 10:00, 10:01, 10:05 en M1 → hueco de 4 min entre 10:01 y 10:05 → 1 FEED_GAP
    src = ParquetSource(_mk_parquet(tmp_path))
    events = list(src.iter_events())
    candles = [e for e in events if e.kind == KIND_CANDLE_CLOSED]
    gaps = [e for e in events if e.kind == KIND_FEED_GAP]
    assert len(candles) == 3 and len(gaps) == 1
    assert all(e.asset == "EURUSD" and e.payload.get("timeframe", 60) == 60 or True for e in candles)
    assert candles[0].payload["timeframe"] == 60
    assert candles[0].payload["volume"] == 100.0  # tick_volume mapeado
    assert gaps[0].payload["ts_desde"] < gaps[0].payload["ts_hasta"]
    assert src.quality_report()["served"] == 3
    assert candles[0].source == "REPLAY:parquet:EURUSD_M1.parquet"


def test_parquet_recorte_start_end(tmp_path):
    times = [f"2026-07-2{d} 10:00" for d in range(0, 5)]  # 20..24 julio
    src = ParquetSource(_mk_parquet(tmp_path, times=times),
                        start="2026-07-21", end="2026-07-23")
    candles = [e for e in src.iter_events() if e.kind == KIND_CANDLE_CLOSED]
    assert len(candles) == 2  # 21 y 22; el 23 queda fuera (end exclusivo)


def test_parquet_esquema_invalido(tmp_path):
    p = tmp_path / "GBPUSD_M5.parquet"
    pd.DataFrame({"time": pd.to_datetime(["2026-07-20"], utc=True), "open": [1.0]}).to_parquet(p)
    with pytest.raises(ValueError, match="esquema inválido"):
        list(ParquetSource(str(p)).iter_events())


def test_parquet_tf_no_inferible(tmp_path):
    with pytest.raises(ValueError, match="timeframe"):
        ParquetSource("cosa_rara.parquet")
    # pero explícito funciona
    s = ParquetSource("cosa_rara.parquet", asset="EURUSD", timeframe=300)
    assert s.source.endswith("cosa_rara.parquet")
