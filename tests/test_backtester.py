"""Tests for src/backtester.py.

Uses an in-memory SQLite database injected via ``tmp_path`` to avoid
any dependency on the real trade_journal.db.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest

from backtester import Backtester
from models import Candle


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS candidates (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        scanned_at      TEXT NOT NULL,
        asset           TEXT NOT NULL,
        direction       TEXT NOT NULL,
        payout          INTEGER,
        amount          REAL,
        stage           TEXT,
        score           REAL,
        decision        TEXT NOT NULL,
        outcome         TEXT DEFAULT 'PENDING',
        profit          REAL DEFAULT 0.0,
        strategy_origin TEXT DEFAULT 'STRAT-A',
        candles_json    TEXT,
        strategy_json   TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_scanned ON candidates(scanned_at);
"""


def _synthetic_candles(n: int = 20) -> list[dict[str, Any]]:
    """Small-body random-ish candles — no clear signal for any strategy."""
    candles: list[dict[str, Any]] = []
    price = 1.0
    for i in range(n):
        direction = 1 if i % 2 == 0 else -1
        candles.append({
            "ts": i * 60,
            "open": price,
            "high": price + 0.001,
            "low": price - 0.001,
            "close": price + direction * 0.0005,
        })
        price += direction * 0.0005
    return json.dumps(candles)


def _momentum_candles() -> str:
    """Last candle has a large bullish body → triggers detect_momentum_1m.

    Lookback candles have small non-zero bodies so avg_body > 0.
    Final candle: body = 0.010, range = 0.011, close_pos ≈ 0.91 (> 2/3).
    """
    candles: list[dict[str, Any]] = []
    price = 1.0
    for i in range(15):
        # Small bullish body for each lookback candle
        candles.append({
            "ts": i * 60,
            "open": price,
            "high": price + 0.0012,
            "low": price - 0.0002,
            "close": price + 0.0010,
        })
        price += 0.0005
    # Bullish momentum candle (body = 0.010, body_ratio > 1.5)
    candles.append({
        "ts": 15 * 60,
        "open": price,
        "high": price + 0.011,
        "low": price,
        "close": price + 0.010,
    })
    return json.dumps(candles)


def _swing_candles() -> str:
    """Candles with clear swing high + upper wick → signals put reversal.

    Needs >= 13 candles for SWING_LOOKBACK=12.
    Structure: 6 up, 1 swing-high peak, 5 down (lower highs after peak),
    then a rejection candle that touches the swing-high level.
    """
    candles: list[dict[str, Any]] = []
    price = 1.0000
    # 6 candles trending up
    for i in range(6):
        candles.append({
            "ts": i * 60,
            "open": price,
            "high": price + 0.0030,
            "low": price - 0.0010,
            "close": price + 0.0020,
        })
        price += 0.0020
    # Swing high peak (candle 6): higher than both neighbors
    peak_high = price + 0.0050
    candles.append({
        "ts": 6 * 60,
        "open": price,
        "high": peak_high,
        "low": price - 0.0010,
        "close": price + 0.0030,
    })
    # 5 candles trending down (lower highs after peak)
    for i in range(7, 12):
        price -= 0.0015
        candles.append({
            "ts": i * 60,
            "open": price + 0.0010,
            "high": price + 0.0020,
            "low": price - 0.0010,
            "close": price,
        })
    # Rejection candle touches the swing-high level with long upper wick
    # Price ≈ 1.012 (peak) - 0.0015*5 ≈ 1.0045 at this point
    rejection_open = price
    candles.append({
        "ts": 12 * 60,
        "open": rejection_open,
        "high": peak_high + 0.0001,  # touches the swing-high level
        "low": rejection_open - 0.0010,
        "close": rejection_open + 0.0005,
    })
    return json.dumps(candles)


def _create_db(path: Path, rows: list[dict[str, Any]]) -> None:
    """Populate a SQLite DB at *path* with the given candidate rows."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)

    now = datetime.now(tz=timezone.utc).isoformat()
    for r in rows:
        conn.execute(
            """INSERT INTO candidates
               (scanned_at, asset, direction, payout, decision,
                outcome, profit, strategy_origin, candles_json, strategy_json)
               VALUES (?,?,?,?,?, ?,?,?,?,?)""",
            (
                now,
                r["asset"],
                r["direction"],
                r.get("payout", 80),
                r.get("decision", "ACCEPTED"),
                r.get("outcome", "PENDING"),
                r.get("profit", 0.0),
                r["strategy_origin"],
                r.get("candles_json", _synthetic_candles()),
                r.get("strategy_json"),
            ),
        )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def db_mixed(tmp_path: Path) -> Path:
    """DB with 5 candidates across different strategy origins."""
    _create_db(tmp_path / "mixed.db", [
        {
            "asset": "EURUSD", "direction": "call",
            "outcome": "WIN", "profit": 0.85,
            "strategy_origin": "STRAT-MOMENTUM",
            "candles_json": _momentum_candles(),
        },
        {
            "asset": "EURUSD", "direction": "put",
            "outcome": "LOSS", "profit": -1.0,
            "strategy_origin": "STRAT-REVERSAL-SWING",
            "candles_json": _swing_candles(),
        },
        {
            "asset": "GBPUSD", "direction": "call",
            "outcome": "WIN", "profit": 0.75,
            "strategy_origin": "STRAT-ORDER-BLOCK",
            "candles_json": _synthetic_candles(),
        },
        {
            "asset": "GBPUSD", "direction": "put",
            "outcome": "PENDING", "profit": 0.0,
            "strategy_origin": "STRAT-MOMENTUM",
            "candles_json": _momentum_candles(),
        },
        {
            "asset": "AUDUSD", "direction": "call",
            "outcome": "PENDING", "profit": 0.0,
            "strategy_origin": "STRAT-A",
            "candles_json": _synthetic_candles(),
            "strategy_json": json.dumps({
                "zone": {
                    "ceiling": 1.01, "floor": 0.99,
                    "bars_inside": 10,
                    "detected_at": time.time(),
                    "range_pct": 0.02,
                },
            }),
        },
    ])
    return tmp_path / "mixed.db"


@pytest.fixture
def db_known_metrics(tmp_path: Path) -> Path:
    """DB with 4 resolved trades (3 WIN, 1 LOSS) for exact metric checks.

    Profits: [0.80, -1.00, 0.75, 0.85] → total = 1.40, win rate = 0.75.
    """
    _create_db(tmp_path / "known.db", [
        {
            "asset": "EURUSD", "direction": "call",
            "outcome": "WIN", "profit": 0.80,
            "strategy_origin": "STRAT-MOMENTUM",
        },
        {
            "asset": "EURUSD", "direction": "put",
            "outcome": "LOSS", "profit": -1.00,
            "strategy_origin": "STRAT-REVERSAL-SWING",
        },
        {
            "asset": "GBPUSD", "direction": "call",
            "outcome": "WIN", "profit": 0.75,
            "strategy_origin": "STRAT-ORDER-BLOCK",
        },
        {
            "asset": "GBPUSD", "direction": "put",
            "outcome": "WIN", "profit": 0.85,
            "strategy_origin": "STRAT-MOMENTUM",
        },
    ])
    return tmp_path / "known.db"


@pytest.fixture
def db_empty(tmp_path: Path) -> Path:
    """Fully empty DB with schema but no rows."""
    path = tmp_path / "empty.db"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    return path


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — load_from_db  (R1)
# ═══════════════════════════════════════════════════════════════════════════════


class TestLoadFromDB:
    def test_load_all_candidates(self, db_mixed: Path):
        bt = Backtester(db_mixed)
        candidates = bt.load_from_db(days=365)
        assert len(candidates) == 5

    def test_load_candidates_have_deserialized_candles(self, db_mixed: Path):
        bt = Backtester(db_mixed)
        candidates = bt.load_from_db(days=365)
        for c in candidates:
            assert len(c["candles"]) > 0
            assert isinstance(c["candles"][0], Candle)
            assert c["candles"][0].close is not None
            assert c["reevaluated_signal"] is None  # not yet evaluated

    def test_load_empty_db_returns_empty(self, db_empty: Path):
        bt = Backtester(db_empty)
        candidates = bt.load_from_db(days=365)
        assert candidates == []

    def test_load_filters_by_day_range(self, db_mixed: Path):
        bt = Backtester(db_mixed)
        # days=0 → no candidates (scanned before the cutoff)
        candidates = bt.load_from_db(days=0)
        assert len(candidates) == 0

    def test_load_candidate_keeps_all_fields(self, db_mixed: Path):
        bt = Backtester(db_mixed)
        candidates = bt.load_from_db(days=365)
        momentum = [c for c in candidates if c["strategy_origin"] == "STRAT-MOMENTUM"]
        assert len(momentum) == 2
        for c in momentum:
            assert c["direction"] in ("call", "put")
            assert c["outcome"] in ("WIN", "LOSS", "PENDING")
            assert c["profit"] is not None
            assert isinstance(c["candles_json"], str)


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — reevaluate  (R2, R5)
# ═══════════════════════════════════════════════════════════════════════════════


class TestReevaluate:
    def test_reevaluate_momentum_detects_signal(self, db_mixed: Path):
        """Momentum candles should produce a 'call' signal."""
        bt = Backtester(db_mixed)
        bt.load_from_db(days=365)
        bt.reevaluate(strategies=["STRAT-MOMENTUM"])
        for c in bt.candidates:
            if c["strategy_origin"] == "STRAT-MOMENTUM":
                assert c["reevaluated_signal"] == "call"
                assert c["reevaluated_strength"] > 0

    def test_reevaluate_reversal_swing_detects_put(self, db_mixed: Path):
        """Swing candles with upper wick should signal 'put'."""
        bt = Backtester(db_mixed)
        bt.load_from_db(days=365)
        bt.reevaluate(strategies=["STRAT-REVERSAL-SWING"])
        swing = [c for c in bt.candidates if c["strategy_origin"] == "STRAT-REVERSAL-SWING"]
        for c in swing:
            assert c["reevaluated_signal"] == "put"
            assert c["reevaluated_strength"] > 0

    def test_reevaluate_noisy_candles_no_signal(self, db_mixed: Path):
        """Random small-body candles should NOT produce a reversal signal."""
        bt = Backtester(db_mixed)
        bt.load_from_db(days=365)
        bt.reevaluate(strategies=["STRAT-REVERSAL-SWING"])
        # The GBPUSD candidate with synthetic noise should have no signal
        ob_candidates = [c for c in bt.candidates if c["strategy_origin"] == "STRAT-ORDER-BLOCK"]
        for c in ob_candidates:
            # Synthetic candles don't have clear OB structure → no signal
            assert c["reevaluated_signal"] is None

    def test_reevaluate_all_strategies(self, db_mixed: Path):
        """Running reevaluate() without filter processes all strategies."""
        bt = Backtester(db_mixed)
        bt.load_from_db(days=365)
        bt.reevaluate()
        for c in bt.candidates:
            # All candidates should have reevaluated_signal set (even if None)
            assert "reevaluated_signal" in c
            assert "reevaluated_strength" in c

    def test_reevaluate_unknown_strategy(self, db_mixed: Path, caplog: pytest.LogCaptureFixture):
        """Unknown strategy origins should be logged as warnings."""
        bt = Backtester(db_mixed)
        bt.load_from_db(days=365)
        # Manually inject a candidate with unknown origin
        bt.candidates.append({
            "id": 999,
            "strategy_origin": "STRAT-UNKNOWN",
            "candles": [],
            "reevaluated_signal": None,
            "reevaluated_strength": 0.0,
        })
        import logging
        with caplog.at_level(logging.WARNING):
            bt.reevaluate()
        assert "unknown strategy_origin" in caplog.text


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — compare  (R5)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCompare:
    def test_compare_returns_structure(self, db_mixed: Path):
        bt = Backtester(db_mixed)
        bt.load_from_db(days=365)
        bt.reevaluate()
        result = bt.compare()
        assert isinstance(result, dict)
        assert result["total"] == 5
        assert "matches" in result
        assert "mismatches" in result
        assert "no_signal_now" in result
        assert result["matches"] + result["mismatches"] + result["no_signal_now"] == result["total"]

    def test_compare_no_signal_count(self, db_mixed: Path):
        bt = Backtester(db_mixed)
        bt.load_from_db(days=365)
        # Don't run reevaluate → all reevaluated_signal are None
        # compare still works with null signals
        result = bt.compare()
        assert result["no_signal_now"] == 5

    def test_compare_empty_no_error(self, db_empty: Path):
        bt = Backtester(db_empty)
        bt.load_from_db(days=365)
        result = bt.compare()
        assert result == {"total": 0, "matches": 0, "mismatches": 0, "no_signal_now": 0}


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — report  (R3)
# ═══════════════════════════════════════════════════════════════════════════════


class TestReport:
    def test_report_contains_all_metrics(self, db_known_metrics: Path):
        bt = Backtester(db_known_metrics)
        bt.load_from_db(days=365)
        report = bt.report()
        assert "Win rate" in report
        assert "Total profit" in report
        assert "Max drawdown" in report
        assert "Sharpe ratio" in report

    def test_report_known_win_rate(self, db_known_metrics: Path):
        """3 WIN + 1 LOSS → win rate = 75%."""
        bt = Backtester(db_known_metrics)
        bt.load_from_db(days=365)
        report = bt.report()
        assert "75.00%" in report

    def test_report_known_total_profit(self, db_known_metrics: Path):
        """0.80 - 1.00 + 0.75 + 0.85 = $1.40."""
        bt = Backtester(db_known_metrics)
        bt.load_from_db(days=365)
        report = bt.report()
        assert "$1.40" in report

    def test_report_all_pending_returns_message(self, db_empty: Path):
        """No resolved trades → friendly message."""
        bt = Backtester(db_empty)
        bt.load_from_db(days=365)
        report = bt.report()
        assert "No resolved trades to report." in report

    def test_report_drawdown_is_negative_or_zero(self, db_known_metrics: Path):
        bt = Backtester(db_known_metrics)
        bt.load_from_db(days=365)
        report = bt.report()
        # Max drawdown should be negative or zero
        assert "Max drawdown" in report
        # Extract the percentage value and check it's ≤ 0
        import re
        match = re.search(r"Max drawdown\s+:\s+(-?\d+\.\d+)%", report)
        assert match is not None
        dd_value = float(match.group(1))
        assert dd_value <= 0.0, f"Drawdown should be ≤ 0, got {dd_value}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — no broker I/O  (R4)
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoBrokerIO:
    def test_no_network_calls_in_backtester_flow(self, db_mixed: Path):
        """The full load → reevaluate → compare → report cycle runs
        without network access. Uses in-memory DB and pure functions."""
        bt = Backtester(db_mixed)
        bt.load_from_db(days=365)
        bt.reevaluate()
        bt.compare()
        bt.report()
        # If this passes without ImportError or network errors, R4 is satisfied.

    def test_modules_dont_import_pyquotex(self, db_mixed: Path):
        """backtester must not import pyquotex or similar broker libs."""
        import backtester as bt_mod  # noqa: F811
        mod_source = Path(bt_mod.__file__).read_text(encoding="utf-8")
        assert "pyquotex" not in mod_source
        assert "websocket" not in mod_source.lower()
        assert "quotex" not in mod_source.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — STRAT-F recognition  (R7, R8)  SDD strat_f_quality_validation
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def db_strat_f(tmp_path: Path) -> Path:
    """DB with a resolved STRAT-F trade for origin-recognition tests."""
    _create_db(tmp_path / "stratf.db", [
        {
            "asset": "GBPUSD_otc", "direction": "call",
            "outcome": "WIN", "profit": 0.91,
            "strategy_origin": "STRAT-F",
            "strategy_json": json.dumps({"direction": "call", "strength": 0.70}),
        },
        {
            "asset": "BRLUSD_otc", "direction": "put",
            "outcome": "LOSS", "profit": -1.0,
            "strategy_origin": "STRAT-F",
            "strategy_json": json.dumps({"direction": "put", "strength": 0.70}),
        },
    ])
    return tmp_path / "stratf.db"


class TestStratFRecognition:
    def test_strat_f_in_strategy_map_or_branch(self):
        """R7 — el backtester reconoce STRAT-F (rama dedicada)."""
        from backtester import Backtester as _BT
        assert hasattr(_BT, "_reevaluate_strat_f")

    def test_reevaluate_strat_f_sets_signal_from_json(self, db_strat_f: Path):
        """R7 — reevaluate procesa STRAT-F usando strategy_json."""
        bt = Backtester(db_strat_f)
        bt.load_from_db(days=365)
        bt.reevaluate(strategies=["STRAT-F"])
        sf = [c for c in bt.candidates if c["strategy_origin"] == "STRAT-F"]
        assert len(sf) == 2
        for c in sf:
            assert c["reevaluated_signal"] in ("call", "put")
            assert c["reevaluated_strength"] == 0.70

    def test_strat_f_appears_in_report(self, db_strat_f: Path):
        """R8 — el reporte incluye las metricas de las señales STRAT-F resueltas."""
        bt = Backtester(db_strat_f)
        bt.load_from_db(days=365)
        bt.reevaluate()
        report = bt.report()
        # 1 WIN + 1 LOSS -> win rate 50%, total profit -0.09
        assert "Win rate" in report
        assert "50.00%" in report

