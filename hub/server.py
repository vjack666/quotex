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
from .hub_scanner import HubScanner

HERE = Path(__file__).resolve().parent
STATIC_DIR = HERE / "static"
INDEX_PATH = STATIC_DIR / "index.html"

DEFAULT_HOST = os.environ.get("HUB_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("HUB_PORT", "8080"))
POLL_INTERVAL = float(os.environ.get("HUB_POLL_SEC", "0.8"))

_PORT_RESOLVED: Optional[int] = None

_scanner: Optional[HubScanner] = None
_bot_ref: Any = None
_clients: set[WebSocket] = set()
_server_task: Optional[asyncio.Task] = None

app = FastAPI(title="Quotex HUB", version="1.0.0", docs_url=None, redoc_url=None)


def init(scanner: HubScanner, bot: Any = None) -> None:
    global _scanner, _bot_ref
    _scanner = scanner
    _bot_ref = bot


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
        return {"status": "waiting"}
    state = _scanner.get_state()
    raw = _serialize(state)
    raw["status"] = "ok"
    return raw


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
    except WebSocketDisconnect:
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
    """Open Microsoft Edge to the dashboard URL."""
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in edge_paths:
        if Path(path).exists():
            subprocess.Popen([path, "--new-window", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    # Fallback: let OS decide
    try:
        import webbrowser
        webbrowser.open(url, new=0, autoraise=True)
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
