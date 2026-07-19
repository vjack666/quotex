"""Unit tests for pure maturing zone watchlist (R1, R8, R9, R11, R13, R14)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from maturing_watchlist import (
    MaturingWatchlist,
    is_r3_young_skip,
    make_key,
    normalize_mode,
    round_band,
)


def test_is_r3_young_skip_detects_spanish_and_english():
    assert is_r3_young_skip("zona muy joven (2 < 3 velas M5)") is True
    assert is_r3_young_skip("Zone too young (1 < 3)") is True
    assert is_r3_young_skip("M1 no rechaza la banda (cierra fuera)") is False
    assert is_r3_young_skip(None) is False
    assert is_r3_young_skip("") is False


def test_normalize_mode_fail_safe():
    assert normalize_mode("live") == "live"
    assert normalize_mode("shadow") == "shadow"
    assert normalize_mode("off") == "off"
    assert normalize_mode("LIVE") == "live"
    assert normalize_mode("bogus") == "off"
    assert normalize_mode(None) == "off"
    assert normalize_mode("") == "off"


def test_make_key_stable_band_rounding():
    k1 = make_key("EURUSD_otc", "call", 1.23456789)
    k2 = make_key("EURUSD_otc", "CALL", 1.23457)
    assert k1 == k2
    assert k1 == f"EURUSD_otc|CALL|{round_band(1.23456789):.5f}"


def test_upsert_young_idempotent_updates_last_seen():
    wl = MaturingWatchlist(max_entries=40, max_age_bars=12, ttl_sec=3600)
    e1 = wl.upsert_young(
        asset="A",
        direction="CALL",
        band=1.1,
        m15_context="range",
        m5_event="fractal_down",
        bars_age=1,
        payout=90,
        now=1000.0,
    )
    assert e1.status == "maturing"
    assert wl.counters["captured"] == 1
    assert len(wl.active()) == 1

    e2 = wl.upsert_young(
        asset="A",
        direction="CALL",
        band=1.1,
        bars_age=2,
        payout=91,
        now=1005.0,
    )
    assert e2 is e1
    assert e1.bars_age == 2
    assert e1.payout == 91
    assert e1.last_seen_ts == 1005.0
    assert e1.first_seen_ts == 1000.0
    assert wl.counters["captured"] == 1
    assert len(wl.active()) == 1


def test_mark_promoted_live_and_shadow():
    wl = MaturingWatchlist()
    e = wl.upsert_young(asset="A", direction="PUT", band=2.0, now=1.0)
    key = e.key
    wl.mark_promoted(key, mode="live")
    assert wl.get(key) is None
    assert wl.counters["promoted_live"] == 1
    assert len(wl.active()) == 0

    e2 = wl.upsert_young(asset="B", direction="CALL", band=3.0, now=2.0)
    wl.mark_promoted(e2.key, mode="shadow")
    assert wl.counters["promoted_shadow"] == 1


def test_drop_invalidated():
    wl = MaturingWatchlist()
    e = wl.upsert_young(asset="X", direction="CALL", band=1.0, now=1.0)
    wl.drop(e.key, "invalidated")
    assert wl.active() == []
    assert wl.counters["dropped_invalid"] == 1


def test_expire_stale_max_age_bars():
    wl = MaturingWatchlist(max_age_bars=12, ttl_sec=99999)
    e = wl.upsert_young(asset="A", direction="CALL", band=1.0, bars_age=5, now=100.0)
    dropped = wl.expire_stale(now=100.0, bars_by_key={e.key: 13})
    assert len(dropped) == 1
    assert dropped[0].drop_reason == "expired"
    assert wl.counters["dropped_expired"] == 1
    assert wl.active() == []


def test_expire_stale_ttl():
    wl = MaturingWatchlist(max_age_bars=100, ttl_sec=3600)
    e = wl.upsert_young(asset="A", direction="CALL", band=1.0, bars_age=1, now=1000.0)
    dropped = wl.expire_stale(now=1000.0 + 3601)
    assert len(dropped) == 1
    assert dropped[0].drop_reason == "ttl"
    assert e.key not in {x.key for x in wl.active()}
    assert wl.counters["dropped_expired"] == 1


def test_cap_evicts_oldest_last_seen():
    wl = MaturingWatchlist(max_entries=2, max_age_bars=100, ttl_sec=99999)
    wl.upsert_young(asset="A", direction="CALL", band=1.0, now=10.0)
    wl.upsert_young(asset="B", direction="CALL", band=2.0, now=20.0)
    wl.upsert_young(asset="C", direction="CALL", band=3.0, now=30.0)
    assets = {e.asset for e in wl.active()}
    assert len(assets) == 2
    assert "A" not in assets
    assert "B" in assets and "C" in assets
    assert wl.counters["dropped_expired"] >= 1


def test_snapshot_includes_counters_and_entries():
    wl = MaturingWatchlist()
    wl.upsert_young(
        asset="EURUSD_otc",
        direction="CALL",
        band=1.05,
        bars_age=2,
        payout=88,
        now=50.0,
    )
    snap = wl.snapshot()
    assert snap["count"] == 1
    assert snap["counters"]["captured"] == 1
    assert snap["entries"][0]["asset"] == "EURUSD_otc"
    assert snap["entries"][0]["bars_age"] == 2
    rows = wl.panel_rows()
    assert rows[0]["direction"] == "CALL"
    assert "band" in rows[0]
