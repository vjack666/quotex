"""Parser del panel HUB para STRAT-F.

Lee la salida de ``progress/diag_strat_f_live.py`` (o cualquier log con el
mismo formato) y la convierte en ``StratFHubState`` (aceptadas / rechazadas
con su razón), que el renderer dibuja como panel de "aceptadas vs rechazadas".

Formato de línea que entiende (uno por activo evaluado):

  SENAL <ACTIVO> <CALL|PUT> | ctx=<...> event=<...> strength=<N> payout=<N>%
  - <ACTIVO> (<N>%) ctx=<...> event=<...> skip=<razon>

Y el resumen:

  Resumen (<N> activos): senales_filtradas=<N>
"""

from __future__ import annotations

import re
from typing import List

from .strat_f_state import StratFHubState, StratFReject, StratFRow


_SIGNAL_RE = re.compile(
    r"^\s*SENAL\s+(?P<asset>\S+)\s+(?P<direction>CALL|PUT)\s*\|"
    r".*?\bctx=(?P<ctx>\S+)\s+event=(?P<event>\S+)\s+"
    r"strength=(?P<strength>\d+)\s+payout=(?P<payout>\d+)%"
)

_SKIP_RE = re.compile(
    r"^\s*-\s+(?P<asset>\S+)\s+\((?P<payout>\d+)%\)\s+"
    r"ctx=(?P<ctx>\S+)\s+event=(?P<event>\S+)\s+skip=(?P<reason>.+?)\s*$"
)

_SUMMARY_RE = re.compile(
    r"Resumen\s+\(?(?P<total>\d+)\)?\s*activos?\)?:\s*"
    r"senales_filtradas=(?P<signals>\d+)"
)


class HubLogParser:
    """Parsea lineas de log del diagnóstico STRAT-F al estado del panel."""

    def parse_lines(self, lines: List[str]) -> StratFHubState:
        state = StratFHubState()
        for raw in lines:
            line = raw.strip()
            if not line:
                continue

            m = _SIGNAL_RE.match(line)
            if m:
                state.accepted.append(
                    StratFRow(
                        asset=m.group("asset"),
                        direction=m.group("direction").lower(),
                        strength=int(m.group("strength")),
                        payout=int(m.group("payout")),
                        ctx=m.group("ctx"),
                        event=m.group("event"),
                    )
                )
                continue

            m = _SKIP_RE.match(line)
            if m:
                state.rejected.append(
                    StratFReject(
                        asset=m.group("asset"),
                        payout=int(m.group("payout")),
                        skip_reason=m.group("reason").strip(),
                    )
                )
                # Enriquecer ctx/event si el parser futuro los necesita.
                continue

            m = _SUMMARY_RE.search(line)
            if m:
                state.total_assets = int(m.group("total"))
                state.filtered_count = int(m.group("signals"))

        # Fallback del resumen si no hubo línea de Resumen pero sí datos.
        if state.total_assets == 0 and state.total > 0:
            state.total_assets = state.total
            state.filtered_count = len(state.accepted)

        return state
