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
from alerter import alerter
from candle_cache import CandleCache
from config import MAX_SIMULTANEOUS_TRADES, MIN_ASSET_SPREAD, MAX_ENTRIES_PER_ASSET
from connection import (
    ConnectionManager, connect_with_retry, create_trading_client, get_open_assets,
    looks_like_connection_issue,
)
from diversification_enforcer import DiversificationEnforcer
from htf_scanner import HTFScanner
from errors import BotError
from executor import TradeExecutor
from loop_utils import seconds_until_next_scan, sleep_with_inline_countdown
from massaniello_persistence import MassanielloPersistence
from massaniello_risk import MassanielloRiskManager
from models import CandidateEntry, ConsolidationZone, PendingReversal, TradeState
from scanner import AssetScanner
from hub.strat_f_panel import StratFPanel

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
        trade_client: Optional[Quotex] = None,
    ):
        self.client = client
        self.trade_client = trade_client
        self.dry_run = dry_run
        self.account_type = account_type
        self.zones: dict[str, ConsolidationZone] = {}
        self.broken_zones: dict[str, float] = {}
        self.trades: dict[str, TradeState] = {}
        self.stats = {
            "scans": 0, "entries": 0, "martins": 0,
            "expired_zones": 0, "skipped": 0, "filtered_sensor": 0,
            "strat_a_signals": 0,
            "strat_a_wins": 0, "strat_a_losses": 0,
            "score_rejected_age": 0,
            "score_rejected_score": 0,
            "rejected_young_zone": 0,
            "martin_attempts_session": 0,
            "martin_wins": 0,
            "martin_losses": 0,
            "rejected_same_asset_limit": 0,
            "rejected_diversification": 0,
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
        self.radar_watchlist: dict[str, Any] = {}
        self._trade_tasks: set[asyncio.Task[Any]] = set()
        self.strat_f_panel = StratFPanel()
        self.greylist_assets = set(GREYLIST_ASSETS)
        if greylist_assets is not None:
            self.greylist_assets = {a.strip() for a in greylist_assets if a and a.strip()}

        self.candle_cache = CandleCache()
        self.connection_mgr = ConnectionManager(client)
        # Semáforo COMPARTIDO del WebSocket: lo usan el prefetch del scan loop y
        # el HTF en background, para no saturar el único socket de Quotex a la vez.
        self._ws_sem = asyncio.Semaphore(CANDLE_FETCH_CONCURRENCY)
        self.htf_scanner = HTFScanner(client, assets_fn=lambda: get_open_assets(client, min_payout=STRAT_A_MIN_PAYOUT), min_payout=STRAT_A_MIN_PAYOUT, on_asset_refresh=self._on_htf_asset_refresh, ws_sem=self._ws_sem)
        self._htf_task: asyncio.Task[Any] | None = None
        self._hub_scanner: Any = None
        self.executor = TradeExecutor(client, self, trade_client, self.htf_scanner)
        self.scanner = AssetScanner(self, self.executor)
        self.diversification_enforcer = DiversificationEnforcer(
            max_simultaneous_trades=MAX_SIMULTANEOUS_TRADES,
            min_asset_spread=MIN_ASSET_SPREAD,
            max_entries_per_asset=MAX_ENTRIES_PER_ASSET,
        )

    def _on_htf_asset_refresh(
        self,
        sym: str,
        payout: int,
        candles_count: int,
        age: float,
        ttl: float,
        ts: float,
    ) -> None:
        hub = self._hub_scanner
        if hub is None:
            return
        try:
            hub.update_htf_status(
                asset=sym,
                payout=payout,
                candles=candles_count,
                library_size=self.htf_scanner.library_size(),
                cache_age_sec=age,
                cache_ttl_sec=ttl,
                refreshed_at_ts=ts,
            )
        except Exception:
            return

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
        if self._htf_task and not self._htf_task.done():
            self._htf_task.cancel()
            try:
                await self._htf_task
            except asyncio.CancelledError:
                pass
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
            "Zonas expiradas:%d  Sin señal:%d  Sensor filtradas:%d%s%s  [A]:%dW/%dL",
            self.stats["scans"], self.stats["entries"], self.stats["martins"],
            self.stats["expired_zones"], self.stats["skipped"], self.stats["filtered_sensor"],
            risk_txt, cycle_txt,
            self.stats["strat_a_wins"], self.stats["strat_a_losses"],
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
    hub_scanner: Any = None,
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

    # Fix F6 (raíz): cliente de trading LIMPIO separado del de datos (scanner/HTF).
    # El scanner abre streams de velas en vivo de ~29 activos en M1+M5 en el mismo
    # socket; eso deja orders/open sin respuesta. Separar elimina la competencia.
    trade_client = None
    try:
        trade_client, tc_reason = await create_trading_client(
            email=EMAIL, password=PASSWORD, account_type=account_type,
        )
        if trade_client is None:
            log.warning("No se pudo crear cliente de trading separado: %s (usando cliente de datos para buy)", tc_reason)
    except Exception as _tc_exc:
        log.warning("Excepción creando cliente de trading: %s", _tc_exc)

    start_balance: Optional[float] = None
    try:
        bal = await client.get_balance()
        start_balance = float(bal)
        log.info("✅ Conectado | Balance %s: %.2f USD", account_type, bal)
    except Exception as exc:
        log.warning("No se pudo leer balance: %s", exc)

    bot = ConsolidationBot(
        client=client, dry_run=dry_run, account_type=account_type, greylist_assets=greylist_assets,
        trade_client=trade_client,
    )
    if start_balance is not None:
        bot.set_session_start_balance(start_balance)

    # ── Enchufar panel STRAT-F al HUB (go-live G1) ───────────────────────────
    if hub_scanner is not None:
        try:
            from hub import server as _hub_server
            _hub_server.init(hub_scanner, bot=bot)
            log.info("HUB STRAT-F panel conectado al bot")
        except Exception as _hub_err:
            log.warning("No se pudo conectar panel STRAT-F al HUB: %s", _hub_err)

    # ── Persistencia Massaniello ──────────────────────────────────────────────
    bot.massaniello_persistence = MassanielloPersistence()
    if RISK_MANAGER == "massaniello":
        state = bot.massaniello_persistence.load()
        if state:
            bot.massaniello_persistence.apply(bot.massaniello, state)
        else:
            log.info("Sin estado Massaniello previo — arrancando con defaults")
    else:
        log.debug("Risk manager no es Massaniello — persistencia omitida")

    # ── Carga de pesos calibrados del entry_scorer ──────────────────────────
    try:
        from weight_calibrator import WeightCalibrator
        _weights_path = Path(__file__).resolve().parent.parent / "data" / "exports" / "calibrated_weights.json"
        if _weights_path.exists():
            _weights_data = WeightCalibrator.load_weights(_weights_path)
            if _weights_data:
                from entry_scorer import WEIGHTS_REBOUND as _WR, WEIGHTS_BREAKOUT as _WB
                _reb = _weights_data.get("default", {}).get("rebound", {})
                _brk = _weights_data.get("default", {}).get("breakout", {})
                if _reb and _brk:
                    _WR.clear()
                    _WR.update(_reb)
                    _WB.clear()
                    _WB.update(_brk)
                    log.info("✅ Pesos calibrados cargados desde %s", _weights_path)
    except Exception as exc:
        log.warning("⚠️ No se pudieron cargar pesos calibrados: %s", exc)

    # ── Kelly Criterion Sizing ──────────────────────────────────────────────
    try:
        from kelly_sizer import KellySizer
        _kelly = KellySizer()
        _kelly_factor = _kelly.calculate()
        if _kelly_factor > 0.0:
            if bot.massaniello._initial_capital is not None:
                _old = bot.massaniello._initial_capital
                bot.massaniello._initial_capital *= _kelly_factor
                log.info(
                    "✅ Kelly sizing aplicado: capital %.2f → %.2f (factor=%.4f)",
                    _old, bot.massaniello._initial_capital, _kelly_factor,
                )
        else:
            log.info("⏸️ Kelly factor %.4f — sin ajuste", _kelly_factor)
        _kelly.close()
    except Exception as exc:
        log.warning("⚠️ No se pudo aplicar Kelly sizing: %s", exc)

    bot._htf_task = asyncio.create_task(bot.htf_scanner.run_forever())
    log.info("[HTF] Scanner 15m iniciado en background")

    if hub_scanner is not None:
        bot._hub_scanner = hub_scanner

        async def _hub_sync():
            while True:
                await asyncio.sleep(2.0)
                hs = bot._hub_scanner
                if hs is None:
                    continue
                hs.state.live_wins = bot.stats["strat_a_wins"]
                hs.state.live_losses = bot.stats["strat_a_losses"]
                if bot.current_balance is not None:
                    hs.state.known_balance = bot.current_balance
                hs.state.total_scans = bot.stats["scans"]
                # El HUB viejo de Masaniello podía no tener este método en la
                # versión con panel STRAT-F; lo salteamos si no existe (el panel
                # nuevo no depende de él).
                if hasattr(hs, "update_masaniello_state"):
                    hs.update_masaniello_state(
                        cycle_num=bot.cycle_id,
                        trades_in_cycle=bot.cycle_ops,
                        wins_in_cycle=bot.cycle_wins,
                        losses_in_cycle=bot.cycle_losses,
                    )

        asyncio.create_task(_hub_sync(), name="hub-sync")

    await bot.reconcile_pending_candidates()

    try:
        if loop_forever and ALIGN_SCAN_TO_CANDLE:
            first_wait = seconds_until_next_scan(time.time())
            await sleep_with_inline_countdown(first_wait, "Sincronizando primer escaneo")

        while True:
            cycle_start = time.time()
            try:
                if loop_forever and not await bot.ensure_connection():
                    alerter.alert_connection_lost()
                    await asyncio.sleep(5.0)
                    continue
                await bot.scan_all()

                hub = bot._hub_scanner
                if hub is not None:
                    strat_a_payload = _extract_candidates_for_hub(bot)
                    hub.record_scan_cycle(
                        total_assets=max(0, bot.stats.get("total_assets_scanned", 0)),
                        strat_a_candidates=strat_a_payload,
                        balance=bot.current_balance,
                        cycle_id=bot.cycle_id,
                        cycle_ops=bot.cycle_ops,
                        cycle_wins=bot.cycle_wins,
                        cycle_losses=bot.cycle_losses,
                    )

                radar_active = bool(STRAT_A_ONLY or STRAT_A_RADAR_ENABLED)
                radar_watchlist = (
                    bot.radar_watchlist
                    if isinstance(getattr(bot, "radar_watchlist", None), dict)
                    else {}
                )
                if radar_active and radar_watchlist:
                    radar_started = time.time()
                    entry_from_radar = False
                    while radar_watchlist and not entry_from_radar:
                        elapsed = time.time() - radar_started
                        if elapsed >= STRAT_A_RADAR_FULL_SCAN_MIN_SEC:
                            break
                        try:
                            entry_from_radar = await bot.scanner.radar_watch_tick()
                        except BotError as exc:
                            log.error("Error radar watch tick: %s", exc)
                        except Exception as exc:
                            log.error("Error radar watch tick: %s", exc, exc_info=True)
                        radar_watchlist = (
                            bot.radar_watchlist
                            if isinstance(getattr(bot, "radar_watchlist", None), dict)
                            else {}
                        )
                        if entry_from_radar or not radar_watchlist:
                            break
                        elapsed = time.time() - radar_started
                        if elapsed >= STRAT_A_RADAR_FULL_SCAN_MIN_SEC:
                            break
                        wait_sec = min(
                            float(STRAT_A_RADAR_TICK_SEC),
                            float(STRAT_A_RADAR_FULL_SCAN_MIN_SEC) - elapsed,
                        )
                        if wait_sec > 0:
                            await sleep_with_inline_countdown(
                                wait_sec,
                                "[RADAR] Próximo tick watchlist",
                            )
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


class BotRunner:
    """Gestiona el lifecycle del bot: start / stop / status.

    Diseñado para ser llamado desde la API web (FastAPI lifespan).
    El bot corre como asyncio.Task que se puede cancelar limpiamente.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task[Any] | None = None
        self._bot: ConsolidationBot | None = None
        self._client: Any = None
        self._state: str = "stopped"  # stopped | starting | running | stopping | error
        self._error: str | None = None
        self._started_at: float | None = None
        self._config: dict[str, Any] = {
            "dry_run": False,
            "real_account": False,
            "amount_initial": 1.0,
            "amount_martin": 3.0,
            "max_loss_session": 0.20,
            "cycle_ops": 5,
            "cycle_wins": 2,
            "cycle_profit_pct": 0.10,
            "min_payout": 80,
            "scan_lead_sec": 35.0,
            # Massaniello
            "massaniello_ops": _config.MASSANIELLO_OPERATIONS,
            "massaniello_wins": _config.MASSANIELLO_EXPECTED_WINS,
            "session_max_min": _config.SESSION_MAX_MIN,
            "massaniello_virtual_capital": _config.MASSANIELLO_VIRTUAL_CAPITAL,
            # Scanner payout
            "strat_f_min_score": _config.STRAT_F_MIN_SCORE,
            "strat_f_zone_min_age": _config.STRAT_F_ZONE_MIN_AGE,
            # Duration
            "duration_sec": _config.DURATION_SEC,
        }

    @property
    def state(self) -> str:
        return self._state

    @property
    def bot(self) -> ConsolidationBot | None:
        return self._bot

    @property
    def error(self) -> str | None:
        return self._error

    def get_config(self) -> dict[str, Any]:
        cfg = dict(self._config)
        cfg["_runner_state"] = self._state
        return cfg

    def update_config(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if k in self._config:
                self._config[k] = v
        self._apply_config_to_module()
        self._apply_config_to_bot()

    def _apply_config_to_module(self) -> None:
        """Push _config values into the config module so imports see updated values."""
        c = self._config
        _config.MASSANIELLO_OPERATIONS = int(c.get("massaniello_ops", 5))
        _config.MASSANIELLO_EXPECTED_WINS = int(c.get("massaniello_wins", 3))
        _config.SESSION_MAX_MIN = int(c.get("session_max_min", 60))
        _config.MASSANIELLO_VIRTUAL_CAPITAL = float(c.get("massaniello_virtual_capital", 30.0))
        _config.MIN_PAYOUT = int(c.get("min_payout", 80))
        _config.STRAT_F_MIN_SCORE = int(c.get("strat_f_min_score", 60))
        _config.STRAT_F_ZONE_MIN_AGE = int(c.get("strat_f_zone_min_age", 3))
        _config.DURATION_SEC = int(c.get("duration_sec", 300))

    def _apply_config_to_bot(self) -> None:
        """Push config changes to the live bot instance (hot-reload)."""
        bot = self._bot
        if bot is None:
            return
        c = self._config
        # Update Massaniello manager on the live bot
        if hasattr(bot, "massaniello") and bot.massaniello is not None:
            mgr = bot.massaniello
            mgr.operations = int(c.get("massaniello_ops", 5))
            mgr.expected_wins = int(c.get("massaniello_wins", 3))
            mgr.session_max_min = int(c.get("session_max_min", 60))
        # Update scanner payout threshold
        if hasattr(bot, "scanner") and bot.scanner is not None:
            pass  # scanner reads config module at import time, already updated

    def get_status(self) -> dict[str, Any]:
        status: dict[str, Any] = {
            "state": self._state,
            "config": self._config,
            "uptime_sec": (time.time() - self._started_at) if self._started_at else None,
        }
        if self._error:
            status["last_error"] = self._error
        if self._bot is not None:
            b = self._bot
            status["balance"] = b.current_balance
            status["stats"] = dict(b.stats)
            status["cycle_id"] = b.cycle_id
            status["cycle_ops"] = b.cycle_ops
            status["cycle_wins"] = b.cycle_wins
            status["cycle_losses"] = b.cycle_losses
            status["cycle_profit"] = b.cycle_profit
            status["active_trades"] = len(b.trades)
            status["account_type"] = b.account_type
        return status

    async def start(self) -> None:
        if self._state in ("running", "starting"):
            return
        self._state = "starting"
        self._error = None
        self._started_at = time.time()
        self._task = asyncio.create_task(self._run(), name="bot-runner")

    async def stop(self) -> None:
        if self._state not in ("running", "starting"):
            return
        self._state = "stopping"
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        self._state = "stopped"
        self._task = None

    async def _run(self) -> None:
        """Wrapper que ejecuta main() y maneja el lifecycle."""
        try:
            self._apply_config_to_module()
            self._state = "running"
            await main(
                dry_run=self._config["dry_run"],
                real_account=self._config["real_account"],
                loop_forever=True,
                hub_scanner=None,  # se conecta después via app.py
            )
        except asyncio.CancelledError:
            log.info("BotRunner: task cancelada — shutdown limpio")
        except SystemExit as exc:
            self._error = f"SystemExit({exc.code})"
            self._state = "error"
            log.error("BotRunner: SystemExit %s", exc.code)
        except Exception as exc:
            self._error = str(exc)
            self._state = "error"
            log.error("BotRunner: error fatal — %s", exc, exc_info=True)
        finally:
            if self._state not in ("error",):
                self._state = "stopped"
            self._started_at = None

    async def shutdown(self) -> None:
        """Shutdown forzado — llamado desde FastAPI lifespan."""
        await self.stop()
        if self._client is not None:
            try:
                await asyncio.wait_for(self._client.close(), timeout=3.0)
            except Exception:
                pass
            self._client = None


_runner = BotRunner()


def _extract_candidates_for_hub(bot: Any) -> list[dict]:
    """Convierte last_scan_candidates del bot a payloads para el hub."""
    raw: list[CandidateEntry] | None = getattr(bot, "last_scan_candidates", None)
    if not raw:
        return []

    strat_a: list[dict] = []
    for c in raw:
        payload = {
            "asset": c.asset,
            "direction": c.direction,
            "score": c.score,
            "payout": c.payout,
            "zone_ceiling": c.zone.ceiling,
            "zone_floor": c.zone.floor,
            "zone_age_min": c.zone.age_minutes,
            "pattern": getattr(c, "_reversal_pattern", "none"),
            "pattern_strength": getattr(c, "_reversal_strength", 0.0),
            "entry_mode": getattr(c, "_entry_mode", "none"),
        }
        strat_a.append(payload)

    return strat_a


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