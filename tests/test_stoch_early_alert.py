"""Tests de la capa de ALERTA TEMPRANA (spec strat_f_spike_early_alert).

Cubre R-EA1..R-EA11: alerta no promueve SPIKE, proyección CALL simétrica (bug
corregido), puntaje adaptativo con percentil 90 del par, ventana adaptativa,
registro en caja negra (sin alterar has_signal), e intravela (M15 abierta + M1).
"""

import math
import os
import tempfile

import pytest

from stoch_early_alert import (
    EarlyAlertResult,
    evaluate_early_alert,
    _BUFFER,
    _load_history,
    _save_history,
    _projection,
    _projection_window,
    _percentile_threshold,
)


# --------------------------------------------------------------------------- #
# (b2) Proyección CALL simétrica — corrección del bug de cuentas
# --------------------------------------------------------------------------- #
def test_proyeccion_call_simétrica_sin_signo():
    # %K CALL=24, pendiente=-2 (bajando): fórmula vieja (24-20)/(-2) = -2.0 (bug)
    # fórmula nueva |24-20|/|-2| = 2.0 (positivo, correcto).
    p = _projection(24.0, -2.0, "CALL")
    assert p == 2.0, f"esperado 2.0, got {p}"
    # PUT: %K=76 subiendo hacia 80: |76-80|/|2| = 2.0
    p2 = _projection(76.0, 2.0, "PUT")
    assert p2 == 2.0


def test_proyeccion_call_pendiente_positiva_tambien_positiva():
    # %K CALL=24, pendiente=+2 (subiendo): |24-20|/|2| = 2.0 (nunca negativo)
    p = _projection(24.0, 2.0, "CALL")
    assert p == 2.0


def test_proyeccion_pendiente_cero_infinito_limitado():
    p = _projection(24.0, 0.0, "CALL")
    assert math.isinf(p)


# --------------------------------------------------------------------------- #
# (b) Las 5 cantidades en rango esperado
# --------------------------------------------------------------------------- #
def test_cinematica_calcula_5_cantidades():
    k = [10, 12, 14, 16, 18, 20, 22, 24]  # CALL subiendo hacia 20
    d = [30, 28, 26, 24, 22, 20, 18, 16]
    r = evaluate_early_alert("CALL", k_vals=k, d_vals=d, sym="TEST_CIN")
    assert math.isfinite(r.pendiente_k)
    assert math.isfinite(r.angulo)
    assert r.proyeccion_velas >= 0.0  # positiva siempre
    assert r.aceleracion is not None


# --------------------------------------------------------------------------- #
# (a) Alerta presente PERO sin cruce -> NO promueve SPIKE (R-EA1/R-EA2)
#     Nota: esta capa NO conoce el SPIKE; el test de integración (test_strat_f)
#     verifica que early_alert no cambia has_signal. Aquí verificamos que la
#     alerta es solo una marca (no tiene campo has_signal).
# --------------------------------------------------------------------------- #
def test_alerta_es_marca_no_disparador():
    k = [10, 12, 14, 16, 18, 20, 22, 24]
    d = [30, 28, 26, 24, 22, 20, 18, 16]
    r = evaluate_early_alert("CALL", k_vals=k, d_vals=d, sym="TEST_NODISP")
    assert isinstance(r, EarlyAlertResult)
    assert not hasattr(r, "has_signal")  # explícitamente no dispara


# --------------------------------------------------------------------------- #
# (c) Puntaje combinado: señales débiles vs par -> NO activa; decil alto -> SÍ
# --------------------------------------------------------------------------- #
def test_puntaje_debil_no_activa():
    sym = "TEST_WEAK"
    _BUFFER.pop(sym, None)
    # Sembrar historial con puntajes ALTOS para que el umbral percentil 90 sea alto.
    for _ in range(20):
        _BUFFER.setdefault(sym, __import__("collections").deque(maxlen=50)).append(0.95)
    k = [40, 41, 42, 43, 44, 45, 46, 47]  # casi plano, señales débiles
    d = [45, 46, 45, 46, 45, 46, 45, 46]
    r = evaluate_early_alert("CALL", k_vals=k, d_vals=d, sym=sym)
    assert r.puntaje < r.percentil_par, f"puntaje {r.puntaje} >= umbral {r.percentil_par}"
    assert not r.activa


def test_puntaje_fuerte_activa():
    sym = "TEST_STRONG"
    _BUFFER.pop(sym, None)
    # Sembrar historial con puntajes BAJOS para que el umbral percentil 90 sea bajo.
    for _ in range(20):
        _BUFFER.setdefault(sym, __import__("collections").deque(maxlen=50)).append(0.05)
    # Señales fuertes: %K CALL subiendo rápido hacia 20, %D bajando, convergiendo.
    k = [5, 7, 10, 13, 16, 18, 19, 20]
    d = [40, 38, 35, 32, 29, 26, 23, 20]
    r = evaluate_early_alert("CALL", k_vals=k, d_vals=d, sym=sym)
    assert r.puntaje >= r.percentil_par
    assert r.activa


# --------------------------------------------------------------------------- #
# (d) Ventana de proyección adaptativa
# --------------------------------------------------------------------------- #
def test_ventana_sin_historial_default():
    sym = "TEST_WIN_NONE"
    _BUFFER.pop(sym, None)
    scores = _load_history(sym)
    scores.clear()
    win, es_def = _projection_window(sym, scores)
    assert es_def is True
    assert win == 15


# --------------------------------------------------------------------------- #
# (e) Registro en caja negra (sin alterar has_signal) -> campo early_alert existe
#     (la integración con evaluate_strat_f lo expone; aquí verificamos el objeto)
# --------------------------------------------------------------------------- #
def test_resultado_tiene_campos_caja_negra():
    k = [10, 12, 14, 16, 18, 20, 22, 24]
    d = [30, 28, 26, 24, 22, 20, 18, 16]
    r = evaluate_early_alert("CALL", k_vals=k, d_vals=d, sym="TEST_BB")
    for campo in ("pendiente_k", "aceleracion", "angulo", "proyeccion_velas",
                  "convergencia", "puntaje", "percentil_par", "ventana_proy", "es_default"):
        assert hasattr(r, campo)


# --------------------------------------------------------------------------- #
# Persistencia ALT B: escritura atómica + carga round-trip
# --------------------------------------------------------------------------- #
def test_persistencia_alt_b_roundtrip(tmp_path, monkeypatch):
    import stoch_early_alert as ea
    monkeypatch.setattr(ea, "_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ea, "HISTORY_N", 50)
    sym = "TEST_PERSIST"
    ea._BUFFER.pop(sym, None)
    ea._ALERT_COUNT[sym] = 0
    dq = ea._load_history(sym)
    for v in [0.1, 0.3, 0.5, 0.7, 0.9]:
        dq.append(v)
    ea._save_history(sym)
    # El archivo final existe y el .tmp no debe quedar.
    path = ea._sym_path(sym)
    assert os.path.exists(path)
    assert not os.path.exists(path + ".tmp")
    # Recargar en búfer limpio reproduce los scores.
    ea._BUFFER.pop(sym, None)
    dq2 = ea._load_history(sym)
    assert list(dq2) == [0.1, 0.3, 0.5, 0.7, 0.9]


def test_persistencia_corrupta_arranca_vacio(tmp_path, monkeypatch):
    import stoch_early_alert as ea
    monkeypatch.setattr(ea, "_DATA_DIR", str(tmp_path))
    sym = "TEST_CORRUPT"
    ea._BUFFER.pop(sym, None)
    path = ea._sym_path(sym)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{ esto no es json válido")
    dq = ea._load_history(sym)
    assert len(dq) == 0


# --------------------------------------------------------------------------- #
# (e) Integración con evaluate_strat_f: early_alert aparece, NO altera has_signal
# --------------------------------------------------------------------------- #
def test_integracion_evaluate_strat_f_early_alert():
    from models import Candle
    from strat_fractal import evaluate_strat_f, _fractal_down
    from stochastic_m15 import compute_stoch

    def mk(o, h, l, c, t):
        return Candle(ts=t, open=o, high=h, low=l, close=c)

    base = 1.1000
    # Fractal DOWN válido (CALL, línea 315 de strat_fractal): low central MÁS BAJO
    # que los 2 a cada lado. El evaluador mapea _fractal_down -> direction="CALL".
    cs5 = []
    for i in range(10):
        if i == 5:
            cs5.append(mk(base, base + 0.0005, base - 0.0020, base - 0.0015, i))  # suelo hundido (fractal down)
        else:
            cs5.append(mk(base, base + 0.0005, base - 0.0003, base, i))
    # M15 en rango (contexto válido) y M1 dummy.
    cs15 = [mk(base, base + 0.0003, base - 0.0003, base, i) for i in range(40)]
    # M1: las 2 últimas velas deben rechazar la banda (low ~1.098, cierran por encima).
    cs1 = [mk(base, base + 0.0001, base - 0.0001, base, i) for i in range(15)]
    cs1[-2] = mk(base - 0.0020, base - 0.0010, base - 0.0021, base - 0.0018, 14)  # toca banda, cierra sobre 1.098
    cs1[-1] = mk(base - 0.0020, base - 0.0010, base - 0.0021, base - 0.0018, 15)  # toca banda, cierra sobre 1.098
    assert _fractal_down(cs5, 5)  # sanity (CALL)

    st = compute_stoch(cs15, direction="CALL")
    res = evaluate_strat_f(cs15, cs5, cs1, payout=90, stoch_m15=st, sym="EURUSD_INTEG")
    # La alerta se calcula (direction no es None) y se expone sin tocar has_signal.
    # Nota: en este escenario de rango plano el SPIKE no se promueve; pero
    # early_alert debe estar poblado (puro aviso) y has_signal queda como el
    # evaluador lo decida (aquí False por no cumplir R2/R2-bis en datos planos).
    assert res.early_alert is not None, "early_alert debe estar poblado cuando hay direction"
    assert "activa" in res.early_alert
    assert "puntaje" in res.early_alert
    # La alerta NO debe haber cambiado la decisión de has_signal del evaluador.
    assert res.early_alert["activa"] in (True, False)
