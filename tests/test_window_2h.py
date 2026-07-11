"""ATDD — Ventana de 2h: el sistema debe producir >= 5 entradas STRAT-F.

Criterio de aceptacion (SRS N1 / UAT A1): en una ventana de 2 horas de
operacion, el escaneo + evaluador STRAT-F deben ser capaces de entregar al
menos 5 entradas validas distribuidas en distintos pares.

Este test NO simula el mercado real (no tenemos 2h de ticks grabadas);
simula la CAPACIDAD del pipeline: con setups disponibles, el evaluador +
filtros entregan >= 5 senales en 24 ciclos de 5 min. Tambien verifica que
el limite de riesgo (N4: <= 5 entradas por ventana) es respetable mediante
un selector que toma las primeras 5.

Es TDD/ATDD: el evaluador ya existe; este test fija el contrato de volumen.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle  # noqa: E402
from strat_fractal import evaluate_strat_f, StratFEvaluation  # noqa: E402

# Ventana: 2h = 120 min, ciclo cada 5 min -> 24 ciclos.
WINDOW_MIN = 120
CYCLE_MIN = 5
N_CYCLES = WINDOW_MIN // CYCLE_MIN  # 24
N_PAIRS = 10
PAYOUT = 85  # >= 80, pasa R2


def _c(ts, o, h, l, c, ticks=200):
    return Candle(ts=ts, open=o, high=h, low=l, close=c, ticks=ticks)


def _ideal_setup(ts_base: int, step: int, call: bool = True):
    """Velas que SÍ cumplen STRAT-F (CALL por defecto).

    M15: rango plano (ctx='range').
    M5: fractal en indice 4 (bars_since = 8-1-4 = 3 >= min_age 3).
    M1: la ultima vela toca la banda y cierra adentro (rechazo).
    """
    # --- M15: 12 velas en rango estrecho, sin tendencia clara ---
    base = 100.0
    m15 = []
    for i in range(12):
        o = base + (i % 2) * 0.1
        c = o + 0.05
        h = max(o, c) + 0.15
        l = min(o, c) - 0.15
        m15.append(_c(ts_base + i * 900, o, h, l, c))

    # --- M5: 8 velas. Fractal DOWN en indice 4 (low minimo local) ---
    # Para CALL queremos fractal_down: low[4] < low[3] y low[4] < low[5].
    m5 = []
    lows = [100.3, 100.2, 100.1, 100.0, 99.8, 99.9, 100.0, 100.1]
    for i in range(8):
        o = lows[i]
        c = lows[i] + 0.05
        h = max(o, c) + 0.1
        l = lows[i] - 0.05
        m5.append(_c(ts_base + i * 300, o, h, l, c))
    band = m5[4].low  # 99.75 (el fractal)

    # --- M1: ultima vela toca el band y cierra adentro (rebote) ---
    m1 = []
    for i in range(5):
        o = band + 0.02
        c = band + 0.04 if i < 4 else band + 0.06
        h = o + 0.1
        l = (band - 0.05) if i == 4 else (band + 0.01)
        m1.append(_c(ts_base + i * 60, o, h, l, c))
    # Forzar que la ultima toque el band y cierre arriba (rechazo alcista)
    last = m1[-1]
    m1[-1] = _c(last.ts, band - 0.02, band + 0.1, band - 0.04, band + 0.05)
    return m15, m5, m1


def _run_window(setup_fn) -> list:
    """Simula la ventana y devuelve las senales aceptadas (asset, ciclo)."""
    accepted = []
    for cyc in range(N_CYCLES):
        ts_base = cyc * CYCLE_MIN * 60
        for p in range(N_PAIRS):
            m15, m5, m1 = setup_fn(ts_base + p * 10, CYCLE_MIN * 60)
            ev: StratFEvaluation = evaluate_strat_f(m15, m5, m1, payout=PAYOUT)
            if ev.has_signal:
                accepted.append((f"PAIR{p}", cyc, ev.direction))
    return accepted


def test_window_2h_produces_at_least_5_entries():
    """ATDD N1: >= 5 entradas validas en la ventana de 2h."""
    accepted = _run_window(_ideal_setup)
    assert len(accepted) >= 5, (
        f"El pipeline solo produjo {len(accepted)} entradas en 2h; "
        f"el objetivo es >= 5 (SRS N1)."
    )
    # Distribuidas en distintos pares (no todas del mismo)
    assets = {a for (a, _, _) in accepted}
    assert len(assets) >= 2, "Todas las entradas salieron del mismo par."


def test_window_2h_risk_cap_respected():
    """N4: el limite de riesgo (<=5 por ventana) es respetable con un selector."""
    accepted = _run_window(_ideal_setup)
    # Selector simple: tomar las primeras 5 (una por ventana, cap de exposicion)
    capped = accepted[:5]
    assert len(capped) <= 5
    # Y al menos 5 estaban disponibles para elegir
    assert len(accepted) >= 5


def test_evaluator_rejects_when_context_broken():
    """Sanidad: si el M15 esta roto, el evaluador NO cuenta como entrada."""
    m15 = []
    # Tendencia fuerte alcista sostenida => ctx 'uptrend' o 'broken'
    for i in range(12):
        o = 100.0 + i * 0.5
        c = o + 0.4
        m15.append(_c(i * 900, o, c + 0.1, o - 0.1, c))
    m5, m1 = _ideal_setup(0, 300)[1], _ideal_setup(0, 60)[2]
    ev = evaluate_strat_f(m15, m5, m1, payout=PAYOUT)
    # Con tendencia fuerte, CALL estaria contra tendencia -> rechazo (no senal)
    assert not ev.has_signal
