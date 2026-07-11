"""Backtester — offline strategy replay engine.

Re-evaluates historical signals from trade_journal.db using the same
strategy functions that generated them. Produces comparison and
performance reports without any broker connection.
"""
from __future__ import annotations

import itertools
import json
import logging
import sqlite3
import statistics
import time
from datetime import datetime, timedelta, timezone
from math import sqrt
from pathlib import Path
from typing import Any, Optional

from models import Candle
from trade_journal import _DB_DIR

log = logging.getLogger("consolidation_bot")

# ── Strategy function map ─────────────────────────────────────────────────────
# Simple strategies: take only candles as input, return (direction, strength) or None.

from strat_momentum import detect_momentum_1m
from strat_reversal_swing import detect_reversal_swing
from strat_order_block import detect_order_block_entry

STRATEGY_MAP: dict[str, Any] = {
    "STRAT-MOMENTUM": detect_momentum_1m,
    "STRAT-REVERSAL-SWING": detect_reversal_swing,
    "STRAT-ORDER-BLOCK": detect_order_block_entry,
    # STRAT-A is handled separately (needs more params).
}


class Backtester:
    """Offline backtesting engine that replays strategies on historical data.

    Usage::

        bt = Backtester()
        bt.load_from_db(days=30)
        bt.reevaluate()
        print(bt.compare())
        print(bt.report())
    """

    # ──────────────────────────────────────────────────────────────────────────
    #  Init
    # ──────────────────────────────────────────────────────────────────────────

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = _DB_DIR / f"trade_journal-{datetime.now().strftime('%Y-%m-%d')}.db"
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self.candidates: list[dict[str, Any]] = []

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazily-opened SQLite connection (read-only for backtesting)."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __del__(self) -> None:
        self.close()

    # ──────────────────────────────────────────────────────────────────────────
    #  Load from DB  (R1)
    # ──────────────────────────────────────────────────────────────────────────

    def load_from_db(self, days: int = 30) -> list[dict[str, Any]]:
        """Load candidates from ``candidates`` table within the given day range.

        Filters for entries that have ``candles_json`` and a known
        ``strategy_origin`` so they can be re-evaluated.

        Returns the candidate list and stores it internally in ``self.candidates``.
        """
        since = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
        origins = (
            "STRAT-MOMENTUM",
            "STRAT-REVERSAL-SWING",
            "STRAT-ORDER-BLOCK",
            "STRAT-A",
            "STRAT-F",
        )
        rows = self.conn.execute(
            f"""SELECT *
                 FROM candidates
                WHERE scanned_at >= ?
                  AND candles_json IS NOT NULL
                  AND strategy_origin IN ({", ".join("?" for _ in origins)})
                ORDER BY scanned_at""",
            (since, *origins),
        ).fetchall()

        self.candidates = []
        for r in rows:
            candles_data = json.loads(r["candles_json"])
            candles = [
                Candle(
                    ts=c["ts"],
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                )
                for c in candles_data
            ]
            self.candidates.append({
                "id": r["id"],
                "scanned_at": r["scanned_at"],
                "asset": r["asset"],
                "direction": r["direction"],
                "payout": r["payout"],
                "score": r["score"],
                "outcome": r["outcome"],
                "profit": r["profit"],
                "strategy_origin": r["strategy_origin"],
                "candles_json": r["candles_json"],
                "strategy_json": r["strategy_json"],
                "candles": candles,
                "reevaluated_signal": None,    # direction from reevaluate
                "reevaluated_strength": 0.0,   # strength from reevaluate
            })

        return self.candidates

    # ──────────────────────────────────────────────────────────────────────────
    #  Re-evaluate  (R2, R5)
    # ──────────────────────────────────────────────────────────────────────────

    def reevaluate(self, strategies: Optional[list[str]] = None) -> None:
        """Replay strategies on every loaded candidate.

        If *strategies* is given (list of origin names), only re-evaluate
        candidates whose ``strategy_origin`` matches one of them.

        Stores the result in each candidate's ``reevaluated_signal``.
        """
        for c in self.candidates:
            origin = c["strategy_origin"]
            if strategies and origin not in strategies:
                continue

            if origin == "STRAT-A":
                self._reevaluate_strat_a(c)
            elif origin == "STRAT-F":
                self._reevaluate_strat_f(c)
            elif origin in STRATEGY_MAP:
                fn = STRATEGY_MAP[origin]
                try:
                    result = fn(c["candles"])
                    if result is not None:
                        c["reevaluated_signal"] = result[0]
                        if len(result) > 1:
                            c["reevaluated_strength"] = float(result[1])
                except Exception as exc:
                    log.warning(
                        "Backtester: %s failed for candidate %d: %s",
                        origin, c["id"], exc,
                    )
            else:
                log.warning("Backtester: unknown strategy_origin '%s'", origin)

    # ── STRAT-F: reconocido por origen para reporte diferenciado ──────────

    def _reevaluate_strat_f(self, c: dict[str, Any]) -> None:
        """Marca un candidato STRAT-F como re-evaluado.

        STRAT-F necesita 3 temporalidades (15m/5m/1m) que no se guardan en el
        journal, así que no se re-simula desde velas: se usa el outcome real ya
        registrado en ``trade_journal.db`` (profit del trade) y se cuenta para
        el reporte diferenciado por origen (R7/R8).
        """
        try:
            strategy = json.loads(c["strategy_json"]) if c.get("strategy_json") else {}
        except (json.JSONDecodeError, TypeError):
            strategy = {}
        c["reevaluated_signal"] = strategy.get("direction", "unknown")
        c["reevaluated_strength"] = float(strategy.get("strength", 0.0))

    # ── STRAT-A: needs zone reconstruction from strategy_json ────────────

    def _reevaluate_strat_a(self, c: dict[str, Any]) -> None:
        """Re-evaluate a STRAT-A candidate.

        Attempts to reconstruct ``ConsolidationZone`` from ``strategy_json``
        and call ``evaluate_strat_a``. If the JSON is missing/incomplete the
        candidate is skipped with a warning.
        """
        from strat_a import ConsolidationZone, evaluate_strat_a  # noqa: PLC0415

        try:
            strategy = (
                json.loads(c["strategy_json"])
                if c.get("strategy_json")
                else {}
            )
        except (json.JSONDecodeError, TypeError):
            log.warning(
                "STRAT-A candidate %d: invalid strategy_json, skipping", c["id"],
            )
            return

        zone_data = strategy.get("zone") or strategy.get("pattern_snapshot", {})
        ceiling = zone_data.get("ceiling")
        floor = zone_data.get("floor")
        if ceiling is None or floor is None:
            log.warning(
                "STRAT-A candidate %d: missing zone (ceiling/floor) in "
                "strategy_json, skipping",
                c["id"],
            )
            return

        zone = ConsolidationZone(
            asset=c["asset"],
            ceiling=float(ceiling),
            floor=float(floor),
            bars_inside=int(zone_data.get("bars_inside", 0)),
            detected_at=float(zone_data.get("detected_at", time.time())),
            range_pct=float(zone_data.get("range_pct", 0)),
        )

        try:
            result = evaluate_strat_a(
                candles_5m=c["candles"],
                candles_1m=c["candles"],
                zone=zone,
                blocks={"bull": [], "bear": []},
                ma_state=None,
            )
            if result.has_signal and result.direction:
                c["reevaluated_signal"] = result.direction
                c["reevaluated_strength"] = float(result.strength)
        except Exception as exc:
            log.warning(
                "STRAT-A candidate %d: evaluate_strat_a raised %s",
                c["id"], exc,
            )

    # ──────────────────────────────────────────────────────────────────────────
    #  Compare  (R5)
    # ──────────────────────────────────────────────────────────────────────────

    def compare(self) -> dict[str, int]:
        """Compare historical decision vs reevaluated signal.

        Returns a dict with keys: ``total``, ``matches``, ``mismatches``,
        ``no_signal_now``.
        """
        total = len(self.candidates)
        matches = 0
        mismatches = 0
        no_signal = 0

        for c in self.candidates:
            orig = c["direction"]
            new = c["reevaluated_signal"]
            if new is None:
                no_signal += 1
            elif orig == new:
                matches += 1
            else:
                mismatches += 1

        return {
            "total": total,
            "matches": matches,
            "mismatches": mismatches,
            "no_signal_now": no_signal,
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  Report  (R3)
    # ──────────────────────────────────────────────────────────────────────────

    def report(self) -> str:
        """Generate a performance metrics report.

        Only considers candidates with ``outcome IN ('WIN', 'LOSS')``.

        Calculates:
            - Win rate: wins / (wins + losses)
            - Total profit: sum of all profits
            - Max drawdown: maximum peak-to-trough decline
            - Sharpe ratio: mean(returns) / std(returns) * sqrt(periods_per_year)
              with risk-free rate = 0 and expiry_minutes = 1.
        """
        resolved = [
            c for c in self.candidates
            if c["outcome"] in ("WIN", "LOSS")
        ]
        if not resolved:
            return "No resolved trades to report."

        wins = sum(1 for c in resolved if c["outcome"] == "WIN")
        losses = sum(1 for c in resolved if c["outcome"] == "LOSS")
        total = wins + losses
        win_rate = wins / total if total > 0 else 0.0

        profits = [c["profit"] for c in resolved]
        total_profit = sum(profits)

        # Max drawdown (peak-to-trough)
        cumulative = list(itertools.accumulate(profits))
        peak = cumulative[0]
        max_dd = 0.0
        for val in cumulative:
            if val > peak:
                peak = val
            if peak != 0:
                dd = (val - peak) / peak
                max_dd = min(max_dd, dd)
            # if peak == 0, drawdown is undefined for that step; skip

        # Sharpe ratio (annualized, risk-free rate = 0, 1m trades)
        if total > 1:
            mean_r = statistics.mean(profits)
            std_r = statistics.stdev(profits)
        else:
            mean_r = profits[0] if profits else 0.0
            std_r = 1.0  # avoid division by zero

        if std_r > 0:
            # 1 trade per minute, ~1440 min/day, ~252 trading days/year
            periods_per_year = 252 * 1440
            sharpe = (mean_r / std_r) * sqrt(periods_per_year)
        else:
            sharpe = 0.0

        lines = [
            "═══ Backtest Report ═══",
            f"Total trades     : {total}",
            f"Wins             : {wins}",
            f"Losses           : {losses}",
            f"Win rate         : {win_rate:.2%}",
            f"Total profit     : ${total_profit:.2f}",
            f"Max drawdown     : {max_dd:.2%}",
            f"Sharpe ratio     : {sharpe:.4f}",
            "═══════════════════════",
        ]
        return "\n".join(lines)
