"""Tests T3 — EpisodeStateMachine: una secuencia sintética por cada transición."""
from observador.metric import Metric
from observador.state_machine import (
    BRAKE,
    CHAOS,
    CONTINUATION,
    EXPANSION,
    EpisodeStateMachine,
    NEUTRALIZATION,
    PRESSURE,
    QUIET,
    QUIET_EXIT_VERSION,
    REBOUND,
    RESOLUTION,
    TRANSITION,
    TRANSITIONS_VERSION,
)


class Driver:
    """Alimenta la máquina con velas sintéticas y acumula eventos."""

    def __init__(self):
        self.sm = EpisodeStateMachine("EURUSD")
        self.ts = 0
        self.events = []
        self.last_close = 1.0

    def candle(self, body):
        o = self.last_close
        c = o + body
        self.ts += 60
        self.last_close = c
        cd = {"ts": self.ts, "open": o, "high": max(o, c), "low": min(o, c), "close": c}
        self.events.extend(self.sm.on_candle(cd))
        return cd

    def quiet(self, n=10):
        # cuerpos alternos ±0.001: mediana 0.001, sin racha >=3
        for i in range(n):
            self.candle(0.001 if i % 2 == 0 else -0.001)

    def to_expansion(self):
        # 3 velas alcistas consecutivas, la última con cuerpo 0.01 > 2*0.001
        self.quiet()
        self.candle(0.001)
        self.candle(0.001)
        self.candle(0.01)
        assert self.sm.state == EXPANSION and self.sm.direction == 1

    def to_pressure(self):
        self.to_expansion()
        self.candle(0.01)  # 4 de las últimas 5 alcistas -> continuidad 0.8
        assert self.sm.state == PRESSURE

    def to_brake(self):
        self.to_pressure()
        # pico de avance 0.01; dos velas con avance 0.001 < 30% * 0.01
        self.candle(0.001)
        self.candle(0.001)
        assert self.sm.state == BRAKE

    def to_transition(self):
        self.to_brake()
        self.candle(-0.001)  # primera vela contraria
        assert self.sm.state == TRANSITION


def _last_event(d):
    return d.events[-1]


def test_quiet_to_expansion_trigger():
    d = Driver()
    d.to_expansion()
    ev = _last_event(d)
    assert ev["state_from"] == QUIET and ev["state_to"] == EXPANSION
    assert isinstance(ev["trigger"], Metric)
    assert ev["trigger"].formula_version == QUIET_EXIT_VERSION
    assert abs(ev["trigger"].raw - 0.01) < 1e-12  # cuerpo de la vela gatillo
    assert ev["ts"] == d.ts


def test_quiet_needs_three_consecutive():
    d = Driver()
    d.quiet()
    d.candle(-0.001)
    d.candle(0.01)  # cuerpo grande pero racha de 1 -> sigue QUIET
    assert d.sm.state == QUIET


def test_expansion_to_pressure():
    d = Driver()
    d.to_pressure()
    ev = _last_event(d)
    assert ev["state_from"] == EXPANSION and ev["state_to"] == PRESSURE
    assert ev["trigger"].formula_version == TRANSITIONS_VERSION
    assert ev["trigger"].raw >= 0.7  # continuidad


def test_pressure_to_brake():
    d = Driver()
    d.to_brake()
    ev = _last_event(d)
    assert ev["state_from"] == PRESSURE and ev["state_to"] == BRAKE
    assert ev["trigger"].formula_version == TRANSITIONS_VERSION
    assert ev["trigger"].raw < 0.30  # ratio avance/pico


def test_brake_to_transition_on_first_contrary_close():
    d = Driver()
    d.to_transition()
    ev = _last_event(d)
    assert ev["state_from"] == BRAKE and ev["state_to"] == TRANSITION
    assert ev["trigger"].formula_version == TRANSITIONS_VERSION


def test_resolution_rebound():
    d = Driver()
    d.to_transition()
    for _ in range(5):
        d.candle(-0.005)  # avance contrario acumulado 0.025 >> 2*mediana
    ev = _last_event(d)
    assert ev["state_from"] == TRANSITION and ev["state_to"] == RESOLUTION
    assert d.sm.resolution_type == REBOUND
    assert d.sm.state == QUIET  # episodio cerrado


def test_resolution_continuation():
    d = Driver()
    d.to_transition()
    for _ in range(5):
        d.candle(0.002)  # retoma la dirección: cierre neto positivo
    assert d.sm.resolution_type == CONTINUATION
    assert d.sm.state == QUIET


def test_resolution_chaos():
    d = Driver()
    d.to_transition()
    # alternancia que termina exactamente en el close de entrada: net = 0
    d.candle(0.001)
    d.candle(-0.001)
    d.candle(0.001)
    d.candle(-0.001)
    d.candle(0.0)
    assert d.sm.resolution_type == CHAOS
    assert d.sm.state == QUIET


def test_timeout_neutralization():
    d = Driver()
    d.to_expansion()
    # alternancia ±0.001: puede llegar a PRESSURE pero nunca a BRAKE
    # (el avance se recupera cada 2 velas) -> timeout de 60 velas en estado
    for i in range(70):
        d.candle(0.001 if i % 2 == 0 else -0.001)
    ev = _last_event(d)
    assert ev["state_to"] == RESOLUTION
    assert d.sm.resolution_type == NEUTRALIZATION
    assert d.sm.state == QUIET
    assert ev["trigger"].raw == 60.0


def test_no_wall_clock_used():
    # la máquina solo conoce ts de velas: los eventos llevan ese ts
    d = Driver()
    d.to_expansion()
    assert all(isinstance(e["ts"], int) for e in d.events)


def test_uses_only_candle_ts_source():
    import inspect
    import observador.state_machine as sm

    src = inspect.getsource(sm)
    assert "time.time" not in src
    assert "datetime.now" not in src and "utcnow" not in src
