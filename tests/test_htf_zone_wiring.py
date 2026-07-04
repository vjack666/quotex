"""Unit tests — HTF 15m cache wiring y zone_memory en STRAT-A."""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config import BROKER_TZ
from entry_scorer import score_candidate
from htf_scanner import HTFScanner
from models import Candle, CandidateEntry, ConsolidationZone
from scanner import AssetScanner
from strat_a import infer_h1_trend


class FakeHTFScanner:
    def __init__(self, candles_map: dict[str, list] | None = None, default: list | None = None):
        self._map = candles_map or {}
        self._default = default if default is not None else []

    def get_candles_15m(self, sym: str) -> list:
        return self._map.get(sym, self._default)


def _trending_15m_candles(n: int = 60, *, bullish: bool, base: float = 1.10) -> list[Candle]:
    candles: list[Candle] = []
    for i in range(n):
        drift = i * (0.00015 if bullish else -0.00015)
        price = base + drift
        body = 0.00005 if bullish else -0.00005
        close = price + body
        candles.append(
            Candle(
                ts=i * 900,
                open=price,
                high=max(price, close) + 0.0001,
                low=min(price, close) - 0.0001,
                close=close,
            )
        )
    return candles


def _make_scanner(monkeypatch, htf: FakeHTFScanner, journal_db: Path | None = None):
    bot = MagicMock()
    bot.htf_scanner = htf
    bot.stats = {"skipped": 0, "rejected_young_zone": 0, "filtered_sensor": 0}
    executor = MagicMock()
    scanner = AssetScanner(bot, executor)

    journal = MagicMock()
    journal.db_path = journal_db or Path(__file__).parent / "_nonexistent_journal.db"
    monkeypatch.setattr("scanner.get_journal", lambda: journal)
    return bot, scanner, journal


def _zone(price: float = 1.10) -> ConsolidationZone:
    return ConsolidationZone(
        asset="EURUSD_otc",
        ceiling=price + 0.0005,
        floor=price - 0.0005,
        bars_inside=14,
        detected_at=0.0,
        range_pct=0.001,
    )


def _seed_expired_zone(
    db_path: Path,
    *,
    asset: str,
    ceiling: float,
    floor: float,
    expiry_reason: str = "TIME_LIMIT",
    bars_inside: int = 12,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expired_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expired_at TEXT NOT NULL,
            asset TEXT NOT NULL,
            expiry_reason TEXT NOT NULL,
            ceiling REAL NOT NULL,
            floor REAL NOT NULL,
            range_pct REAL,
            bars_inside INTEGER,
            age_min REAL,
            last_close REAL,
            break_body REAL DEFAULT NULL,
            payout INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        INSERT INTO expired_zones (
            expired_at, asset, expiry_reason, ceiling, floor,
            range_pct, bars_inside, age_min, last_close, payout
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            datetime.now(tz=BROKER_TZ).isoformat(),
            asset,
            expiry_reason,
            ceiling,
            floor,
            0.001,
            bars_inside,
            30.0,
            (ceiling + floor) / 2,
            88,
        ),
    )
    conn.commit()
    conn.close()


@pytest.mark.asyncio
async def test_htf_scanner_fetch_import(monkeypatch):
    captured: list[int] = []

    async def fake_fetch(client, asset, tf_sec, count, **kwargs):
        captured.append(tf_sec)
        return [_trending_15m_candles(5, bullish=True)[0]]

    monkeypatch.setattr("connection.fetch_candles_with_retry", fake_fetch)

    scanner = HTFScanner(MagicMock(), min_payout=87)
    candles = await scanner._fetch_15m("EURUSD_otc")

    assert captured == [900]
    assert len(candles) == 1


def test_htf_veto_missing_candles(monkeypatch):
    htf = FakeHTFScanner(default=_trending_15m_candles(5, bullish=True))
    _, scanner, _ = _make_scanner(monkeypatch, htf)

    passed, candles_15m, zones, skip = scanner._apply_strat_a_htf_zone_gates(
        "EURUSD_otc", "call", 1.10,
    )

    assert not passed
    assert skip == "htf_reject"
    assert len(candles_15m) < 10
    assert zones == []


def test_htf_veto_misaligned_put(monkeypatch):
    htf = FakeHTFScanner(default=_trending_15m_candles(60, bullish=True))
    bot, scanner, _ = _make_scanner(monkeypatch, htf)

    passed, _, _, skip = scanner._apply_strat_a_htf_zone_gates(
        "EURUSD_otc", "put", 1.10,
    )

    assert not passed
    assert skip == "htf_reject"
    assert bot.stats["skipped"] == 1


def test_htf_pass_aligned_call(monkeypatch):
    htf = FakeHTFScanner(default=_trending_15m_candles(60, bullish=True))
    _, scanner, _ = _make_scanner(monkeypatch, htf)

    passed, candles_15m, zones, skip = scanner._apply_strat_a_htf_zone_gates(
        "EURUSD_otc", "call", 1.10,
    )

    assert passed
    assert skip is None
    assert len(candles_15m) >= 10
    assert zones == []
    assert infer_h1_trend(candles_15m) == "bullish"


def test_zone_memory_populated_from_db(monkeypatch, tmp_path):
    sym = "EURUSD_otc"
    price = 1.1000
    db_path = tmp_path / "journal.db"
    _seed_expired_zone(
        db_path,
        asset=sym,
        ceiling=price + 0.0008,
        floor=price + 0.0002,
        expiry_reason="TIME_LIMIT",
    )

    htf = FakeHTFScanner(default=_trending_15m_candles(60, bullish=False))
    _, scanner, _ = _make_scanner(monkeypatch, htf, journal_db=db_path)

    passed, _, zones, _ = scanner._apply_strat_a_htf_zone_gates(sym, "put", price)

    assert passed
    assert len(zones) >= 1


def test_score_breakdown_zone_memory_nonzero(monkeypatch, tmp_path):
    sym = "EURUSD_otc"
    price = 1.1000
    db_path = tmp_path / "journal.db"
    _seed_expired_zone(
        db_path,
        asset=sym,
        ceiling=price + 0.0008,
        floor=price + 0.0002,
        expiry_reason="TIME_LIMIT",
    )

    from zone_memory import query_nearby_zones

    zones = query_nearby_zones(db_path, sym, price)
    assert zones

    candidate = CandidateEntry(
        asset=sym,
        payout=88,
        zone=_zone(price),
        direction="put",
        candles=[Candle(ts=0, open=price, high=price, low=price, close=price)],
        zone_memory=zones,
        candles_15m=_trending_15m_candles(30, bullish=False),
    )
    score_candidate(candidate)

    assert candidate.score_breakdown.get("zone_memory", 0) != 0


def test_score_candidate_trend_prefers_15m_over_5m():
    """R15: trend usa candles_15m (>=25) en lugar de velas 5m del candidato."""
    sym = "EURUSD_otc"
    price = 1.1000
    zone = _zone(price)

    flat_5m = [
        Candle(ts=i * 300, open=price, high=price + 0.0001, low=price - 0.0001, close=price)
        for i in range(30)
    ]
    bearish_15m = _trending_15m_candles(30, bullish=False, base=price)

    base = dict(
        asset=sym,
        payout=88,
        zone=zone,
        direction="put",
        candles=flat_5m,
    )

    cand_5m_only = CandidateEntry(**base, candles_15m=[])
    score_candidate(cand_5m_only)
    trend_5m = cand_5m_only.score_breakdown["trend"]

    cand_with_15m = CandidateEntry(**base, candles_15m=bearish_15m)
    score_candidate(cand_with_15m)
    trend_15m = cand_with_15m.score_breakdown["trend"]

    assert trend_15m != trend_5m
    assert trend_15m > trend_5m


def test_zone_memory_wall_veto(monkeypatch, tmp_path):
    sym = "EURUSD_otc"
    price = 1.1000
    db_path = tmp_path / "journal.db"
    _seed_expired_zone(
        db_path,
        asset=sym,
        ceiling=price - 0.0001,
        floor=price - 0.0010,
        expiry_reason="TIME_LIMIT",
        bars_inside=20,
    )

    htf = FakeHTFScanner(default=_trending_15m_candles(60, bullish=False))
    bot, scanner, _ = _make_scanner(monkeypatch, htf, journal_db=db_path)

    passed, _, zones, skip = scanner._apply_strat_a_htf_zone_gates(sym, "put", price)

    assert not passed
    assert skip == "zone_memory_wall"
    assert zones
    assert bot.stats["skipped"] == 1