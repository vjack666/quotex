"""Tests deterministas para el agente offline de aprendizaje buenas/malas.

No dependen del estado de los DBs reales: usan trades sinteticos para
validar la logica pura (analyze, detect_patterns, render_report,
compute_drift) y la carga lightgbm-free.
"""

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from ml_features import FEATURE_NAMES  # noqa: E402

# Importamos el agente como modulo.
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import agent_review as ag  # noqa: E402


def _mk(target, **feats):
    """Construye un trade sintetico con features por defecto + overrides."""
    f = {name: 0.0 for name in FEATURE_NAMES}
    f.update(feats)
    return {"features": f, "target": target, "ts": 1.0, "source": "synthetic"}


def _synth_trades():
    """Dataset sintetico con patrones claros y una feature muerta."""
    trades = []
    # WIN fuertes: PUT en Z3 con spring_margin alto y angle positivo.
    for _ in range(20):
        trades.append(_mk(1, direction=0.0, stoch_zone=3.0, spring_margin=1000.0, math_angle_deg=1.0, payout=88.0))
    # LOSS claros: PUT en Z5 con spring_margin bajo y angle negativo.
    for _ in range(20):
        trades.append(_mk(0, direction=0.0, stoch_zone=5.0, spring_margin=2.0, math_angle_deg=-1.0, payout=88.0))
    # Ruido: CALL variado.
    for _ in range(10):
        trades.append(_mk(1, direction=1.0, stoch_zone=1.0, payout=85.0))
    for _ in range(10):
        trades.append(_mk(0, direction=1.0, stoch_zone=1.0, payout=85.0))
    return trades


def test_analyze_basic():
    trades = _synth_trades()
    a = ag.analyze(trades)
    assert a["n"] == 60
    assert a["n_win"] == 30
    assert abs(a["winrate"] - 0.5) < 1e-9
    # Una de las dos features claramente separadoras debe estar en el top.
    top = a["discrimination"][0]["feature"]
    assert top in ("math_angle_deg", "spring_margin")
    # payout tiene varianza 0 dentro de cada subgrupo dominante? no: tiene 85 y 88.
    # direction y stoch_zone no deben estar muertas.
    assert "direction" not in a["dead_features"]


def test_dead_features_detected():
    # Todos los trades con score_compression siempre 0 -> muerta.
    trades = [_mk(1, score_compression=0.0) for _ in range(5)] + \
             [_mk(0, score_compression=0.0) for _ in range(5)]
    a = ag.analyze(trades)
    assert "score_compression" in a["dead_features"]


def test_detect_patterns_good_and_bad():
    trades = _synth_trades()
    pat = ag.detect_patterns(trades, min_support=5, good_wr=0.7, bad_wr=0.3)
    good_dirs = {(e["direction"], e["stoch_zone"]) for e in pat["good"]}
    bad_dirs = {(e["direction"], e["stoch_zone"]) for e in pat["bad"]}
    assert ("PUT", 3) in good_dirs   # PUT Z3 -> 100% win
    assert ("PUT", 5) in bad_dirs    # PUT Z5 -> 0% win


def test_detect_patterns_min_support_filters():
    # Poco volumen en Z3 -> no debe aparecer aunque sea 100% win.
    trades = [_mk(1, direction=0.0, stoch_zone=3.0) for _ in range(3)]
    pat = ag.detect_patterns(trades, min_support=10, good_wr=0.7, bad_wr=0.3)
    assert pat["good"] == []
    assert pat["bad"] == []


def test_compute_drift():
    prev = {"winrate": 0.5, "discrimination": [{"feature": "a"}, {"feature": "b"}]}
    cur = {"winrate": 0.6, "discrimination": [{"feature": "a"}, {"feature": "b"}]}
    d = ag.compute_drift(prev, cur)
    assert abs(d["winrate_delta"] - 0.1) < 1e-9
    assert d["top_features_changed"] is False

    cur2 = {"winrate": 0.6, "discrimination": [{"feature": "x"}, {"feature": "y"}]}
    d2 = ag.compute_drift(prev, cur2)
    assert d2["top_features_changed"] is True


def test_build_digest_short():
    trades = _synth_trades()
    a = ag.analyze(trades)
    pat = ag.detect_patterns(trades, min_support=5, good_wr=0.7, bad_wr=0.3)
    digest = ag._build_digest(a, pat, {}, None, "data/agent/report-X.md")
    assert "QUOTEX agent digest" in digest
    assert "MEJOR patron GOOD" in digest
    assert "PEOR patron BAD" in digest
    assert "reporte completo" in digest


def test_render_report_no_crash():
    trades = _synth_trades()
    a = ag.analyze(trades)
    pat = ag.detect_patterns(trades, min_support=5, good_wr=0.7, bad_wr=0.3)
    report = ag.render_report(a, pat, {}, None)
    assert "Winrate global" in report
    assert "BAD patterns" in report
    assert "GOOD patterns" in report


def test_load_resolved_trades_real_runs():
    """Smoke test: la carga lightgbm-free debe correr sobre los DBs reales
    sin crashear (no imponemos conteo exacto, solo que devuelva lista)."""
    trades = ag.load_resolved_trades()
    assert isinstance(trades, list)
    # Cada fila debe tener las 18 features.
    for t in trades[:5]:
        assert set(t["features"].keys()) == set(FEATURE_NAMES)
        assert t["target"] in (0, 1)
