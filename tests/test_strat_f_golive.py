"""Tests de go-live STRAT-F: GAP G1 (panel en vivo) + GAP G2 (STRAT_F_ONLY).

Verifican el cableado sin red:
- G1: el scanner vuelca el batch STRAT-F al panel del bot (que el server expone).
- G2: modo STRAT_F_ONLY aísla la ejecución a solo STRAT-F.
- Integración: scan_all con batch aceptado + STRAT_F_ONLY opera STRAT-F vía enter_trade.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hub.strat_f_panel import StratFPanel  # noqa: E402
from hub.strat_f_state import StratFReject, StratFRow  # noqa: E402
from models import SignalMode  # noqa: E402


# ── Helpers ────────────────────────────────────────────────────────────────
def _make_scanner_with_batch(accepted, rejected):
    """Armado minimo de AssetScanner solo para ejercitar _flush_strat_f_panel."""
    import scanner as scanner_mod

    bot = types.SimpleNamespace(strat_f_panel=None)
    executor = types.SimpleNamespace()
    sc = scanner_mod.AssetScanner(bot, executor)
    # _strat_f_batch es [aceptadas, rechazadas] (misma forma que lo llena scan_all)
    sc._strat_f_batch = [accepted, rejected]
    return sc


def _fake_candidate(origin: str):
    c = types.SimpleNamespace()
    c._strategy_origin = origin
    c.score = 70.0
    c.asset = origin
    c.direction = "call"
    c.payout = 85
    c.zone = types.SimpleNamespace(ceiling=1.1000, floor=1.0980, age_minutes=5,
                                    range_pct=0.002, bars_inside=20)
    c.score_breakdown = {"trend": 10.0, "payout": 15.0}
    c._ob_info = "sin datos"
    c._ma_info = "sin datos"
    c.candles_1m = []
    c.last_price = 1.0990
    c.mode = SignalMode.REBOUND
    c.candles = []
    return c


# ── G1: el scanner llena el panel del bot ──────────────────────────────────
def test_flush_fills_bot_panel():
    accepted = [{"asset": "X_otc", "direction": "call", "strength": 70,
                 "payout": 92, "ctx": "range", "event": "fractal_down"}]
    rejected = [{"asset": "Y_otc", "payout": 80, "skip_reason": "M1 no rebota"}]
    sc = _make_scanner_with_batch(accepted, rejected)
    sc._flush_strat_f_panel()
    state = sc.bot.strat_f_panel.get_state()
    assert isinstance(state.accepted[0], StratFRow)
    assert state.accepted[0].asset == "X_otc"
    assert state.accepted[0].strength == 70
    assert isinstance(state.rejected[0], StratFReject)
    assert state.rejected[0].asset == "Y_otc"
    assert state.total_assets == 2


def test_flush_no_batch_is_noop():
    sc = _make_scanner_with_batch([], [])
    sc._strat_f_batch = None
    # No debe lanzar; el panel del bot queda sin tocar (o se crea vacío).
    sc._flush_strat_f_panel()
    assert sc.bot.strat_f_panel is None or isinstance(sc.bot.strat_f_panel, StratFPanel)


# ── G2: filtro STRAT_F_ONLY ─────────────────────────────────────────────────
def test_strat_f_only_filters_candidates():
    from config import STRAT_F_ONLY as _cfg_val  # noqa: F401
    cands = [_fake_candidate("STRAT-A"), _fake_candidate("STRAT-F"),
             _fake_candidate("STRAT-MOMENTUM")]
    filtered = [c for c in cands
                if getattr(c, "_strategy_origin", "STRAT-A") == "STRAT-F"]
    assert len(filtered) == 1
    assert getattr(filtered[0], "_strategy_origin") == "STRAT-F"


def test_scan_all_respects_strat_f_only(monkeypatch):
    """scan_all con STRAT_F_ONLY=True solo opera STRAT-F (no STRAT-A)."""
    import config as cfg
    import scanner as scanner_mod
    import collections
    import asyncio
    from consolidation_bot import ConsolidationBot

    monkeypatch.setattr(cfg, "STRAT_F_ONLY", True)

    # Bot real (sin conectar) para tener todos los atributos legítimos.
    client = types.SimpleNamespace()
    bot = ConsolidationBot(client=client, dry_run=True, account_type="PRACTICE")
    executor = types.SimpleNamespace()
    executor.enter_trade = None
    executor.refresh_balance_and_risk = lambda: asyncio.sleep(0)
    executor._update_dynamic_threshold = lambda: 62
    executor._record_scan_acceptances = lambda n: None
    async def _fake_process_pending_martin(cands):
        return (cands, False)
    executor._process_pending_martin = _fake_process_pending_martin
    executor._strategy_snapshot = lambda: {"mode": "STRAT_F_ONLY"}
    sc = scanner_mod.AssetScanner(bot, executor)

    # Batch con 1 aceptada STRAT-F para alimentar el panel.
    sc._strat_f_batch = [
        [{"asset": "Z_otc", "direction": "put", "strength": 75,
          "payout": 90, "ctx": "range", "event": "fractal_up"}],
        [],
    ]
    # Candidatos: STRAT-A de score alto + STRAT-F de score 70.
    fa = _fake_candidate("STRAT-A"); fa.score = 85.0; fa.asset = "A"
    ff = _fake_candidate("STRAT-F"); ff.score = 70.0; ff.asset = "F"
    candidates = [fa, ff]

    # Monkeypatch de los métodos pesados de scan_all que no necesitamos.
    async def _fake_prepare():
        return [("A", 85), ("F", 90)]
    monkeypatch.setattr(sc, "_scan_phase_prepare", _fake_prepare)
    async def _fake_prefetch(assets):
        return types.SimpleNamespace()
    monkeypatch.setattr(sc, "_scan_phase_prefetch", _fake_prefetch)
    async def _fake_evaluate(cycle):
        return {"candidates": candidates,
                "cycle_ob_summary": {},
                "cycle_ma_summary": {},
                "candles_1m_collected": {},
                "last_prices_collected": {}}
    monkeypatch.setattr(sc, "_scan_phase_evaluate_assets", _fake_evaluate)
    # Contador de enter_trade.
    calls = []
    async def _fake_enter(asset, direction, amount, zone, reason, stage,
                          journal_cid=None, signal_ts=None,
                          strategy_origin="STRAT-A", duration_sec=0, payout=0,
                          score_original=0):
        calls.append((asset, strategy_origin))
        return True
    monkeypatch.setattr(sc.executor, "enter_trade", _fake_enter)

    asyncio.run(sc.scan_all())

    # Debió operar SOLO la STRAT-F (la STRAT-A quedó fuera por el filtro).
    assert len(calls) == 1
    assert calls[0][0] == "F"
    assert calls[0][1] == "STRAT-F"

    # Y el panel del bot se actualizó con la aceptada.
    state = bot.strat_f_panel.get_state()
    assert len(state.accepted) == 1
    assert state.accepted[0].asset == "Z_otc"
