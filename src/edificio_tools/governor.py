"""Gobernador — riesgo y sizing (R6).

CUANDO el ENSAMBLADOR produce BUY o SELL, el sistema invoca al GOBERNADOR antes
de enviar la orden. El Gobernador calcula el tamano de lote via Massaniello
usando la FRECUENCIA y RACHA de la SERIE FILTRADA (la composicion ya filtrada,
no todo el universo P3), y VETA la orden si el DD proyectado excede el limite.

Massaniello (apuesta de cuota fija):
  f = (1 - (1 - p)^n) / n
donde p = WR de la serie filtrada, n = n de la serie filtrada (frecuencia).
Esta f es la fraccion del bankroll a arriesgar de forma que, tras una racha
adversa, la serie se recupera. Para binarias con payout r se ajusta por el
factor de recuperacion.

El veto: si la racha adversa maxima (streak) proyectada con la fraccion f
supera el drawdown limite del cliente, NO_TRADE.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Sizing:
    allowed: bool
    lot_fraction: float     # fraccion del bankroll a arriesgar (0 si vetado)
    lot_size: float         # unidades (bankroll * lot_fraction)
    projected_dd: float     # drawdown proyectado si se alcanza la racha
    reason: str
    meta: Optional[dict] = None


def massaniello_fraction(wr: float, n: int, payout: float = 0.85) -> float:
    """Fraccion Massaniello para binarias.

    wr     : win rate de la serie filtrada (0..1)
    n      : n (frecuencia) de la serie filtrada
    payout : retorno neto por unidad apostada (0.85 = paga 85% sobre el stake)
    """
    if not (0.0 < wr < 1.0):
        raise ValueError(f"wr fuera de rango: {wr}")
    if n <= 0:
        raise ValueError(f"n debe ser > 0: {n}")
    p = wr
    # Formula base (even-money), ajustada por payout:
    # la recuperacion requiere ganar 1/(1+payout) de las veces en la racha.
    base = (1.0 - (1.0 - p) ** n) / n
    # Ajuste por payout: a mayor payout, menor fraccion necesaria.
    adj = base / (1.0 + payout)
    return max(0.0, min(adj, 1.0))


def expected_max_streak(n: int, wr: float) -> int:
    """Racha adversa maxima esperada en n trades con win rate wr.

    Aproximacion de la corrida mas larga de perdidas:
      L ≈ log(n) / log(1/(1-wr))
    """
    if n <= 0 or not (0.0 < wr < 1.0):
        raise ValueError("n>0 y 0<wr<1 requeridos")
    import math
    return max(1, int(round(math.log(n) / math.log(1.0 / (1.0 - wr)))))


@dataclass
class Governor:
    """Calcula sizing Massaniello y veta por DD (R6)."""

    bankroll: float
    dd_limit: float = 0.20            # drawdown maximo tolerado (20% del bankroll)
    payout: float = 0.85             # payout del broker
    streak_tolerance: Optional[int] = None  # si None, se deriva de n y wr

    def size(self, wr: float, n: int) -> Sizing:
        """Calcula sizing para la serie filtrada (wr, n)."""
        f = massaniello_fraction(wr, n, self.payout)
        streak = self.streak_tolerance or expected_max_streak(n, wr)
        # DD proyectado si se alcanza la racha adversa maxima:
        # cada perdida quita f del bankroll (binaria: pierdes el stake).
        projected_dd = min(1.0, f * streak)
        if projected_dd > self.dd_limit:
            return Sizing(
                allowed=False, lot_fraction=0.0, lot_size=0.0,
                projected_dd=projected_dd,
                reason=f"DD proyectado {projected_dd:.1%} > limite {self.dd_limit:.1%}",
                meta={"f": f, "streak": streak},
            )
        lot = self.bankroll * f
        return Sizing(
            allowed=True, lot_fraction=f, lot_size=round(lot, 2),
            projected_dd=projected_dd,
            reason=f"Massaniello f={f:.4f} streak={streak} DD={projected_dd:.1%}",
            meta={"f": f, "streak": streak},
        )
