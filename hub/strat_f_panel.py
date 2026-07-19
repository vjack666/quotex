"""Panel STRAT-F del HUB (estado + registro).

Reemplaza la VISTA del dashboard: el panel que el usuario ve ahora es
STRAT-F (aceptadas vs rechazadas con razón). No toca la lógica de
trading (Masaniello vive en consolidation_bot.py y sigue alimentando el
hub legacy internamente; este módulo es solo la capa visible nueva).

Uso:
    panel = StratFPanel()
    panel.record_strat_f(accepted=[...], rejected=[...], total_assets=14)
    state = panel.get_state()   # -> StratFHubState
"""

from __future__ import annotations

import logging
import time

from .strat_f_state import StratFHubState, StratFMaturing, StratFReject, StratFRow

log = logging.getLogger("hub.strat_f_panel")


class StratFPanel:
    """Capa visible del HUB centrada en STRAT-F."""

    def __init__(self) -> None:
        self.state = StratFHubState()
        self.cycle = 0

    def record_strat_f(
        self,
        *,
        accepted: list[StratFRow] | None = None,
        rejected: list[StratFReject] | None = None,
        maturing: list[StratFMaturing] | None = None,
        total_assets: int = 0,
        cycle: int = 0,
        timestamp: float | None = None,
    ) -> StratFHubState:
        """Registra el resultado de un ciclo STRAT-F."""
        self.cycle += 1
        now = timestamp if timestamp is not None else time.time()
        self.state = StratFHubState(
            accepted=list(accepted or []),
            rejected=list(rejected or []),
            maturing=list(maturing or []),
            total_assets=int(total_assets),
            filtered_count=len(accepted or []),
            cycle=int(cycle) or self.cycle,
            timestamp=float(now),
        )
        log.info(
            "STRAT-F | ciclo=%d aceptadas=%d rechazadas=%d madurando=%d",
            self.state.cycle,
            len(self.state.accepted),
            len(self.state.rejected),
            len(self.state.maturing),
        )
        return self.state

    def get_state(self) -> StratFHubState:
        """Devuelve el estado STRAT-F actual (lo usa server.py / main.py)."""
        return self.state
