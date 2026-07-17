"""Ejecución de órdenes, martingala y gestión de ciclo."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timedelta
from math import ceil
from typing import TYPE_CHECKING, Any, Deque, List, Optional, Tuple

from alerter import alerter
import config as _cfg
from config import (
    ADAPTIVE_THRESHOLD_BASE,
    ADAPTIVE_THRESHOLD_HIGH,
    ADAPTIVE_THRESHOLD_LOW,
    ADAPTIVE_THRESHOLD_WINDOW_SCANS,
    ASSET_BLACKLIST_DURATION_MIN,
    ASSET_LOSS_STREAK_LIMIT,
    BROKER_TZ,
    CANDLE_FETCH_1M_TIMEOUT_SEC,
    CYCLE_MAX_OPERATIONS,
    CYCLE_TARGET_PROFIT_PCT,
    CYCLE_TARGET_WINS,
    ENTRY_MAX_LAG_SEC,
    ENTRY_REJECT_LAST_SEC,
    ENTRY_SYNC_TO_CANDLE,
    MARTIN_ALERT_PCT,
    MARTIN_LIVE_WINDOW_MAX_SEC,
    MARTIN_LIVE_WINDOW_MIN_SEC,
    MARTIN_LOW_BALANCE_THRESHOLD,
    MARTIN_MAX_ATTEMPTS_LOW_BALANCE,
    MARTIN_MAX_ATTEMPTS_SESSION,
    MARTIN_MAX_PCT_BALANCE,
    MARTIN_MONITOR_INTERVAL_SEC,
    MARTIN_RESOLVE_GRACE_SEC,
    MARTIN_RESOLVE_MAX_ATTEMPTS,
    MARTIN_RESOLVE_RETRY_SEC,
    MARTIN_RESOLVE_TIMEOUT_SEC,
    MAX_CONCURRENT_TRADES,
    MAX_CONSECUTIVE_ENTRIES_PER_ASSET,
    MAX_LOSS_SESSION,
    MIN_ORDER_AMOUNT,
    MIN_PAYOUT,
    ORDER_FAIL_QUARANTINE_CYCLES,
    PENDING_RECONCILE_AGE_MIN,
    RISK_MANAGER,
    TF_5M,
    CANDLES_LOOKBACK,
    MIN_CONSOLIDATION_BARS,
    MAX_RANGE_PCT,
    TOUCH_TOLERANCE_PCT,
    MAX_CONSOLIDATION_MIN,
    SCAN_INTERVAL_SEC,
    COOLDOWN_BETWEEN_ENTRIES,
    VOLUME_MULTIPLIER,
    VOLUME_LOOKBACK,
    ZONE_MIN_AGE_MIN,
    ZONE_AGE_REBOUND_MIN,
    ZONE_AGE_BREAKOUT_MIN,
    ALIGN_SCAN_TO_CANDLE,
    SCAN_LEAD_SEC,
    STRICT_PATTERN_CHECK,
    BROKER_TZ_LABEL,
    USE_DYNAMIC_ATR_RANGE,
    ATR_PERIOD,
    ATR_RANGE_FACTOR,
    MIN_DYNAMIC_RANGE_PCT,
    MAX_DYNAMIC_RANGE_PCT,
    H1_CONFIRM_ENABLED,
    MASSANIELLO_VIRTUAL_CAPITAL,
)
from config import EMAIL, PASSWORD


def _live_duration_sec() -> int:
    """Read order duration from the live config module (hub may hot-reload it).

    Never use a frozen ``from config import DURATION_SEC`` binding: hub saves
    duration_min=15 as DURATION_SEC=900 on the module, but import-time names
    stay at the old value (often 300).
    """
    return int(getattr(_cfg, "DURATION_SEC", 300))
from connection import create_trading_client, fetch_candles_with_retry, get_open_assets, place_order
from entry_sync import EntrySynchronizer
from entry_scorer import CandidateEntry
from models import (
    ConsolidationZone,
    EntryTimingInfo,
    MartinPending,
    TradeState,
    make_trade_key,
)
from strat_a import price_at_ceiling, price_at_floor
from trade_journal import get_journal
from black_box_recorder import get_black_box
from stochastic_m15 import compute_stoch
from strat_f_postmortem import analyze_postmortem
from candle_patterns import fetch_candles_1m
from m1_micro_confirm import confirm_m1_micro

if TYPE_CHECKING:
    from pyquotex.stable_api import Quotex

log = logging.getLogger("executor")

class TradeExecutor:
    def __init__(self, client, bot, trade_client=None, htf_scanner=None, session_manager=None):
        self.client = client
        self.bot = bot
        # Cliente de trading LIMPIO (separado del de datos) para buy().
        # Si es None, usa client (fallback compatibilidad).
        self.trade_client = trade_client if trade_client is not None else client
        # Referencia directa al HTF scanner para pausarlo durante la orden.
        self.htf = htf_scanner
        self.entry_sync = EntrySynchronizer()
        # Session manager for lifecycle tracking
        self.session_manager = session_manager

    async def _reconnect_if_needed(self, label: str) -> bool:
        """Restore the shared client socket if it dropped.

        FIX B (skill Pitfall J CORRECTION): the bot runs on ONE Quotex WebSocket
        (self.client) used for scan + HTF + orders via otc_trader.enviar_orden.
        There is no separate trade_client. Background tasks (per-leg resolve,
        monitor) call broker methods on this same socket but, unlike the main
        loop, never re-established it. When Cloudflare drops the idle socket
        mid-wait, those tasks looped on a dead socket and the trade never popped,
        hanging the bot in "En espera de finalizar trade".

        This bridges that gap using the bot's own connection manager — the exact
        path the main loop uses — so reconnection stays serialized by
        _RECONNECT_LOCK (RT-02) and cannot corrupt the session.
        """
        try:
            ensure_fn = getattr(self.bot, "ensure_connection", None)
            if ensure_fn is None:
                return False
            ok = await ensure_fn()
            if ok:
                log.info("🔌 WS reconectado (%s)", label)
            else:
                log.warning("⚠ No se pudo reconectar WS (%s)", label)
            return bool(ok)
        except Exception as exc:
            log.debug("⚠ _reconnect_if_needed(%s) exc: %s", label, exc)
            return False

    @staticmethod
    def _uses_massaniello() -> bool:
        return RISK_MANAGER == "massaniello"

    def _sync_massaniello_session_start(self) -> None:
        if not self._uses_massaniello():
            return
        self.bot.session_start_time = self.bot.massaniello.session_start_time

    def _massaniello_session_blocks_entry(self) -> Tuple[bool, str]:
        if not self._uses_massaniello():
            return False, ""
        mgr = self.bot.massaniello
        if mgr.is_session_complete():
            return True, "sesión Massaniello cumplida (3 ITM)"
        if mgr.is_session_failed():
            return True, "sesión Massaniello fallida"
        if mgr.is_session_timeout():
            return True, f"sesión Massaniello expirada ({mgr.session_max_min} min)"
        if mgr.is_session_exhausted():
            return True, "sesión Massaniello sin operaciones restantes"
        if not mgr.can_enter():
            return True, "sesión Massaniello no admite más entradas"
        return False, ""

    def _build_session_end_summary(self, reason: str) -> dict:
        """Snapshot for hub modal — capture BEFORE resetting Massaniello."""
        mgr = self.bot.massaniello
        st = mgr.session_status() if hasattr(mgr, "session_status") else {}
        wins = int(st.get("wins", getattr(mgr, "wins", 0) or 0))
        losses = int(st.get("losses", getattr(mgr, "losses", 0) or 0))
        entries = int(st.get("entries", getattr(mgr, "entries", 0) or 0))
        trades = entries if entries > 0 else (wins + losses)
        bal = st.get("balance", getattr(mgr, "current_balance", None))
        init = st.get("initial_capital", getattr(mgr, "_initial_capital", None))
        pnl = None
        if bal is not None and init is not None:
            try:
                pnl = float(bal) - float(init)
            except (TypeError, ValueError):
                pnl = None
        wr = (wins / trades * 100.0) if trades > 0 else None
        elapsed = float(st.get("elapsed_min") or 0.0)
        failed = bool(st.get("failed") or mgr.is_session_failed())
        complete = bool(st.get("complete") or mgr.is_session_complete())
        timeout = bool(st.get("timeout") or mgr.is_session_timeout())
        exhausted = bool(st.get("exhausted") or mgr.is_session_exhausted())
        if failed:
            status = "SESSION_FAILED"
        elif timeout:
            status = "SESSION_TIMEOUT"
        elif exhausted:
            status = "SESSION_EXHAUSTED"
        elif complete:
            status = "SESSION_COMPLETE"
        else:
            status = "SESSION_ENDED"
        return {
            "reason": reason,
            "status": status,
            "wins": wins,
            "losses": losses,
            "itm": wins,
            "otm": losses,
            "entries": entries,
            "trades": trades,
            "win_rate": wr,
            "pnl": pnl,
            "balance": bal,
            "initial_capital": init,
            "elapsed_min": elapsed,
            "duration": elapsed,
            "failed": failed,
            "complete": complete,
            "timeout": timeout,
            "exhausted": exhausted,
            "expected_wins": int(st.get("expected_wins", getattr(mgr, "expected_wins", 0) or 0)),
            "operations": int(st.get("operations", getattr(mgr, "operations", 0) or 0)),
        }

    def _auto_continue_enabled(self) -> bool:
        """True when cycle end must roll into a new scan cycle (24/7 data)."""
        return bool(
            getattr(_cfg, "CONTINUOUS_DATA_COLLECTION_MODE", False)
            or getattr(_cfg, "SESSION_AUTO_RESET_ON_COMPLETE", False)
        )

    def _maybe_stop_massaniello_session(self) -> None:
        if not self._uses_massaniello():
            return
        blocked, reason = self._massaniello_session_blocks_entry()
        if blocked:
            # Capture summary BEFORE reset so hub payload is not empty (0/0).
            summary = self._build_session_end_summary(reason)
            self.bot.last_session_summary = summary  # type: ignore[attr-defined]
            log.debug(
                "Resumen ciclo Massaniello: trades=%s ITM/OTM=%s/%s WR=%s pnl=%s dur=%.1fmin (%s)",
                summary.get("trades"),
                summary.get("itm"),
                summary.get("otm"),
                f"{summary['win_rate']:.1f}%" if summary.get("win_rate") is not None else "–",
                f"{summary['pnl']:+.2f}" if summary.get("pnl") is not None else "–",
                float(summary.get("elapsed_min") or 0.0),
                summary.get("status"),
            )
            # Always roll a fresh Massaniello instance after a terminal cycle.
            from massaniello_risk import MassanielloRiskManager

            self.bot.massaniello = MassanielloRiskManager()
            vcap = self._massaniello_virtual()
            if vcap is not None:
                self.set_session_start_balance(vcap)
            if hasattr(self.bot, "massaniello_persistence") and self.bot.massaniello_persistence:
                self.bot.massaniello_persistence.save(self.bot.massaniello)

            auto_continue = self._auto_continue_enabled()
            if auto_continue:
                # Product rule: ONLY reset Massaniello; bot keeps scanning/trading.
                # No session-ended notice (toast/modal/log spam).
                self.bot.session_stop_hit = False
                if self.session_manager is not None:
                    self.session_manager.bootstrap_for_run(
                        self.bot.massaniello, force_new=True
                    )
                log.debug(
                    "Massaniello reset after cycle (%s) — continue scanning",
                    reason,
                )
            else:
                # Legacy: stop scan and open hub session_completed modal.
                self.bot.session_stop_hit = True
                if self.session_manager is not None:
                    self.session_manager.session_completed(summary)
                else:
                    try:
                        from hub.events import event_bus
                        event_bus.publish("session_completed", summary)
                    except Exception:
                        pass
                log.info(
                    "🛑 Sesión Massaniello finalizada — %s (escaneo detenido)",
                    reason,
                )

    def _massaniello_virtual(self) -> Optional[float]:
        """Capital virtual de referencia para Massaniello (demo). None si desactivado."""
        v = float(MASSANIELLO_VIRTUAL_CAPITAL or 0.0)
        return v if v > 0 else None

    def set_session_start_balance(self, balance: float) -> None:
        vcap = self._massaniello_virtual()
        if vcap is not None:
            balance = vcap  # demo: usa saldo virtual fijo, ignora el real
        self.bot.session_start_balance = float(balance)
        self.bot.current_balance = float(balance)
        self.bot.massaniello.set_balance(float(balance))
        self._sync_massaniello_session_start()
        if self.bot.cycle_start_balance is None:
            self.bot.cycle_start_balance = float(balance)

    @staticmethod
    def _round_up_to_cents(value: float) -> float:
        return ceil(max(0.0, value) * 100.0) / 100.0

    def _compute_initial_amount(self, payout_pct: int) -> Tuple[float, float]:
        """
        Calcula monto de entrada usando MassanielloRiskManager.
        Retorna (monto, ganancia_esperada).
        """
        vcap = self._massaniello_virtual()
        mgr = self.bot.massaniello
        played = mgr.wins + mgr.losses
        if vcap is not None and played == 0:
            # Demo: sembrar el capital de secuencia en $30 SOLO al inicio.
            # Luego el manager mantiene su capital vivo (evoluciona con wins/losses).
            mgr.set_balance(vcap)
        elif self.bot.current_balance is not None and vcap is None:
            mgr.set_balance(self.bot.current_balance)
        self._sync_massaniello_session_start()

        amount, status = mgr.next_stake(payout_pct)

        if status != "OK":
            log.warning("⚠ _compute_initial_amount: %s | amount=%.2f", status, amount)
            return 0.0, 0.0

        payout_rate = max(0.01, float(payout_pct) / 100.0)
        expected_profit = self._round_up_to_cents(amount * payout_rate)

        return amount, expected_profit

    def _compute_compensation_amount(self, payout_pct: int, base_loss: float) -> Tuple[float, float]:
        """
        Calcula monto de compensación (gale legacy).
        Con Massaniello activo delega en next_stake (sin martingala intra-sesión).
        Retorna (monto, ganancia_esperada).
        """
        if self._uses_massaniello():
            return self._compute_initial_amount(payout_pct)

        if self.bot.current_balance is not None:
            self.bot.massaniello.set_balance(self.bot.current_balance)
            self._sync_massaniello_session_start()

        amount, status = self.bot.massaniello.next_stake(payout_pct)

        if status != "OK":
            log.warning("⚠ _compute_compensation_amount: %s | amount=%.2f", status, amount)
            return 0.0, 0.0

        payout_rate = max(0.01, float(payout_pct) / 100.0)
        expected_profit = self._round_up_to_cents(amount * payout_rate)

        return amount, expected_profit
    async def _get_asset_payout(self, asset: str, default: int = MIN_PAYOUT) -> int:
        try:
            assets_now = await get_open_assets(self.client, MIN_PAYOUT)
            for as_sym, as_payout in assets_now:
                if as_sym == asset:
                    return int(as_payout)
        except Exception:
            pass
        return int(default)
    async def _get_current_price(self, asset: str) -> Optional[float]:
        candles = await fetch_candles_with_retry(
            self.client,
            asset,
            60,
            3,
            timeout_sec=CANDLE_FETCH_1M_TIMEOUT_SEC,
            retries=1,
        )
        if candles:
            return float(candles[-1].close)
        return self.bot.last_known_price.get(asset)
    def _cap_martin_amount(self, amount: float, balance: Optional[float]) -> float:
        if balance is None or balance <= 0:
            return max(MIN_ORDER_AMOUNT, self._round_up_to_cents(amount))
        capped = self._round_up_to_cents(balance * MARTIN_MAX_PCT_BALANCE)
        if amount > capped:
            log.warning("⚠ Martin cappado a $%.2f (20%% de $%.2f)", capped, balance)
            return max(MIN_ORDER_AMOUNT, capped)
        return max(MIN_ORDER_AMOUNT, self._round_up_to_cents(amount))

    def _update_dynamic_threshold(self) -> int:
        if len(self.bot.accepted_scans_window) < ADAPTIVE_THRESHOLD_WINDOW_SCANS:
            self.bot.current_score_threshold = ADAPTIVE_THRESHOLD_BASE
            return self.bot.current_score_threshold

        accepted_last_window = sum(self.bot.accepted_scans_window)
        if accepted_last_window == 0:
            self.bot.current_score_threshold = ADAPTIVE_THRESHOLD_LOW
        elif accepted_last_window > 2:
            self.bot.current_score_threshold = ADAPTIVE_THRESHOLD_HIGH
        else:
            self.bot.current_score_threshold = ADAPTIVE_THRESHOLD_BASE
        return self.bot.current_score_threshold
    def _record_scan_acceptances(self, accepted_count: int) -> None:
        self.bot.accepted_scans_window.append(max(0, int(accepted_count)))
    def _cleanup_asset_blacklist(self) -> None:
        now_ts = time.time()
        expired_assets = [
            asset for asset, until_ts in self.bot.asset_blacklist_until.items()
            if now_ts >= until_ts
        ]
        for asset in expired_assets:
            self.bot.asset_blacklist_until.pop(asset, None)
            self.bot.asset_loss_streaks[asset] = 0
            log.warning("✅ [BLACKLIST] %s liberado — tiempo expirado", asset)
    def _is_asset_blacklisted(self, asset: str) -> bool:
        until_ts = self.bot.asset_blacklist_until.get(asset)
        if until_ts is None:
            return False
        if time.time() >= until_ts:
            self.bot.asset_blacklist_until.pop(asset, None)
            self.bot.asset_loss_streaks[asset] = 0
            log.warning("✅ [BLACKLIST] %s liberado — tiempo expirado", asset)
            return False
        return True
    def _register_asset_outcome(self, asset: str, outcome: str) -> None:
        if outcome == "WIN":
            self.bot.asset_loss_streaks[asset] = 0
            return
        if outcome != "LOSS":
            return

        streak = int(self.bot.asset_loss_streaks.get(asset, 0)) + 1
        self.bot.asset_loss_streaks[asset] = streak
        if streak < ASSET_LOSS_STREAK_LIMIT:
            return

        until_ts = time.time() + (ASSET_BLACKLIST_DURATION_MIN * 60)
        self.bot.asset_blacklist_until[asset] = until_ts
        log.warning(
            "⚠ [BLACKLIST] %s añadido — %d LOSS consecutivos (%d min)",
            asset,
            streak,
            ASSET_BLACKLIST_DURATION_MIN,
        )
    def _can_enter_asset_now(self, asset: str, stage: str) -> Tuple[bool, str]:
        """
        Limita la sobre-repetición del mismo activo.
        Nota: martingala y multi-duration legs quedan exentos.
        """
        if stage in ("martin", "multi_leg"):
            return True, "MARTIN_EXEMPT" if stage == "martin" else "MULTI_LEG_EXEMPT"
        if MAX_CONSECUTIVE_ENTRIES_PER_ASSET <= 0:
            return True, "LIMIT_DISABLED"
        if self.bot.last_entry_asset != asset:
            return True, "NEW_ASSET"
        if self.bot.last_entry_asset_streak < MAX_CONSECUTIVE_ENTRIES_PER_ASSET:
            return True, "WITHIN_LIMIT"
        reason = (
            f"máximo {MAX_CONSECUTIVE_ENTRIES_PER_ASSET} entradas consecutivas "
            f"en {asset}"
        )
        return False, reason

    @staticmethod
    def _trade_dict_key(trade: "TradeState", fallback: str = "") -> str:
        """Prefer TradeState.trade_key; fall back to asset or caller key."""
        key = getattr(trade, "trade_key", "") or ""
        if key:
            return key
        return fallback or getattr(trade, "asset", "") or ""

    def _pop_trade_if_match(self, trade: "TradeState", fallback_key: str = "") -> None:
        key = self._trade_dict_key(trade, fallback_key)
        if key and self.bot.trades.get(key) is trade:
            self.bot.trades.pop(key, None)
            return
        # Legacy: key was pure asset before multi-duration.
        asset = getattr(trade, "asset", "") or fallback_key
        if asset and self.bot.trades.get(asset) is trade:
            self.bot.trades.pop(asset, None)

    def _is_massaniello_primary_trade(self, trade: "TradeState") -> bool:
        """Non-primary multi-duration legs must not burn Massaniello ops."""
        if not bool(getattr(_cfg, "MULTI_DURATION_DATA_COLLECTION", False)):
            return True
        primary = int(getattr(_cfg, "MULTI_DURATION_MASSANIELLO_PRIMARY_SEC", 300))
        return int(getattr(trade, "duration_sec", 0) or 0) == primary
    def _register_successful_entry_asset(self, asset: str) -> None:
        if self.bot.last_entry_asset == asset:
            self.bot.last_entry_asset_streak += 1
        else:
            self.bot.last_entry_asset = asset
            self.bot.last_entry_asset_streak = 1

    def _current_martin_attempt_limit(self) -> int:
        if self._uses_massaniello():
            return 0
        balance = self.bot.current_balance
        if balance is None:
            balance = self.bot.massaniello.current_balance
        if balance is not None and balance < MARTIN_LOW_BALANCE_THRESHOLD:
            return MARTIN_MAX_ATTEMPTS_LOW_BALANCE
        return MARTIN_MAX_ATTEMPTS_SESSION
    def _martin_session_available(self) -> bool:
        if self._uses_massaniello():
            return False
        used = int(self.bot.stats.get("martin_attempts_session", 0))
        max_attempts = self._current_martin_attempt_limit()
        if used >= max_attempts:
            log.info(
                "⛔ Martingala desactivada: límite de sesión alcanzado (%d/%d)",
                used,
                max_attempts,
            )
            return False
        return True
    def _track_task(self, task: asyncio.Task[Any]) -> None:
        self.bot._trade_tasks.add(task)
        task.add_done_callback(self._on_background_task_done)
    def _on_background_task_done(self, task: asyncio.Task[Any]) -> None:
        # Always drain task exception to avoid "Task exception was never retrieved"
        # when the process is interrupted with Ctrl+C.
        self.bot._trade_tasks.discard(task)
        self.bot._followup_capture_tasks.discard(task)
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        except Exception:
            return
        if exc is None:
            return
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            return
        log.debug("Tarea background finalizada con error: %s", exc)
    async def shutdown_background_tasks(self) -> None:
        pending = [
            t for t in (list(self.bot._trade_tasks) + list(self.bot._followup_capture_tasks))
            if not t.done()
        ]
        if not pending:
            return
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    def _consume_fresh_watched_candidate(self, asset: str) -> Optional[CandidateEntry]:
        watched = self.bot.watched_candidates.get(asset)
        if not watched:
            return None
        candidate, detected_at = watched
        if (time.time() - detected_at) > 300:
            self.bot.watched_candidates.pop(asset, None)
            return None
        self.bot.watched_candidates.pop(asset, None)
        return candidate
    async def _try_enter_martin_now(
        self,
        *,
        asset: str,
        amount: float,
        original_loss: float,
        strategy_origin: str,
        score_original: float,
        payout_hint: int = MIN_PAYOUT,
    ) -> bool:
        if self._uses_massaniello():
            return False
        if not self._martin_session_available():
            return False

        candidate = self._consume_fresh_watched_candidate(asset)
        if candidate is not None:
            log.info(
                "🔄 MARTIN DIFERIDO %s $%.2f — recuperando $%.2f",
                asset,
                amount,
                original_loss,
            )
            entered = await self.enter_trade(
                asset,
                candidate.direction,
                amount,
                candidate.zone,
                f"MARTIN diferido | recuperando ${original_loss:.2f}",
                "martin",
                signal_ts=getattr(candidate, "_signal_ts_1m", candidate.candles[-1].ts if candidate.candles else None),
                strategy_origin=strategy_origin,
                duration_sec=_live_duration_sec(),
                payout=candidate.payout,
                score_original=score_original,
            )
            if entered:
                self.bot.stats["martins"] += 1
            return entered

        zone = self.bot.zones.get(asset)
        if zone is None:
            return False

        price = await self._get_current_price(asset)
        if price is None:
            return False

        direction: Optional[str] = None
        reason = ""
        if price_at_floor(price, zone.floor):
            direction = "call"
            reason = f"MARTIN inmediato desde piso {zone.floor:.5f}"
        elif price_at_ceiling(price, zone.ceiling):
            direction = "put"
            reason = f"MARTIN inmediato desde techo {zone.ceiling:.5f}"

        if direction is None:
            return False

        payout_now = await self._get_asset_payout(asset, payout_hint)
        log.info(
            "🔄 MARTIN DIFERIDO %s $%.2f — recuperando $%.2f",
            asset,
            amount,
            original_loss,
        )
        entered = await self.enter_trade(
            asset,
            direction,
            amount,
            zone,
            reason,
            "martin",
            strategy_origin=strategy_origin,
            duration_sec=_live_duration_sec(),
            payout=payout_now,
            score_original=score_original,
        )
        if entered:
            self.bot.stats["martins"] += 1
        return entered
    async def _monitor_trade_live(self, asset: str, trade: TradeState) -> None:
        if self._uses_massaniello():
            return
        alerted = False
        recovery_logged = False
        while not trade.resolved:
            elapsed = time.time() - trade.opened_at
            secs_left = trade.duration_sec - elapsed
            if secs_left <= 0 or trade.martin_fired:
                return

            price = await self._get_current_price(asset)
            if price is None:
                await asyncio.sleep(MARTIN_MONITOR_INTERVAL_SEC)
                continue

            hub = getattr(self.bot, "_hub_scanner", None)
            if hub is not None and price is not None:
                hub.update_active_trade_timer(secs_left, price)

            losing_probably = (
                price < trade.entry_price * (1.0 - MARTIN_ALERT_PCT)
                if trade.direction == "call"
                else price > trade.entry_price * (1.0 + MARTIN_ALERT_PCT)
            )

            if losing_probably:
                alerted = True

            if (
                losing_probably
                and MARTIN_LIVE_WINDOW_MIN_SEC <= secs_left <= MARTIN_LIVE_WINDOW_MAX_SEC
                and not trade.martin_fired
                and trade.stage != "martin"
                and trade.score_original >= 70.0
                and self._martin_session_available()
            ):
                payout_now = await self._get_asset_payout(asset, trade.payout)
                amount, _ = self._compute_compensation_amount(payout_now, trade.amount)
                balance = self.bot.current_balance
                if balance is None:
                    try:
                        balance = float(await self.client.get_balance())
                    except Exception:
                        balance = None
                amount = self._cap_martin_amount(amount, balance)
                zone = ConsolidationZone(
                    asset=asset,
                    ceiling=trade.ceiling,
                    floor=trade.floor,
                    bars_inside=0,
                    detected_at=time.time(),
                    range_pct=0.0,
                )
                trade.martin_fired = True
                log.info(
                    "⚡ MARTIN ANTICIPADO %s %s $%.2f — precio en contra con %.0fs restantes",
                    asset,
                    trade.direction.upper(),
                    amount,
                    secs_left,
                )
                entered = await self.enter_trade(
                    asset,
                    trade.direction,
                    amount,
                    zone,
                    f"MARTIN anticipado | precio en contra con {secs_left:.0f}s restantes",
                    "martin",
                    strategy_origin=trade.strategy_origin,
                    duration_sec=_live_duration_sec(),
                    payout=payout_now,
                    score_original=trade.score_original,
                )
                if entered:
                    self.bot.stats["martins"] += 1
                return

            if alerted and not losing_probably and secs_left > MARTIN_LIVE_WINDOW_MIN_SEC and not recovery_logged:
                log.info("✅ %s: precio recuperado, martin cancelado", asset)
                recovery_logged = True
                alerted = False

            await asyncio.sleep(MARTIN_MONITOR_INTERVAL_SEC)
    async def _resolve_trade_after_expiry(self, asset: str, trade: TradeState) -> None:
        wait_sec = max(0.0, trade.duration_sec + MARTIN_RESOLVE_GRACE_SEC - (time.time() - trade.opened_at))
        if wait_sec > 0:
            # Main loop owns the user-facing "waiting" line; keep this quiet.
            log.debug(
                "⌛ %s: esperando liquidación broker (%.0fs = duration+grace)…",
                asset,
                wait_sec,
            )
            await asyncio.sleep(wait_sec)
        await self._resolve_trade(trade, asset)

    @staticmethod
    def _interpret_broker_result(
        win_val: Any = None,
        *,
        status: Any = None,
        payload: Any = None,
        trade_amount: float = 0.0,
        payout_pct: int = 80,
    ) -> Optional[Tuple[str, float]]:
        """Map broker payload to (WIN|LOSS, profit) or None if not settled yet.

        Critical: profitAmount == 0 / missing history must NOT be treated as LOSS.
        Quotex often exposes the ticket before profit is final (lag after expiry).
        """
        # Path A: check_win() → bool or numeric PnL
        if win_val is not None:
            if isinstance(win_val, bool):
                if win_val:
                    payout_rate = max(0.01, float(payout_pct) / 100.0)
                    return "WIN", float(trade_amount) * payout_rate
                return "LOSS", -abs(float(trade_amount))
            if isinstance(win_val, (int, float)):
                profit = float(win_val)
                if profit > 0:
                    return "WIN", profit
                if profit < 0:
                    return "LOSS", profit
                # profit == 0 → still open / not settled
                return None
            return None

        # Path B: get_result() → ("win"|"loss"|None, payload)
        if status is None:
            return None
        status_l = str(status).strip().lower()
        profit = 0.0
        if isinstance(payload, dict):
            try:
                profit = float(payload.get("profitAmount", 0) or 0)
            except (TypeError, ValueError):
                profit = 0.0

        if profit > 0:
            return "WIN", profit
        if profit < 0:
            return "LOSS", profit

        # Ambiguous: library may label profit==0 as "loss" before settlement.
        # Only trust explicit status when profit is non-zero (handled above).
        if status_l in {"win", "loss"} and profit == 0:
            return None
        return None
    async def _process_pending_martin(
        self,
        candidates: list[CandidateEntry],
    ) -> tuple[list[CandidateEntry], bool]:
        if self._uses_massaniello():
            return candidates, False
        if not self.bot.pending_martin:
            return candidates, False

        remaining = list(candidates)
        entered_any = False
        for asset, pending in list(self.bot.pending_martin.items()):
            if not self._martin_session_available():
                break
            pending.scans_waited += 1
            matching = [c for c in remaining if c.asset == asset]
            if matching and len(self.bot.trades) < MAX_CONCURRENT_TRADES:
                chosen = max(matching, key=lambda c: c.score)
                entered = await self.enter_trade(
                    chosen.asset,
                    chosen.direction,
                    pending.amount,
                    chosen.zone,
                    f"MARTIN diferido | recuperando ${pending.original_loss:.2f}",
                    "martin",
                    signal_ts=getattr(chosen, "_signal_ts_1m", chosen.candles[-1].ts if chosen.candles else None),
                    strategy_origin="STRAT-A",
                    duration_sec=_live_duration_sec(),
                    payout=chosen.payout,
                    score_original=pending.score_original,
                )
                if entered:
                    log.info(
                        "🔄 MARTIN DIFERIDO %s $%.2f — recuperando $%.2f",
                        asset,
                        pending.amount,
                        pending.original_loss,
                    )
                    self.bot.stats["martins"] += 1
                    self.bot.pending_martin.pop(asset, None)
                    remaining = [c for c in remaining if c.asset != asset]
                    entered_any = True
                    continue

            if pending.scans_waited >= pending.max_wait_scans:
                log.info("⏰ %s: martin diferido expirado", asset)
                self.bot.pending_martin.pop(asset, None)

        return remaining, entered_any
    def _reset_cycle(self, reason: str) -> None:
        log.info(
            "🔁 Reinicio de ciclo #%d | motivo=%s | ops=%d wins=%d loss=%d profit=%.2f",
            self.bot.cycle_id,
            reason,
            self.bot.cycle_ops,
            self.bot.cycle_wins,
            self.bot.cycle_losses,
            self.bot.cycle_profit,
        )
        self.bot.cycle_id += 1
        self.bot.cycle_ops = 0
        self.bot.cycle_wins = 0
        self.bot.cycle_losses = 0
        self.bot.cycle_profit = 0.0
        if self.bot.current_balance is not None:
            self.bot.cycle_start_balance = float(self.bot.current_balance)
    def _update_cycle_after_result(self, outcome: str, profit: float) -> None:
        if outcome not in {"WIN", "LOSS"}:
            return

        self.bot.cycle_ops += 1
        self.bot.cycle_profit += float(profit)
        if outcome == "WIN":
            self.bot.cycle_wins += 1
        else:
            self.bot.cycle_losses += 1

        # 1) Regla: reiniciar al alcanzar +10% del balance base del ciclo.
        if (
            self.bot.cycle_start_balance
            and self.bot.current_balance is not None
            and self.bot.cycle_start_balance > 0
        ):
            growth = (self.bot.current_balance - self.bot.cycle_start_balance) / self.bot.cycle_start_balance
            if growth >= CYCLE_TARGET_PROFIT_PCT:
                self._reset_cycle(f"objetivo +{int(CYCLE_TARGET_PROFIT_PCT*100)}% cumplido")
                return

        # 2) Regla: ciclo objetivo cumplido con 2 wins.
        if self.bot.cycle_wins >= CYCLE_TARGET_WINS:
            self._reset_cycle(f"objetivo {CYCLE_TARGET_WINS}W cumplido")
            return

        # 3) Regla: reinicio al completar 6 operaciones.
        if self.bot.cycle_ops >= CYCLE_MAX_OPERATIONS:
            self._reset_cycle(f"límite de {CYCLE_MAX_OPERATIONS} operaciones")
            return

        # 4) Regla anticipada: si matemáticamente ya no se puede llegar al objetivo de wins.
        remaining = CYCLE_MAX_OPERATIONS - self.bot.cycle_ops
        if self.bot.cycle_wins + remaining < CYCLE_TARGET_WINS:
            self._reset_cycle(
                f"objetivo {CYCLE_TARGET_WINS}W imposible en este ciclo",
            )
    async def refresh_balance_and_risk(self) -> bool:
        """Actualiza balance y aplica stop-loss de sesión."""
        if self.bot.dry_run:
            return False
        vcap = self._massaniello_virtual()
        if vcap is not None:
            # Demo: el riesgo NO usa el saldo real de la cuenta. El Massaniello
            # mantiene su capital de secuencia VIVO (evoluciona con wins/losses);
            # solo lo sembramos en $30 si es el arranque de la secuencia.
            mgr = self.bot.massaniello
            if mgr.wins + mgr.losses == 0 and mgr.session_start_time is None:
                mgr.set_balance(vcap)
            self.bot.current_balance = float(mgr.current_balance or vcap)
            self._sync_massaniello_session_start()
            return False
        try:
            bal = float(await self.client.get_balance())
        except Exception as exc:
            log.debug("No se pudo actualizar balance de sesión: %s", exc)
            return False

        if self.bot.session_start_balance is None:
            self.set_session_start_balance(bal)

        self.bot.current_balance = bal
        self.bot.massaniello.set_balance(bal)
        self._sync_massaniello_session_start()
        if not self.bot.session_start_balance or self.bot.session_start_balance <= 0:
            return False

        drawdown = (self.bot.session_start_balance - bal) / self.bot.session_start_balance
        if drawdown >= MAX_LOSS_SESSION:
            self.bot.session_stop_hit = True
            log.error(
                "🛑 STOP-LOSS DE SESIÓN activado: drawdown=%.1f%% (inicio=%.2f, actual=%.2f)",
                drawdown * 100,
                self.bot.session_start_balance,
                bal,
            )
            alerter.alert_stop_loss(drawdown * 100, bal)
            return True
        return False
    async def reconcile_pending_candidates(self, max_age_minutes: Optional[float] = None) -> None:
        """
        Reconciliar ACCEPTED/PENDING al arrancar para no contaminar métricas.
        Si no se puede resolver una orden, se marca UNRESOLVED.
        """
        journal = get_journal()
        if journal._conn is None:
            return

        if max_age_minutes is not None and max_age_minutes > 0:
            cutoff = (datetime.now(tz=BROKER_TZ) - timedelta(minutes=float(max_age_minutes))).isoformat()
            rows = journal._conn.execute(
                """SELECT id, order_id
                   FROM candidates
                   WHERE outcome='PENDING'
                     AND decision='ACCEPTED'
                     AND datetime(scanned_at) <= datetime(?)""",
                (cutoff,),
            ).fetchall()
        else:
            rows = journal._conn.execute(
                """SELECT id, order_id
                   FROM candidates
                   WHERE outcome='PENDING' AND decision='ACCEPTED'"""
            ).fetchall()

        if not rows:
            if max_age_minutes is None:
                log.info("♻ Reconciliación inicial: no hay PENDING para revisar.")
            else:
                log.debug(
                    "♻ Reconciliación periódica: no hay PENDING con edad >= %.1f min.",
                    float(max_age_minutes),
                )
            return

        resolved = 0
        unresolved = 0

        for row in rows:
            rid = int(row[0])
            oid = str(row[1] or "").strip()

            # Sin identificador usable, no hay forma confiable de consultar resultado.
            if not oid or oid in {"BROKER_NO_ID"} or oid.startswith("DRY-"):
                journal._conn.execute(
                    "UPDATE candidates SET outcome='UNRESOLVED', closed_at=? WHERE id=? AND outcome='PENDING'",
                    (datetime.now(tz=BROKER_TZ).isoformat(), rid),
                )
                unresolved += 1
                continue

            try:
                outcome = None
                profit = 0.0
                interpreted = None

                # Compatibilidad: si guardamos REF-<id>, intentar check_win por id numérico.
                if oid.startswith("REF-"):
                    ref_id = int(oid.split("-", 1)[1])
                    win_val = await self.client.check_win(ref_id)
                    interpreted = self._interpret_broker_result(win_val, trade_amount=0.0)
                else:
                    status, payload = await self.client.get_result(oid)
                    interpreted = self._interpret_broker_result(
                        status=status, payload=payload, trade_amount=0.0,
                    )

                if interpreted is not None:
                    outcome, profit = interpreted
                    journal._conn.execute(
                        "UPDATE candidates SET outcome=?, profit=?, closed_at=? WHERE id=? AND outcome='PENDING'",
                        (outcome, float(profit), datetime.now(tz=BROKER_TZ).isoformat(), rid),
                    )
                    resolved += 1
                else:
                    # Leave PENDING — do not force UNRESOLVED/LOSS while broker lagging
                    log.debug("Reconcile: id=%s still unsettled — keep PENDING", rid)
            except Exception:
                journal._conn.execute(
                    "UPDATE candidates SET outcome='UNRESOLVED', closed_at=? WHERE id=? AND outcome='PENDING'",
                    (datetime.now(tz=BROKER_TZ).isoformat(), rid),
                )
                unresolved += 1

        journal._conn.commit()
        if max_age_minutes is None:
            log.info(
                "♻ Reconciliación inicial completada: %d resueltas, %d UNRESOLVED (total=%d).",
                resolved,
                unresolved,
                len(rows),
            )
        else:
            log.info(
                "♻ Reconciliación periódica (>= %.1f min): %d resueltas, %d UNRESOLVED (total=%d).",
                float(max_age_minutes),
                resolved,
                unresolved,
                len(rows),
            )
    def _strategy_snapshot(self) -> dict:
        """Snapshot de parámetros activos para auditoría de caja negra."""
        return {
            "tf_sec": TF_5M,
            "candles_lookback": CANDLES_LOOKBACK,
            "min_consolidation_bars": MIN_CONSOLIDATION_BARS,
            "max_range_pct": MAX_RANGE_PCT,
            "touch_tolerance_pct": TOUCH_TOLERANCE_PCT,
            "max_consolidation_min": MAX_CONSOLIDATION_MIN,
            "min_payout": MIN_PAYOUT,
            "duration_sec": _live_duration_sec(),
            "max_concurrent_trades": MAX_CONCURRENT_TRADES,
            "cooldown_between_entries": COOLDOWN_BETWEEN_ENTRIES,
            "max_consecutive_entries_per_asset": MAX_CONSECUTIVE_ENTRIES_PER_ASSET,
            "martin_low_balance_threshold": MARTIN_LOW_BALANCE_THRESHOLD,
            "martin_max_attempts_low_balance": MARTIN_MAX_ATTEMPTS_LOW_BALANCE,
            "martin_max_attempts_session": MARTIN_MAX_ATTEMPTS_SESSION,
            "score_threshold_base": ADAPTIVE_THRESHOLD_BASE,
            "score_threshold_session": self.bot.current_score_threshold,
            "volume_multiplier": VOLUME_MULTIPLIER,
            "volume_lookback": VOLUME_LOOKBACK,
            "zone_age_rebound_min": ZONE_AGE_REBOUND_MIN,
            "zone_age_breakout_min": ZONE_AGE_BREAKOUT_MIN,
            "strict_pattern_check": STRICT_PATTERN_CHECK,
            "entry_sync_to_candle": ENTRY_SYNC_TO_CANDLE,
            "entry_sync_tf_sec": self.entry_sync.tf_sec,
            "entry_max_lag_sec": ENTRY_MAX_LAG_SEC,
            "entry_reject_last_sec": ENTRY_REJECT_LAST_SEC,
            "align_scan_to_candle": ALIGN_SCAN_TO_CANDLE,
            "scan_lead_sec": SCAN_LEAD_SEC,
            "broker_tz": BROKER_TZ_LABEL,
            "compensation_pending": self.bot.compensation_pending,
            "last_closed_outcome": self.bot.last_closed_outcome,
            "last_closed_amount": self.bot.last_closed_amount,
            "max_loss_session": MAX_LOSS_SESSION,
            "dynamic_atr_range": USE_DYNAMIC_ATR_RANGE,
            "atr_period": ATR_PERIOD,
            "atr_range_factor": ATR_RANGE_FACTOR,
            "min_dynamic_range_pct": MIN_DYNAMIC_RANGE_PCT,
            "max_dynamic_range_pct": MAX_DYNAMIC_RANGE_PCT,
            "h1_confirm_enabled": H1_CONFIRM_ENABLED,
            "cycle_max_operations": CYCLE_MAX_OPERATIONS,
            "cycle_target_wins": CYCLE_TARGET_WINS,
            "cycle_target_profit_pct": CYCLE_TARGET_PROFIT_PCT,
            "cycle_id": self.bot.cycle_id,
            "cycle_ops": self.bot.cycle_ops,
            "cycle_wins": self.bot.cycle_wins,
            "cycle_losses": self.bot.cycle_losses,
            "cycle_profit": self.bot.cycle_profit,
            "last_entry_asset": self.bot.last_entry_asset,
            "last_entry_asset_streak": self.bot.last_entry_asset_streak,
            "greylist_assets": sorted(self.bot.greylist_assets),
        }
    async def _sync_to_next_candle_open(self, signal_ts: Optional[int] = None) -> EntryTimingInfo:
        """Delega sincronización y validación de timing al EntrySynchronizer."""
        # Hub may have changed DURATION_SEC after EntrySynchronizer construction.
        self.entry_sync.duration_sec = _live_duration_sec()
        return await self.entry_sync.sync_and_validate(signal_ts)
    async def _resolve_trade(self, trade: "TradeState", sym: str) -> None:
        """
        Consulta el resultado de una operación expirada al broker
        y actualiza el journal con WIN / LOSS / UNRESOLVED sin bloquear el bot.

        Never treats profitAmount==0 as LOSS (broker lag after expiry).
        """
        if trade.resolved:
            return

        journal = get_journal()
        has_id  = bool(trade.order_id) and not trade.order_id.startswith("DRY-")
        has_ref = trade.order_ref > 0
        if self.bot.dry_run:
            trade.resolved = True
            self._pop_trade_if_match(trade, sym)
            hub = getattr(self.bot, "_hub_scanner", None)
            if hub is not None and not self.bot.trades:
                hub.close_active_trade()
            return

        outcome = "UNRESOLVED"
        profit  = 0.0
        payout_pct = int(getattr(trade, "payout", 0) or 80)
        if has_id or has_ref:
            for attempt in range(1, MARTIN_RESOLVE_MAX_ATTEMPTS + 1):
                interpreted: Optional[Tuple[str, float]] = None
                # FIX B: if the WS dropped since the order opened (idle-timeout
                # during the wait), the broker call below hangs/fails on a dead
                # socket. Reconnect every attempt via the bot's own manager
                # (serialized by _RECONNECT_LOCK). Without this the leg stays
                # stuck in bot.trades forever and the loop hangs at
                # "En espera de finalizar trade".
                await self._reconnect_if_needed(f"resolve:{sym}")
                try:
                    if has_ref:
                        # check_win blocks until game_state==1; give it real time.
                        win_val = await asyncio.wait_for(
                            self.client.check_win(trade.order_ref),
                            timeout=MARTIN_RESOLVE_TIMEOUT_SEC,
                        )
                        interpreted = self._interpret_broker_result(
                            win_val,
                            trade_amount=float(trade.amount),
                            payout_pct=payout_pct,
                        )
                        if interpreted is None:
                            log.info(
                                "⏳ %s: resultado aún no liquidado (check_win=%r) intento %d/%d",
                                sym,
                                win_val,
                                attempt,
                                MARTIN_RESOLVE_MAX_ATTEMPTS,
                            )
                    elif has_id:
                        status, payload = await asyncio.wait_for(
                            self.client.get_result(trade.order_id),
                            timeout=MARTIN_RESOLVE_TIMEOUT_SEC,
                        )
                        interpreted = self._interpret_broker_result(
                            status=status,
                            payload=payload,
                            trade_amount=float(trade.amount),
                            payout_pct=payout_pct,
                        )
                        if interpreted is None:
                            log.info(
                                "⏳ %s: ticket sin PnL final (status=%r profit=%s) intento %d/%d",
                                sym,
                                status,
                                (payload or {}).get("profitAmount") if isinstance(payload, dict) else None,
                                attempt,
                                MARTIN_RESOLVE_MAX_ATTEMPTS,
                            )
                    if interpreted is not None:
                        outcome, profit = interpreted
                        break
                except asyncio.TimeoutError:
                    log.info(
                        "⏳ %s: timeout esperando liquidación broker intento %d/%d",
                        sym,
                        attempt,
                        MARTIN_RESOLVE_MAX_ATTEMPTS,
                    )
                except Exception as exc:
                    log.warning(
                        "No se pudo obtener resultado de %s / ref=%s intento %d/%d: %s",
                        trade.order_id,
                        trade.order_ref,
                        attempt,
                        MARTIN_RESOLVE_MAX_ATTEMPTS,
                        exc,
                    )

                if attempt < MARTIN_RESOLVE_MAX_ATTEMPTS:
                    await asyncio.sleep(MARTIN_RESOLVE_RETRY_SEC)

        if outcome == "UNRESOLVED":
            log.warning(
                "⚠ %s: quedó UNRESOLVED (no se forzó LOSS). "
                "Se reintentará en reconcile a los 15 min.",
                sym,
            )

        trade.resolved = True
        asset_sym = getattr(trade, "asset", None) or sym
        is_primary = self._is_massaniello_primary_trade(trade)

        if trade.journal_id:
            journal.update_outcome_by_id(row_id=trade.journal_id, outcome=outcome, profit=profit)
        else:
            journal.update_outcome(order_id=trade.order_id, outcome=outcome, profit=profit)
        await self.refresh_balance_and_risk()
        balance_now = self.bot.current_balance if self.bot.current_balance is not None else 0.0
        log.info(
            "🏁 %s %s $%.2f | dur=%ds | saldo: $%.2f%s",
            asset_sym,
            outcome,
            profit,
            int(getattr(trade, "duration_sec", 0) or 0),
            balance_now,
            "" if is_primary else " (multi-leg, no Massaniello)",
        )
        if is_primary:
            self._update_cycle_after_result(outcome=outcome, profit=profit)

        # Post-mortem caja negra STRAT-F (Fase 4): solo estrategia STRAT-F.
        # WIN and LOSS both resolve order_result + profit (data collection).
        # Post-mortem analysis fields stay LOSS-focused.
        # Resolución por id exacto (trade.black_box_cid) si está vinculado;
        # fallback por asset para compatibilidad con ciclos previos.
        if getattr(trade, "strategy_origin", "") == "STRAT-F":
            try:
                bb = get_black_box()
                bb_cid = getattr(trade, "black_box_cid", 0) or 0
                before = None
                if bb_cid:
                    before = bb.get_candidate_by_id(bb_cid)
                if before is None:
                    before = bb.get_pending_candidate_before(asset_sym)
                candles_post = []
                if before or bb_cid:
                    if before:
                        post_raw = await fetch_candles_1m(self.client, asset_sym, count=5)
                        candles_post = [
                            {"ts": c.ts, "o": c.open, "h": c.high, "l": c.low, "c": c.close}
                            for c in (post_raw or [])
                        ]
                        loss_reason, improvement_hint = analyze_postmortem(
                            before_candles_1m=before["candles_1m"],
                            after_candles_1m=candles_post,
                            direction=before["direction"] or trade.direction,
                            outcome=outcome,
                            entry_price=getattr(trade, "entry_price", None),
                            exit_price=None,
                        )
                    else:
                        loss_reason, improvement_hint = "", ""
                    # Always write order_result for WIN and LOSS (and UNRESOLVED).
                    if bb_cid:
                        bb.resolve_candidate_by_id(
                            bb_cid, outcome, profit,
                            entry_price=getattr(trade, "entry_price", None),
                            candles_post=candles_post or None,
                            stoch_m15=(before or {}).get("stoch_m15") if before else None,
                            loss_reason=(loss_reason or None) if outcome == "LOSS" else None,
                            improvement_hint=(improvement_hint or None) if outcome == "LOSS" else None,
                        )
                    elif before:
                        bb.resolve_candidate_for_asset(
                            asset_sym, outcome, profit,
                            entry_price=getattr(trade, "entry_price", None),
                            candles_post=candles_post,
                            stoch_m15=before.get("stoch_m15"),
                            loss_reason=(loss_reason or None) if outcome == "LOSS" else None,
                            improvement_hint=(improvement_hint or None) if outcome == "LOSS" else None,
                        )
                    if outcome == "LOSS" and before:
                        log.info(
                            "[POST-MORTEM] %s %s | razon=%s | mejora=%s",
                            asset_sym, trade.direction, loss_reason, improvement_hint,
                        )
            except Exception as exc:
                log.debug("[POST-MORTEM] %s: error (no bloquea): %s", asset_sym, exc)

        hub = getattr(self.bot, "_hub_scanner", None)
        if hub is not None:
            hub.record_trade_result(asset=asset_sym, outcome=outcome, profit=profit)
            remaining_others = [
                t for t in self.bot.trades.values()
                if t is not trade and not getattr(t, "resolved", False)
            ]
            if not remaining_others:
                hub.close_active_trade()

        if outcome == "WIN":
            self.bot.stats["strat_a_wins"] = self.bot.stats.get("strat_a_wins", 0) + 1
            if not is_primary:
                self.bot.stats["multi_duration_wins"] = (
                    self.bot.stats.get("multi_duration_wins", 0) + 1
                )
            if trade.stage == "martin":
                self.bot.stats["martin_wins"] = self.bot.stats.get("martin_wins", 0) + 1
        elif outcome == "LOSS":
            self.bot.stats["strat_a_losses"] = self.bot.stats.get("strat_a_losses", 0) + 1
            if not is_primary:
                self.bot.stats["multi_duration_losses"] = (
                    self.bot.stats.get("multi_duration_losses", 0) + 1
                )
            if trade.stage == "martin":
                self.bot.stats["martin_losses"] = self.bot.stats.get("martin_losses", 0) + 1

        if is_primary:
            self._register_asset_outcome(asset_sym, outcome)

        # Notify session manager that trade is resolved (primary only avoids 4x churn)
        if is_primary and self.session_manager is not None:
            self.session_manager.exit_trade()

        # Massaniello / continuous / compensation: primary duration only.
        if is_primary and outcome == "WIN":
            self.bot.compensation_pending = False
            self.bot.last_closed_outcome  = "WIN"
            self.bot.pending_martin.pop(asset_sym, None)
            self.bot.massaniello.register_win(trade.amount, trade.payout)
            self._sync_massaniello_session_start()
            if self._uses_massaniello() and hasattr(self.bot, "massaniello_persistence"):
                self.bot.massaniello_persistence.save(self.bot.massaniello)
            log.info("✅ WIN registrado — próxima entrada usará stake Massaniello")
            if hasattr(self.bot, "continuous") and self.bot.continuous is not None:
                self.bot.continuous.register_win()
            self._maybe_stop_massaniello_session()
        elif is_primary and outcome == "LOSS":
            if not self._uses_massaniello():
                self.bot.compensation_pending = True
            self.bot.last_closed_amount   = trade.amount
            self.bot.last_closed_outcome  = "LOSS"
            _, loss_status = self.bot.massaniello.register_loss(trade.amount)
            self._sync_massaniello_session_start()
            if self._uses_massaniello() and hasattr(self.bot, "massaniello_persistence"):
                self.bot.massaniello_persistence.save(self.bot.massaniello)
            log.info(
                "💔 LOSS registrado ($%.2f) — próxima entrada usará stake Massaniello (%s)",
                trade.amount,
                loss_status,
            )
            if hasattr(self.bot, "continuous") and self.bot.continuous is not None:
                self.bot.continuous.register_loss(amount=trade.amount)
            self._maybe_stop_massaniello_session()
            if not self._uses_massaniello():
                skip_martin = False
                if (not trade.martin_fired) and trade.stage != "martin":
                    if trade.score_original < 70.0:
                        log.info(
                            "⛔ %s: martingala omitida — score original %.1f < 70.0",
                            asset_sym,
                            trade.score_original,
                        )
                        skip_martin = True
                    if not self._martin_session_available():
                        skip_martin = True
                    if not skip_martin:
                        payout_now = await self._get_asset_payout(asset_sym, trade.payout)
                        martin_amount, _ = self._compute_compensation_amount(payout_now, trade.amount)
                        martin_amount = self._cap_martin_amount(martin_amount, self.bot.current_balance)
                        entered = await self._try_enter_martin_now(
                            asset=asset_sym,
                            amount=martin_amount,
                            original_loss=trade.amount,
                            strategy_origin=trade.strategy_origin,
                            score_original=trade.score_original,
                            payout_hint=payout_now,
                        )
                        if not entered:
                            self.bot.pending_martin[asset_sym] = MartinPending(
                                asset=asset_sym,
                                amount=martin_amount,
                                original_loss=trade.amount,
                                score_original=trade.score_original,
                                created_at=datetime.now(tz=BROKER_TZ),
                            )

        self._pop_trade_if_match(trade, sym)

        # Avisar si hay candidatos vigilados listos para considerar en el próximo escaneo.
        if self.bot.watched_candidates:
            now_ts = time.time()
            freshness_sec = 300  # solo mostrar si se detectaron en los últimos 5 min
            still_fresh = {
                a: (c, ts) for a, (c, ts) in self.bot.watched_candidates.items()
                if (now_ts - ts) <= freshness_sec
            }
            if still_fresh:
                names = ", ".join(
                    f"{a}({c.direction.upper()} score={c.score:.1f})"
                    for a, (c, _) in still_fresh.items()
                )
                log.info(
                    "🎯 Trade cerrado — candidatos vigilados disponibles: %s — "
                    "el próximo escaneo evaluará entrar.",
                    names,
                )
            else:
                self.bot.watched_candidates.clear()
                log.info("🎯 Trade cerrado — candidatos vigilados vencidos, se descartaron.")
    async def _check_martin(self, sym: str) -> bool:
        """
        Fallback liviano: limpia trades ya resueltos o dispara resolución si
        la tarea en background no lo hizo.

        ``sym`` may be a pure asset or a trade_key (asset#duration).
        """
        trade = self.open_trades_get(sym)
        if trade is None:
            return False

        if trade.resolved:
            self._pop_trade_if_match(trade, sym)
            return False

        elapsed = time.time() - trade.opened_at

        if elapsed > (trade.duration_sec + MARTIN_RESOLVE_GRACE_SEC + 15.0):
            await self._resolve_trade(trade, self._trade_dict_key(trade, sym))

        return False
    def open_trades_get(self, sym: str) -> Optional[TradeState]:
        """Lookup by trade_key or pure asset (first match)."""
        direct = self.bot.trades.get(sym)
        if direct is not None:
            return direct
        # Asset-only lookup across multi-duration keys.
        for key, trade in self.bot.trades.items():
            if getattr(trade, "asset", None) == sym or key.startswith(f"{sym}#"):
                return trade
        return None

    def _set_last_order_attempt(
        self,
        asset: str,
        direction: str,
        status: str,
        reason: str = "",
    ) -> None:
        """Update bot.last_order_attempt for hub UX and scanner logs."""
        self.bot.last_order_attempt = {
            "asset": asset,
            "direction": direction,
            "status": status,
            "reason": reason or "",
            "ts": time.time(),
        }

    async def _m1_micro_confirm_pre_buy(
        self, asset: str, direction: str
    ) -> Tuple[bool, str]:
        """Fetch recent M1 candles and run pure micro-trend confirm.

        Fail-open on fetch errors so data collection is not starved.
        Returns (ok, reason).
        """
        try:
            candles = await fetch_candles_1m(self.client, asset, count=5)
        except Exception as exc:
            log.debug("M1 micro fetch fail %s: %s — pass", asset, exc)
            return True, "m1_fetch_fail_pass"
        if candles is None:
            return True, "m1_fetch_fail_pass"
        ok, reason, _metrics = confirm_m1_micro(candles, direction)
        return ok, reason

    @staticmethod
    def _is_hard_order_fail(reject_reason: Optional[str]) -> bool:
        """Timeout / unexpected / connection-class broker failures."""
        r = (reject_reason or "").lower()
        return (
            "timeout" in r
            or "unexpected" in r
            or "connection" in r
            or "lost" in r
        )

    async def _resolve_entry_timing(
        self,
        *,
        skip_open_wait: bool,
        signal_ts: Optional[int],
    ) -> EntryTimingInfo:
        """Resolve entry-TF open timing; alts may skip wait when lag still OK."""
        self.entry_sync.duration_sec = _live_duration_sec()
        if skip_open_wait:
            now = time.time()
            tf = self.entry_sync.tf_sec
            current_open = (int(now) // tf) * tf
            timing = self.entry_sync.compute_timing(current_open, now)
            if timing.ok:
                log.info(
                    "⏱ skip_open_wait: lag actual OK (%.3fs) — sin espera a próximo open",
                    timing.lag_sec,
                )
                return timing
            log.info(
                "⏱ skip_open_wait: lag no válido (%.3fs) — un único wait a próximo open",
                timing.lag_sec,
            )
            return await self._sync_to_next_candle_open(signal_ts)
        return await self._sync_to_next_candle_open(signal_ts)

    async def enter_trade(
        self, sym: str, direction: str, amount: float,
        zone: ConsolidationZone, reason: str, stage: str,
        journal_cid: int = 0,
        signal_ts: Optional[int] = None,
        strategy_origin: str = "STRAT-A",
        duration_sec: Optional[int] = None,
        payout: int = MIN_PAYOUT,
        score_original: float = 0.0,
        black_box_cid: int = 0,
        *,
        skip_open_wait: bool = False,
        multi_leg: bool = False,
        register_entry_asset: bool = True,
    ) -> bool:
        # Preserve caller order duration (multi-duration legs). Do NOT replace
        # with entry-sync timing.duration_sec — that mirrors config, not expiry.
        if duration_sec is None:
            duration_sec = _live_duration_sec()
        duration_sec = int(duration_sec)
        entry_stage = "multi_leg" if multi_leg else stage
        blocked, block_reason = self._massaniello_session_blocks_entry()
        if blocked:
            log.info("⏭ %s: entrada bloqueada — %s", sym, block_reason)
            if journal_cid:
                _j = get_journal()
                if _j._conn is not None:
                    _j._conn.execute(
                        """UPDATE candidates
                           SET decision='REJECTED_SESSION',
                               reject_reason=?,
                               outcome='SESSION_BLOCKED'
                           WHERE id=?""",
                        (block_reason, journal_cid),
                    )
                    _j._conn.commit()
            return False

        # Continuous mode: check guard rate limiting (first multi-leg only)
        if (
            not multi_leg
            and hasattr(self.bot, "continuous")
            and self.bot.continuous is not None
        ):
            cont = self.bot.continuous
            if not cont.can_enter_now():
                wait = cont.seconds_until_next_entry()
                log.debug(
                    "⏭ %s: entrada bloqueada (continuous rate limit) — %.0fs restantes",
                    sym, wait,
                )
                return False
            cont.record_entry()

        if (
            self.bot.compensation_pending
            and stage != "martin"
            and not multi_leg
            and not self._uses_massaniello()
        ):
            lock_reason = "gale activo: solo operación martingala cuenta"
            log.info("⏭ %s: entrada bloqueada — %s", sym, lock_reason)
            if journal_cid:
                _j = get_journal()
                if _j._conn is not None:
                    _j._conn.execute(
                        """UPDATE candidates
                           SET decision='REJECTED_GALE_LOCK',
                               reject_reason=?,
                               outcome='GALE_LOCK_SKIPPED'
                           WHERE id=?""",
                        (lock_reason, journal_cid),
                    )
                    _j._conn.commit()
            return False

        if stage == "martin":
            if self._uses_massaniello():
                return False
            if not self._martin_session_available():
                return False
            self.bot.stats["martin_attempts_session"] += 1

        can_enter_asset, same_asset_reason = self._can_enter_asset_now(sym, entry_stage)
        if not can_enter_asset:
            self.bot.stats["rejected_same_asset_limit"] += 1
            log.info("⏭ %s: entrada bloqueada — %s", sym, same_asset_reason)
            if journal_cid:
                _j = get_journal()
                if _j._conn is not None:
                    _j._conn.execute(
                        """UPDATE candidates
                           SET decision='REJECTED_LIMIT',
                               reject_reason=?,
                               outcome='LIMIT_SKIPPED'
                           WHERE id=?""",
                        (same_asset_reason, journal_cid),
                    )
                    _j._conn.commit()
            return False

        # Prewarm trade_client before/during open wait so buy() is ready at open.
        prewarm_task: Optional[asyncio.Task] = None
        if stage in ("initial", "martin") or multi_leg:
            self._set_last_order_attempt(sym, direction, "waiting_open")
            prewarm_task = asyncio.create_task(self._reconnect_if_needed("prewarm"))
            timing = await self._resolve_entry_timing(
                skip_open_wait=skip_open_wait,
                signal_ts=signal_ts,
            )
            self.entry_sync.log_order_timing(sym, timing)
            if journal_cid:
                _j = get_journal()
                if _j._conn is not None:
                    _j.log_entry_timing(
                        candidate_id=journal_cid,
                        time_since_open=timing.time_since_open_sec,
                        secs_to_close=timing.secs_to_close_sec,
                        duration_sec=duration_sec,
                        timing_decision=timing.decision,
                    )
            if not timing.ok:
                if prewarm_task is not None and not prewarm_task.done():
                    prewarm_task.cancel()
                    try:
                        await prewarm_task
                    except (asyncio.CancelledError, Exception):
                        pass
                reject_reason = f"timing 1m inválido: lag +{timing.lag_sec:.2f}s"
                self._set_last_order_attempt(sym, direction, "failed", reject_reason)
                if journal_cid:
                    _j = get_journal()
                    if _j._conn is not None:
                        _j._conn.execute(
                            """UPDATE candidates
                               SET decision='REJECTED_TIMING',
                                   reject_reason=?,
                                   outcome='TIMING_SKIPPED'
                               WHERE id=?""",
                            (reject_reason, journal_cid),
                        )
                        _j._conn.commit()
                return False
            # Keep caller duration_sec (multi-duration). Do not overwrite from timing.

        icon = "🟢" if direction == "call" else "🔴"
        log.info("[%s] %s ENTRADA[%s] %s  %s  $%.2f  %ds  | %s",
                 strategy_origin, icon, stage, direction.upper(), sym, amount, duration_sec, reason)

        # Fix F6k: 1 sola instancia de Quotex. El HTF scanner corre en
        # run_forever sobre el MISMO WebSocket #1 que buy() usa. Aunque
        # lo pausamos, el run_forever sigue vivo y el broker no confirma
        # buy() (buy_timeout). Solución: CANCELAR la task HTF antes de
        # buy() (WS#1 100% limpio) y RECREARLA después. Pruebas S2/S3/S5
        # confirmaron que scan masivo + client.buy() SIN HTF -> status=True.
        htf_task = getattr(self.bot, "_htf_task", None)
        if htf_task is not None and not htf_task.done():
            htf_task.cancel()
            try:
                await htf_task
            except (asyncio.CancelledError, Exception):
                pass
        # Fix event-loop: yield control para que corutinas pendientes
        # (incl. callbacks del WS thread que setean buy_id) se ejecuten
        # ANTES de enviar la orden. Sin esto, el loop puede estar saturado
        # por tareas del scan/HTF y el polling de buy_id no arranca a tiempo.
        await asyncio.sleep(0)
        if prewarm_task is not None:
            try:
                await prewarm_task
            except (asyncio.CancelledError, Exception) as exc:
                log.warning("  ⚠ prewarm/reconexión falló: %s — reintento síncrono", exc)
                await self._reconnect_if_needed("prewarm-retry")
        else:
            await self._reconnect_if_needed("prewarm")
        try:
            # M1 micro-trend gate: after timing + prewarm, before buy.
            # multi_leg=True skips re-check (first leg already confirmed).
            if (
                bool(getattr(_cfg, "M1_MICRO_CONFIRM_ENABLED", True))
                and not multi_leg
            ):
                m1_ok, m1_reason = await self._m1_micro_confirm_pre_buy(sym, direction)
                if not m1_ok:
                    log.info(
                        "⏭ M1 micro: %s %s blocked (%s)",
                        sym,
                        direction.upper(),
                        m1_reason,
                    )
                    self._set_last_order_attempt(sym, direction, "failed", m1_reason)
                    if journal_cid:
                        _j = get_journal()
                        if _j._conn is not None:
                            _j._conn.execute(
                                """UPDATE candidates
                                   SET decision='REJECTED_M1_MICRO',
                                       reject_reason=?,
                                       outcome='M1_MICRO_SKIPPED'
                                   WHERE id=?""",
                                (m1_reason, journal_cid),
                            )
                            _j._conn.commit()
                    return False

            self._set_last_order_attempt(sym, direction, "sending")
            log.info("  → buy() llamando a %s %s $%.2f %ds (event loop limpio)",
                     direction.upper(), sym, amount, duration_sec)
            ok, oid, open_price, order_ref, reject_reason = await place_order(
                self.client,
                sym,
                direction,
                amount,
                duration_sec,
                self.bot.dry_run,
                account_type=self.bot.account_type,
            )
        finally:
            # Recrear la task HTF para el próximo ciclo (also after M1 block).
            try:
                if getattr(self.bot, "htf_scanner", None) is not None:
                    self.bot._htf_task = asyncio.create_task(
                        self.bot.htf_scanner.run_forever()
                    )
            except Exception as exc:
                log.warning("  ⚠ No se pudo recrear la task HTF: %s", exc)
        if not ok:
            fail_reason = reject_reason or "broker_rejected"
            log.error("  ✗ Fallo al colocar orden en %s | reason=%s", sym, fail_reason)
            self._set_last_order_attempt(sym, direction, "failed", fail_reason)
            # Hard fails quarantine longer; soft rejects keep short cooldown.
            if not hasattr(self.bot, "failed_assets") or self.bot.failed_assets is None:
                self.bot.failed_assets = {}
            if self._is_hard_order_fail(fail_reason):
                self.bot.failed_assets[sym] = int(ORDER_FAIL_QUARANTINE_CYCLES)
            else:
                self.bot.failed_assets[sym] = 2
            # Marcar en el journal que la orden fue rechazada por el broker
            if journal_cid:
                _j = get_journal()
                if _j._conn is not None:
                    _j._conn.execute(
                        "UPDATE candidates SET outcome='BROKER_REJECTED', reject_reason=? WHERE id=?",
                        (fail_reason[:500], journal_cid)
                    )
                    _j._conn.commit()
            return False

        self._set_last_order_attempt(sym, direction, "accepted")
        if register_entry_asset:
            self._register_successful_entry_asset(sym)

        tkey = make_trade_key(sym, int(duration_sec))
        self.bot.trades[tkey] = TradeState(
            asset=sym, direction=direction, amount=amount,
            entry_price=open_price, ceiling=zone.ceiling, floor=zone.floor,
            order_id=oid, order_ref=order_ref, stage=stage,
            journal_id=journal_cid,
            strategy_origin=strategy_origin,
            duration_sec=int(duration_sec),
            payout=int(payout),
            score_original=float(score_original),
            black_box_cid=int(black_box_cid),
            trade_key=tkey,
        )
        trade = self.bot.trades[tkey]
        # Persist duration on black-box candidate when linked.
        if black_box_cid:
            try:
                get_black_box().update_candidate(
                    int(black_box_cid),
                    duration_sec=int(duration_sec),
                )
            except Exception:
                pass
        hub = getattr(self.bot, "_hub_scanner", None)
        if hub is not None:
            hub.record_entry(
                strategy=strategy_origin,
                asset=sym,
                direction=direction,
                duration_sec=int(duration_sec),
                entry_price=float(open_price) if open_price else None,
            )
        self._track_task(asyncio.create_task(
            self._resolve_trade_after_expiry(tkey, trade),
            name=f"resolve:{tkey}:{stage}",
        ))
        if strategy_origin == "STRAT-A" and stage == "initial" and not multi_leg:
            self._track_task(asyncio.create_task(
                self._monitor_trade_live(sym, trade),
                name=f"monitor:{sym}",
            ))
        # Actualizar el journal con el order_id real del broker (aunque sea vacío)
        if journal_cid:
            stored_oid = oid if oid else f"REF-{order_ref}" if order_ref else "BROKER_NO_ID"
            _j = get_journal()
            if _j._conn is not None:
                _j._conn.execute(
                    "UPDATE candidates SET order_id=? WHERE id=?",
                    (stored_oid, journal_cid)
                )
                _j._conn.commit()

        self.bot.stats["entries"] = self.bot.stats.get("entries", 0) + 1
        self.bot.stats["strat_a_signals"] = self.bot.stats.get("strat_a_signals", 0) + 1

        # Notify session manager once per multi-batch (first leg only)
        if self.session_manager is not None and not multi_leg:
            self.session_manager.enter_trade()
            self.session_manager.set_trade_reason(reason, {
                "asset": sym,
                "direction": direction,
                "amount": amount,
                "strategy": strategy_origin,
                "score": score_original,
                "payout": payout,
                "duration_sec": int(duration_sec),
            })

        if oid:
            log.info("  ✓ Orden aceptada  id=%s  open=%.5f  ref=%s", oid, open_price, order_ref)
        else:
            log.warning("  ⚠ Orden enviada pero broker NO devolvió id  open=%.5f  ref=%s", open_price, order_ref)
        try:
            bal = await self.client.get_balance()
            log.info("  💰 Balance: %.2f USD", bal)
        except asyncio.CancelledError:
            log.info("Interrupción durante lectura de balance; continuando cierre limpio.")
            return True
        except Exception:
            pass
        return True

    def _register_filled_trade(
        self,
        *,
        sym: str,
        direction: str,
        amount: float,
        zone: ConsolidationZone,
        stage: str,
        journal_cid: int,
        strategy_origin: str,
        duration_sec: int,
        payout: int,
        score_original: float,
        black_box_cid: int,
        oid: Any,
        open_price: Any,
        order_ref: Any,
    ) -> TradeState:
        """Register one filled leg (TradeState, resolve task, hub, black-box)."""
        tkey = make_trade_key(sym, int(duration_sec))
        self.bot.trades[tkey] = TradeState(
            asset=sym,
            direction=direction,
            amount=amount,
            entry_price=open_price,
            ceiling=zone.ceiling,
            floor=zone.floor,
            order_id=oid,
            order_ref=order_ref,
            stage=stage,
            journal_id=journal_cid,
            strategy_origin=strategy_origin,
            duration_sec=int(duration_sec),
            payout=int(payout),
            score_original=float(score_original),
            black_box_cid=int(black_box_cid),
            trade_key=tkey,
        )
        trade = self.bot.trades[tkey]
        if black_box_cid:
            try:
                get_black_box().update_candidate(
                    int(black_box_cid),
                    duration_sec=int(duration_sec),
                )
            except Exception:
                pass
        hub = getattr(self.bot, "_hub_scanner", None)
        if hub is not None:
            hub.record_entry(
                strategy=strategy_origin,
                asset=sym,
                direction=direction,
                duration_sec=int(duration_sec),
                entry_price=float(open_price) if open_price else None,
            )
        self._track_task(asyncio.create_task(
            self._resolve_trade_after_expiry(tkey, trade),
            name=f"resolve:{tkey}:{stage}",
        ))
        if journal_cid:
            stored_oid = oid if oid else f"REF-{order_ref}" if order_ref else "BROKER_NO_ID"
            _j = get_journal()
            if _j._conn is not None:
                _j._conn.execute(
                    "UPDATE candidates SET order_id=? WHERE id=?",
                    (stored_oid, journal_cid),
                )
                _j._conn.commit()
        self.bot.stats["entries"] = self.bot.stats.get("entries", 0) + 1
        self.bot.stats["strat_a_signals"] = self.bot.stats.get("strat_a_signals", 0) + 1
        return trade

    async def enter_multi_duration(
        self,
        sym: str,
        direction: str,
        amount: float,
        zone: ConsolidationZone,
        reason: str,
        stage: str,
        *,
        durations: Optional[Tuple[int, ...]] = None,
        journal_cids: Optional[List[int]] = None,
        signal_ts: Optional[int] = None,
        strategy_origin: str = "STRAT-A",
        payout: int = MIN_PAYOUT,
        score_original: float = 0.0,
        black_box_cids: Optional[List[int]] = None,
    ) -> bool:
        """Place all multi-duration legs after one open-sync + prewarm + M1 check.

        With MULTI_DURATION_PARALLEL, legs fire via asyncio.gather so entry times
        align for A/B expiry comparison. Returns True if at least one leg fills.
        """
        if durations is None:
            durations = tuple(
                int(d) for d in getattr(_cfg, "MULTI_DURATION_SECS", (60, 300, 600, 900))
            )
        if not durations:
            return False

        ignore_blocks = bool(
            getattr(_cfg, "MULTI_DURATION_IGNORE_SESSION_BLOCKS", False)
        )
        blocked, block_reason = self._massaniello_session_blocks_entry()
        if blocked:
            if ignore_blocks:
                log.debug(
                    "📊 Multi-duration data mode: ignoring session block (%s) for %s",
                    block_reason,
                    sym,
                )
            else:
                log.info("⏭ %s: entrada bloqueada — %s", sym, block_reason)
                return False

        # Continuous mode: rate-limit once for the whole batch.
        if hasattr(self.bot, "continuous") and self.bot.continuous is not None:
            cont = self.bot.continuous
            if not cont.can_enter_now():
                wait = cont.seconds_until_next_entry()
                log.debug(
                    "⏭ %s: entrada bloqueada (continuous rate limit) — %.0fs restantes",
                    sym,
                    wait,
                )
                return False
            cont.record_entry()

        if (
            self.bot.compensation_pending
            and stage != "martin"
            and not self._uses_massaniello()
        ):
            lock_reason = "gale activo: solo operación martingala cuenta"
            log.info("⏭ %s: entrada bloqueada — %s", sym, lock_reason)
            return False

        can_enter_asset, same_asset_reason = self._can_enter_asset_now(sym, stage)
        if not can_enter_asset:
            self.bot.stats["rejected_same_asset_limit"] = (
                self.bot.stats.get("rejected_same_asset_limit", 0) + 1
            )
            log.info("⏭ %s: entrada bloqueada — %s", sym, same_asset_reason)
            return False

        # Single open-sync + prewarm for the whole batch.
        self._set_last_order_attempt(sym, direction, "waiting_open")
        prewarm_task = asyncio.create_task(self._reconnect_if_needed("prewarm-multi"))
        timing = await self._resolve_entry_timing(
            skip_open_wait=False,
            signal_ts=signal_ts,
        )
        self.entry_sync.log_order_timing(sym, timing)
        first_jcid = 0
        if journal_cids:
            first_jcid = int(journal_cids[0] or 0) if journal_cids else 0
        if first_jcid:
            _j = get_journal()
            if _j._conn is not None:
                _j.log_entry_timing(
                    candidate_id=first_jcid,
                    time_since_open=timing.time_since_open_sec,
                    secs_to_close=timing.secs_to_close_sec,
                    duration_sec=int(durations[0]),
                    timing_decision=timing.decision,
                )
        if not timing.ok:
            if prewarm_task is not None and not prewarm_task.done():
                prewarm_task.cancel()
                try:
                    await prewarm_task
                except (asyncio.CancelledError, Exception):
                    pass
            reject_reason = f"timing 1m inválido: lag +{timing.lag_sec:.2f}s"
            self._set_last_order_attempt(sym, direction, "failed", reject_reason)
            return False

        icon = "🟢" if direction == "call" else "🔴"
        log.info(
            "[%s] %s ENTRADA[%s] multi %s  %s  $%.2f  legs=%s  | %s",
            strategy_origin,
            icon,
            stage,
            direction.upper(),
            sym,
            amount,
            "/".join(f"{int(d)}s" for d in durations),
            reason,
        )

        # Cancel HTF once so buy() has a clean WS (same fix as enter_trade).
        htf_task = getattr(self.bot, "_htf_task", None)
        if htf_task is not None and not htf_task.done():
            htf_task.cancel()
            try:
                await htf_task
            except (asyncio.CancelledError, Exception):
                pass
        await asyncio.sleep(0)
        try:
            await prewarm_task
        except (asyncio.CancelledError, Exception) as exc:
            log.warning("  ⚠ prewarm/reconexión falló: %s — reintento síncrono", exc)
            await self._reconnect_if_needed("prewarm-multi-retry")

        # M1 micro-trend once for the batch.
        if bool(getattr(_cfg, "M1_MICRO_CONFIRM_ENABLED", True)):
            m1_ok, m1_reason = await self._m1_micro_confirm_pre_buy(sym, direction)
            if not m1_ok:
                log.info(
                    "⏭ M1 micro: %s %s blocked (%s)",
                    sym,
                    direction.upper(),
                    m1_reason,
                )
                self._set_last_order_attempt(sym, direction, "failed", m1_reason)
                try:
                    if getattr(self.bot, "htf_scanner", None) is not None:
                        self.bot._htf_task = asyncio.create_task(
                            self.bot.htf_scanner.run_forever()
                        )
                except Exception as exc:
                    log.warning("  ⚠ No se pudo recrear la task HTF: %s", exc)
                return False

        self._set_last_order_attempt(sym, direction, "sending")
        batch_ts = time.time()
        parallel = bool(getattr(_cfg, "MULTI_DURATION_PARALLEL", True))
        results: list[Any] = []
        try:
            if parallel:
                results = list(
                    await asyncio.gather(
                        *[
                            place_order(
                                self.client,
                                sym,
                                direction,
                                amount,
                                int(d),
                                self.bot.dry_run,
                                account_type=self.bot.account_type,
                            )
                            for d in durations
                        ],
                        return_exceptions=True,
                    )
                )
            else:
                # Fast sequential fallback: no re-sync / re-prewarm between legs.
                for d in durations:
                    try:
                        results.append(
                            await place_order(
                                self.client,
                                sym,
                                direction,
                                amount,
                                int(d),
                                self.bot.dry_run,
                                account_type=self.bot.account_type,
                            )
                        )
                    except Exception as exc:
                        results.append(exc)
        finally:
            try:
                if getattr(self.bot, "htf_scanner", None) is not None:
                    self.bot._htf_task = asyncio.create_task(
                        self.bot.htf_scanner.run_forever()
                    )
            except Exception as exc:
                log.warning("  ⚠ No se pudo recrear la task HTF: %s", exc)

        filled: list[int] = []
        for i, d in enumerate(durations):
            jcid = 0
            if journal_cids and i < len(journal_cids):
                jcid = int(journal_cids[i] or 0)
            bbcid = 0
            if black_box_cids and i < len(black_box_cids):
                bbcid = int(black_box_cids[i] or 0)
            result = results[i] if i < len(results) else None
            if isinstance(result, BaseException):
                log.error(
                    "  ✗ Multi-leg %ds exception %s: %s",
                    int(d),
                    sym,
                    result,
                )
                if jcid:
                    _j = get_journal()
                    if _j._conn is not None:
                        _j._conn.execute(
                            "UPDATE candidates SET outcome='BROKER_REJECTED', "
                            "reject_reason=? WHERE id=?",
                            (str(result)[:500], jcid),
                        )
                        _j._conn.commit()
                continue
            if not result or not result[0]:
                fail_reason = ""
                if result and len(result) >= 5:
                    fail_reason = result[4] or "broker_rejected"
                else:
                    fail_reason = "broker_rejected"
                log.error(
                    "  ✗ Fallo multi-leg %ds en %s | reason=%s",
                    int(d),
                    sym,
                    fail_reason,
                )
                if jcid:
                    _j = get_journal()
                    if _j._conn is not None:
                        _j._conn.execute(
                            "UPDATE candidates SET outcome='BROKER_REJECTED', "
                            "reject_reason=? WHERE id=?",
                            (fail_reason[:500], jcid),
                        )
                        _j._conn.commit()
                continue
            ok, oid, open_price, order_ref, _reject = result
            self._register_filled_trade(
                sym=sym,
                direction=direction,
                amount=amount,
                zone=zone,
                stage=stage,
                journal_cid=jcid,
                strategy_origin=strategy_origin,
                duration_sec=int(d),
                payout=int(payout),
                score_original=float(score_original),
                black_box_cid=bbcid,
                oid=oid,
                open_price=open_price,
                order_ref=order_ref,
            )
            filled.append(int(d))
            if oid:
                log.info(
                    "  ✓ Multi-leg %ds id=%s open=%.5f ref=%s",
                    int(d),
                    oid,
                    open_price,
                    order_ref,
                )
            else:
                log.warning(
                    "  ⚠ Multi-leg %ds sin id open=%.5f ref=%s",
                    int(d),
                    open_price,
                    order_ref,
                )

        if not filled:
            self._set_last_order_attempt(sym, direction, "failed", "multi_batch_empty")
            if not hasattr(self.bot, "failed_assets") or self.bot.failed_assets is None:
                self.bot.failed_assets = {}
            self.bot.failed_assets[sym] = 2
            return False

        self._set_last_order_attempt(sym, direction, "accepted")
        self._register_successful_entry_asset(sym)
        if self.session_manager is not None:
            self.session_manager.enter_trade()
            self.session_manager.set_trade_reason(reason, {
                "asset": sym,
                "direction": direction,
                "amount": amount,
                "strategy": strategy_origin,
                "score": score_original,
                "payout": payout,
                "duration_sec": int(filled[0]),
                "multi_durations": list(filled),
                "batch_ts": batch_ts,
            })

        log.info(
            "📊 Multi-duration batch ts=%.3f %s %s → filled=%s (all=%s parallel=%s)",
            batch_ts,
            sym,
            direction.upper(),
            "/".join(f"{d}s" for d in filled),
            "/".join(f"{int(d)}s" for d in durations),
            parallel,
        )
        if len(filled) < len(durations):
            log.warning(
                "⚠ Multi-duration partial fill %s: ok=%s missing=%s",
                sym,
                filled,
                [int(d) for d in durations if int(d) not in filled],
            )
        try:
            bal = await self.client.get_balance()
            log.info("  💰 Balance: %.2f USD", bal)
        except asyncio.CancelledError:
            log.info("Interrupción durante lectura de balance; continuando cierre limpio.")
            return True
        except Exception:
            pass
        return True