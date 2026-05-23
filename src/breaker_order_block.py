from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import mean
from typing import Dict, List, Optional, Tuple

from models import Candle


class BoBPhase(str, Enum):
    WAITING = "WAITING"
    SETUP = "SETUP"
    RETEST = "RETEST"
    CONFIRMED = "CONFIRMED"


@dataclass
class BoBSetup:
    direction: str  # "buy" | "sell"
    zone_low: float
    zone_high: float
    breakout_close: float
    breakout_ts: int
    breakout_index: int
    base_range_pct: float
    displacement_ratio: float


@dataclass
class BoBState:
    symbol: str
    timeframe: str
    phase: BoBPhase = BoBPhase.WAITING
    direction: str = ""
    zone_low: float = 0.0
    zone_high: float = 0.0
    breakout_ts: int = 0
    breakout_index: int = -1
    retest_ts: int = 0
    confirmed_ts: int = 0
    last_reason: str = ""


@dataclass
class BoBResult:
    symbol: str
    timeframe: str
    state: BoBPhase
    direction: str = ""
    confidence: float = 0.0
    signal: Optional[str] = None
    transition: bool = False
    message: str = ""
    checklist: Optional[Dict[str, Optional[bool]]] = None


class BreakerOrderBlockDetector:
    """Detector BoB por fases: setup -> retest -> confirmation.

    Este detector NO envía órdenes. Solo evalúa estructura y emite estado/señal.
    """

    def __init__(
        self,
        *,
        base_lookback: int = 12,
        max_base_range_pct: float = 0.0025,
        displacement_body_mult: float = 1.40,
        retest_tolerance_pct: float = 0.0006,
        confirmation_body_mult: float = 1.15,
        setup_ttl_candles: int = 20,
    ) -> None:
        self.base_lookback = max(8, int(base_lookback))
        self.max_base_range_pct = max(0.0001, float(max_base_range_pct))
        self.displacement_body_mult = max(1.0, float(displacement_body_mult))
        self.retest_tolerance_pct = max(0.0, float(retest_tolerance_pct))
        self.confirmation_body_mult = max(1.0, float(confirmation_body_mult))
        self.setup_ttl_candles = max(4, int(setup_ttl_candles))
        self._states: Dict[Tuple[str, str], BoBState] = {}

    def evaluate(self, *, symbol: str, timeframe: str, candles: List[Candle]) -> BoBResult:
        key = (symbol.upper(), timeframe)
        state = self._states.get(key)
        if state is None:
            state = BoBState(symbol=symbol.upper(), timeframe=timeframe)
            self._states[key] = state

        if len(candles) < self.base_lookback + 3:
            return BoBResult(
                symbol=symbol.upper(),
                timeframe=timeframe,
                state=BoBPhase.WAITING,
                checklist=self._phase_checklist(BoBPhase.WAITING),
            )

        setup = self._detect_setup(candles)

        if state.phase == BoBPhase.WAITING:
            if setup is None:
                return BoBResult(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    state=BoBPhase.WAITING,
                    checklist=self._phase_checklist(BoBPhase.WAITING),
                )
            self._apply_setup(state, setup)
            return BoBResult(
                symbol=symbol.upper(),
                timeframe=timeframe,
                state=BoBPhase.SETUP,
                direction=state.direction,
                confidence=self._setup_confidence(setup.displacement_ratio),
                transition=True,
                message="BOB SETUP DETECTADO: estructura valida formada",
                checklist={
                    "consolidation": True,
                    "breakout": True,
                    "retest": False,
                    "momentum": False,
                },
            )

        if state.phase == BoBPhase.SETUP:
            if self._is_setup_expired(state, candles):
                self._reset_state(state, reason="setup_expirado")
                return BoBResult(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    state=BoBPhase.WAITING,
                    checklist=self._phase_checklist(BoBPhase.WAITING),
                )

            if self._touches_retest_zone(state, candles[-1]):
                state.phase = BoBPhase.RETEST
                state.retest_ts = int(candles[-1].ts)
                state.last_reason = "retest_tocado"
                return BoBResult(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    state=BoBPhase.RETEST,
                    direction=state.direction,
                    confidence=0.60,
                    transition=True,
                    message="BOB EN FASE RETEST: esperando confirmacion",
                    checklist={
                        "consolidation": True,
                        "breakout": True,
                        "retest": True,
                        "momentum": False,
                    },
                )

            return BoBResult(
                symbol=symbol.upper(),
                timeframe=timeframe,
                state=BoBPhase.SETUP,
                direction=state.direction,
                checklist=self._phase_checklist(BoBPhase.SETUP),
            )

        if state.phase == BoBPhase.RETEST:
            if self._is_setup_expired(state, candles):
                self._reset_state(state, reason="retest_expirado")
                return BoBResult(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    state=BoBPhase.WAITING,
                    checklist=self._phase_checklist(BoBPhase.WAITING),
                )

            if self._is_confirmation_triggered(state, candles):
                state.phase = BoBPhase.CONFIRMED
                state.confirmed_ts = int(candles[-2].ts)
                state.last_reason = "confirmado"
                signal = "BUY" if state.direction == "buy" else "SELL"
                return BoBResult(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    state=BoBPhase.CONFIRMED,
                    direction=state.direction,
                    confidence=0.75,
                    signal=signal,
                    transition=True,
                    message="BOB CONFIRMADO -> SENAL GENERADA",
                    checklist={
                        "consolidation": True,
                        "breakout": True,
                        "retest": True,
                        "momentum": True,
                    },
                )

            return BoBResult(
                symbol=symbol.upper(),
                timeframe=timeframe,
                state=BoBPhase.RETEST,
                direction=state.direction,
                checklist=self._phase_checklist(BoBPhase.RETEST),
            )

        # CONFIRMED: mantener una iteracion para visibilidad y luego volver a WAITING.
        self._reset_state(state, reason="confirmed_consumed")
        return BoBResult(
            symbol=symbol.upper(),
            timeframe=timeframe,
            state=BoBPhase.WAITING,
            checklist=self._phase_checklist(BoBPhase.WAITING),
        )

    @staticmethod
    def _phase_checklist(phase: BoBPhase) -> Dict[str, Optional[bool]]:
        if phase == BoBPhase.SETUP:
            return {
                "consolidation": True,
                "breakout": True,
                "retest": False,
                "momentum": False,
            }
        if phase == BoBPhase.RETEST:
            return {
                "consolidation": True,
                "breakout": True,
                "retest": True,
                "momentum": False,
            }
        if phase == BoBPhase.CONFIRMED:
            return {
                "consolidation": True,
                "breakout": True,
                "retest": True,
                "momentum": True,
            }
        return {
            "consolidation": False,
            "breakout": False,
            "retest": False,
            "momentum": False,
        }

    def _detect_setup(self, candles: List[Candle]) -> Optional[BoBSetup]:
        breakout = candles[-2]  # ultima vela cerrada
        base = candles[-(self.base_lookback + 2):-2]
        if len(base) < self.base_lookback:
            return None

        zone_low = min(float(c.low) for c in base)
        zone_high = max(float(c.high) for c in base)
        zone_mid = (zone_low + zone_high) / 2.0
        if zone_mid <= 0:
            return None

        base_range_pct = (zone_high - zone_low) / zone_mid
        if base_range_pct > self.max_base_range_pct:
            return None

        breakout_close = float(breakout.close)
        breakout_open = float(breakout.open)
        breakout_body = abs(breakout_close - breakout_open)
        body_hist = [abs(float(c.close) - float(c.open)) for c in base[-8:]]
        avg_body = mean(body_hist) if body_hist else 0.0
        if avg_body <= 1e-9:
            return None

        displacement_ratio = breakout_body / avg_body
        if displacement_ratio < self.displacement_body_mult:
            return None

        direction = ""
        if breakout_close > zone_high:
            direction = "buy"
        elif breakout_close < zone_low:
            direction = "sell"
        else:
            return None

        return BoBSetup(
            direction=direction,
            zone_low=zone_low,
            zone_high=zone_high,
            breakout_close=breakout_close,
            breakout_ts=int(breakout.ts),
            breakout_index=len(candles) - 2,
            base_range_pct=base_range_pct,
            displacement_ratio=displacement_ratio,
        )

    def _apply_setup(self, state: BoBState, setup: BoBSetup) -> None:
        state.phase = BoBPhase.SETUP
        state.direction = setup.direction
        state.zone_low = setup.zone_low
        state.zone_high = setup.zone_high
        state.breakout_ts = setup.breakout_ts
        state.breakout_index = setup.breakout_index
        state.retest_ts = 0
        state.confirmed_ts = 0
        state.last_reason = "setup_detected"

    def _touches_retest_zone(self, state: BoBState, candle: Candle) -> bool:
        tol = max(float(candle.close) * self.retest_tolerance_pct, 1e-9)
        high = float(candle.high)
        low = float(candle.low)

        zone_low = state.zone_low - tol
        zone_high = state.zone_high + tol

        if state.direction == "buy":
            return low <= zone_high and high >= zone_low
        if state.direction == "sell":
            return high >= zone_low and low <= zone_high
        return False

    def _is_confirmation_triggered(self, state: BoBState, candles: List[Candle]) -> bool:
        if len(candles) < 4:
            return False

        c = candles[-2]  # ultima vela cerrada
        prev = candles[-3]
        recent = candles[-10:-2]
        hist_body = [abs(float(x.close) - float(x.open)) for x in recent]
        avg_body = mean(hist_body) if hist_body else 0.0
        if avg_body <= 1e-9:
            return False

        body = abs(float(c.close) - float(c.open))
        up_wick = float(c.high) - max(float(c.open), float(c.close))
        down_wick = min(float(c.open), float(c.close)) - float(c.low)

        if state.direction == "buy":
            bullish_close = float(c.close) > float(c.open)
            wick_reject = bullish_close and down_wick >= body * 1.2
            impulse = bullish_close and body >= avg_body * self.confirmation_body_mult and float(c.close) > state.zone_high
            momentum = float(c.close) > float(prev.close)
            return (wick_reject or impulse) and momentum

        if state.direction == "sell":
            bearish_close = float(c.close) < float(c.open)
            wick_reject = bearish_close and up_wick >= body * 1.2
            impulse = bearish_close and body >= avg_body * self.confirmation_body_mult and float(c.close) < state.zone_low
            momentum = float(c.close) < float(prev.close)
            return (wick_reject or impulse) and momentum

        return False

    def _is_setup_expired(self, state: BoBState, candles: List[Candle]) -> bool:
        if state.breakout_index < 0:
            return True
        candles_since_break = (len(candles) - 2) - state.breakout_index
        return candles_since_break > self.setup_ttl_candles

    @staticmethod
    def _reset_state(state: BoBState, *, reason: str) -> None:
        state.phase = BoBPhase.WAITING
        state.direction = ""
        state.zone_low = 0.0
        state.zone_high = 0.0
        state.breakout_ts = 0
        state.breakout_index = -1
        state.retest_ts = 0
        state.confirmed_ts = 0
        state.last_reason = reason

    @staticmethod
    def _setup_confidence(displacement_ratio: float) -> float:
        # Normaliza impulso del breakout a rango [0, 1] para el router.
        return max(0.0, min(1.0, displacement_ratio / 2.5))


__all__ = [
    "BoBPhase",
    "BoBResult",
    "BoBState",
    "BreakerOrderBlockDetector",
]
