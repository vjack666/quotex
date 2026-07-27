"""EpisodeStateMachine — estados y transiciones v1 del Observador (R2.x).

Reglas EXACTAS de design.md D2/D3. Sin relojes propios: la máquina solo
conoce el ts de las velas que recibe (jamás relojes del sistema). Todos los
triggers son Metric (PTM v3) con formula_version 'quiet_exit_v1' o
'transitions_v1'.
"""
from __future__ import annotations

from collections import deque

from observador.metric import Metric
from observador.pressure import continuity_fraction, median_body

# --- Constantes versionadas (D2/D3, no números mágicos sueltos) ---
QUIET_EXIT_VERSION = "quiet_exit_v1"
TRANSITIONS_VERSION = "transitions_v1"

ROLLING_WINDOW = 30          # velas para la mediana de cuerpos (D2)
QUIET_BODY_FACTOR = 2.0      # cuerpo > 2.0 x mediana (D2)
QUIET_MIN_CONSECUTIVE = 3    # >=3 velas consecutivas misma dirección (D2)
PRESSURE_CONTINUITY = 0.7    # continuidad >= 0.7 en 5 velas (D3)
BRAKE_PEAK_FRACTION = 0.30   # avance < 30% del pico (D3)
BRAKE_MIN_CANDLES = 2        # durante >=2 velas consecutivas (D3)
TRANSITION_CANDLES = 5       # RESOLUTION exactamente 5 velas después (D3)
REBOUND_BODY_FACTOR = 2.0    # avance contrario >= 2 x cuerpo mediano (D3)
STATE_TIMEOUT = 60           # 60 velas en un estado (salvo QUIET) (R2.4)

QUIET = "QUIET"
EXPANSION = "EXPANSION"
PRESSURE = "PRESSURE"
BRAKE = "BRAKE"
TRANSITION = "TRANSITION"
RESOLUTION = "RESOLUTION"

REBOUND = "REBOUND"
CONTINUATION = "CONTINUATION"
CHAOS = "CHAOS"
NEUTRALIZATION = "NEUTRALIZATION"


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


class EpisodeStateMachine:
    """Máquina de estados de episodios para un asset."""

    def __init__(self, asset: str) -> None:
        self.asset = asset
        self._state = QUIET
        self._direction: int | None = None
        self._resolution_type: str | None = None
        self._window: deque[dict] = deque(maxlen=ROLLING_WINDOW)
        self._prev_close: float | None = None
        # racha de velas consecutivas en la misma dirección de cuerpo
        self._streak_dir = 0
        self._streak_len = 0
        # episodio
        self._peak_advance = 0.0
        self._brake_count = 0
        # TRANSITION
        self._transition_count = 0
        self._transition_entry_close = 0.0
        # timeout
        self._candles_in_state = 0

    # --- propiedades públicas ---
    @property
    def state(self) -> str:
        return self._state

    @property
    def direction(self) -> int | None:
        return self._direction

    @property
    def resolution_type(self) -> str | None:
        return self._resolution_type

    # --- núcleo ---
    def on_candle(self, candle: dict) -> list[dict]:
        events: list[dict] = []
        prev_close = self._prev_close
        body = candle["close"] - candle["open"]

        # racha direccional (por cuerpo de vela)
        sign = 1 if body > 0 else (-1 if body < 0 else 0)
        if sign != 0 and sign == self._streak_dir:
            self._streak_len += 1
        else:
            self._streak_dir = sign
            self._streak_len = 1 if sign != 0 else 0

        self._window.append(candle)
        self._candles_in_state += 1
        med = median_body(list(self._window))

        # avance neto por vela respecto a la dirección del episodio
        advance = 0.0
        if self._direction is not None and prev_close is not None:
            advance = (candle["close"] - prev_close) * self._direction
            if advance > self._peak_advance:
                self._peak_advance = advance

        ts = candle["ts"]

        if self._state == QUIET:
            if (
                med > 0.0
                and abs(body) > QUIET_BODY_FACTOR * med
                and self._streak_len >= QUIET_MIN_CONSECUTIVE
            ):
                self._direction = self._streak_dir
                trig = Metric(
                    abs(body),
                    _clamp01(abs(body) / (QUIET_BODY_FACTOR * med)),
                    1.0,
                    QUIET_EXIT_VERSION,
                )
                events.append(self._go(EXPANSION, ts, trig))
                self._peak_advance = 0.0
        elif self._state == EXPANSION:
            assert self._direction is not None
            cont = continuity_fraction(list(self._window), self._direction)
            if cont >= PRESSURE_CONTINUITY:
                trig = Metric(cont, _clamp01(cont), 1.0, TRANSITIONS_VERSION)
                events.append(self._go(PRESSURE, ts, trig))
        elif self._state == PRESSURE:
            if self._peak_advance > 0.0 and advance < BRAKE_PEAK_FRACTION * self._peak_advance:
                self._brake_count += 1
            else:
                self._brake_count = 0
            if self._brake_count >= BRAKE_MIN_CANDLES:
                ratio = advance / self._peak_advance if self._peak_advance else 0.0
                trig = Metric(ratio, _clamp01(ratio), 1.0, TRANSITIONS_VERSION)
                events.append(self._go(BRAKE, ts, trig))
        elif self._state == BRAKE:
            if body * self._direction < 0:
                trig = Metric(
                    abs(body),
                    _clamp01(abs(body) / (QUIET_BODY_FACTOR * med)) if med else 0.0,
                    1.0,
                    TRANSITIONS_VERSION,
                )
                events.append(self._go(TRANSITION, ts, trig))
                self._transition_count = 0
                self._transition_entry_close = candle["close"]
        elif self._state == TRANSITION:
            self._transition_count += 1
            if self._transition_count >= TRANSITION_CANDLES:
                net = (candle["close"] - self._transition_entry_close) * self._direction
                contrary = -net if net < 0 else 0.0
                if med > 0.0 and contrary >= REBOUND_BODY_FACTOR * med:
                    rtype = REBOUND
                elif net > 0:
                    rtype = CONTINUATION
                else:
                    rtype = CHAOS
                norm = _clamp01(abs(net) / (REBOUND_BODY_FACTOR * med)) if med else 0.0
                trig = Metric(net, norm, 1.0, TRANSITIONS_VERSION)
                events.append(self._resolve(rtype, ts, trig))

        # timeout: 60 velas en un mismo estado (salvo QUIET y ya resuelto)
        if (
            self._state not in (QUIET, RESOLUTION)
            and self._candles_in_state >= STATE_TIMEOUT
        ):
            trig = Metric(float(self._candles_in_state), 1.0, 1.0, TRANSITIONS_VERSION)
            events.append(self._resolve(NEUTRALIZATION, ts, trig))

        self._prev_close = candle["close"]
        return events

    # --- helpers ---
    def _go(self, new_state: str, ts, trigger: Metric) -> dict:
        ev = {"state_from": self._state, "state_to": new_state, "ts": ts, "trigger": trigger}
        self._state = new_state
        self._candles_in_state = 0
        self._brake_count = 0
        return ev

    def _resolve(self, rtype: str, ts, trigger: Metric) -> dict:
        ev = self._go(RESOLUTION, ts, trigger)
        self._resolution_type = rtype
        # episodio cerrado → volver a QUIET para el siguiente
        self._state = QUIET
        self._direction = None
        self._peak_advance = 0.0
        self._transition_count = 0
        self._candles_in_state = 0
        return ev
