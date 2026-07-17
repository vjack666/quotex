"""Tests de la heurística observacional spring_confirmed (NO es el SSD real).

Solo verifica que la etiqueta se calcule y propague sin alterar la
decisión de entrada. No bloquea ni cambia score/dirección.
"""
from models import Candle
from strat_fractal import (
    _spring_heuristic_5m1m,
    evaluate_strat_f,
)


def _c(ts, o, h, l, c):
    return Candle(ts=ts, open=o, high=h, low=l, close=c)


def _make_5m(fractal_low, post_lows, fractal_idx=2, n=6):
    """Arma 5m con fractal_down en fractal_idx y post-velas con low=post_lows."""
    candles = [
        _c(0, 1.1000, 1.1010, 1.0990, 1.1005),
        _c(300, 1.1005, 1.1015, 1.0995, 1.1000),
        _c(600, 1.1000, 1.1005, fractal_low, 1.0998),  # fractal down (suelo)
    ]
    for i, pl in enumerate(post_lows):
        candles.append(
            _c(900 + i * 300, pl + 0.0005, pl + 0.0010, pl, pl + 0.0003)
        )
    while len(candles) < n:
        candles.append(_c(len(candles) * 300, 1.10, 1.101, 1.099, 1.10))
    return candles, fractal_idx


def test_spring_call_true_when_min_above_band():
    candles_5m, fidx = _make_5m(fractal_low=1.0980, post_lows=[1.0985, 1.0990, 1.0992])
    # mínimo post-fractal 1.0985 >= band 1.0980 -> spring True
    res = _spring_heuristic_5m1m(candles_5m, [], fidx, 1.0980, "CALL")
    assert res is True


def test_spring_call_false_when_break_below_band():
    candles_5m, fidx = _make_5m(fractal_low=1.0980, post_lows=[1.0975, 1.0981, 1.0990])
    # primera post-vela rompió el suelo (1.0975 < 1.0980) -> False
    res = _spring_heuristic_5m1m(candles_5m, [], fidx, 1.0980, "CALL")
    assert res is False


def test_spring_put_mirror_true():
    candles_5m = [
        _c(0, 1.2000, 1.2010, 1.1990, 1.2005),
        _c(300, 1.2005, 1.2015, 1.1995, 1.2000),
        _c(600, 1.2000, 1.2020, 1.1998, 1.2015),  # fractal up (techo)
    ]
    for i, ph in enumerate([1.2015, 1.2012, 1.2010]):
        candles_5m.append(
            _c(900 + i * 300, ph - 0.0003, ph, ph - 0.0005, ph - 0.0002)
        )
    while len(candles_5m) < 6:
        candles_5m.append(_c(len(candles_5m) * 300, 1.20, 1.201, 1.199, 1.20))
    # máximo post-fractal <= band 1.2020 -> spring True
    res = _spring_heuristic_5m1m(candles_5m, [], 2, 1.2020, "PUT")
    assert res is True


def test_spring_none_when_insufficient():
    candles_5m, fidx = _make_5m(fractal_low=1.0980, post_lows=[])
    # fractal en last_idx (sin post-velas 5m) y sin 1m -> None
    candles_5m = candles_5m[:3]
    res = _spring_heuristic_5m1m(candles_5m, [], 2, 1.0980, "CALL")
    assert res is None


def test_evaluate_strat_f_propagates_spring_confirmed():
    candles_5m, fidx = _make_5m(fractal_low=1.0980, post_lows=[1.0985, 1.0990, 1.0992])
    candles_1m = [_c(i * 60, 1.10, 1.10, 1.099, 1.10) for i in range(10)]
    candles_15m = [_c(i * 900, 1.10, 1.105, 1.095, 1.10) for i in range(10)]
    ev = evaluate_strat_f(candles_15m, candles_5m, candles_1m, payout=90)
    assert ev.has_signal is True
    assert ev.spring_confirmed is True


def test_evaluate_strat_f_spring_true_does_not_block():
    # Fractal válido (post-velas con low >= band) -> spring_confirmed=True.
    # La señal se acepta IGUAL (la etiqueta no bloquea).
    candles_5m, fidx = _make_5m(fractal_low=1.0980, post_lows=[1.0985, 1.0990, 1.0992])
    candles_1m = [_c(i * 60, 1.10, 1.10, 1.099, 1.10) for i in range(10)]
    candles_15m = [_c(i * 900, 1.10, 1.105, 1.095, 1.10) for i in range(10)]
    ev = evaluate_strat_f(candles_15m, candles_5m, candles_1m, payout=90)
    assert ev.has_signal is True
    assert ev.spring_confirmed is True
