"""Cálculo de Kelly Criterion para sizing conservador del capital."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from trade_journal import _DB_DIR

log = logging.getLogger("consolidation_bot")

# ── Constantes ────────────────────────────────────────────────────────────────

DEFAULT_FRACTIONAL = 0.25  # 25 % del Kelly completo
MIN_TRADES = 10            # mínimo de trades para significancia estadística
MAX_KELLY = 1.0
MIN_KELLY = 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  KellySizer
# ─────────────────────────────────────────────────────────────────────────────


class KellySizer:
    """Calcula el factor de Kelly fraccional desde datos históricos.

    Fórmula completa::

        f* = (p * (b + 1) - 1) / b

    donde:
        p = win rate histórico (0.0 - 1.0)
        b = payout ratio promedio (ej. 0.85 para 85 %)

    El resultado final aplica una fracción configurable (default 25 %)
    y se acota a [0.0, 1.0].
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self._resolve_latest_db()
        self._conn: Optional[sqlite3.Connection] = None

    # ── Helpers internos ──────────────────────────────────────────────────

    @staticmethod
    def _resolve_latest_db() -> Optional[Path]:
        """Busca el archivo trade_journal-*.db más reciente."""
        if not _DB_DIR.exists():
            return None
        candidates = sorted(
            _DB_DIR.glob("trade_journal-*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            if not self.db_path or not self.db_path.exists():
                raise FileNotFoundError(
                    f"No se encontró BD del trade journal: {self.db_path}"
                )
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Cierra la conexión a la BD si está abierta."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ── Consultas a la BD ─────────────────────────────────────────────────

    def _get_win_rate(self) -> tuple[float, int]:
        """Retorna (win_rate, total_trades) desde la tabla candidates.

        Filtra por decision='ACCEPTED' y outcome WIN/LOSS.
        Si hay menos de MIN_TRADES, retorna (0.0, total).
        """
        try:
            _ = self.conn  # may raise FileNotFoundError
        except FileNotFoundError:
            return 0.0, 0
        try:
            row = self.conn.execute(
                """SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) AS wins
                   FROM candidates
                   WHERE decision = 'ACCEPTED'
                     AND outcome IN ('WIN', 'LOSS')"""
            ).fetchone()
        except sqlite3.OperationalError as exc:
            log.warning("[KellySizer] Error consultando win rate: %s", exc)
            return 0.0, 0

        total = int(row["total"] or 0)
        wins = int(row["wins"] or 0)

        if total < MIN_TRADES:
            return 0.0, total

        return wins / total, total

    def _get_avg_payout(self) -> float:
        """Retorna payout promedio como ratio (85 % → 0.85)."""
        try:
            row = self.conn.execute(
                """SELECT AVG(payout) AS avg_payout
                   FROM candidates
                   WHERE decision = 'ACCEPTED'
                     AND outcome IN ('WIN', 'LOSS')
                     AND payout IS NOT NULL"""
            ).fetchone()
        except sqlite3.OperationalError as exc:
            log.warning("[KellySizer] Error consultando payout: %s", exc)
            return 0.0

        raw = row["avg_payout"]
        if raw is None:
            return 0.0
        return float(raw) / 100.0

    # ── Cálculo principal ─────────────────────────────────────────────────

    def calculate(
        self,
        fractional: float = DEFAULT_FRACTIONAL,
    ) -> float:
        """Calcula el factor de Kelly fraccional.

        Args:
            fractional: Fracción del Kelly completo a aplicar (default 0.25).

        Returns:
            Factor entre 0.0 y 1.0. 0.0 significa "no ajustar".
        """
        win_rate, total_trades = self._get_win_rate()

        if total_trades < MIN_TRADES or win_rate <= 0.0:
            log.debug(
                "[KellySizer] Datos insuficientes (%d trades, WR=%.2f%%) "
                "— devolviendo 0.0",
                total_trades,
                win_rate * 100,
            )
            return 0.0

        payout_ratio = self._get_avg_payout()
        if payout_ratio <= 0.0:
            log.debug(
                "[KellySizer] Payout inválido (%f) — devolviendo 0.0",
                payout_ratio,
            )
            return 0.0

        # Kelly completo
        full_kelly = (win_rate * (payout_ratio + 1.0) - 1.0) / payout_ratio
        full_kelly = max(MIN_KELLY, min(MAX_KELLY, full_kelly))

        # Fracción del Kelly conservador
        fractional_kelly = full_kelly * fractional
        result = max(MIN_KELLY, min(MAX_KELLY, fractional_kelly))

        log.info(
            "[KellySizer] WR=%.2f%%  Payout=%.1f%%  f*=%.4f  "
            "frac=%.4f  → factor=%.4f  (trades=%d)",
            win_rate * 100,
            payout_ratio * 100,
            full_kelly,
            fractional,
            result,
            total_trades,
        )
        return result
