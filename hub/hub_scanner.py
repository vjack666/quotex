"""Lógica de estado del HUB STRAT-F.

Reemplaza hub_scanner.py viejo (orientado a STRAT-A / Masaniello).
Ahora el HUB solo sabe de STRAT-F: aceptadas vs rechazadas con razón.

Conserva el nombre de clase `HubScanner` y `get_state()` para no romper
server.py (que instancia `HubScanner()` y lee `get_state()`).
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Sequence

from .strat_f_state import StratFHubState, StratFMaturing, StratFReject, StratFRow

log = logging.getLogger("hub_scanner")


class HubScanner:
    """Gestor de ciclos de escaneo y estado visible del HUB STRAT-F."""

    def __init__(self) -> None:
        self.state = StratFHubState()
        self.scan_count = 0
        # Evento que se activa cuando se registra un ciclo (para re-render).
        self.scan_event: asyncio.Event = asyncio.Event()

    # ── API de registro STRAT-F ──────────────────────────────

    def record_strat_f(
        self,
        *,
        accepted: Sequence[StratFRow] = (),
        rejected: Sequence[StratFReject] = (),
        maturing: Sequence[StratFMaturing] = (),
        total_assets: int = 0,
        cycle: int = 0,
        timestamp: float | None = None,
    ) -> StratFHubState:
        """Registra el resultado de un ciclo STRAT-F.

        El bot (scanner.py) o el diag (via parser) llaman esto con las
        señales aceptadas y los rechazos ya clasificados.
        """
        self.scan_count += 1
        now = timestamp or time.time()
        self.state = StratFHubState(
            accepted=list(accepted),
            rejected=list(rejected),
            maturing=list(maturing),
            total_assets=int(total_assets),
            filtered_count=len(accepted),
            cycle=int(cycle) or self.scan_count,
            timestamp=float(now),
        )
        self.scan_event.set()
        log.info(
            "STRAT-F | ciclo=%d aceptadas=%d rechazadas=%d madurando=%d",
            self.state.cycle,
            len(self.state.accepted),
            len(self.state.rejected),
            len(self.state.maturing),
        )
        return self.state

    # ── Compatibilidad con server.py ─────────────────────────

    def get_state(self) -> StratFHubState:
        """Devuelve el estado actual del HUB (lo usa server.py)."""
        return self.state

    def set_state(self, state: StratFHubState) -> None:
        """Replace state without bumping scan_count (used to mirror bot panel)."""
        self.state = state
        self.scan_event.set()

    @property
    def last_state(self) -> StratFHubState:
        return self.state

    # ── Stubs de compatibilidad (API vieja del HUB) ───────────────
    # El HUB rediseñado se alimenta en vivo desde el bot vía
    # server._enrich_with_bot (lee bot.trades, Massaniello, balance), por lo que
    # estos eventos ya no actualizan estado propio. Se mantienen como NO-OP para
    # no romper el executor/bot que todavía los llaman. Si se quiere telemetría
    # fina, redirigir aquí al StratFPanel o al recorder.
    def record_entry(self, *, strategy: str = "", asset: str = "", direction: str = "",
                     duration_sec: int = 0, entry_price: float | None = None) -> None:
        log.debug("[HUB] record_entry stub: %s %s %s @%s", strategy, asset, direction, entry_price)

    def update_active_trade_timer(self, secs_left: float, price: float) -> None:
        log.debug("[HUB] update_active_trade_timer stub: %.1fs @%.5f", secs_left, price)

    def close_active_trade(self) -> None:
        log.debug("[HUB] close_active_trade stub")

    def record_trade_result(self, *, asset: str = "", outcome: str = "", profit: float = 0.0) -> None:
        log.debug("[HUB] record_trade_result stub: %s %s %.2f", asset, outcome, profit)

    def update_htf_status(self, *, asset: str = "", payout: int = 0, candles: int = 0,
                          library_size: int = 0, cache_age_sec: float = 0.0,
                          cache_ttl_sec: float = 0.0, refreshed_at_ts: float = 0.0) -> None:
        log.debug("[HUB] update_htf_status stub: %s lib=%d", asset, library_size)

    def record_scan_cycle(self, *, total_assets: int = 0, strat_a_candidates: Any = None,
                          balance: float | None = None, cycle_id: int = 0, cycle_ops: int = 0,
                          cycle_wins: int = 0, cycle_losses: int = 0, **kwargs: Any) -> None:
        log.debug("[HUB] record_scan_cycle stub: cycle=%d assets=%d", cycle_id, total_assets)
