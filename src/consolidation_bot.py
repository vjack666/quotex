"""
consolidation_bot.py — Facade del bot de consolidación Quotex.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Optional, Set

for _candidate in (Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"):
    if _candidate.exists():
        for _ln in _candidate.read_text(encoding="utf-8").splitlines():
            _ln = _ln.strip()
            if _ln and not _ln.startswith("#") and "=" in _ln:
                _k, _, _v = _ln.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())
        break

from pyquotex.stable_api import Quotex  # type: ignore

import config as _config
from config import *  # noqa: F401,F403 — re-export para main.py
from connection import ConnectionManager, connect_with_retry, looks_like_connection_issue
from errors import BotError
from executor import TradeExecutor
from loop_utils import seconds_until_next_scan, sleep_with_inline_countdown
from massaniello_risk import MassanielloRiskManager
from models import ConsolidationZone, PendingReversal, TradeState
from scanner import AssetScanner

_stdout_handler = logging.StreamHandler(sys.stdout)
if hasattr(_stdout_handler.stream, "reconfigure"):
    try:
        _stdout_handler.stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        _stdout_handler,
        logging.FileHandler("consolidation_bot.log", encoding="utf-8"),
    ],
)
logging.getLogger("pyquotex").setLevel(logging.WARNING)
logging.getLogger("websocket").setLevel(logging.CRITICAL)
log = logging.getLogger("consolidation_bot")


class ConsolidationBot:
    """Orquestador: compone conexión, scanner y executor."""

    def __init__(
        self,
        client: Quotex,
        dry_run: bool,
        account_type: str = "PRACTICE",
        greylist_assets: Optional[set[str]] = None,
    ):
        self.client = client
        self.dry_run = dry_run
        self.account_type = account_type
        self.zones: dict[str, ConsolidationZone] = {}
        self.broken_zones: dict[str, float] = {}
        self.trades: dict[str, TradeState] = {}
        self.stats = {
            "scans": 0, "entries": 0, "martins": 0,
            "expired_zones": 0, "skipped": 0, "filtered_sensor": 0,
            "strat_a_signals": 0, "strat_b_signals": 0,
            "strat_a_wins": 0, "strat_a_losses": 0,
            "strat_b_wins": 0, "strat_b_losses": 0,
            "score_rejected_age": 0,
            "score_rejected_score": 0,
            "rejected_young_zone": 0,
            "martin_attempts_session": 0,
            "martin_wins": 0,
            "martin_losses": 0,
            "rejected_same_asset_limit": 0,
        }
        self.compensation_pending = False
        self.last_closed_amount = 0.0
        self.last_closed_outcome = ""
        self.session_start_balance: Optional[float] = None
        self.session_start_time: Optional[float] = None
        self.current_balance: Optional[float] = None
        self.massaniello = MassanielloRiskManager()
        self.session_stop_hit = False
        self.cycle_id = 1
        self.cycle_ops = 0
        self.cycle_wins = 0
        self.cycle_losses = 0
        self.cycle_profit = 0.0
        self.cycle_start_balance: Optional[float] = None
        self.watched_candidates: dict = {}
        self.capture_dir = BROKEN_CAPTURE_DIR
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self._followup_capture_tasks: set[asyncio.Task[Any]] = set()
        self.last_known_price: dict[str, float] = {}
        self.failed_assets: dict[str, int] = {}
        self.pending_reversals: dict[str, PendingReversal] = {}
        self.pending_martin: dict = {}
        self.accepted_scans_window: Deque[int] = deque(maxlen=ADAPTIVE_THRESHOLD_WINDOW_SCANS)
        self.current_score_threshold = ADAPTIVE_THRESHOLD_BASE
        self.last_entry_asset: Optional[str] = None
        self.last_entry_asset_streak = 0
        self.asset_loss_streaks: dict[str, int] = {}
        self.asset_blacklist_until: dict[str, float] = {}
        self.order_blocks_by_asset: dict = {}
        self.ma_state_by_asset: dict = {}
        self._trade_tasks: set[asyncio.Task[Any]] = set()
        self.greylist_assets = set(GREYLIST_ASSETS)
        if greylist_assets is not None:
            self.greylist_assets = {a.strip() for a in greylist_assets if a and a.strip()}

        self.connection_mgr = ConnectionManager(client)
        self.executor = TradeExecutor(client, self)
        self.scanner = AssetScanner(self, self.executor)

    def set_session_start_balance(self, balance: float) -> None:
        self.executor.set_session_start_balance(balance)

    async def scan_all(self) -> None:
        await self.scanner.scan_all()

    async def ensure_connection(self) -> bool:
        return await self.connection_mgr.ensure_connection(self.account_type)

    async def reconcile_pending_candidates(self, max_age_minutes: Optional[float] = None) -> None:
        await self.executor.reconcile_pending_candidates(max_age_minutes)

    async def refresh_balance_and_risk(self) -> bool:
        return await self.executor.refresh_balance_and_risk()

    async def shutdown_background_tasks(self) -> None:
        await self.executor.shutdown_background_tasks()

    def log_stats(self) -> None:
        risk_txt = ""
        if self.session_start_balance and self.current_balance:
            dd = (self.session_start_balance - self.current_balance) / self.session_start_balance
            risk_txt = f"  Drawdown:{dd*100:.1f}%"
        cycle_txt = (
            f"  Ciclo#{self.cycle_id} {self.cycle_wins}W/{self.cycle_losses}L "
            f"ops:{self.cycle_ops}/{CYCLE_MAX_OPERATIONS}"
        )
        log.info(
            "📊 STATS | Scans:%d  Entradas:%d  Martingalas:%d  "
            "Zonas expiradas:%d  Sin señal:%d  Sensor filtradas:%d%s%s  [A]:%dW/%dL  [B]:%dW/%dL",
            self.stats["scans"], self.stats["entries"], self.stats["martins"],
            self.stats["expired_zones"], self.stats["skipped"], self.stats["filtered_sensor"],
            risk_txt, cycle_txt,
            self.stats["strat_a_wins"], self.stats["strat_a_losses"],
            self.stats["strat_b_wins"], self.stats["strat_b_losses"],
        )
        if RISK_MANAGER == "massaniello":
            ms = self.massaniello.session_status()
            log.info(
                "📊 MASSANIELLO | %dW/%dL ops:%d/%d  entradas:%d  %.1f/%.0f min",
                ms["wins"],
                ms["losses"],
                ms["wins"] + ms["losses"],
                ms["operations"],
                ms["entries"],
                ms["elapsed_min"],
                ms["session_max_min"],
            )
        else:
            log.info(
                "📊 MARTIN | Sesión:%d/%d  Wins:%d  Losses:%d",
                self.stats.get("martin_attempts_session", 0),
                self.executor._current_martin_attempt_limit(),
                self.stats.get("martin_wins", 0),
                self.stats.get("martin_losses", 0),
            )


async def main(
    dry_run: bool,
    real_account: bool,
    loop_forever: bool,
    greylist_assets: Optional[set[str]] = None,
) -> None:
    if not EMAIL or not PASSWORD:
        print("ERROR: Falta QUOTEX_EMAIL / QUOTEX_PASSWORD en el .env")
        sys.exit(1)

    if RISK_MANAGER == "massaniello" and real_account:
        log.warning(
            "⚠️ Massaniello solo permite cuenta DEMO — flag --real ignorado, usando PRACTICE",
        )
        real_account = False

    client = Quotex(email=EMAIL, password=PASSWORD)
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║      CONSOLIDATION BOT — Quotex              ║")
    log.info("║  Cuenta  : %-34s║", "REAL ⚠️" if real_account else "DEMO ✅")
    log.info("║  Modo    : %-34s║", "LIVE" if not dry_run else "DRY-RUN")
    log.info("╚══════════════════════════════════════════════╝")

    check, reason = await connect_with_retry(client)
    if not check:
        log.critical("No se pudo conectar a Quotex: %s", reason)
        sys.exit(1)

    account_type = "REAL" if real_account else "PRACTICE"
    await client.change_account(account_type)

    start_balance: Optional[float] = None
    try:
        bal = await client.get_balance()
        start_balance = float(bal)
        log.info("✅ Conectado | Balance %s: %.2f USD", account_type, bal)
    except Exception as exc:
        log.warning("No se pudo leer balance: %s", exc)

    bot = ConsolidationBot(
        client=client, dry_run=dry_run, account_type=account_type, greylist_assets=greylist_assets,
    )
    if start_balance is not None:
        bot.set_session_start_balance(start_balance)

    await bot.reconcile_pending_candidates()

    try:
        if loop_forever and ALIGN_SCAN_TO_CANDLE:
            first_wait = seconds_until_next_scan(time.time())
            await sleep_with_inline_countdown(first_wait, "Sincronizando primer escaneo")

        while True:
            cycle_start = time.time()
            try:
                if loop_forever and not await bot.ensure_connection():
                    await asyncio.sleep(5.0)
                    continue
                await bot.scan_all()
                await bot.reconcile_pending_candidates(max_age_minutes=PENDING_RECONCILE_AGE_MIN)
                if bot.session_stop_hit:
                    break
            except asyncio.CancelledError:
                break
            except BotError as exc:
                log.error("Error de dominio en ciclo: %s", exc)
            except Exception as exc:
                log.error("Error en ciclo: %s", exc, exc_info=True)
                if looks_like_connection_issue(str(exc)):
                    await bot.ensure_connection()

            bot.log_stats()
            if not loop_forever:
                break

            if ALIGN_SCAN_TO_CANDLE:
                sleep_for = seconds_until_next_scan(time.time())
            else:
                elapsed = time.time() - cycle_start
                sleep_for = max(5.0, SCAN_INTERVAL_SEC - elapsed)

            try:
                await sleep_with_inline_countdown(sleep_for, "Próximo escaneo")
            except asyncio.CancelledError:
                break
    except KeyboardInterrupt:
        log.info("Detenido por el usuario (Ctrl+C).")
    finally:
        try:
            await asyncio.wait_for(bot.shutdown_background_tasks(), timeout=3.0)
        except Exception:
            pass
        try:
            await asyncio.wait_for(client.close(), timeout=3.0)
        except Exception:
            pass
        log.info("Bot detenido.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Consolidation Bot — Quotex")
    p.add_argument("--live", action="store_true")
    p.add_argument("--real", action="store_true")
    p.add_argument("--loop", action="store_true")
    p.add_argument("--greylist", type=str, default=",".join(sorted(GREYLIST_ASSETS)))
    p.add_argument("--pattern-put-blacklist", type=str, default=",".join(sorted(PATTERN_PUT_BLACKLIST)))
    p.add_argument("--scan-top-n", type=int, default=SCAN_MAX_ASSETS_PER_CYCLE)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    parsed_greylist = {t.strip() for t in (args.greylist or "").split(",") if t.strip()}
    globals()["SCAN_MAX_ASSETS_PER_CYCLE"] = max(0, int(args.scan_top_n))
    globals()["PATTERN_PUT_BLACKLIST"] = {
        t.strip() for t in (args.pattern_put_blacklist or "").split(",") if t.strip()
    }
    _config.SCAN_MAX_ASSETS_PER_CYCLE = SCAN_MAX_ASSETS_PER_CYCLE
    _config.PATTERN_PUT_BLACKLIST = PATTERN_PUT_BLACKLIST
    try:
        asyncio.run(main(
            dry_run=not args.live,
            real_account=args.real,
            loop_forever=args.loop,
            greylist_assets=parsed_greylist,
        ))
    except KeyboardInterrupt:
        raise SystemExit(0)