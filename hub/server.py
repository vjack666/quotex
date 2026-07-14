"""FastAPI + WebSocket server for the live hub dashboard."""
from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .events import event_bus
from .hub_models import HubState
from .strat_f_panel import StratFPanel
from .hub_scanner import HubScanner

# El módulo src.stats usa imports pelados (p.ej. `from black_box_recorder import ...`).
# Al correr `python -m hub.server` desde la raíz, src/ no está en sys.path, así que
# lo insertamos antes de importarlo. Los tests ya hacen esto; aquí cubrimos el launcher.
import sys as _sys
_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SRC_DIR))

from src.stats import build_stats  # noqa: E402

HERE = Path(__file__).resolve().parent
STATIC_DIR = HERE / "static"
INDEX_PATH = STATIC_DIR / "index.html"

DEFAULT_HOST = os.environ.get("HUB_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("HUB_PORT", "8080"))
POLL_INTERVAL = float(os.environ.get("HUB_POLL_SEC", "0.8"))

_PORT_RESOLVED: Optional[int] = None

_scanner: Optional[HubScanner] = None
_panel: Optional[StratFPanel] = None
_bot_ref: Any = None
_clients: set[WebSocket] = set()
_server_task: Optional[asyncio.Task] = None
_browser_proc: Any = None  # Popen de la ventana Edge del HUB (para cerrarla al apagar)

app = FastAPI(title="Quotex HUB", version="1.0.0", docs_url=None, redoc_url=None)


def init(scanner: HubScanner, bot: Any = None) -> None:
    global _scanner, _bot_ref, _panel
    _scanner = scanner
    _bot_ref = bot
    # El bot real llena su propio StratFPanel; el server lo usa para el WS.
    if bot is not None and getattr(bot, "strat_f_panel", None) is not None:
        _panel = bot.strat_f_panel
    elif _panel is None:
        _panel = StratFPanel()


def _serialize(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dataclass_fields__"):
        return {f: _serialize(getattr(obj, f)) for f in obj.__dataclass_fields__}
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if isinstance(obj, float):
        if obj != obj:
            return None
        if obj == float("inf") or obj == float("-inf"):
            return None
    return obj


def _build_snapshot() -> dict:
    if not _scanner:
        base = {"status": "waiting"}
    else:
        state = _scanner.get_state()
        raw = _serialize(state)
        raw["status"] = "ok"
        base = raw
    # Estado STRAT-F (panel nuevo, visible).
    if _panel is not None:
        base["strat_f"] = _serialize(_panel.get_state())
    # Enriquecer con datos vivos del bot (balance, operación, Massaniello,
    # actividad). El bot es la fuente de verdad; StratFHubState no tiene estos
    # campos, así que se leen aquí directamente en vez de inyectarlos en el
    # dataclass (donde _serialize los descartaría).
    _enrich_with_bot(base)
    return base


def _enrich_with_bot(base: dict) -> None:
    bot = _bot_ref
    if bot is None:
        return
    # ── Balance y actividad ──────────────────────────────
    if getattr(bot, "current_balance", None) is not None:
        base["known_balance"] = bot.current_balance
    stats = getattr(bot, "stats", None) or {}
    base["total_scans"] = stats.get("scans")
    base["live_wins"] = stats.get("strat_a_wins")
    base["live_losses"] = stats.get("strat_a_losses")
    if stats.get("total_assets_scanned") is not None:
        base["total_assets_scanned"] = stats.get("total_assets_scanned")

    # ── Operación en curso (primer trade abierto sin resolver) ──
    trades = getattr(bot, "trades", None) or {}
    active = next((t for t in trades.values() if not getattr(t, "resolved", False)), None)
    if active is not None:
        base["active_trade_asset"] = active.asset
        base["active_trade_direction"] = active.direction
        base["active_trade_entry_price"] = active.entry_price
        last_price = getattr(bot, "last_known_price", {}) or {}
        cur = last_price.get(active.asset)
        if cur is not None:
            base["active_trade_current_price"] = cur
            if active.entry_price:
                base["active_trade_delta_pct"] = (cur - active.entry_price) / active.entry_price * 100.0
        base["active_trade_amount"] = active.amount
        base["active_trade_payout"] = active.payout
        remaining = active.opened_at + active.duration_sec - time.time()
        base["active_trade_time_remaining_sec"] = max(0.0, remaining)

    # ── Gestión Massaniello ──────────────────────────────
    mgr = getattr(bot, "massaniello", None)
    if mgr is not None and hasattr(mgr, "session_status"):
        st = mgr.session_status()
        wins, losses = st["wins"], st["losses"]
        total = wins + losses
        safety = "OK"
        if st.get("failed"):
            safety = "FAIL"
        elif st.get("timeout"):
            safety = "TIMEOUT"
        elif st.get("exhausted"):
            safety = "EXHAUSTED"
        next_stake_amt = None
        try:
            from config import MASSANIELLO_VIRTUAL_CAPITAL
            assigned = float(MASSANIELLO_VIRTUAL_CAPITAL or 0.0)
        except Exception:
            assigned = float(st.get("initial_capital") or 0.0)
        try:
            stake_amt, _st = mgr.next_stake(92)
            next_stake_amt = float(stake_amt) if stake_amt else None
        except Exception:
            next_stake_amt = None
        base["masaniello"] = {
            "cycle_num": getattr(bot, "cycle_id", None),
            "sequence": "W" * wins + "L" * losses,
            "total_pnl": (st["balance"] - st["initial_capital"])
            if (st.get("balance") is not None and st.get("initial_capital") is not None)
            else None,
            "win_rate_pct": (wins / total * 100.0) if total else None,
            "wins_in_cycle": wins,
            "losses_in_cycle": losses,
            "safety_status": safety,
            "assigned_capital": assigned,
            "bankroll": st.get("balance"),
            "initial_capital": st.get("initial_capital"),
            "operations": st.get("operations"),
            "expected_wins": st.get("expected_wins"),
            "next_stake": next_stake_amt,
            "can_enter": st.get("can_enter"),
        }


async def _broadcast(msg: str) -> None:
    stale: list[WebSocket] = []
    for ws in _clients:
        try:
            await ws.send_text(msg)
        except Exception:
            stale.append(ws)
    for ws in stale:
        _clients.discard(ws)


async def _state_poller() -> None:
    last_payload = ""
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        if not _clients or not _scanner:
            continue
        snapshot = _build_snapshot()
        payload = json.dumps({"type": "state_update", "data": snapshot}, default=str)
        if payload == last_payload:
            continue
        last_payload = payload
        await _broadcast(payload)


async def _event_relay() -> None:
    queue = event_bus.subscribe()
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                await _broadcast(msg)
            except asyncio.TimeoutError:
                if _clients:
                    await _broadcast(json.dumps({"type": "ping", "timestamp": time.time()}))
    finally:
        event_bus.unsubscribe(queue)


# Serve static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    if INDEX_PATH.exists():
        return HTMLResponse(INDEX_PATH.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Quotex HUB</h1><p>index.html not found</p>")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "clients": len(_clients),
        "scanner": _scanner is not None,
        "timestamp": time.time(),
    }


@app.get("/api/state")
async def api_state():
    return _build_snapshot()


@app.get("/api/strat_f")
async def api_strat_f():
    if _panel is None:
        return {"status": "waiting"}
    return _serialize(_panel.get_state())


@app.get("/api/blackbox")
async def api_blackbox():
    """Reporte de la caja negra STRAT-F (win_rate, ranking pérdidas, A/B estocástico)."""
    try:
        return build_stats()
    except Exception as exc:  # DB aún no creada (Fase 6 pendiente) o sin datos
        return {"status": "empty", "error": str(exc), "total_resolved": 0}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)

    state = _build_snapshot()
    try:
        await ws.send_json({"type": "init", "data": state, "timestamp": time.time()})
    except Exception:
        _clients.discard(ws)
        return

    try:
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=45)
                if raw.strip() == "ping":
                    await ws.send_json({"type": "pong", "timestamp": time.time()})
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping", "timestamp": time.time()})
            except WebSocketDisconnect:
                break
            except asyncio.CancelledError:
                break
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        _clients.discard(ws)


def _resolve_port(requested: int, host: str = DEFAULT_HOST) -> int:
    """Return `requested` if free, otherwise find a random free port."""
    global _PORT_RESOLVED
    if _PORT_RESOLVED is not None:
        return _PORT_RESOLVED
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, requested))
            _PORT_RESOLVED = requested
            return requested
        except OSError:
            pass
        s.close()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
            s2.bind((host, 0))
            _PORT_RESOLVED = s2.getsockname()[1]
            return _PORT_RESOLVED


def used_port() -> Optional[int]:
    return _PORT_RESOLVED


def _open_browser(url: str) -> None:
    """Open Microsoft Edge to the dashboard URL.

    Se lanza en modo app con un perfil dedicado (--user-data-dir) para que sea
    un proceso propio y killable: así podemos cerrar la ventana al apagar el
    server (Ctrl+C). Con --new-window Edge delega en una instancia existente y
    el proceso muere al instante, dejando la ventana huérfana.
    """
    global _browser_proc
    import tempfile
    profile_dir = os.path.join(tempfile.gettempdir(), "quotex_hub_edge")
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in edge_paths:
        if Path(path).exists():
            _browser_proc = subprocess.Popen(
                [path, f"--app={url}", f"--user-data-dir={profile_dir}", "--no-first-run"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    # Fallback: let OS decide (no killable, no se cerrará automáticamente)
    try:
        import webbrowser
        webbrowser.open(url, new=0, autoraise=True)
    except Exception:
        pass


def _close_browser() -> None:
    """Cierra la ventana del HUB abierta por _open_browser (si sigue viva)."""
    global _browser_proc
    proc = _browser_proc
    if proc is None:
        return
    _browser_proc = None
    if proc.poll() is not None:
        return  # ya terminó
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    except Exception:
        pass


async def _auto_open_dashboard(host: str, port: int) -> None:
    """Wait a moment for server startup, then open browser."""
    if os.environ.get("HUB_NO_OPEN", "").lower() in ("1", "true", "yes"):
        return
    await asyncio.sleep(1.5)
    url = f"http://localhost:{port}"
    _open_browser(url)


async def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    actual_port = _resolve_port(port, host)
    poller = asyncio.create_task(_state_poller())
    relay = asyncio.create_task(_event_relay())

    config = uvicorn.Config(
        app,
        host=host,
        port=actual_port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    if actual_port != port:
        print(f"  ─> HUB dashboard: http://localhost:{actual_port} (puerto {port} en uso, se asignó uno libre)")
    else:
        print(f"  ─> HUB dashboard: http://localhost:{actual_port}  (HUB_PORT={port})")
    asyncio.create_task(_auto_open_dashboard(host, actual_port))
    try:
        await server.serve()
    finally:
        _close_browser()
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


def start(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> asyncio.Task:
    global _server_task
    port = _resolve_port(port, host)
    _server_task = asyncio.create_task(run_server(host=host, port=port))
    return _server_task


async def stop() -> None:
    global _server_task
    if _server_task:
        _server_task.cancel()
        try:
            await _server_task
        except asyncio.CancelledError:
            pass
        _server_task = None
