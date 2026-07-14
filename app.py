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
from hub.server import app as _hub_app, init as _hub_init, run_server as _hub_run_server, _open_browser, _auto_open_dashboard
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

    # Auto-open browser (unless disabled)
    if os.environ.get("HUB_NO_OPEN", "").lower() not in ("1", "true", "yes"):
        port = getattr(application.state, "_port", 8080)
        asyncio.create_task(_auto_open_dashboard("0.0.0.0", port))

    yield

    # Shutdown
    log.info("Shutting down...")
    await _runner.shutdown()
    poller.cancel()
    relay.cancel()
    try:
        await poller
    except asyncio.CancelledError:
        pass
    try:
        await relay
    except asyncio.CancelledError:
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
    """Stop the trading bot gracefully."""
    if _runner.state not in ("running", "starting"):
        return {"status": "already_stopped", "state": _runner.state}
    await _runner.stop()
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
    )
    interesting = {k: body.get(k) for k in keys_of_interest if k in body}
    if interesting:
        log.info("HUB config save (antes de aplicar): %s", interesting)
    _runner.update_config(**body)
    cfg = _runner.get_config()
    log.info(
        "HUB config aplicada → Massaniello %s ops / %s ITM | capital=$%s | "
        "min_payout=%s%% (escáner + stake)",
        cfg.get("massaniello_ops"),
        cfg.get("massaniello_wins"),
        cfg.get("massaniello_virtual_capital"),
        cfg.get("min_payout"),
    )
    return {"status": "updated", "config": cfg}


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
    """Health check endpoint."""
    return {
        "status": "ok",
        "runner_state": _runner.state,
        "uptime_sec": (time.time() - _runner._started_at) if _runner._started_at else None,
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

def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="QUOTEX Web App")
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    if args.no_browser:
        os.environ["HUB_NO_OPEN"] = "1"

    # Store port in app state so lifespan can use it
    _hub_app.state._port = args.port

    print(f"  → QUOTEX Web App: http://localhost:{args.port}")
    print(f"  → Dashboard: http://localhost:{args.port}/")
    print(f"  → API docs: http://localhost:{args.port}/api/bot/status")
    print()

    uvicorn.run(
        _hub_app,
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
