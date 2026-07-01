"""Motor de decisión SMC con ley de dictadura HTF (H4)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

from models import Candle
from smc_analysis import (
    Bias,
    StructureEventType,
    Zone,
    detect_structure,
)


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


@dataclass
class Decision:
    signal: Signal
    h4_bias: Bias
    m15_bias: Bias
    m1_last_event: Optional[StructureEventType]
    reason: str
    best_zone: Optional[Zone] = None


class SMCDecisionEngine:
    def __init__(
        self,
        h4_candles: Sequence[Candle],
        m15_candles: Sequence[Candle],
        m1_candles: Sequence[Candle],
        h4_strength: int = 3,
        m15_strength: int = 3,
        m1_strength: int = 2,
    ) -> None:
        self.h4_result = detect_structure(h4_candles, swing_strength=h4_strength)
        self.m15_result = detect_structure(m15_candles, swing_strength=m15_strength)
        self.m1_result = detect_structure(m1_candles, swing_strength=m1_strength)

    def decide(self) -> Decision:
        h4_bias = self.h4_result.bias
        m15_bias = self.m15_result.bias

        if h4_bias == Bias.NEUTRAL:
            return Decision(
                signal=Signal.WAIT,
                h4_bias=h4_bias,
                m15_bias=m15_bias,
                m1_last_event=self._last_m1_event_type(),
                reason="ESPERANDO ALINEACIÓN CON H4 | H4 sin tendencia clara",
            )

        if m15_bias != h4_bias:
            conflict_note = self._m15_conflict_note(h4_bias, m15_bias)
            return Decision(
                signal=Signal.WAIT,
                h4_bias=h4_bias,
                m15_bias=m15_bias,
                m1_last_event=self._last_m1_event_type(),
                reason=f"ESPERANDO ALINEACIÓN CON H4 | {conflict_note}",
            )

        best_zone = self._best_zone(h4_bias)
        m1_confirms, m1_note = self._m1_confirms(h4_bias)

        if not best_zone:
            return Decision(
                signal=Signal.WAIT,
                h4_bias=h4_bias,
                m15_bias=m15_bias,
                m1_last_event=self._last_m1_event_type(),
                reason=(
                    f"H4={h4_bias.value} ✓  M15={m15_bias.value} ✓  "
                    f"| Sin zona {'oferta' if h4_bias == Bias.BEARISH else 'demanda'} "
                    f"con FVG disponible | {m1_note}"
                ),
            )

        if not m1_confirms:
            return Decision(
                signal=Signal.WAIT,
                h4_bias=h4_bias,
                m15_bias=m15_bias,
                m1_last_event=self._last_m1_event_type(),
                reason=(
                    f"H4={h4_bias.value} ✓  M15={m15_bias.value} ✓  "
                    f"| Zona localizada [{best_zone.bottom:.5f}–{best_zone.top:.5f}] "
                    f"| Esperando gatillo M1: {m1_note}"
                ),
                best_zone=best_zone,
            )

        signal = Signal.SELL if h4_bias == Bias.BEARISH else Signal.BUY
        zone_type = "OFERTA" if h4_bias == Bias.BEARISH else "DEMANDA"

        return Decision(
            signal=signal,
            h4_bias=h4_bias,
            m15_bias=m15_bias,
            m1_last_event=self._last_m1_event_type(),
            reason=(
                f"H4={h4_bias.value} ✓  M15={m15_bias.value} ✓  "
                f"| ZONA {zone_type} [{best_zone.bottom:.5f}–{best_zone.top:.5f}] FVG=✓ "
                f"| {m1_note}"
            ),
            best_zone=best_zone,
        )

    def _last_m1_event_type(self) -> Optional[StructureEventType]:
        if self.m1_result.events:
            return self.m1_result.events[-1].event_type
        return None

    def _best_zone(self, h4_bias: Bias) -> Optional[Zone]:
        candidates = [
            z for z in self.m15_result.zones
            if (h4_bias == Bias.BEARISH and z.is_supply)
            or (h4_bias == Bias.BULLISH and not z.is_supply)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda z: z.score)

    def _m1_confirms(self, h4_bias: Bias) -> tuple[bool, str]:
        last_event = self.m1_result.events[-1] if self.m1_result.events else None

        if last_event is None:
            return False, "M1 sin estructura suficiente"

        if h4_bias == Bias.BEARISH:
            if last_event.event_type == StructureEventType.BOS_DOWN:
                return True, f"M1 BOS ↓ @ {last_event.broken_level:.5f}  → VENTA confirmada"
            if last_event.event_type == StructureEventType.CHOCH_UP:
                return False, "CHoCH ↑ M1 = RETROCESO HACIA ZONA DE VENTA (trampa alcista)"
            return False, f"M1 {last_event.event_type.value} | esperando BOS ↓"

        if last_event.event_type == StructureEventType.BOS_UP:
            return True, f"M1 BOS ↑ @ {last_event.broken_level:.5f}  → COMPRA confirmada"
        if last_event.event_type == StructureEventType.CHOCH_DOWN:
            return False, "CHoCH ↓ M1 = RETROCESO HACIA ZONA DE COMPRA (trampa bajista)"
        return False, f"M1 {last_event.event_type.value} | esperando BOS ↑"

    @staticmethod
    def _m15_conflict_note(h4_bias: Bias, m15_bias: Bias) -> str:
        if h4_bias == Bias.BEARISH and m15_bias == Bias.BULLISH:
            return (
                "H4 BAJISTA pero M15 alcista — "
                "CHoCH ↑ M15 = RETROCESO HACIA ZONA DE VENTA"
            )
        if h4_bias == Bias.BULLISH and m15_bias == Bias.BEARISH:
            return (
                "H4 ALCISTA pero M15 bajista — "
                "CHoCH ↓ M15 = RETROCESO HACIA ZONA DE COMPRA"
            )
        return f"H4={h4_bias.value} vs M15={m15_bias.value} — marcos en conflicto"