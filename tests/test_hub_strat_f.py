"""Tests para el nuevo HUB STRAT-F (modelo + parser + render).

Reemplaza tests/hub orientados a STRAT-A. Cubre R1,R2,R3,R4,R5,R6,R7,R10.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hub.strat_f_state import StratFHubState, StratFReject, StratFRow  # noqa: E402
from hub.parser import HubLogParser  # noqa: E402
from hub.render import render_dashboard  # noqa: E402


def _sample_log() -> list[str]:
    return """
Activos abiertos (payout>=80%): 14
  - AUDNZD_otc (95%) ctx=uptrend event=fractal_down skip=M1 no rechaza la banda (cierra fuera)
  SENAL USDPKR_otc CALL | ctx=range event=fractal_down strength=70 payout=92%
  - USCrude_otc (92%) ctx=downtrend event=fractal_down skip=CALL contra tendencia M15
Resumen (14 activos): senales_filtradas=1
""".splitlines()


# ── T2: modelo ────────────────────────────────────────────────
def test_state_defaults_empty():
    s = StratFHubState()
    assert s.accepted == []
    assert s.rejected == []
    assert s.total == 0
    assert s.accept_rate == 0.0


def test_state_totals_and_rate():
    s = StratFHubState(
        accepted=[StratFRow("X", "call", 70, 92, "range", "fractal_down")],
        rejected=[StratFReject("Y", 80, "M1 no rebota")],
        total_assets=14,
    )
    assert s.total == 2
    assert abs(s.accept_rate - 0.5) < 1e-9


# ── T3: parser desde log del diag ─────────────────────────────
def test_parser_separates_signals_and_skips():
    snap = HubLogParser().parse_lines(_sample_log())
    assert isinstance(snap, StratFHubState)
    assert len(snap.accepted) == 1
    assert len(snap.rejected) == 2
    assert snap.total_assets == 14
    assert snap.filtered_count == 1


def test_parser_signal_fields():
    snap = HubLogParser().parse_lines(_sample_log())
    sig = snap.accepted[0]
    assert sig.asset == "USDPKR_otc"
    assert sig.direction == "call"
    assert sig.strength == 70
    assert sig.payout == 92
    assert sig.ctx == "range"


def test_parser_reject_fields():
    snap = HubLogParser().parse_lines(_sample_log())
    reject = snap.rejected[0]
    assert reject.asset == "AUDNZD_otc"
    assert "M1 no rechaza" in reject.skip_reason


# ── T5: render ───────────────────────────────────────────────
def test_render_contains_sections():
    snap = HubLogParser().parse_lines(_sample_log())
    panel = render_dashboard(snap)
    assert "STRAT-F" in panel
    assert "ACEPTADAS" in panel
    assert "RECHAZADAS" in panel
    assert "USDPKR_otc" in panel     # aceptada
    assert "AUDNZD_otc" in panel     # rechazada
    assert "Principio" in panel
