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

from .strat_f_state import StratFHubState, StratFReject, StratFRow

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
            total_assets=int(total_assets),
            filtered_count=len(accepted),
            cycle=int(cycle) or self.scan_count,
            timestamp=float(now),
        )
        self.scan_event.set()
        log.info(
            "STRAT-F | ciclo=%d aceptadas=%d rechazadas=%d",
            self.state.cycle,
            len(self.state.accepted),
            len(self.state.rejected),
        )
        return self.state

    # ── Compatibilidad con server.py ─────────────────────────

    def get_state(self) -> StratFHubState:
        """Devuelve el estado actual del HUB (lo usa server.py)."""
        return self.state

    @property
    def last_state(self) -> StratFHubState:
        return self.state
