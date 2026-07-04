"""Tests de persistencia Massaniello — R6."""
from __future__ import annotations

import sys
import sqlite3
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from massaniello_persistence import MassanielloPersistence
from massaniello_risk import MassanielloRiskManager
from trade_journal import Journal


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def journal() -> Journal:
    """Journal en memoria — sin efectos laterales en BD real."""
    j = Journal(db_path=Path(":memory:"))
    yield j
    j.close()


@pytest.fixture
def persistence(journal: Journal) -> MassanielloPersistence:
    return MassanielloPersistence(journal)


@pytest.fixture
def manager() -> MassanielloRiskManager:
    mgr = MassanielloRiskManager(operations=5, expected_wins=3, session_max_min=60)
    mgr.set_balance(100.0)
    return mgr


@pytest.fixture
def manager_no_balance() -> MassanielloRiskManager:
    return MassanielloRiskManager(operations=5, expected_wins=3, session_max_min=60)


# ── Tests ────────────────────────────────────────────────────────────────────


class TestSave:
    """R1 + R5 — Guardado exitoso."""

    def test_save_inserts_row(self, persistence: MassanielloPersistence, journal: Journal, manager: MassanielloRiskManager):
        manager.register_win(1.0, 92)
        row_id = persistence.save(manager)
        assert row_id > 0

        row = journal.conn.execute(
            "SELECT * FROM massaniello_state WHERE id = ?", (row_id,)
        ).fetchone()
        assert row is not None
        assert row["operations"] == 5
        assert row["expected_wins"] == 3
        assert row["session_max_min"] == 60
        assert row["entries"] == 1
        assert row["wins"] == 1
        assert row["losses"] == 0
        assert row["current_balance"] is not None
        assert row["initial_capital"] is not None
        assert row["session_active"] == 1

    def test_save_multiple_rows(self, persistence: MassanielloPersistence, manager: MassanielloRiskManager):
        row1 = persistence.save(manager)
        manager.register_win(1.0, 92)
        row2 = persistence.save(manager)
        assert row2 > row1

    def test_save_after_session_complete(self, persistence: MassanielloPersistence, manager: MassanielloRiskManager):
        for _ in range(3):
            manager.register_win(1.0, 92)
        row_id = persistence.save(manager)
        row = persistence._journal.conn.execute(
            "SELECT session_active FROM massaniello_state WHERE id = ?", (row_id,)
        ).fetchone()
        assert row is not None
        assert row["session_active"] == 0


class TestLoad:
    """R2 — Recuperación exitosa."""

    def test_load_returns_last_state(self, persistence: MassanielloPersistence, manager: MassanielloRiskManager):
        persistence.save(manager)
        manager.register_win(1.0, 92)
        persistence.save(manager)

        state = persistence.load()
        assert state is not None
        assert state["wins"] == 1
        assert state["entries"] == 1
        assert state["operations"] == 5

    def test_load_returns_none_when_no_data(self, persistence: MassanielloPersistence):
        assert persistence.load() is None

    def test_load_includes_all_required_fields(self, persistence: MassanielloPersistence, manager: MassanielloRiskManager):
        manager.register_win(1.0, 92)
        persistence.save(manager)
        state = persistence.load()
        assert state is not None
        for key in ("operations", "expected_wins", "session_max_min",
                    "session_start_time", "entries", "wins", "losses",
                    "current_balance", "initial_capital"):
            assert key in state, f"Campo {key} faltante en estado guardado"


class TestApply:
    """R3 + R4 — Restauración y validación."""

    def test_apply_restores_fields(self, persistence: MassanielloPersistence, manager: MassanielloRiskManager):
        manager.register_win(2.0, 90)
        manager.register_loss(1.0)
        persistence.save(manager)

        state = persistence.load()
        fresh = MassanielloRiskManager()
        persistence.apply(fresh, state)

        assert fresh.operations == 5
        assert fresh.expected_wins == 3
        assert fresh.wins == 1
        assert fresh.losses == 1
        assert fresh.entries == 2
        assert fresh._initial_capital == 100.0
        assert fresh.current_balance is not None

    def test_apply_invalid_state_does_not_modify(self, persistence: MassanielloPersistence, manager_no_balance: MassanielloRiskManager):
        mgr = manager_no_balance
        original_ops = mgr.operations

        invalid = {"operations": -5, "expected_wins": 3, "session_max_min": 60}
        persistence.apply(mgr, invalid)

        assert mgr.operations == original_ops

    def test_apply_negative_values_rejected(self, persistence: MassanielloPersistence, manager_no_balance: MassanielloRiskManager):
        mgr = manager_no_balance
        original_ops = mgr.operations

        bad = {"operations": 5, "expected_wins": 3, "session_max_min": 60, "wins": -1}
        persistence.apply(mgr, bad)

        assert mgr.operations == original_ops

    def test_apply_bad_types_rejected(self, persistence: MassanielloPersistence, manager_no_balance: MassanielloRiskManager):
        mgr = manager_no_balance
        original_ops = mgr.operations

        bad = {"operations": "not_a_number", "expected_wins": 3, "session_max_min": 60}
        persistence.apply(mgr, bad)

        assert mgr.operations == original_ops


class TestCorruption:
    """R4 — Datos corruptos o inválidos."""

    def test_load_corrupt_table_returns_none(self, persistence: MassanielloPersistence, journal: Journal):
        """Corrupción a nivel BD — load() no debe lanzar excepción."""
        journal.conn.execute("DROP TABLE IF EXISTS massaniello_state")
        journal.conn.commit()

        state = persistence.load()
        assert state is None

    def test_load_invalid_rows_still_returned(self, persistence: MassanielloPersistence, journal: Journal):
        """Filas con valores fuera de rango: load() devuelve el dict, apply() lo valida."""
        journal.conn.execute(
            """INSERT INTO massaniello_state
               (saved_at, operations, expected_wins, session_max_min, entries, wins, losses, session_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("2024-06-01T00:00:00", -1, 3, 60, 0, 0, 0, 1),
        )
        journal.conn.commit()

        state = persistence.load()
        assert state is not None
        assert state["operations"] == -1

        mgr = MassanielloRiskManager()
        persistence.apply(mgr, state)
        # Apply should have rejected the negative value
        assert mgr.operations == 5

    def test_load_empty_table_returns_none(self, persistence: MassanielloPersistence, journal: Journal):
        """Tabla existe pero vacía."""
        journal.conn.execute("DELETE FROM massaniello_state")
        journal.conn.commit()
        assert persistence.load() is None
