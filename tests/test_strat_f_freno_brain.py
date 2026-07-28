"""Tests de cableado: STRAT-F delega en el motor de leyes (cerebro de freno).

No tocan el bot. Verifican que evaluate_strat_f, con STRAT_F_FRENO_BRAIN
ON, llama al motor y traduce su salida a StratFEvaluation SIN cambiar la
forma que el scanner consume (has_signal/direction/strength/zone/...).

Usa datos REALES de cajas negras para el test de integracion (el freno ya
marca 88% ahi). Si no hay DB, esos tests se skipean (no es fallo).
"""
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from models import Candle
from strat_fractal import evaluate_strat_f, StratFEvaluation


def _make_candles(ohlc_list, ts0=1_700_000_000):
    out = []
    for i, (o, h, l, c) in enumerate(ohlc_list):
        out.append(Candle(
            ts=ts0 + i * 900,  # 15m
            open=o, high=h, low=l, close=c,
            ticks=0,
        ))
    return out


def test_freno_ON_motor_dispara_traduce_senal():
    # Mockea el cerebro para que decida entrar en CALL.
    fake = StratFEvaluation(
        has_signal=True, direction="CALL", strength=0.85,
        m15_context="IMPULSE_DYING", m5_event="freno",
        pattern_name="freno_rebound", zone=None, confirms=True,
        info="FRENO-BRAIN OK leyes=['FRENO-IMPULSO-MUERTO'] conf=40 dir=CALL",
    )
    candles = _make_candles([(1.20 + i * 1e-4, 1.20 + i * 1e-4, 1.20 + i * 1e-4,
                             1.20 + i * 1e-4) for i in range(40)])
    with patch("strat_fractal._run_freno_brain", return_value=fake):
        ev = evaluate_strat_f(candles, candles, candles, payout=85,
                              freno_brain=True)
    assert ev.has_signal is True
    assert ev.direction == "CALL"
    assert ev.m15_context == "IMPULSE_DYING"
    assert ev.m5_event == "freno"
    assert ev.pattern_name == "freno_rebound"
    assert ev.confirms is True


def test_freno_ON_motor_bloquea_traduce_skip():
    fake = StratFEvaluation(
        has_signal=False, direction=None,
        m15_context="IMPULSE_DYING", m5_event="freno",
        skip_reason="freno:STOCH-EXTREMO stoch 50.0 no sobreventa para CALL",
        info="FRENO-BRAIN bloqueado por STOCH-EXTREMO",
    )
    candles = _make_candles([(1.20 + i * 1e-4,) * 4 for i in range(40)])
    with patch("strat_fractal._run_freno_brain", return_value=fake):
        ev = evaluate_strat_f(candles, candles, candles, payout=85,
                              freno_brain=True)
    assert ev.has_signal is False
    assert "freno:" in (ev.skip_reason or "")


def test_freno_OFF_no_llama_motor():
    # Con freno OFF, el cerebro no debe disparar (cae al fractal clasico).
    # Usamos velas sin fractal -> skip normal de fractal, NO de freno.
    candles = _make_candles([(1.20,) * 4 for _ in range(40)])
    with patch("strat_fractal._run_freno_brain") as mk:
        ev = evaluate_strat_f(candles, candles, candles, payout=85,
                              freno_brain=False)
    mk.assert_not_called()
    # El fractal clasico no encuentra fractal -> skip sin mencionar freno.
    assert ev.has_signal is False
    assert "freno" not in (ev.skip_reason or "")


def _real_m15_from_blackbox():
    db = Path("data/db/black_box_strat_2026-07-17.db")
    if not db.exists():
        pytest.skip("caja negra no disponible")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT asset, candles_15m FROM scan_candidates "
            "WHERE candles_15m IS NOT NULL"
        ).fetchall()
    finally:
        con.close()
    from collections import defaultdict
    by_asset: dict[str, dict] = defaultdict(dict)
    for asset, raw in rows:
        try:
            arr = json.loads(raw)
        except (TypeError, ValueError):
            continue
        for cc in arr or []:
            try:
                ts = float(cc["ts"])
            except (KeyError, TypeError, ValueError):
                continue
            by_asset[asset][ts] = cc
    for asset, d in by_asset.items():
        if len(d) < 40:
            continue
        series = [d[k] for k in sorted(d)]
        candles = _make_candles(
            [(float(c["o"]), float(c["h"]), float(c["l"]), float(c["c"]))
             for c in series],
            ts0=int(series[0]["ts"]),
        )
        return candles, asset
    pytest.skip("sin activo con >=40 velas M15")


def test_freno_ON_integracion_datos_reales_no_explota():
    # Verifica que el cableado real (motor + datos reales) produce una
    # evaluacion valida sin excepcion. No afirma direccion (depende de datos).
    try:
        (candles, asset) = _real_m15_from_blackbox()
    except TypeError:
        pytest.skip("caja negra no disponible")
    ev = evaluate_strat_f(candles, candles, candles, payout=85,
                          freno_brain=True, sym=asset)
    assert isinstance(ev, StratFEvaluation)
    # Sea senal o skip, el campo m15_context refleja el cerebro.
    assert ev.m15_context == "IMPULSE_DYING"
    if ev.has_signal:
        assert ev.direction in ("CALL", "PUT")
        assert ev.strength > 0
