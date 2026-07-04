"""Tests de Kelly Criterion Sizing — R8."""
from __future__ import annotations

import sys
import sqlite3
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kelly_sizer import KellySizer, DEFAULT_FRACTIONAL, MIN_TRADES


# ── Helpers ──────────────────────────────────────────────────────────────────


def _create_memory_db() -> sqlite3.Connection:
    """Crea BD en memoria con la tabla candidates y estructura mínima."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE candidates (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            scanned_at       TEXT NOT NULL,
            asset            TEXT NOT NULL,
            direction        TEXT NOT NULL,
            payout           INTEGER,
            decision         TEXT NOT NULL,
            outcome          TEXT DEFAULT 'PENDING',
            profit           REAL DEFAULT 0.0,
            strategy_origin  TEXT DEFAULT 'STRAT-A'
        );
    """)
    return conn


def _seed_trades(
    conn: sqlite3.Connection,
    *,
    wins: int = 0,
    losses: int = 0,
    payout: int = 85,
    decision: str = "ACCEPTED",
) -> None:
    """Inserta trades de prueba en la BD."""
    for _ in range(wins):
        conn.execute(
            """INSERT INTO candidates
               (scanned_at, asset, direction, payout, decision, outcome, profit)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("2024-06-01T00:00:00", "EURUSD_otc", "call", payout, decision, "WIN", float(payout) / 100.0),
        )
    for _ in range(losses):
        conn.execute(
            """INSERT INTO candidates
               (scanned_at, asset, direction, payout, decision, outcome, profit)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("2024-06-01T00:00:00", "EURUSD_otc", "put", payout, decision, "LOSS", -1.0),
        )
    conn.commit()


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def empty_conn() -> sqlite3.Connection:
    """BD sin datos."""
    conn = _create_memory_db()
    yield conn
    conn.close()


@pytest.fixture
def sized_conn() -> sqlite3.Connection:
    """BD con trades balanceados (60% WR, 85% payout)."""
    conn = _create_memory_db()
    # 12 WIN + 8 LOSS = 20 trades → 60% WR, supera MIN_TRADES
    _seed_trades(conn, wins=12, losses=8, payout=85)
    return conn


@pytest.fixture
def high_wr_conn() -> sqlite3.Connection:
    """BD con 80% WR."""
    conn = _create_memory_db()
    _seed_trades(conn, wins=16, losses=4, payout=85)
    return conn


@pytest.fixture
def low_payout_conn() -> sqlite3.Connection:
    """BD con payout bajo (75%)."""
    conn = _create_memory_db()
    _seed_trades(conn, wins=12, losses=8, payout=75)
    return conn


@pytest.fixture
def perfect_wr_conn() -> sqlite3.Connection:
    """BD con 100% WR (solo wins)."""
    conn = _create_memory_db()
    _seed_trades(conn, wins=20, losses=0, payout=85)
    return conn


@pytest.fixture
def zero_wr_conn() -> sqlite3.Connection:
    """BD con 0% WR (solo losses)."""
    conn = _create_memory_db()
    _seed_trades(conn, wins=0, losses=20, payout=85)
    return conn


def make_sizer(conn: sqlite3.Connection) -> KellySizer:
    """Crea KellySizer apuntando a una BD en memoria."""
    sizer = KellySizer.__new__(KellySizer)
    sizer.db_path = None
    sizer._conn = conn
    return sizer


# ── Tests ────────────────────────────────────────────────────────────────────


class TestCalculation:
    """R1, R7, R8 — Cálculo con datos válidos y variantes."""

    def test_calculates_positive_factor(self, sized_conn: sqlite3.Connection):
        """Kelly con 60% WR, 85% payout → factor positivo."""
        sizer = make_sizer(sized_conn)
        factor = sizer.calculate()
        # Kelly completo: (0.6 * 1.85 - 1) / 0.85 = (1.11 - 1) / 0.85 = 0.1294
        # Fraccional 25%: 0.1294 * 0.25 = 0.0324
        assert 0.0 < factor <= 1.0

    def test_higher_wr_gives_higher_factor(
        self, sized_conn: sqlite3.Connection, high_wr_conn: sqlite3.Connection,
    ):
        """80% WR > 60% WR → factor mayor."""
        sizer_low = make_sizer(sized_conn)
        sizer_high = make_sizer(high_wr_conn)
        assert sizer_high.calculate() > sizer_low.calculate()

    def test_factor_clamped_to_one(
        self, perfect_wr_conn: sqlite3.Connection,
    ):
        """100% WR con 85% payout: Kelly completo = (1*1.85-1)/0.85=1.0
        Fraccional 25% = 0.25"""
        sizer = make_sizer(perfect_wr_conn)
        factor = sizer.calculate()
        assert 0.0 <= factor <= 1.0

    def test_zero_win_rate_returns_zero(self, zero_wr_conn: sqlite3.Connection):
        """0% WR → 0.0."""
        sizer = make_sizer(zero_wr_conn)
        assert sizer.calculate() == 0.0

    def test_low_payout_reduces_factor(
        self, sized_conn: sqlite3.Connection, low_payout_conn: sqlite3.Connection,
    ):
        """Mismo WR con payout menor → factor menor o igual."""
        sizer_normal = make_sizer(sized_conn)
        sizer_low = make_sizer(low_payout_conn)
        assert sizer_low.calculate() <= sizer_normal.calculate()

    def test_custom_fractional(self, sized_conn: sqlite3.Connection):
        """Fracción personalizada (50%) → factor mayor que default."""
        sizer = make_sizer(sized_conn)
        default_factor = sizer.calculate(fractional=0.25)
        double_factor = sizer.calculate(fractional=0.50)
        assert double_factor > default_factor


class TestInsufficientData:
    """R3, R5 — Sin datos o datos insuficientes."""

    def test_empty_db_returns_zero(self, empty_conn: sqlite3.Connection):
        """BD sin filas → 0.0."""
        sizer = make_sizer(empty_conn)
        assert sizer.calculate() == 0.0

    def test_fewer_than_min_trades_returns_zero(self, empty_conn: sqlite3.Connection):
        """Menos de MIN_TRADES trades → 0.0."""
        _seed_trades(empty_conn, wins=3, losses=2, payout=85)
        sizer = make_sizer(empty_conn)
        assert sizer.calculate() == 0.0

    def test_only_pending_trades_returns_zero(self, empty_conn: sqlite3.Connection):
        """Trades sin resultado (PENDING) no cuentan → 0.0."""
        for _ in range(MIN_TRADES + 5):
            empty_conn.execute(
                """INSERT INTO candidates
                   (scanned_at, asset, direction, payout, decision, outcome)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("2024-06-01T00:00:00", "EURUSD_otc", "call", 85, "ACCEPTED", "PENDING"),
            )
        empty_conn.commit()
        sizer = make_sizer(empty_conn)
        assert sizer.calculate() == 0.0


class TestEdgeCases:
    """R4, R7 — Casos extremos y límites."""

    def test_kelly_negative_returns_zero(self, empty_conn: sqlite3.Connection):
        """Win rate que da Kelly negativo → 0.0.
        Con payout 85%, Kelly negativo cuando p < 1/1.85 ≈ 0.5405.
        50% WR debe dar negativo.
        """
        _seed_trades(empty_conn, wins=10, losses=10, payout=85)
        sizer = make_sizer(empty_conn)
        factor = sizer.calculate()
        assert factor == 0.0

    def test_null_payout_returns_zero(self, empty_conn: sqlite3.Connection):
        """Payout NULL en BD → 0.0."""
        for _ in range(12):
            empty_conn.execute(
                """INSERT INTO candidates
                   (scanned_at, asset, direction, payout, decision, outcome, profit)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("2024-06-01T00:00:00", "EURUSD_otc", "call", None, "ACCEPTED", "WIN", 0.85),
            )
        for _ in range(8):
            empty_conn.execute(
                """INSERT INTO candidates
                   (scanned_at, asset, direction, payout, decision, outcome, profit)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("2024-06-01T00:00:00", "EURUSD_otc", "put", None, "ACCEPTED", "LOSS", -1.0),
            )
        empty_conn.commit()
        sizer = make_sizer(empty_conn)
        assert sizer.calculate() == 0.0

    def test_db_does_not_exist(self):
        """BD inexistente → 0.0 sin excepción."""
        fake_path = Path("/nonexistent/trade_journal-2024-01-01.db")
        sizer = KellySizer(db_path=fake_path)
        assert sizer.calculate() == 0.0

    def test_missing_table_returns_zero(self, empty_conn: sqlite3.Connection):
        """Tabla candidates no existe → 0.0 sin excepción."""
        empty_conn.execute("DROP TABLE candidates")
        empty_conn.commit()
        sizer = make_sizer(empty_conn)
        assert sizer.calculate() == 0.0
