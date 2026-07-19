"""QUOTEX Web App — FastAPI entry point.

Usage:
    python app.py              # Start on port 8080
    python app.py --port 3000  # Custom port
    python app.py --no-browser # Don't auto-open browser
"""
from __future__ import annotations

import argparse
import asyncio
import io
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# ── UTF-8 for Windows ──────────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
else:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ── Path setup ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _load_dotenv() -> None:
    """Load .env before importing modules (config reads EMAIL at import time)."""
    for candidate in (ROOT / ".env", SRC_DIR / ".env"):
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())
        break


_load_dotenv()

# ── Logging with ring buffer for WebSocket streaming ───────────────────────────
from collections import deque
LOG_RING_SIZE = 200
_log_ring: deque[dict[str, Any]] = deque(maxlen=LOG_RING_SIZE)
_log_subscribers: set[asyncio.Queue] = set()


class _WebLogHandler(logging.Handler):
    """Captures log records into ring buffer + pushes to WebSocket subscribers."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "ts": record.created,
                "level": record.levelname,
                "logger": record.name,
                "msg": self.format(record),
            }
        except Exception:
            return
        _log_ring.append(entry)
        # Push to all subscribers (non-blocking)
        dead: list[asyncio.Queue] = []
        for q in _log_subscribers:
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _log_subscribers.discard(q)


def _setup_web_logging() -> None:
    """Add web log handler to consolidation_bot + black_box_recorder loggers."""
    handler = _WebLogHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
    handler.setLevel(logging.INFO)
    for name in ("consolidation_bot", "black_box_recorder"):
        logging.getLogger(name).addHandler(handler)
    # Also capture root warnings/errors
    logging.getLogger().addHandler(handler)


# ── Import hub server (FastAPI app lives here) ────────────────────────────────
from fastapi import WebSocket
from hub.server import (
    app as _hub_app,
    init as _hub_init,
    run_server as _hub_run_server,
    _open_browser,
    _auto_open_dashboard,
    schedule_hub_auto_open,
)
from hub.hub_scanner import HubScanner

# ── BotRunner import ──────────────────────────────────────────────────────────
from consolidation_bot import _runner, BotRunner

# ── Lifespan ──────────────────────────────────────────────────────────────────

_hub_scanner: HubScanner | None = None


@asynccontextmanager
async def lifespan(application):
    global _hub_scanner
    _setup_web_logging()

    log = logging.getLogger("app")
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║      QUOTEX WEB APP — Starting               ║")
    log.info("╚══════════════════════════════════════════════╝")

    # Start hub scanner + state poller + event relay
    _hub_scanner = HubScanner()
    _hub_init(_hub_scanner, bot=None)

    # Start background tasks
    poller = asyncio.create_task(_state_poller())
    relay = asyncio.create_task(_event_relay())

    log.info("Hub dashboard ready. Bot is STOPPED — use /api/bot/start to begin.")

    # Auto-open hub as soon as API is up (also scheduled from main(); this is backup).
    if os.environ.get("HUB_NO_OPEN", "").strip().lower() not in ("1", "true", "yes"):
        port = getattr(application.state, "_port", 8080)
        schedule_hub_auto_open(int(port))

    yield

    # Shutdown (Ctrl+C, SIGTERM, or window close when handlers fire).
    # Browser first; bot stop hard-capped at 2s so lifespan never hangs.
    log.info("Shutting down...")
    try:
        from hub.server import kill_hub_browser_tree
        kill_hub_browser_tree()
    except Exception:
        pass
    try:
        await asyncio.wait_for(_runner.shutdown(), timeout=2.0)
    except Exception:
        pass
    poller.cancel()
    relay.cancel()
    try:
        await asyncio.wait_for(poller, timeout=0.5)
    except (asyncio.CancelledError, Exception):
        pass
    try:
        await asyncio.wait_for(relay, timeout=0.5)
    except (asyncio.CancelledError, Exception):
        pass
    log.info("App stopped.")


# Re-configure the hub app with our lifespan
_hub_app.router.lifespan_context = lifespan


# ── Background tasks (from hub.server) ────────────────────────────────────────
# We re-use the hub's internals for state polling and event relay.

async def _state_poller():
    """Poll bot state and push to WebSocket clients every 0.8s."""
    import json
    from hub.server import _clients, _build_snapshot, POLL_INTERVAL

    last_payload = ""
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        if not _clients:
            continue
        # Refresh hub scanner with bot state
        if _hub_scanner is not None and _runner.bot is not None:
            _hub_init(_hub_scanner, bot=_runner.bot)
        snapshot = _build_snapshot()
        # Add bot runner status
        snapshot["runner"] = _runner.get_status()
        payload = json.dumps({"type": "state_update", "data": snapshot}, default=str)
        if payload == last_payload:
            continue
        last_payload = payload
        stale = []
        for ws in _clients:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            _clients.discard(ws)


async def _event_relay():
    """Relay hub events to WebSocket clients."""
    import json
    from hub.server import _clients
    from hub.events import event_bus

    queue = event_bus.subscribe()
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                stale = []
                for ws in _clients:
                    try:
                        await ws.send_text(msg)
                    except Exception:
                        stale.append(ws)
                for ws in stale:
                    _clients.discard(ws)
            except asyncio.TimeoutError:
                if _clients:
                    ping = json.dumps({"type": "ping", "timestamp": time.time()})
                    stale = []
                    for ws in _clients:
                        try:
                            await ws.send_text(ping)
                        except Exception:
                            stale.append(ws)
                    for ws in stale:
                        _clients.discard(ws)
    finally:
        event_bus.unsubscribe(queue)


# ── REST API Endpoints ────────────────────────────────────────────────────────

@_hub_app.get("/api/bot/status")
async def bot_status():
    """Get bot runner status, stats, and config."""
    return _runner.get_status()


@_hub_app.post("/api/bot/start")
async def bot_start():
    """Start the trading bot."""
    if _runner.state in ("running", "starting"):
        return {"status": "already_running", "state": _runner.state}
    # Connect hub scanner to bot after it starts
    asyncio.create_task(_connect_hub_after_start())
    await _runner.start()
    return {"status": "started", "state": _runner.state}


async def _connect_hub_after_start():
    """Wait for bot to be running, then connect hub scanner."""
    for _ in range(50):  # 5 seconds max
        if _runner.state == "running" and _runner.bot is not None:
            if _hub_scanner is not None:
                _hub_init(_hub_scanner, bot=_runner.bot)
                _runner.bot._hub_scanner = _hub_scanner
            return
        await asyncio.sleep(0.1)


@_hub_app.post("/api/bot/stop")
async def bot_stop():
    """Stop the trading bot gracefully (user action → disarm schedule)."""
    if _runner.state not in ("running", "starting"):
        # Still disarm schedule if user hits Detener while already stopped
        await _runner.stop(user=True)
        return {"status": "already_stopped", "state": _runner.state}
    await _runner.stop(user=True)
    # Cierra también el server/app para que no quede en "reconectando…"
    # ni procesos huérfanos (equivalente a FINALIZAR pero desde STOP).
    _force_exit_cleanup(timeout_sec=2.0)
    return {"status": "stopped", "state": _runner.state}


@_hub_app.post("/api/shutdown")
async def shutdown_server():
    """Stop bot + close browser + kill server."""
    import signal, threading
    # Stop bot if running
    if _runner.state in ("running", "starting"):
        await _runner.stop()
    # Close browser window
    from hub.server import _close_browser
    _close_browser()
    # Kill server after short delay (so response reaches client)
    def _kill():
        import time; time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=_kill, daemon=True).start()
    return {"status": "shutting_down"}


@_hub_app.get("/api/config")
async def get_config():
    """Get current bot configuration."""
    return _runner.get_config()


@_hub_app.post("/api/config")
async def update_config(body: dict[str, Any]):
    """Update bot configuration (only when bot is stopped)."""
    if _runner.state in ("running", "starting"):
        return {"error": "Cannot change config while bot is running. Stop it first."}
    log = logging.getLogger("app")
    # Audit trail: what the user committed from the hub
    keys_of_interest = (
        "massaniello_ops",
        "massaniello_wins",
        "massaniello_virtual_capital",
        "min_payout",
        "session_max_min",
        "schedule_mode",
        "duration_min",
        "max_consecutive_sessions",
        "work_block_hours",
        "rest_hours",
        "max_sessions_per_day",
    )
    interesting = {k: body.get(k) for k in keys_of_interest if k in body}
    if interesting:
        log.info("HUB config save (antes de aplicar): %s", interesting)
    _runner.update_config(**body)
    cfg = _runner.get_config()
    log.info(
        "HUB config aplicada → Massaniello %s ops / %s ITM | capital=$%s | "
        "min_payout=%s%% | schedule=%s duration_min=%s",
        cfg.get("massaniello_ops"),
        cfg.get("massaniello_wins"),
        cfg.get("massaniello_virtual_capital"),
        cfg.get("min_payout"),
        cfg.get("schedule_mode"),
        cfg.get("duration_min"),
    )
    return {"status": "updated", "config": cfg}


@_hub_app.post("/api/stake-mode")
async def set_stake_mode(body: dict[str, Any]):
    """Gestión Massaniello EN VIVO (solo monto, indep. del modo 24h).
    body: {"mode": "fixed"|"massaniello", "stake": float}"""
    import config as _cfg
    mode = str(body.get("mode", "massaniello")).lower()
    if mode not in ("fixed", "massaniello"):
        return {"error": "mode debe ser 'fixed' o 'massaniello'"}
    _cfg.STAKE_MODE = mode
    if "stake" in body:
        try:
            _cfg.FIXED_STAKE_USD = max(0.1, float(body["stake"]))
        except (TypeError, ValueError):
            return {"error": "stake inválido"}
    try:
        _runner._config["STAKE_MODE"] = mode
        _runner._config["FIXED_STAKE_USD"] = _cfg.FIXED_STAKE_USD
    except Exception:
        pass
    logging.getLogger("app").info(
        "STAKE MODE (Massaniello) → %s | fixed_stake=$%.2f",
        mode, getattr(_cfg, "FIXED_STAKE_USD", 2.0),
    )
    return {"status": "updated", "stake_mode": mode,
            "fixed_stake_usd": getattr(_cfg, "FIXED_STAKE_USD", 2.0)}


@_hub_app.post("/api/daily-guard")
async def set_daily_guard(body: dict[str, Any]):
    """Modo 24h EN VIVO (solo frenos del guard, indep. de la gestión Massaniello).
    body: {"enabled": true|false}  False = sin pausa por pérdida diaria (24h)."""
    import config as _cfg
    enabled = bool(body.get("enabled", True))
    _cfg.DAILY_LOSS_GUARD_ENABLED = enabled
    try:
        _runner._config["DAILY_LOSS_GUARD_ENABLED"] = enabled
    except Exception:
        pass
    logging.getLogger("app").info(
        "DAILY LOSS GUARD (modo 24h) → %s", "ON" if enabled else "OFF"
    )
    return {"status": "updated", "daily_loss_guard_enabled": enabled}


@_hub_app.get("/api/massaniello/preview")
async def massaniello_preview(
    payout: int | None = None,
    capital: float | None = None,
    ops: int | None = None,
    itm: int | None = None,
    form: int = 0,
):
    """Next-stake preview using the same Massaniello formula as the bot.

    Query overrides (optional, for live hub typing without save):
      capital, ops, itm, payout, form=1
    """
    from massaniello_preview import preview_from_runner

    return preview_from_runner(
        _runner,
        payout_pct=payout,
        assigned_capital=capital,
        operations=ops,
        expected_wins=itm,
        use_form_overrides=bool(form),
    )


@_hub_app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Get recent log entries."""
    entries = list(_log_ring)
    return entries[-limit:]


@_hub_app.post("/api/session/reset")
async def reset_session():
    """Reset Massaniello session — clears session_stop_hit so bot resumes scanning."""
    bot = _runner.bot
    if bot is None:
        return {"error": "Bot is not running"}
    if not hasattr(bot, "session_stop_hit"):
        return {"error": "Bot does not use Massaniello sessions"}
    was_stopped = bot.session_stop_hit
    bot.session_stop_hit = False
    # Force a fresh Massaniello cycle if the current one is complete/failed
    if hasattr(bot, "massaniello") and bot.massaniello is not None:
        mgr = bot.massaniello
        if mgr.is_session_complete() or mgr.is_session_failed() or mgr.is_session_exhausted():
            from massaniello_risk import MassanielloRiskManager
            bot.massaniello = MassanielloRiskManager()
            if hasattr(bot.executor, "set_session_start_balance") and bot.current_balance:
                bot.executor.set_session_start_balance(bot.current_balance)
    log.info("🔄 Sesión Massaniello reiniciada manualmente desde dashboard")
    return {"status": "reset", "was_stopped": was_stopped}


@_hub_app.get("/health")
async def health():
    """Shallow liveness: process is up and HTTP responds."""
    return {
        "status": "ok",
        "runner_state": _runner.state,
        "uptime_sec": (time.time() - _runner._started_at) if _runner._started_at else None,
        "timestamp": time.time(),
    }


@_hub_app.get("/health/ready")
async def health_ready():
    """Readiness: hub HTTP works (bot may be stopped). Always 200 when app is up."""
    return {
        "status": "ready",
        "runner_state": _runner.state,
        "browser_profile": "quotex_hub_edge",
        "timestamp": time.time(),
    }


# ── Black Box API Endpoints ───────────────────────────────────────────────────

@_hub_app.get("/api/blackbox/trades")
async def get_blackbox_trades(limit: int = 100, date_from: str = ""):
    """Get trade history from black box."""
    from black_box_recorder import get_black_box
    bb = get_black_box()
    trades = bb.get_trades(limit=limit, date_from=date_from or None)
    return {"trades": trades, "count": len(trades)}


@_hub_app.delete("/api/blackbox/trades")
async def clear_blackbox_trades():
    """Clear trade history from black box (JSONL files preserved)."""
    from black_box_recorder import get_black_box
    bb = get_black_box()
    deleted = bb.clear_trades()
    return {"status": "cleared", "deleted": deleted}


@_hub_app.get("/api/blackbox/session")
async def get_blackbox_session():
    """Get current session summary from black box."""
    from black_box_recorder import get_black_box
    bb = get_black_box()
    return bb.get_session_summary()


# ── Session Management API Endpoints ──────────────────────────────────────────

@_hub_app.post("/api/session/new-cycle")
async def new_cycle():
    """Confirm and start a new trading cycle."""
    result = _runner.confirm_new_cycle()
    return result


@_hub_app.post("/api/session/reject-cycle")
async def reject_cycle():
    """Decline new cycle — stop bot."""
    result = _runner.reject_new_cycle()
    return result


@_hub_app.get("/api/session/status")
async def session_status():
    """Get current session status."""
    return _runner.get_session_status()


# ── WebSocket for logs ────────────────────────────────────────────────────────

@_hub_app.websocket("/ws/logs")
async def ws_logs(ws: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await ws.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _log_subscribers.add(q)
    try:
        # Send recent logs on connect
        for entry in list(_log_ring)[-50:]:
            await ws.send_json(entry)
        # Stream new logs
        while True:
            try:
                entry = await asyncio.wait_for(q.get(), timeout=30)
                await ws.send_json(entry)
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping", "timestamp": time.time()})
            except asyncio.CancelledError:
                break
    except Exception:
        pass
    finally:
        _log_subscribers.discard(q)


# ── Entry point ───────────────────────────────────────────────────────────────

_PID_LOCK_PATH = ROOT / "runtime" / "main.lock"


def _stop_bot_for_exit():
    """Return awaitable shutdown if bot is running; else None."""
    if _runner.state in ("running", "starting"):
        return _runner.shutdown()
    return None


def _force_exit_cleanup(timeout_sec: float = 2.0) -> None:
    """Kill Edge hub tree first, then stop bot with hard timeout ≤ 2s."""
    from hub.process_lifecycle import run_exit_cleanup
    from hub.server import kill_hub_browser_tree

    run_exit_cleanup(
        kill_browser=kill_hub_browser_tree,
        stop_bot_coro_or_fn=_stop_bot_for_exit,
        timeout_sec=timeout_sec,
    )
    try:
        from hub.process_lifecycle import release_pid_lock
        release_pid_lock(_PID_LOCK_PATH)
    except Exception:
        pass


def _install_exit_cleanup() -> None:
    """On console X / Ctrl+C / atexit: hard-timeout cleanup so the process dies.

    Never runs unbounded ``run_until_complete(shutdown)`` — max 2s then done.
    CTRL_CLOSE_EVENT (window X) forces ``os._exit(0)`` within Windows' ~5s window.
    """
    import atexit

    atexit.register(_force_exit_cleanup)

    if os.name == "nt":
        try:
            import ctypes

            Handler = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)

            def _ctrl_handler(ctrl_type: int) -> int:
                # 0=Ctrl+C, 1=Ctrl+Break, 2=Close window (CTRL_CLOSE_EVENT)
                if ctrl_type not in (0, 1, 2):
                    return 0
                _force_exit_cleanup(timeout_sec=2.0)
                if ctrl_type == 2:
                    # Window close: we handled cleanup; force exit so orphans die.
                    os._exit(0)
                    return 1  # noqa: unreachable — signals handled to OS
                # Ctrl+C / Break: cleanup done; let default raise KeyboardInterrupt
                return 0

            # Keep reference so GC does not collect the callback
            main._ctrl_handler_ref = Handler(_ctrl_handler)  # type: ignore[attr-defined]
            ctypes.windll.kernel32.SetConsoleCtrlHandler(main._ctrl_handler_ref, 1)
        except Exception:
            pass


def main():
    import uvicorn
    from hub.process_lifecycle import acquire_pid_lock, release_pid_lock

    parser = argparse.ArgumentParser(description="QUOTEX Web App")
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    if args.no_browser:
        os.environ["HUB_NO_OPEN"] = "1"
    else:
        # Lazy default: always open hub unless user passed --no-browser.
        os.environ.pop("HUB_NO_OPEN", None)

    if not acquire_pid_lock(_PID_LOCK_PATH):
        print(
            f"[ERROR] Another QUOTEX webapp instance is already running "
            f"(lock: {_PID_LOCK_PATH}). Stop it first or run stop_webapp.bat."
        )
        # Still try to open hub so the user lands on the running dashboard.
        if not args.no_browser:
            try:
                schedule_hub_auto_open(int(args.port))
                # Give the opener a moment, then exit this second launcher.
                import time as _time
                _time.sleep(1.5)
            except Exception:
                pass
        sys.exit(1)

    # Store port in app state so lifespan can use it
    _hub_app.state._port = args.port

    print(f"  → QUOTEX Web App: http://localhost:{args.port}")
    print(f"  → Dashboard: http://localhost:{args.port}/")
    print(f"  → API docs: http://localhost:{args.port}/api/bot/status")
    print(f"  → Hub opens automatically — no extra clicks")
    print(f"  → Ctrl+C or close this window to stop server + hub browser")
    print()

    _install_exit_cleanup()

    # Start opener BEFORE uvicorn so it is already waiting when the port binds.
    if not args.no_browser:
        schedule_hub_auto_open(int(args.port))

    try:
        uvicorn_kwargs: dict[str, Any] = {
            "host": args.host,
            "port": args.port,
            "log_level": "info",
            "access_log": False,
        }
        # Graceful shutdown budget (uvicorn ≥ 0.15); ignore if unsupported.
        try:
            import inspect
            if "timeout_graceful_shutdown" in inspect.signature(uvicorn.run).parameters:
                uvicorn_kwargs["timeout_graceful_shutdown"] = 3
        except Exception:
            pass

        uvicorn.run(_hub_app, **uvicorn_kwargs)
    except KeyboardInterrupt:
        _force_exit_cleanup(timeout_sec=2.0)
    finally:
        release_pid_lock(_PID_LOCK_PATH)


if __name__ == "__main__":
    main()
