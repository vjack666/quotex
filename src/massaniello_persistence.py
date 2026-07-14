"""Persistencia de sesión Massaniello en SQLite."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from trade_journal import Journal, get_journal

if TYPE_CHECKING:
    from massaniello_risk import MassanielloRiskManager

log = logging.getLogger(__name__)

_TZ = timezone.utc


class MassanielloPersistence:
    """Guarda y recupera el estado de MassanielloRiskManager en SQLite."""

    def __init__(self, journal: Optional[Journal] = None) -> None:
        self._journal = journal or get_journal()

    # ── Save ──────────────────────────────────────────────────────────────────

    def save(self, manager: MassanielloRiskManager) -> int:
        """INSERT del estado actual de *manager* en massaniello_state.

        Devuelve el row_id de la fila insertada.
        """
        now = datetime.now(tz=_TZ).isoformat(timespec="seconds")
        session_active = 1 if manager.can_enter() else 0
        cur = self._journal.conn.execute(
            """INSERT INTO massaniello_state (
                saved_at, operations, expected_wins, session_max_min,
                session_start_time, entries, wins, losses,
                current_balance, initial_capital, session_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                now,
                int(manager.operations),
                int(manager.expected_wins),
                int(manager.session_max_min),
                manager.session_start_time,
                int(manager.entries),
                int(manager.wins),
                int(manager.losses),
                manager.current_balance,
                manager._initial_capital,
                session_active,
            ),
        )
        self._journal.conn.commit()
        row_id = int(cur.lastrowid or 0)
        log.debug("Massaniello state saved (id=%d, session_active=%d)", row_id, session_active)
        return row_id

    # ── Load ──────────────────────────────────────────────────────────────────

    def load(self) -> Optional[dict]:
        """SELECT de la última fila de massaniello_state.

        Retorna dict con la fila si existe, None si no hay datos.
        En caso de corrupción o error, loggea warning y retorna None.
        """
        try:
            row = self._journal.conn.execute(
                "SELECT * FROM massaniello_state ORDER BY id DESC LIMIT 1"
            ).fetchone()
        except Exception as exc:
            log.warning("No se pudo leer estado Massaniello previo: %s", exc)
            return None

        if row is None:
            return None

        return dict(row)

    # ── Apply ─────────────────────────────────────────────────────────────────

    def apply(self, manager: MassanielloRiskManager, state: dict) -> None:
        """Restaura campos de *manager* desde *state*.

        No modifica si el estado es inválido (valores negativos, tipos incorrectos).
        Si la sesión previa ya estaba completa/fallida, NO restaura contadores —
        solo recupera el balance para que la nueva sesión empiece limpia.
        """
        validated = self._validate_state(state)
        if validated is None:
            log.warning("Estado Massaniello inválido — arrancando con defaults")
            return

        # Si la sesión previa ya estaba completa/fallida/agotada → NO restaurar
        # contadores. Solo recuperamos el balance y dejamos el manager en defaults.
        if validated.get("session_active", 1) == 0:
            log.info("Sesión Massaniello previa estaba completa — arrancando nueva sesión limpia")
            if validated.get("current_balance") is not None:
                manager.current_balance = validated["current_balance"]
                manager._initial_capital = validated.get("initial_capital") or validated["current_balance"]
            # wins, losses, entries, session_start_time quedan en 0/None (defaults del __init__)
            log.info("  → Contadores en cero (nueva sesión), balance recuperado: %s", manager.current_balance)
            return

        # Sesión activa → restaurar todo normal
        manager.operations = validated["operations"]
        manager.expected_wins = validated["expected_wins"]
        manager.session_max_min = validated["session_max_min"]
        manager.session_start_time = validated.get("session_start_time")
        manager.entries = validated["entries"]
        manager.wins = validated["wins"]
        manager.losses = validated["losses"]
        manager.current_balance = validated.get("current_balance")
        manager._initial_capital = validated.get("initial_capital")

        log.info(
            "Estado Massaniello restaurado: %dW/%dL  ops=%d/%d  balance=%s",
            manager.wins,
            manager.losses,
            manager.wins + manager.losses,
            manager.operations,
            manager.current_balance,
        )

    # ── Validación interna ────────────────────────────────────────────────────

    @staticmethod
    def _validate_state(state: dict) -> Optional[dict]:
        """Valida tipos y rangos básicos. Retorna state limpio o None."""
        try:
            ops = int(state.get("operations", 0))
            ew = int(state.get("expected_wins", 0))
            smm = int(state.get("session_max_min", 0))
            entries = int(state.get("entries", 0))
            wins = int(state.get("wins", 0))
            losses = int(state.get("losses", 0))
        except (ValueError, TypeError):
            return None

        if ops <= 0 or ew <= 0 or smm <= 0:
            return None
        if wins < 0 or losses < 0 or entries < 0:
            return None

        sst = state.get("session_start_time")
        if sst is not None:
            try:
                sst = float(sst)
            except (ValueError, TypeError):
                sst = None

        cb = state.get("current_balance")
        if cb is not None:
            try:
                cb = float(cb)
            except (ValueError, TypeError):
                cb = None

        ic = state.get("initial_capital")
        if ic is not None:
            try:
                ic = float(ic)
            except (ValueError, TypeError):
                ic = None

        session_active = int(state.get("session_active", 1))

        return {
            "operations": ops,
            "expected_wins": ew,
            "session_max_min": smm,
            "session_start_time": sst,
            "entries": entries,
            "wins": wins,
            "losses": losses,
            "current_balance": cb,
            "initial_capital": ic,
            "session_active": session_active,
        }
