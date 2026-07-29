"""Cálculo de Kelly Criterion para sizing conservador del capital."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from trade_journal import _DB_DIR
from config import (
    KELLY_FRACTION,
    KELLY_MIN_TRADES,
    KELLY_ROLLING_WINDOW,
    KELLY_MIN_STAKE,
    KELLY_MAX_STAKE_PCT,
)

log = logging.getLogger("consolidation_bot")

# ── Constantes ────────────────────────────────────────────────────────────────

DEFAULT_FRACTIONAL = 0.25  # 25 % del Kelly completo (legacy)
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

    Versión mejorada con win rate rolling, cálculo de edge, fracción
    dinámica basada en edge, ajuste por confianza ML y stake con
    límites min/max.
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

    def _rolling_win_rate(
        self, window: int = KELLY_ROLLING_WINDOW, strategy: str | None = None,
    ) -> tuple[float, int]:
        """Win rate from last N trades. If strategy specified, filter by strategy_origin."""
        try:
            _ = self.conn
        except FileNotFoundError:
            return 0.0, 0

        try:
            if strategy is not None:
                rows = self.conn.execute(
                    """SELECT outcome FROM (
                        SELECT outcome FROM candidates
                        WHERE decision = 'ACCEPTED'
                          AND outcome IN ('WIN', 'LOSS')
                          AND strategy_origin = ?
                        ORDER BY id DESC LIMIT ?
                    )""",
                    (strategy, window),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    """SELECT outcome FROM (
                        SELECT outcome FROM candidates
                        WHERE decision = 'ACCEPTED'
                          AND outcome IN ('WIN', 'LOSS')
                        ORDER BY id DESC LIMIT ?
                    )""",
                    (window,),
                ).fetchall()
        except sqlite3.OperationalError as exc:
            log.warning("[KellySizer] Error consultando rolling win rate: %s", exc)
            return 0.0, 0

        total = len(rows)
        if total < KELLY_MIN_TRADES:
            return 0.0, total

        wins = sum(1 for r in rows if r["outcome"] == "WIN")
        return wins / total, total

    # ── Enhanced Kelly methods ────────────────────────────────────────────

    @staticmethod
    def _edge(win_rate: float, payout_ratio: float) -> float:
        """Edge = win_rate * payout_ratio - (1 - win_rate)"""
        return win_rate * payout_ratio - (1.0 - win_rate)

    @staticmethod
    def _dynamic_fraction(edge: float) -> float:
        """Map edge to fraction: >0.2→0.5, 0.1-0.2→0.3, 0-0.1→0.1, ≤0→0.0"""
        if edge > 0.2:
            return 0.5
        elif edge > 0.1:
            return 0.3
        elif edge > 0.0:
            return 0.1
        else:
            return 0.0

    @staticmethod
    def _confidence_adjust(fraction: float, confidence: float | None) -> float:
        """Adjust fraction by ML confidence: >0.7→×1.2, 0.4-0.7→×1.0, <0.4→×0.5, None→×1.0"""
        if confidence is None:
            return fraction
        if confidence > 0.7:
            return fraction * 1.2
        elif confidence >= 0.4:
            return fraction * 1.0
        else:
            return fraction * 0.5

    def _calculate_stake(self, balance: float, fraction: float) -> float:
        """Calculate stake with KELLY_MIN_STAKE and KELLY_MAX_STAKE_PCT limits."""
        if balance <= 0.0:
            return 0.0
        stake = balance * fraction
        stake = max(KELLY_MIN_STAKE, min(stake, balance * KELLY_MAX_STAKE_PCT))
        return round(min(stake, balance), 2)

    # ── Cálculo principal ─────────────────────────────────────────────────

    def calculate(
        self,
        fractional: float = KELLY_FRACTION,
        strategy: str | None = None,
        confidence: float | None = None,
        balance: float = 0.0,
    ) -> dict:
        """Calcula el factor de Kelly fraccional mejorado.

        Args:
            fractional: Fracción del Kelly completo (legacy, la fracción
                dinámica basada en edge reemplaza este valor por defecto).
            strategy: Filtrar por strategy_origin (None = todas).
            confidence: Confianza ML (0-1 o None).
            balance: Balance de cuenta para calcular stake.

        Returns:
            Dict con fraction, stake, edge, win_rate, payout_ratio,
            total_trades, strategy, confidence, reason.
        """
        win_rate, total_trades = self._rolling_win_rate(strategy=strategy)

        if total_trades < KELLY_MIN_TRADES or win_rate <= 0.0:
            log.debug(
                "[KellySizer] Datos insuficientes (%d trades, WR=%.2f%%)",
                total_trades,
                win_rate * 100,
            )
            return {
                "fraction": 0.0,
                "stake": 0.0,
                "edge": 0.0,
                "win_rate": win_rate,
                "payout_ratio": 0.0,
                "total_trades": total_trades,
                "strategy": strategy,
                "confidence": confidence,
                "reason": f"Insufficient data: {total_trades} trades (min {KELLY_MIN_TRADES})",
            }

        payout_ratio = self._get_avg_payout()
        if payout_ratio <= 0.0:
            log.debug(
                "[KellySizer] Payout inválido (%f) — devolviendo 0.0",
                payout_ratio,
            )
            return {
                "fraction": 0.0,
                "stake": 0.0,
                "edge": 0.0,
                "win_rate": win_rate,
                "payout_ratio": payout_ratio,
                "total_trades": total_trades,
                "strategy": strategy,
                "confidence": confidence,
                "reason": f"Invalid payout: {payout_ratio}",
            }

        # Full Kelly
        full_kelly = (win_rate * (payout_ratio + 1.0) - 1.0) / payout_ratio
        full_kelly = max(MIN_KELLY, min(MAX_KELLY, full_kelly))

        # Edge-based dynamic fraction
        edge_val = self._edge(win_rate, payout_ratio)
        dyn_frac = self._dynamic_fraction(edge_val)

        # Fractional Kelly with dynamic fraction
        fractional_kelly = full_kelly * dyn_frac

        # ML confidence adjustment
        fraction = self._confidence_adjust(fractional_kelly, confidence)
        fraction = max(MIN_KELLY, min(MAX_KELLY, fraction))

        # Stake calculation
        stake = self._calculate_stake(balance, fraction)

        log.info(
            "[KELLY] WR=%.1f%% payout=%.0f%% edge=%.3f → fraction=%.4f stake=$%.2f",
            win_rate * 100,
            payout_ratio * 100,
            edge_val,
            fraction,
            stake,
        )

        reason = (
            f"WR={win_rate * 100:.1f}% payout={payout_ratio * 100:.0f}% "
            f"edge={edge_val:.3f} dyn_frac={dyn_frac} "
            f"full_kelly={full_kelly:.4f}"
        )

        return {
            "fraction": fraction,
            "stake": stake,
            "edge": edge_val,
            "win_rate": win_rate,
            "payout_ratio": payout_ratio,
            "total_trades": total_trades,
            "strategy": strategy,
            "confidence": confidence,
            "reason": reason,
        }
