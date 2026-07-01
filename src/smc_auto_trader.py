"""Trader autónomo SMC: velas multi-TF, decisión y envío de órdenes."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from pyquotex.stable_api import Quotex  # type: ignore

from config import MIN_PAYOUT
from connection import fetch_candles, get_open_assets, place_order
from models import Candle
from smc_decision_engine import SMCDecisionEngine, Signal

log = logging.getLogger("smc_auto_trader")

TF_M1 = 60
TF_M15 = 900
TF_H4 = 14400
TF_H1 = 3600

H4_COUNT = 120
M15_COUNT = 80
M1_COUNT = 40
H4_MIN_CANDLES = 10

DEFAULT_ASSET = "EURUSD_otc"
DEFAULT_AMOUNT = 5.0
DEFAULT_DURATION = 60
DEFAULT_MIN_PAYOUT = max(MIN_PAYOUT, 75)
DEFAULT_INTERVAL_SEC = 60
TRADE_COOLDOWN_SEC = 30.0
MAX_CONSECUTIVE_ERRORS = 10


@dataclass
class RunCycleResult:
    signal: Signal
    reason: str
    order_placed: bool
    order_id: str = ""
    asset: str = ""
    direction: str = ""
    last_trade_ts: float = 0.0


class SMCAutoTrader:
    def __init__(
        self,
        client: Quotex,
        asset: str = DEFAULT_ASSET,
        amount: float = DEFAULT_AMOUNT,
        duration: int = DEFAULT_DURATION,
        min_payout: int = DEFAULT_MIN_PAYOUT,
        dry_run: bool = True,
        account_type: str = "PRACTICE",
        cooldown_sec: float = TRADE_COOLDOWN_SEC,
    ) -> None:
        self.client = client
        self.asset = asset
        self.amount = amount
        self.duration = duration
        self.min_payout = min_payout
        self.dry_run = dry_run
        self.account_type = account_type
        self.cooldown_sec = cooldown_sec
        self._last_trade_ts = 0.0

    async def fetch_all_timeframes(
        self,
        asset: Optional[str] = None,
    ) -> Tuple[List[Candle], List[Candle], List[Candle], str]:
        symbol = asset or self.asset
        h4 = await fetch_candles(self.client, symbol, TF_H4, H4_COUNT)
        tf_label = "H4"

        if len(h4) < H4_MIN_CANDLES:
            h4 = await fetch_candles(self.client, symbol, TF_H1, H4_COUNT)
            tf_label = "H1(fallback)"

        m15 = await fetch_candles(self.client, symbol, TF_M15, M15_COUNT)
        m1 = await fetch_candles(self.client, symbol, TF_M1, M1_COUNT)
        return h4, m15, m1, tf_label

    async def find_open_asset(
        self,
        preferred: Optional[str] = None,
        allow_fallback: bool = True,
    ) -> Optional[Tuple[str, int]]:
        assets = await get_open_assets(self.client, self.min_payout)
        if not assets:
            return None

        target = preferred or self.asset
        for sym, payout in assets:
            if sym == target:
                return sym, payout

        if allow_fallback:
            return assets[0]
        return None

    async def run_once(self) -> RunCycleResult:
        log.info("── Inicio de ciclo  asset=%s ──", self.asset)

        try:
            h4, m15, m1, tf_label = await self.fetch_all_timeframes()
        except Exception as exc:
            log.error("Error obteniendo velas: %s", exc)
            return RunCycleResult(
                signal=Signal.WAIT,
                reason=f"error_velas:{exc}",
                order_placed=False,
            )

        log.info("Velas: %s=%d  M15=%d  M1=%d", tf_label, len(h4), len(m15), len(m1))

        if len(h4) < H4_MIN_CANDLES or len(m15) < 6 or len(m1) < 6:
            log.warning("Datos insuficientes para análisis SMC, saltando ciclo.")
            return RunCycleResult(
                signal=Signal.WAIT,
                reason="datos_insuficientes",
                order_placed=False,
            )

        engine = SMCDecisionEngine(h4, m15, m1)
        decision = engine.decide()

        zone_txt = "ninguna"
        if decision.best_zone:
            z = decision.best_zone
            zone_txt = f"[{z.bottom:.5f}–{z.top:.5f}]"

        log.info(
            "SMC → SIGNAL=%s  H4=%s  M15=%s  ZONA=%s",
            decision.signal.value,
            decision.h4_bias.value,
            decision.m15_bias.value,
            zone_txt,
        )
        log.info("Razón: %s", decision.reason)

        if decision.signal == Signal.WAIT:
            return RunCycleResult(
                signal=Signal.WAIT,
                reason=decision.reason,
                order_placed=False,
            )

        now = time.time()
        if self._last_trade_ts and (now - self._last_trade_ts) < self.cooldown_sec:
            remaining = int(self.cooldown_sec - (now - self._last_trade_ts))
            log.info("Cooldown activo: %ds restantes.", remaining)
            return RunCycleResult(
                signal=decision.signal,
                reason=f"cooldown:{remaining}s",
                order_placed=False,
                last_trade_ts=self._last_trade_ts,
            )

        open_asset = await self.find_open_asset()
        if not open_asset:
            log.warning(
                "Señal %s pero no hay activo OTC abierto con payout ≥%d%%.",
                decision.signal.value,
                self.min_payout,
            )
            return RunCycleResult(
                signal=decision.signal,
                reason="sin_activo_abierto",
                order_placed=False,
            )

        trade_symbol, payout = open_asset
        direction = "call" if decision.signal == Signal.BUY else "put"

        log.info(
            "EJECUTANDO %s  activo=%s payout=%d%%  monto=%.2f  duración=%ds",
            direction.upper(),
            trade_symbol,
            payout,
            self.amount,
            self.duration,
        )

        if self.dry_run:
            log.info("[DRY-RUN] Orden NO enviada (usa dry_run=False para enviar realmente).")
            ok, order_id, _, _, reject = await place_order(
                self.client,
                trade_symbol,
                direction,
                self.amount,
                self.duration,
                dry_run=True,
                account_type=self.account_type,
            )
            return RunCycleResult(
                signal=decision.signal,
                reason=decision.reason,
                order_placed=ok,
                order_id=order_id,
                asset=trade_symbol,
                direction=direction,
                last_trade_ts=self._last_trade_ts,
            )

        try:
            ok, order_id, _, _, reject = await place_order(
                self.client,
                trade_symbol,
                direction,
                self.amount,
                self.duration,
                dry_run=False,
                account_type=self.account_type,
            )
        except Exception as exc:
            log.error("Excepción al enviar orden: %s", exc)
            return RunCycleResult(
                signal=decision.signal,
                reason=f"order_exception:{exc}",
                order_placed=False,
                asset=trade_symbol,
                direction=direction,
            )

        if not ok:
            log.error("✗ Orden rechazada por el broker. info=%s", reject)
            return RunCycleResult(
                signal=decision.signal,
                reason=f"rejected:{reject}",
                order_placed=False,
                asset=trade_symbol,
                direction=direction,
            )

        self._last_trade_ts = time.time()
        log.info("✓ ORDEN ACEPTADA  id=%s", order_id)
        return RunCycleResult(
            signal=decision.signal,
            reason=decision.reason,
            order_placed=True,
            order_id=order_id,
            asset=trade_symbol,
            direction=direction,
            last_trade_ts=self._last_trade_ts,
        )

    async def run_loop(self, interval_sec: int = DEFAULT_INTERVAL_SEC) -> None:
        consecutive_errors = 0
        log.info(
            "=== SMC Auto Trader iniciado === asset=%s amount=%.2f duration=%ds "
            "interval=%ds dry_run=%s",
            self.asset,
            self.amount,
            self.duration,
            interval_sec,
            self.dry_run,
        )

        try:
            while True:
                cycle_start = time.time()
                try:
                    await self.run_once()
                    consecutive_errors = 0
                except Exception as exc:
                    consecutive_errors += 1
                    log.error("Error en ciclo: %s", exc, exc_info=True)
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        log.critical("Demasiados fallos de reconexión. Deteniendo.")
                        break

                elapsed = time.time() - cycle_start
                sleep_for = max(0.0, interval_sec - elapsed)
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
        except KeyboardInterrupt:
            log.info("Detenido por el usuario (Ctrl+C).")
        finally:
            log.info("=== SMC Auto Trader detenido ===")