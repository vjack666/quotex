"""Guard de integridad de timeframe (causa raíz USDPHP 2026-07-27).

Quotex a veces devuelve velas de OTRO timeframe (M1 cuando se pidió M5/M15).
_enforce_timeframe debe: dejar pasar spacing correcto, resamplear spacing más
fino (datos reales, jamás inventados) y descartar spacing incompatible.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from connection import _dominant_spacing, _enforce_timeframe, _resample_candles  # noqa: E402
from models import Candle  # noqa: E402


def _mk(ts: int, o: float, h: float, l: float, c: float, ticks: int = 1) -> Candle:
    return Candle(ts=ts, open=o, high=h, low=l, close=c, ticks=ticks)


def _series(start: int, step: int, n: int) -> list[Candle]:
    out = []
    px = 100.0
    for i in range(n):
        out.append(_mk(start + i * step, px, px + 0.5, px - 0.5, px + 0.1))
        px += 0.1
    return out


def test_spacing_correcto_pasa_intacto():
    velas = _series(1_785_150_000, 300, 30)
    assert _enforce_timeframe(velas, 300, "X_otc") == velas


def test_m1_disfrazada_de_m5_se_resamplea():
    # 30 velas de 60s pedidas como M5 → deben salir buckets de 300s
    velas = _series(1_785_150_000, 60, 30)
    out = _enforce_timeframe(velas, 300, "USDPHP_otc")
    assert out, "no debe descartar: puede resamplear"
    spacing = _dominant_spacing(out)
    assert spacing == 300
    assert all(c.ts % 300 == 0 for c in out)


def test_m1_disfrazada_de_m15_se_resamplea():
    velas = _series(1_785_150_000, 60, 45)
    out = _enforce_timeframe(velas, 900, "USDPHP_otc")
    assert out and _dominant_spacing(out) == 900


def test_resample_ohlc_correcto():
    base = 1_785_150_000  # múltiplo de 300
    velas = [
        _mk(base + 0, 10.0, 11.0, 9.5, 10.5, ticks=2),
        _mk(base + 60, 10.5, 12.0, 10.4, 11.0, ticks=3),
        _mk(base + 120, 11.0, 11.2, 8.0, 9.0, ticks=1),
        _mk(base + 180, 9.0, 9.5, 8.8, 9.2, ticks=4),
        _mk(base + 240, 9.2, 9.6, 9.0, 9.4, ticks=5),
    ]
    out = _resample_candles(velas, 300)
    assert len(out) == 1
    v = out[0]
    assert v.ts == base
    assert v.open == 10.0 and v.close == 9.4
    assert v.high == 12.0 and v.low == 8.0
    assert v.ticks == 15


def test_spacing_incompatible_se_descarta():
    # velas de 900s cuando se pidió 300s: no se puede recomponer → []
    velas = _series(1_785_150_000, 900, 10)
    assert _enforce_timeframe(velas, 300, "X_otc") == []


def test_tf_m1_no_se_toca():
    velas = _series(1_785_150_000, 60, 10)
    assert _enforce_timeframe(velas, 60, "X_otc") == velas


def test_pocas_velas_no_se_toca():
    velas = _series(1_785_150_000, 60, 2)
    assert _enforce_timeframe(velas, 300, "X_otc") == velas
