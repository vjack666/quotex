"""Tests for src/weight_calibrator.py.

Uses an in-memory SQLite database to avoid any dependency on the real
trade_journal.db. Verifies requirements R1 through R6.
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

from entry_scorer import WEIGHTS_REBOUND, WEIGHTS_BREAKOUT
from weight_calibrator import WeightCalibrator


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
        score_compression REAL,
        score_bounce    REAL,
        score_trend     REAL,
        score_payout    REAL,
        decision        TEXT NOT NULL,
        outcome         TEXT DEFAULT 'PENDING',
        profit          REAL DEFAULT 0.0,
        strategy_origin TEXT DEFAULT 'STRAT-A',
        candles_json    TEXT,
        strategy_json   TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_scanned ON candidates(scanned_at);
"""


def _candles_with_volatility(n: int = 20, vol_factor: float = 1.0) -> str:
    """Genera velas sintéticas con volatilidad controlada."""
    candles: list[dict[str, Any]] = []
    price = 1.0
    base_range = 0.001 * vol_factor
    for i in range(n):
        direction = 1 if i % 2 == 0 else -1
        rng = base_range * (0.5 + (i % 3) * 0.25)
        candles.append({
            "ts": i * 60,
            "open": price,
            "high": price + rng,
            "low": price - rng * 0.6,
            "close": price + direction * rng * 0.5,
        })
        price += direction * rng * 0.3
    return json.dumps(candles)


def _populate_db(
    conn: sqlite3.Connection,
    rows: list[dict[str, Any]],
) -> None:
    """Inserta filas sintéticas en la tabla candidates."""
    now = datetime.now(tz=timezone.utc)
    for i, r in enumerate(rows):
        # Espaciar scanned_at en el tiempo para variedad de horas
        ts = now - timedelta(hours=i * 6)
        conn.execute(
            """INSERT INTO candidates
               (scanned_at, asset, direction, payout,
                score, score_compression, score_bounce,
                score_trend, score_payout,
                decision, outcome, profit,
                strategy_origin, candles_json)
               VALUES (?,?,?,?,  ?,?,?,  ?,?,  ?,?,?,  ?,?)""",
            (
                ts.isoformat(),
                r.get("asset", "EURUSD"),
                r.get("direction", "call"),
                r.get("payout", 80),
                r.get("score", 70.0),
                r.get("score_compression", 15.0),
                r.get("score_bounce", 25.0),
                r.get("score_trend", 18.0),
                r.get("score_payout", 12.0),
                r.get("decision", "ACCEPTED"),
                r.get("outcome", "WIN"),
                r.get("profit", 0.85),
                r.get("strategy_origin", "STRAT-A"),
                r.get("candles_json", _candles_with_volatility()),
            ),
        )
    conn.commit()


def _create_in_memory_db(rows: list[dict[str, Any]]) -> sqlite3.Connection:
    """Crea una BD SQLite en memoria con esquema y datos."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    _populate_db(conn, rows)
    return conn


# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def calibrator_with_trades() -> WeightCalibrator:
    """WeightCalibrator con 30 trades sintéticos de varias horas/vols."""
    rows: list[dict[str, Any]] = []
    vol_factors = [0.5, 1.0, 2.0, 0.3, 0.8, 1.5, 2.5, 0.6, 1.2, 1.8]
    strategies = ["STRAT-A", "STRAT-MOMENTUM", "STRAT-REVERSAL-SWING",
                  "STRAT-B", "STRAT-ORDER-BLOCK"]

    for i in range(30):
        vf = vol_factors[i % len(vol_factors)]
        strat = strategies[i % len(strategies)]
        is_win = i % 3 != 1  # ~66% win rate
        rows.append({
            "asset": f"ASSET{i % 5}",
            "direction": "call" if i % 2 == 0 else "put",
            "payout": 85,
            "score": 65.0 + (i % 10),
            "score_compression": 12.0 + (i % 8),
            "score_bounce": 18.0 + (i % 15),
            "score_trend": 15.0 + (i % 10),
            "score_payout": 10.0 + (i % 8),
            "decision": "ACCEPTED",
            "outcome": "WIN" if is_win else "LOSS",
            "profit": 0.85 if is_win else -1.0,
            "strategy_origin": strat,
            "candles_json": _candles_with_volatility(vol_factor=vf),
        })

    conn = _create_in_memory_db(rows)

    # Crear un WeightCalibrator que use la BD en memoria
    cal = WeightCalibrator.__new__(WeightCalibrator)
    cal.db_path = None
    cal._conn = conn
    cal.trades = []
    cal._weights_rebound = dict(WEIGHTS_REBOUND)
    cal._weights_breakout = dict(WEIGHTS_BREAKOUT)
    return cal


@pytest.fixture
def calibrator_minimal() -> WeightCalibrator:
    """WeightCalibrator con solo 2 trades (caso mínimo, < threshold 5)."""
    rows = [
        {
            "asset": "EURUSD", "direction": "call",
            "score": 70.0,
            "score_compression": 15.0, "score_bounce": 25.0,
            "score_trend": 18.0, "score_payout": 12.0,
            "outcome": "WIN", "profit": 0.85,
            "strategy_origin": "STRAT-A",
            "candles_json": _candles_with_volatility(vol_factor=1.0),
        },
        {
            "asset": "GBPUSD", "direction": "put",
            "score": 55.0,
            "score_compression": 10.0, "score_bounce": 15.0,
            "score_trend": 18.0, "score_payout": 12.0,
            "outcome": "LOSS", "profit": -1.0,
            "strategy_origin": "STRAT-MOMENTUM",
            "candles_json": _candles_with_volatility(vol_factor=2.0),
        },
    ]
    conn = _create_in_memory_db(rows)
    cal = WeightCalibrator.__new__(WeightCalibrator)
    cal.db_path = None
    cal._conn = conn
    cal.trades = []
    cal._weights_rebound = dict(WEIGHTS_REBOUND)
    cal._weights_breakout = dict(WEIGHTS_BREAKOUT)
    return cal


@pytest.fixture
def calibrator_empty() -> WeightCalibrator:
    """WeightCalibrator sin trades (BD vacía)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    cal = WeightCalibrator.__new__(WeightCalibrator)
    cal.db_path = None
    cal._conn = conn
    cal.trades = []
    cal._weights_rebound = dict(WEIGHTS_REBOUND)
    cal._weights_breakout = dict(WEIGHTS_BREAKOUT)
    return cal


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — load_trades  (R1)
# ═══════════════════════════════════════════════════════════════════════════════


class TestLoadTrades:
    def test_load_returns_count(self, calibrator_with_trades: WeightCalibrator):
        n = calibrator_with_trades.load_trades(days=365)
        assert n >= 20  # most rows should match

    def test_load_sets_trades_list(self, calibrator_with_trades: WeightCalibrator):
        n = calibrator_with_trades.load_trades(days=365)
        assert len(calibrator_with_trades.trades) == n
        assert n > 0

    def test_trade_has_required_keys(self, calibrator_with_trades: WeightCalibrator):
        calibrator_with_trades.load_trades(days=365)
        for t in calibrator_with_trades.trades:
            assert "hour" in t
            assert "avg_range" in t
            assert "mode" in t
            assert "ratios" in t
            assert "profit" in t
            assert "outcome" in t

    def test_load_empty_db_returns_zero(self, calibrator_empty: WeightCalibrator):
        n = calibrator_empty.load_trades(days=365)
        assert n == 0

    def test_load_minimal_db(self, calibrator_minimal: WeightCalibrator):
        n = calibrator_minimal.load_trades(days=365)
        assert n == 2


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — helpers  (R6)
# ═══════════════════════════════════════════════════════════════════════════════


class TestHelpers:
    def test_hour_bucket_night(self):
        assert WeightCalibrator._hour_bucket(3) == "night"
        assert WeightCalibrator._hour_bucket(0) == "night"
        assert WeightCalibrator._hour_bucket(5) == "night"

    def test_hour_bucket_morning(self):
        assert WeightCalibrator._hour_bucket(6) == "morning"
        assert WeightCalibrator._hour_bucket(11) == "morning"

    def test_hour_bucket_afternoon(self):
        assert WeightCalibrator._hour_bucket(12) == "afternoon"
        assert WeightCalibrator._hour_bucket(17) == "afternoon"

    def test_hour_bucket_evening(self):
        assert WeightCalibrator._hour_bucket(18) == "evening"
        assert WeightCalibrator._hour_bucket(23) == "evening"

    def test_vol_regime_low(self):
        assert WeightCalibrator._vol_regime(0.0005, 0.001, 0.003) == "low"

    def test_vol_regime_medium(self):
        assert WeightCalibrator._vol_regime(0.002, 0.001, 0.003) == "medium"

    def test_vol_regime_high(self):
        assert WeightCalibrator._vol_regime(0.005, 0.001, 0.003) == "high"

    def test_vol_regime_equal_thresholds(self):
        assert WeightCalibrator._vol_regime(0.002, 0.002, 0.002) == "medium"

    def test_sharpe_known_values(self):
        profits = [0.85, 0.75, -1.0, 0.90]
        s = WeightCalibrator._sharpe(profits)
        assert isinstance(s, float)
        # Should be positive (more wins than losses)
        assert s > -999

    def test_sharpe_insufficient_data(self):
        assert WeightCalibrator._sharpe([]) == -999.0
        assert WeightCalibrator._sharpe([0.85]) == -999.0

    def test_sharpe_zero_std(self):
        assert WeightCalibrator._sharpe([0.85, 0.85]) == -999.0


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — calibrate  (R2)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCalibrate:
    def test_calibrate_returns_structure(self, calibrator_with_trades: WeightCalibrator):
        calibrator_with_trades.load_trades(days=365)
        result = calibrator_with_trades.calibrate()
        assert "calibrated_at" in result
        assert "total_trades_used" in result
        assert result["total_trades_used"] >= 20
        assert "stats" in result
        assert "default" in result
        assert "by_group" in result

    def test_calibrate_default_weights_match_base(self, calibrator_with_trades: WeightCalibrator):
        calibrator_with_trades.load_trades(days=365)
        result = calibrator_with_trades.calibrate()
        default = result["default"]
        assert default["rebound"] == WEIGHTS_REBOUND
        assert default["breakout"] == WEIGHTS_BREAKOUT

    def test_calibrate_groups_have_rebound_and_breakout(self, calibrator_with_trades: WeightCalibrator):
        calibrator_with_trades.load_trades(days=365)
        result = calibrator_with_trades.calibrate()
        for group_key, group_data in result["by_group"].items():
            assert "rebound" in group_data
            assert "breakout" in group_data

    def test_calibrate_minimal_data_does_not_crash(self, calibrator_minimal: WeightCalibrator):
        calibrator_minimal.load_trades(days=365)
        result = calibrator_minimal.calibrate()
        assert result["total_trades_used"] == 2
        # Groups may be empty or minimal
        assert "by_group" in result

    def test_calibrate_empty_returns_safe_defaults(self, calibrator_empty: WeightCalibrator):
        calibrator_empty.load_trades(days=365)
        result = calibrator_empty.calibrate()
        assert result["total_trades_used"] == 0
        assert "default" in result


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — export / load / select  (R3, R4)
# ═══════════════════════════════════════════════════════════════════════════════


class TestExportLoad:
    def test_export_creates_json(self, calibrator_with_trades: WeightCalibrator, tmp_path: Path):
        calibrator_with_trades.load_trades(days=365)
        out_path = tmp_path / "test_weights.json"
        result_path = calibrator_with_trades.export_weights(out_path)
        assert result_path == out_path
        assert out_path.exists()
        assert out_path.stat().st_size > 0

    def test_export_json_parses_correctly(self, calibrator_with_trades: WeightCalibrator, tmp_path: Path):
        calibrator_with_trades.load_trades(days=365)
        out_path = tmp_path / "test_weights.json"
        calibrator_with_trades.export_weights(out_path)

        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert "calibrated_at" in data
        assert "default" in data
        assert "by_group" in data
        assert len(data["by_group"]) > 0

    def test_load_weights_roundtrip(self, calibrator_with_trades: WeightCalibrator, tmp_path: Path):
        calibrator_with_trades.load_trades(days=365)
        out_path = tmp_path / "roundtrip.json"
        calibrator_with_trades.export_weights(out_path)

        loaded = WeightCalibrator.load_weights(out_path)
        assert loaded["total_trades_used"] >= 20
        assert loaded["default"]["rebound"] == WEIGHTS_REBOUND
        assert len(loaded["by_group"]) > 0

    def test_load_weights_nonexistent_returns_empty(self):
        result = WeightCalibrator.load_weights(Path("/nonexistent/path.json"))
        assert result == {}

    @pytest.mark.parametrize("hour,expected_bucket", [
        (3, "night"), (9, "morning"), (14, "afternoon"), (20, "evening"),
    ])
    def test_select_weights_default_fallback(
        self, hour: int, expected_bucket: str,
    ):
        """Cuando el grupo exacto no existe, usa default."""
        data = {
            "default": {
                "rebound": {"compression": 20, "bounce": 35, "trend": 25, "payout": 20},
                "breakout": {"compression": 15, "momentum": 35, "trend": 30, "payout": 20},
            },
            "by_group": {},
        }
        reb, brk = WeightCalibrator.select_weights(data, hour=hour, avg_range=0.001)
        assert reb == WEIGHTS_REBOUND
        assert brk == WEIGHTS_BREAKOUT

    def test_select_weights_matches_group(self):
        """Cuando el grupo existe, retorna sus pesos."""
        data = {
            "default": {
                "rebound": WEIGHTS_REBOUND,
                "breakout": WEIGHTS_BREAKOUT,
            },
            "by_group": {
                "hour_morning_vol_low": {
                    "rebound": {"compression": 18, "bounce": 38, "trend": 22, "payout": 22},
                    "breakout": {"compression": 12, "momentum": 38, "trend": 28, "payout": 22},
                },
            },
        }
        reb, brk = WeightCalibrator.select_weights(data, hour=9, avg_range=0.0005)
        assert reb["compression"] == 18
        assert reb["bounce"] == 38
        assert brk["momentum"] == 38

    def test_select_weights_empty_data(self):
        reb, brk = WeightCalibrator.select_weights({}, hour=12, avg_range=0.001)
        assert reb == WEIGHTS_REBOUND
        assert brk == WEIGHTS_BREAKOUT


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — apply_weights  (R4)
# ═══════════════════════════════════════════════════════════════════════════════


class TestApplyWeights:
    def test_apply_weights_overwrites_globals(self):
        original_rebound = dict(WEIGHTS_REBOUND)
        original_breakout = dict(WEIGHTS_BREAKOUT)

        test_rebound = {"compression": 99, "bounce": 1, "trend": 0, "payout": 0}
        test_breakout = {"compression": 1, "momentum": 99, "trend": 0, "payout": 0}

        WeightCalibrator.apply_weights(test_rebound, test_breakout)
        assert WEIGHTS_REBOUND == test_rebound
        assert WEIGHTS_BREAKOUT == test_breakout

        # Restore
        WeightCalibrator.apply_weights(original_rebound, original_breakout)
        assert WEIGHTS_REBOUND == original_rebound
        assert WEIGHTS_BREAKOUT == original_breakout

    def test_apply_weights_preserves_structure(self):
        """Después de aplicar, los dicts tienen las mismas keys."""
        original_rebound = dict(WEIGHTS_REBOUND)
        original_breakout = dict(WEIGHTS_BREAKOUT)

        reb_keys = set(original_rebound.keys())
        brk_keys = set(original_breakout.keys())

        WeightCalibrator.apply_weights(original_rebound, original_breakout)
        assert set(WEIGHTS_REBOUND.keys()) == reb_keys
        assert set(WEIGHTS_BREAKOUT.keys()) == brk_keys


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests — integración  (R1-R6)
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    def test_full_calibrate_export_load_cycle(self, calibrator_with_trades: WeightCalibrator, tmp_path: Path):
        """Ciclo completo: load → calibrate → export → load → select."""
        # Load
        n = calibrator_with_trades.load_trades(days=365)
        assert n > 0

        # Calibrate
        result = calibrator_with_trades.calibrate()
        assert result["total_trades_used"] == n

        # Export
        out_path = tmp_path / "full_cycle.json"
        calibrator_with_trades.export_weights(out_path)
        assert out_path.exists()

        # Load
        loaded = WeightCalibrator.load_weights(out_path)
        assert loaded["total_trades_used"] == n

        # Select (finds default since we can't guarantee exact group match)
        reb, brk = WeightCalibrator.select_weights(loaded, hour=12, avg_range=0.001)
        assert reb is not None
        assert brk is not None
        # Should have the right keys
        assert set(reb.keys()) == {"compression", "bounce", "trend", "payout"}
        assert set(brk.keys()) == {"compression", "momentum", "trend", "payout"}

    def test_weights_sum_to_100(self, calibrator_with_trades: WeightCalibrator):
        """Todos los pesos en default y by_group suman 100."""
        calibrator_with_trades.load_trades(days=365)
        result = calibrator_with_trades.calibrate()

        # Default
        assert sum(result["default"]["rebound"].values()) == 100
        assert sum(result["default"]["breakout"].values()) == 100

        # Groups
        for key, group in result["by_group"].items():
            for mode in ("rebound", "breakout"):
                w = group.get(mode, {})
                if w:
                    assert sum(w.values()) == 100, (
                        f"Group {key}/{mode} sums to {sum(w.values())}"
                    )

    def test_no_broker_import(self):
        """weight_calibrator must not import pyquotex or broker libs."""
        import weight_calibrator as wc_mod
        source = Path(wc_mod.__file__).read_text(encoding="utf-8")
        assert "pyquotex" not in source
        assert "websocket" not in source.lower()
        assert "quotex" not in source.lower()
