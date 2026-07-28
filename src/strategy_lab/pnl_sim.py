"""pnl_sim — rentabilidad del edge del freno contra costos reales de Quotex.

Funciones puras sobre arrays/escalares (sin reloj de pared, sin I/O).
Modelo de opciones binarias: por cada señal se apuesta `stake`.
  - acierto  -> gana `payout * stake`  (payout como ratio, p.ej. 0.85 = 85%)
  - fallo    -> pierde `stake`
Es decir: retorno neto de la señal = +payout*stake (win) o -stake (loss).

Todo umbral/parámetro es argumento de función: cero literales mágicos.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

# Fracciones por defecto documentadas (pueden sobreescribirse por parámetro).
DEFAULT_PAYOUT = 0.85   # 85% payout típico Quotex
DEFAULT_STAKE = 100.0   # capital por señal (unidad monetaria)


def expectancy_per_signal(win_rate: float, payout: float) -> float:
    """Retorno esperado neto por $1 apostado.

    E = win_rate*payout - (1 - win_rate)*1
    Positivo => la señal es rentable antes de costos operativos extra.
    """
    loss_rate = 1.0 - win_rate
    return win_rate * payout - loss_rate * 1.0


def break_even_wr(payout: float) -> float:
    """Win-rate tal que expectancy = 0.

    Resolviendo w*payout - (1-w) = 0  =>  w = 1 / (1 + payout).
    """
    return 1.0 / (1.0 + payout)


def simulate(entries: Sequence[bool],
             payout: float = DEFAULT_PAYOUT,
             stake: float = DEFAULT_STAKE) -> dict:
    """Simula una secuencia de señales (acierto=True/False).

    Returns
    -------
    dict con:
      equity_curve      : np.ndarray, PnL acumulado (len n+1, arranca en 0)
      total_return      : PnL neto total (moneda)
      n                 : nº de señales
      wins              : nº de aciertos
      expectancy_realizada : retorno medio realizado por señal (moneda)
      roi               : ROI = total_return / (n * stake)  (sin reinversión)
    """
    wins_arr = np.asarray(entries, dtype=bool)
    n = int(wins_arr.size)
    wins = int(wins_arr.sum())

    # resultado por señal: +payout*stake si acierta, -stake si falla
    per_signal = np.where(wins_arr, payout * stake, -stake)
    equity_curve = np.concatenate(([0.0], np.cumsum(per_signal)))
    total_return = float(equity_curve[-1])
    expectancy_realizada = total_return / n if n else 0.0
    capital_at_risk = n * stake
    roi = total_return / capital_at_risk if capital_at_risk else 0.0

    return {
        "equity_curve": equity_curve,
        "total_return": total_return,
        "n": n,
        "wins": wins,
        "expectancy_realizada": expectancy_realizada,
        "roi": roi,
    }


def roi_annualized(equity_curve: Sequence[float],
                   n_signals_per_year: float) -> float:
    """ROI anualizado asumiendo reinversión simple (capitalización geométrica).

    Supuesto documentado: `equity_curve` es un índice de riqueza donde
    equity_curve[0] = capital inicial (>0) y cada paso capitaliza el
    retorno del periodo anterior (reinversión total de ganancias/pérdidas).
    Crecimiento total = equity[-1]/equity[0]; años = n / n_signals_per_year.
    ROI anualizado = crecimiento_total ** (1/años) - 1.
    Si años<=0 devuelve el ROI simple (crecimiento - 1).
    """
    eq = np.asarray(equity_curve, dtype=float)
    if eq.size < 2:
        return 0.0
    initial = float(eq[0])
    if initial <= 0.0:
        raise ValueError("equity_curve[0] (capital inicial) debe ser > 0")
    n = eq.size - 1
    total_growth = float(eq[-1]) / initial
    years = n / float(n_signals_per_year) if n_signals_per_year else 0.0
    if years <= 0.0:
        return total_growth - 1.0
    return total_growth ** (1.0 / years) - 1.0
