"""
diversification_enforcer.py — Rechaza entradas que violan límites de diversificación.

Límites verificados:
  - max_simultaneous_trades: máximo de trades abiertos simultáneamente.
  - min_asset_spread: cantidad mínima de activos distintos entre trades abiertos.
  - max_entries_per_asset: máximo de entradas concurrentes en un mismo activo.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import TradeState

log = logging.getLogger("diversification_enforcer")


class DiversificationEnforcer:
    """Valida que una nueva entrada no viole los límites de diversificación."""

    def __init__(
        self,
        max_simultaneous_trades: int = 3,
        min_asset_spread: int = 2,
        max_entries_per_asset: int = 1,
    ) -> None:
        self.max_simultaneous_trades = max_simultaneous_trades
        self.min_asset_spread = min_asset_spread
        self.max_entries_per_asset = max_entries_per_asset

    def check(
        self,
        open_trades: dict[str, "TradeState"],
        candidate_asset: str,
        *,
        stage: str = "initial",
    ) -> tuple[bool, str]:
        """
        Verifica si se permite una entrada para ``candidate_asset``.

        Parameters
        ----------
        open_trades : dict[str, TradeState]
            Diccionario de trades actualmente abiertos (``bot.trades``).
        candidate_asset : str
            Símbolo del activo que se desea entrar.
        stage : str
            Etapa de la entrada. ``"martin"`` y ``"breakout"`` quedan exentas.

        Returns
        -------
        (ok, reason)
            ``(True, "")`` si la entrada está permitida,
            ``(False, "descripción del límite violado")`` si debe rechazarse.
        """
        # Martingala y breakout quedan exentas (no romper recuperación de ciclo)
        if stage in ("martin", "breakout"):
            return True, ""

        total = len(open_trades)

        # ── 1) Límite global ────────────────────────────────────────────────
        if self.max_simultaneous_trades > 0 and total >= self.max_simultaneous_trades:
            reason = (
                f"max_simultaneous_trades={self.max_simultaneous_trades}: "
                f"{total} trade(s) abierto(s)"
            )
            log.info("⛔ %s: rechazado — %s", candidate_asset, reason)
            return False, reason

        # ── 2) Spread mínimo de activos ─────────────────────────────────────
        # Si los trades abiertos están concentrados en muy pocos activos, no
        # permitimos añadir OTRO trade al MISMO activo — forzamos diversificación.
        if total > 0 and self.min_asset_spread > 1:
            unique_assets = set(open_trades.keys())
            if (
                len(unique_assets) < self.min_asset_spread
                and candidate_asset in open_trades
            ):
                reason = (
                    f"min_asset_spread={self.min_asset_spread}: "
                    f"solo {len(unique_assets)} activo(s) distinto(s) entre "
                    f"{total} trade(s) — {candidate_asset} ya está abierto"
                )
                log.info("⛔ %s: rechazado — %s", candidate_asset, reason)
                return False, reason

        # ── 3) Máximo por activo ────────────────────────────────────────────
        if self.max_entries_per_asset > 0:
            entries_for_asset = sum(
                1 for a in open_trades if a == candidate_asset
            )
            if entries_for_asset >= self.max_entries_per_asset:
                reason = (
                    f"max_entries_per_asset={self.max_entries_per_asset}: "
                    f"{candidate_asset} ya tiene {entries_for_asset} entrada(s)"
                )
                log.info("⛔ %s: rechazado — %s", candidate_asset, reason)
                return False, reason

        return True, ""
