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
    DURATION_SEC,
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
    PENDING_RECONCILE_AGE_MIN,
    RISK_MANAGER,
    TF_1M,
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
from connection import create_trading_client, fetch_candles_with_retry, get_open_assets, place_order
from entry_sync import EntrySynchronizer
from entry_scorer import CandidateEntry
from models import ConsolidationZone, EntryTimingInfo, MartinPending, TradeState
from strat_a import price_at_ceiling, price_at_floor
from trade_journal import get_journal
from black_box_recorder import get_black_box
from stochastic_m15 import compute_stoch
from strat_f_postmortem import analyze_postmortem
from candle_patterns import fetch_candles_1m

if TYPE_CHECKING:
    from pyquotex.stable_api import Quotex

log = logging.getLogger("executor")

class TradeExecutor:
    def __init__(self, client, bot, trade_client=None, htf_scanner=None):
        self.client = client
        self.bot = bot
        # Cliente de trading LIMPIO (separado del de datos) para buy().
        # Si es None, usa client (fallback compatibilidad).
        self.trade_client = trade_client if trade_client is not None else client
        # Referencia directa al HTF scanner para pausarlo durante la orden.
        self.htf = htf_scanner
        self.entry_sync = EntrySynchronizer()

    async def _ensure_trade_client_alive(self) -> None:
        """Crea un trade_client FRESCO antes de cada orden.

        Fix definitivo: pyquotex.buy() Internamente hace:
          1. start_candles_stream() — subscribe a velas en vivo
          2. get_server_time() — profile + server time
          3. api.buy() → settings_apply + tick + orders/open
          4. Espera buy_id por duration+5 segundos

        Todos esos pasos envían mensajes WS. Si el trade_client estuvo idle
        durante el scan (60-90s), el WS puede parecer vivo (get_balance pasa)
        pero los flujos internos de buy() fallan silenciosamente.

        Solución: crear un trade_client FRESCO (igual que compra_venta_m5_otc.py
        que funciona en <2s). Un connect + buy inmediato = WS limpio.
        """
        try:
            account_type = getattr(self.bot, "account_type", "PRACTICE")
            tc, tc_reason = await create_trading_client(
                email=EMAIL, password=PASSWORD, account_type=account_type,
            )
            if tc is not None:
                self.trade_client = tc
                log.info("  ✓ trade_client fresco creado para orden")
            else:
                log.error("  ✗ No se pudo crear trade_client: %s", tc_reason)
        except Exception as exc:
            log.error("  ✗ Excepción creando trade_client: %s", exc)

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

    def _maybe_stop_massaniello_session(self) -> None:
        if not self._uses_massaniello():
            return
        blocked, reason = self._massaniello_session_blocks_entry()
        if blocked:
            # Secuencia 5/3 cumplida (3 ITM) o fallida (3 losses / expirada /
            # sin ops): se detiene el escaneo y se reinicia el Massaniello en
            # el capital virtual para el proximo arranque.
            self.bot.session_stop_hit = True
            vcap = self._massaniello_virtual()
            if vcap is not None:
                from massaniello_risk import MassanielloRiskManager
                self.bot.massaniello = MassanielloRiskManager()
                self.set_session_start_balance(vcap)
            log.info("🛑 Sesión Massaniello finalizada — %s (escaneo detenido)", reason)

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
        Nota: martingala queda exenta para no romper recuperación de ciclo.
        """
        if stage == "martin":
            return True, "MARTIN_EXEMPT"
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
                duration_sec=DURATION_SEC,
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
            duration_sec=DURATION_SEC,
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
                    duration_sec=DURATION_SEC,
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
            await asyncio.sleep(wait_sec)
        await self._resolve_trade(trade, asset)
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
                    duration_sec=DURATION_SEC,
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

                # Compatibilidad: si guardamos REF-<id>, intentar check_win por id numérico.
                if oid.startswith("REF-"):
                    ref_id = int(oid.split("-", 1)[1])
                    win_val = await self.client.check_win(ref_id)
                    if isinstance(win_val, (int, float)):
                        profit = float(win_val)
                        outcome = "WIN" if profit > 0 else "LOSS"
                    elif isinstance(win_val, bool):
                        outcome = "WIN" if win_val else "LOSS"
                else:
                    status, payload = await self.client.get_result(oid)
                    if status == "win":
                        outcome = "WIN"
                        if isinstance(payload, dict):
                            profit = float(payload.get("profitAmount", 0) or 0)
                    elif status == "loss":
                        outcome = "LOSS"
                        if isinstance(payload, dict):
                            profit = float(payload.get("profitAmount", 0) or 0)

                if outcome in {"WIN", "LOSS"}:
                    journal._conn.execute(
                        "UPDATE candidates SET outcome=?, profit=?, closed_at=? WHERE id=? AND outcome='PENDING'",
                        (outcome, float(profit), datetime.now(tz=BROKER_TZ).isoformat(), rid),
                    )
                    resolved += 1
                else:
                    journal._conn.execute(
                        "UPDATE candidates SET outcome='UNRESOLVED', closed_at=? WHERE id=? AND outcome='PENDING'",
                        (datetime.now(tz=BROKER_TZ).isoformat(), rid),
                    )
                    unresolved += 1
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
            "duration_sec": DURATION_SEC,
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
        return await self.entry_sync.sync_and_validate(signal_ts)
    async def _resolve_trade(self, trade: "TradeState", sym: str) -> None:
        """
        Consulta el resultado de una operación expirada al broker
        y actualiza el journal con WIN / LOSS / UNRESOLVED sin bloquear el bot.
        """
        if trade.resolved:
            return

        journal = get_journal()
        has_id  = bool(trade.order_id) and not trade.order_id.startswith("DRY-")
        has_ref = trade.order_ref > 0
        if self.bot.dry_run:
            trade.resolved = True
            if self.bot.trades.get(sym) is trade:
                self.bot.trades.pop(sym, None)
            hub = getattr(self.bot, "_hub_scanner", None)
            if hub is not None:
                hub.close_active_trade()
            return

        outcome = "UNRESOLVED"
        profit  = 0.0
        if has_id or has_ref:
            for attempt in range(1, MARTIN_RESOLVE_MAX_ATTEMPTS + 1):
                try:
                    if has_ref:
                        win_val = await asyncio.wait_for(
                            self.client.check_win(trade.order_ref),
                            timeout=MARTIN_RESOLVE_TIMEOUT_SEC,
                        )
                        if isinstance(win_val, bool):
                            outcome = "WIN" if win_val else "LOSS"
                            profit = trade.amount * 0.8 if win_val else -abs(trade.amount)
                            break
                        if isinstance(win_val, (int, float)):
                            profit = float(win_val)
                            outcome = "WIN" if profit > 0 else "LOSS"
                            break
                    elif has_id:
                        status, payload = await asyncio.wait_for(
                            self.client.get_result(trade.order_id),
                            timeout=MARTIN_RESOLVE_TIMEOUT_SEC,
                        )
                        if status == "win":
                            outcome = "WIN"
                            if isinstance(payload, dict):
                                profit = float(payload.get("profitAmount", 0) or 0)
                            break
                        if status == "loss":
                            outcome = "LOSS"
                            if isinstance(payload, dict):
                                profit = float(payload.get("profitAmount", 0) or 0)
                            if profit == 0:
                                profit = -abs(trade.amount)
                            break
                except asyncio.TimeoutError:
                    log.debug("%s: check_win timeout intento %d/%d", sym, attempt, MARTIN_RESOLVE_MAX_ATTEMPTS)
                except Exception as exc:
                    log.debug(
                        "No se pudo obtener resultado de %s / ref=%s intento %d/%d: %s",
                        trade.order_id,
                        trade.order_ref,
                        attempt,
                        MARTIN_RESOLVE_MAX_ATTEMPTS,
                        exc,
                    )

                if attempt < MARTIN_RESOLVE_MAX_ATTEMPTS:
                    await asyncio.sleep(MARTIN_RESOLVE_RETRY_SEC)

        trade.resolved = True

        if trade.journal_id:
            journal.update_outcome_by_id(row_id=trade.journal_id, outcome=outcome, profit=profit)
        else:
            journal.update_outcome(order_id=trade.order_id, outcome=outcome, profit=profit)
        await self.refresh_balance_and_risk()
        balance_now = self.bot.current_balance if self.bot.current_balance is not None else 0.0
        log.info("🏁 %s %s $%.2f | saldo: $%.2f", sym, outcome, profit, balance_now)
        self._update_cycle_after_result(outcome=outcome, profit=profit)

        # Post-mortem caja negra STRAT-F (Fase 4): solo estrategia STRAT-F.
        # En caso de pérdida, baja velas 1m post-expiry y evalúa si había OTRA
        # MEJOR ENTRADA pocos minutos después (alimenta calibración / IA).
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
                    before = bb.get_pending_candidate_before(sym)
                candles_post = []
                if before:
                    post_raw = await fetch_candles_1m(self.client, sym, count=5)
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
                    if bb_cid:
                        bb.resolve_candidate_by_id(
                            bb_cid, outcome, profit,
                            entry_price=getattr(trade, "entry_price", None),
                            candles_post=candles_post,
                            stoch_m15=before.get("stoch_m15"),
                            loss_reason=loss_reason or None,
                            improvement_hint=improvement_hint or None,
                        )
                    else:
                        bb.resolve_candidate_for_asset(
                            sym, outcome, profit,
                            entry_price=getattr(trade, "entry_price", None),
                            candles_post=candles_post,
                            stoch_m15=before.get("stoch_m15"),
                            loss_reason=loss_reason or None,
                            improvement_hint=improvement_hint or None,
                        )
                    if outcome == "LOSS":
                        log.info(
                            "[POST-MORTEM] %s %s | razon=%s | mejora=%s",
                            sym, trade.direction, loss_reason, improvement_hint,
                        )
            except Exception as exc:
                log.debug("[POST-MORTEM] %s: error (no bloquea): %s", sym, exc)

        hub = getattr(self.bot, "_hub_scanner", None)
        if hub is not None:
            hub.record_trade_result(asset=sym, outcome=outcome, profit=profit)
            hub.close_active_trade()

        if outcome == "WIN":
            self.bot.stats["strat_a_wins"] += 1
            if trade.stage == "martin":
                self.bot.stats["martin_wins"] += 1
        elif outcome == "LOSS":
            self.bot.stats["strat_a_losses"] += 1
            if trade.stage == "martin":
                self.bot.stats["martin_losses"] += 1

        self._register_asset_outcome(sym, outcome)

        # Actualizar estado de compensación para la próxima entrada
        if outcome == "WIN":
            self.bot.compensation_pending = False
            self.bot.last_closed_outcome  = "WIN"
            self.bot.pending_martin.pop(sym, None)
            self.bot.massaniello.register_win(trade.amount, trade.payout)
            self._sync_massaniello_session_start()
            if self._uses_massaniello() and hasattr(self.bot, "massaniello_persistence"):
                self.bot.massaniello_persistence.save(self.bot.massaniello)
            log.info("✅ WIN registrado — próxima entrada usará stake Massaniello")
            self._maybe_stop_massaniello_session()
        elif outcome == "LOSS":
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
            self._maybe_stop_massaniello_session()
            if not self._uses_massaniello():
                skip_martin = False
                if (not trade.martin_fired) and trade.stage != "martin":
                    if trade.score_original < 70.0:
                        log.info(
                            "⛔ %s: martingala omitida — score original %.1f < 70.0",
                            sym,
                            trade.score_original,
                        )
                        skip_martin = True
                    if not self._martin_session_available():
                        skip_martin = True
                    if not skip_martin:
                        payout_now = await self._get_asset_payout(sym, trade.payout)
                        martin_amount, _ = self._compute_compensation_amount(payout_now, trade.amount)
                        martin_amount = self._cap_martin_amount(martin_amount, self.bot.current_balance)
                        entered = await self._try_enter_martin_now(
                            asset=sym,
                            amount=martin_amount,
                            original_loss=trade.amount,
                            strategy_origin=trade.strategy_origin,
                            score_original=trade.score_original,
                            payout_hint=payout_now,
                        )
                        if not entered:
                            self.bot.pending_martin[sym] = MartinPending(
                                asset=sym,
                                amount=martin_amount,
                                original_loss=trade.amount,
                                score_original=trade.score_original,
                                created_at=datetime.now(tz=BROKER_TZ),
                            )

        if self.bot.trades.get(sym) is trade:
            self.bot.trades.pop(sym, None)

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
        """
        trade = self.open_trades_get(sym)
        if trade is None:
            return False

        if trade.resolved:
            if self.bot.trades.get(sym) is trade:
                self.bot.trades.pop(sym, None)
            return False

        elapsed = time.time() - trade.opened_at

        if elapsed > (trade.duration_sec + MARTIN_RESOLVE_GRACE_SEC + 15.0):
            await self._resolve_trade(trade, sym)

        return False
    def open_trades_get(self, sym: str) -> Optional[TradeState]:
        return self.bot.trades.get(sym)
    async def enter_trade(
        self, sym: str, direction: str, amount: float,
        zone: ConsolidationZone, reason: str, stage: str,
        journal_cid: int = 0,
        signal_ts: Optional[int] = None,
        strategy_origin: str = "STRAT-A",
        duration_sec: int = DURATION_SEC,
        payout: int = MIN_PAYOUT,
        score_original: float = 0.0,
        black_box_cid: int = 0,
    ) -> bool:
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

        if self.bot.compensation_pending and stage != "martin" and not self._uses_massaniello():
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

        can_enter_asset, same_asset_reason = self._can_enter_asset_now(sym, stage)
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

        if stage in ("initial", "martin"):
            timing = await self._sync_to_next_candle_open(signal_ts)
            self.entry_sync.log_order_timing(sym, timing)
            if journal_cid:
                _j = get_journal()
                if _j._conn is not None:
                    _j.log_entry_timing(
                        candidate_id=journal_cid,
                        time_since_open=timing.time_since_open_sec,
                        secs_to_close=timing.secs_to_close_sec,
                        duration_sec=timing.duration_sec,
                        timing_decision=timing.decision,
                    )
            if not timing.ok:
                if journal_cid:
                    reject_reason = f"timing 1m inválido: lag +{timing.lag_sec:.2f}s"
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
            duration_sec = timing.duration_sec

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
        await self._ensure_trade_client_alive()
        log.info("  → buy() llamando a %s %s $%.2f %ds (event loop limpio)",
                 direction.upper(), sym, amount, duration_sec)
        try:
            ok, oid, open_price, order_ref, reject_reason = await place_order(
                self.trade_client,
                sym,
                direction,
                amount,
                duration_sec,
                self.bot.dry_run,
                account_type=self.bot.account_type,
            )
        finally:
            # Recrear la task HTF para el próximo ciclo.
            try:
                if getattr(self.bot, "htf_scanner", None) is not None:
                    self.bot._htf_task = asyncio.create_task(
                        self.bot.htf_scanner.run_forever()
                    )
            except Exception as exc:
                log.warning("  ⚠ No se pudo recrear la task HTF: %s", exc)
        if not ok:
            log.error("  ✗ Fallo al colocar orden en %s | reason=%s", sym, reject_reason)
            # Marcar activo para skip durante 2 ciclos consecutivos.
            # failed_assets vive en el bot (consolidation_bot.py:114), no en el executor.
            self.bot.failed_assets[sym] = 2
            # Marcar en el journal que la orden fue rechazada por el broker
            if journal_cid:
                _j = get_journal()
                if _j._conn is not None:
                    _j._conn.execute(
                        "UPDATE candidates SET outcome='BROKER_REJECTED', reject_reason=? WHERE id=?",
                        (reject_reason[:500] if reject_reason else "broker_rejected", journal_cid)
                    )
                    _j._conn.commit()
            return False

        self._register_successful_entry_asset(sym)

        self.bot.trades[sym] = TradeState(
            asset=sym, direction=direction, amount=amount,
            entry_price=open_price, ceiling=zone.ceiling, floor=zone.floor,
            order_id=oid, order_ref=order_ref, stage=stage,
            journal_id=journal_cid,
            strategy_origin=strategy_origin,
            duration_sec=int(duration_sec),
            payout=int(payout),
            score_original=float(score_original),
            black_box_cid=int(black_box_cid),
        )
        trade = self.bot.trades[sym]
        hub = getattr(self.bot, "_hub_scanner", None)
        if hub is not None:
            hub.record_entry(
                strategy=strategy_origin,
                asset=sym,
                direction=direction,
                duration_sec=int(duration_sec),
                entry_price=float(open_price) if open_price else None,
            )
        self._track_task(asyncio.create_task(self._resolve_trade_after_expiry(sym, trade), name=f"resolve:{sym}:{stage}"))
        if strategy_origin == "STRAT-A" and stage == "initial":
            self._track_task(asyncio.create_task(self._monitor_trade_live(sym, trade), name=f"monitor:{sym}"))
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

        self.bot.stats["entries"] += 1
        self.bot.stats["strat_a_signals"] += 1

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