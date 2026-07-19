"""Scanner integration tests for maturing zone watchlist (R5–R7, R14)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import black_box_recorder as bbr
import config as cfg
import scanner as sc
from maturing_watchlist import MaturingWatchlist, is_r3_young_skip, normalize_mode
from models import ConsolidationZone


def _make_cycle(assets):
    candles_15m = [
        SimpleNamespace(ts=i, open=100 + i, high=101 + i, low=99 + i, close=100 + i)
        for i in range(20)
    ]
    # Enough M5 bars for fractal_band_and_age (need >= 5 + wings).
    candles_5m = []
    for i in range(10):
        # fractal_down at idx 5: low is local min
        if i == 5:
            lo, hi = 98.0, 100.0
        else:
            lo, hi = 99.0, 101.0
        candles_5m.append(
            SimpleNamespace(ts=i, open=100.0, high=hi, low=lo, close=100.0)
        )
    candles_1m = [
        SimpleNamespace(ts=i, open=100, high=101, low=99, close=100) for i in range(5)
    ]
    return SimpleNamespace(
        assets=assets,
        candles_5m={a[0]: list(candles_5m) for a in assets},
        candles_1m={a[0]: candles_1m for a in assets},
        candles_15m={a[0]: candles_15m for a in assets},
        scan_number=1,
        blocks_by_symbol={},
        ob_tf_labels={},
        candles_h1={},
    )


def _zone(asset: str = "EURUSD_otc", band: float = 98.0) -> ConsolidationZone:
    return ConsolidationZone(
        asset=asset,
        ceiling=band,
        floor=band,
        bars_inside=10,
        detected_at=0.0,
        range_pct=0.002,
    )


def _eval_young():
    return SimpleNamespace(
        direction=None,
        strength=0.0,
        m15_context="range",
        m5_event="fractal_down",
        skip_reason="zona muy joven (2 < 3 velas M5)",
        has_signal=False,
        zone=None,
        pattern_name="none",
    )


def _eval_valid(direction: str = "CALL", band: float = 98.0):
    return SimpleNamespace(
        direction=direction,
        strength=0.8,
        m15_context="range",
        m5_event="fractal_down",
        skip_reason="",
        has_signal=True,
        zone=_zone(band=band),
        pattern_name="fractal_down",
    )


def _eval_hard_fail():
    return SimpleNamespace(
        direction=None,
        strength=0.0,
        m15_context="range",
        m5_event="fractal_down",
        skip_reason="M1 no rechaza la banda (cierra fuera)",
        has_signal=False,
        zone=None,
        pattern_name="none",
    )


def _stoch(k: float = 50.0) -> dict:
    return {
        "k": k,
        "d": k,
        "estado": "NEUTRO",
        "cruce": None,
        "divergencia": None,
        "contradicts": 0,
    }


def _make_self(*, mode: str = "live"):
    self = MagicMock()
    self.bot.trades = {}
    self.bot.greylist_assets = set()
    self.bot.asset_blacklist_until = {}
    self.bot.failed_assets = {}
    self.bot.stats = {}
    self.bot.zones = {}
    self.bot.last_known_price = {}
    self.bot.order_blocks_by_asset = {}
    self.bot.maturing_watchlist = MaturingWatchlist(
        max_entries=40, max_age_bars=12, ttl_sec=3600
    )
    self.bot.strat_f_panel = None
    self.executor._is_asset_blacklisted.return_value = False
    self.executor._compute_initial_amount.return_value = (10.0, None)
    return self


def _setup_bb(tmp: str) -> bbr.BlackBoxRecorder:
    bbr._recorder = None
    bbr.BLACK_BOX_DB = Path(tmp) / "bb_maturing.db"
    bbr.BLACK_BOX_LOG = Path(tmp) / "bb_maturing.jsonl"
    return bbr.BlackBoxRecorder()


async def _run_scan(self, eval_return, *, mode: str = "live", asset="EURUSD_otc", payout=90):
    tmp = tempfile.mkdtemp()
    rec = _setup_bb(tmp)
    with (
        patch.object(sc, "evaluate_strat_f", return_value=eval_return),
        patch.object(sc, "compute_stoch", return_value=_stoch(50.0)),
        patch.object(sc, "get_black_box", return_value=rec),
        patch.object(cfg, "MATURING_WATCHLIST_MODE", mode),
        patch.object(sc._runtime_config, "MATURING_WATCHLIST_MODE", mode),
        patch.object(sc._runtime_config, "STRAT_A_ONLY", False),
        patch.object(sc, "STRAT_F_ENABLED", True),
        patch.object(sc, "STRAT_MOMENTUM_ENABLED", False),
        patch.object(sc, "STRAT_ORDER_BLOCK_ENABLED", False),
        patch.object(sc, "STRAT_REVERSAL_SWING_ENABLED", False)
        if hasattr(sc, "STRAT_REVERSAL_SWING_ENABLED")
        else patch.object(sc, "STRAT_F_ENABLED", True),
    ):
        # Disable other strategies via config flags when present.
        extra_patches = []
        for name, val in (
            ("STRAT_MOMENTUM_ENABLED", False),
            ("STRAT_ORDER_BLOCK_ENABLED", False),
            ("STRAT_REVERSAL_SWING_ENABLED", False),
            ("STRAT_A_RADAR_ENABLED", False),
        ):
            if hasattr(sc, name):
                extra_patches.append(patch.object(sc, name, val))
        for p in extra_patches:
            p.start()
        try:
            result = await sc.AssetScanner._scan_phase_evaluate_assets(
                self, _make_cycle([(asset, payout)])
            )
        finally:
            for p in extra_patches:
                p.stop()
    return result, rec, self


@pytest.mark.asyncio
async def test_capture_r3_young_when_mode_live():
    self = _make_self(mode="live")
    result, _rec, self = await _run_scan(self, _eval_young(), mode="live")
    wl = self.bot.maturing_watchlist
    assert len(wl.active()) == 1
    entry = wl.active()[0]
    assert entry.asset == "EURUSD_otc"
    assert entry.direction == "CALL"
    assert entry.status == "maturing"
    assert wl.counters["captured"] == 1
    # No live STRAT-F candidate from young skip.
    f_cands = [c for c in result["candidates"] if getattr(c, "_strategy_origin", "") == "STRAT-F"]
    assert f_cands == []


@pytest.mark.asyncio
async def test_mode_off_does_not_capture():
    self = _make_self(mode="off")
    await _run_scan(self, _eval_young(), mode="off")
    assert self.bot.maturing_watchlist.active() == []
    assert self.bot.maturing_watchlist.counters["captured"] == 0


@pytest.mark.asyncio
async def test_non_r3_skip_not_captured():
    self = _make_self(mode="live")
    await _run_scan(self, _eval_hard_fail(), mode="live")
    assert self.bot.maturing_watchlist.active() == []


@pytest.mark.asyncio
async def test_live_promote_creates_candidate_and_clears_watchlist():
    self = _make_self(mode="live")
    # Seed watchlist as if previous scan captured young zone.
    self.bot.maturing_watchlist.upsert_young(
        asset="EURUSD_otc",
        direction="CALL",
        band=98.0,
        m5_event="fractal_down",
        bars_age=2,
        payout=90,
        now=1.0,
    )
    result, _rec, self = await _run_scan(self, _eval_valid(), mode="live")
    f_cands = [c for c in result["candidates"] if getattr(c, "_strategy_origin", "") == "STRAT-F"]
    assert len(f_cands) == 1
    assert getattr(f_cands[0], "_maturing_promoted", False) is True
    assert self.bot.maturing_watchlist.active() == []
    assert self.bot.maturing_watchlist.counters["promoted_live"] == 1


@pytest.mark.asyncio
async def test_shadow_promote_no_candidate():
    self = _make_self(mode="shadow")
    self.bot.maturing_watchlist.upsert_young(
        asset="EURUSD_otc",
        direction="CALL",
        band=98.0,
        m5_event="fractal_down",
        bars_age=2,
        payout=90,
        now=1.0,
    )
    result, _rec, self = await _run_scan(self, _eval_valid(), mode="shadow")
    f_cands = [c for c in result["candidates"] if getattr(c, "_strategy_origin", "") == "STRAT-F"]
    assert f_cands == []
    assert self.bot.maturing_watchlist.active() == []
    assert self.bot.maturing_watchlist.counters["promoted_shadow"] == 1


@pytest.mark.asyncio
async def test_hard_fail_invalidates_maturing_entry():
    self = _make_self(mode="live")
    self.bot.maturing_watchlist.upsert_young(
        asset="EURUSD_otc",
        direction="CALL",
        band=98.0,
        m5_event="fractal_down",
        bars_age=2,
        payout=90,
        now=1.0,
    )
    await _run_scan(self, _eval_hard_fail(), mode="live")
    assert self.bot.maturing_watchlist.active() == []
    assert self.bot.maturing_watchlist.counters["dropped_invalid"] == 1


def test_is_r3_and_mode_helpers_used_by_scanner():
    assert is_r3_young_skip("zona muy joven (1 < 3 velas M5)")
    assert normalize_mode("nope") == "off"


def test_flush_panel_includes_maturing_rows():
    from hub.strat_f_panel import StratFPanel

    self = MagicMock()
    self.bot.maturing_watchlist = MaturingWatchlist()
    self.bot.maturing_watchlist.upsert_young(
        asset="AUDCAD_otc",
        direction="PUT",
        band=1.23456,
        bars_age=2,
        payout=90,
        now=10.0,
    )
    self.bot.strat_f_panel = StratFPanel()
    self.bot._hub_scanner = None
    scanner = sc.AssetScanner(self.bot, MagicMock())
    scanner._strat_f_batch = [
        [],
        [{"asset": "X", "payout": 80, "skip_reason": "zona muy joven", "stoch_m15": None}],
    ]
    scanner._flush_strat_f_panel()
    state = self.bot.strat_f_panel.get_state()
    assert len(state.maturing) == 1
    assert state.maturing[0].asset == "AUDCAD_otc"
    assert state.maturing[0].bars_age == 2
