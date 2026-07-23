"""Tests del repartidor de café (CaffeineLoop / keepalive de aplicación).

Garantiza que el café llegue en el formato correcto: TEXTO "2" por el
WebSocket de engine.io, NO un ping frame binario (que es lo que ignora Quotex
y causa el "se duerme").
"""

import asyncio
import time
from unittest.mock import MagicMock

import pytest

import config as _config
from caffeine import (
    CaffeineLoop, _ws_send_text, _ENGINEIO_PING, _SOCKETIO_TICK,
    ConnectionWatchdog,
)


class _FakeWS:
    """WebSocketApp falsificado que registra QUÉ se envió y CÓMO."""

    def __init__(self):
        self.sent = []          # lista de (payload, opcode)

    def send(self, payload, opcode=None):
        # Réplica mínima de WebSocketApp.send: opcode None => TEXTO.
        self.sent.append((payload, opcode))


class _FakeClient:
    """Cliente pyquotex falso con la jerarquía REAL de pyquotex.

    ``Quotex`` NO tiene ``websocket_client`` asignado; el WebSocketApp vivo vive
    en ``client.api.websocket_client.wss`` (propiedad ``client.api.websocket``).
    El cliente falso REPRODUCE ese bug: si caffeine lee ``client.websocket``
    directo, debe caer en None / AttributeError (igual que en prod).
    """

    def __init__(self):
        self.api = _FakeAPI()

    @property
    def websocket(self):
        # Réplica del bug de pyquotex: Quotex.websocket_client es None.
        raise AttributeError("'NoneType' object has no attribute 'wss'")


class _FakeAPI:
    def __init__(self):
        self.websocket_client = _FakeWebsocketClient()

    @property
    def websocket(self):
        # Réplica de QuotexAPI.websocket (api.py:134) -> websocket_client.wss
        return self.websocket_client.wss


class _FakeWebsocketClient:
    def __init__(self):
        self.wss = _FakeWS()


def test_keepalive_sends_engineio_ping_as_text_not_pingframe():
    """El café debe ser el TEXTO '2', no un ping frame binario."""
    client = _FakeClient()
    ok = _ws_send_text(client, _ENGINEIO_PING)
    assert ok is True
    assert len(client.api.websocket_client.wss.sent) == 1
    payload, opcode = client.api.websocket_client.wss.sent[0]
    assert payload == "2"
    # opcode None => WebSocketApp lo manda como TEXTO (engine.io ping de app).
    # Un ping frame binario tendría opcode != None (OPCODE_PING).
    assert opcode is None, "El café NO debe ser un ping frame; debe ser texto."


def test_old_bug_client_websocket_is_none():
    """Regresión: leer client.websocket directo caía en None/AttributeError.

    Documenta el bug original: caffeine debe resolver client.api.websocket,
    no client.websocket (que en pyquotex es None).
    """
    client = _FakeClient()
    # El camino viejo (client.websocket) rompe igual que en producción.
    try:
        direct = client.websocket
        assert direct is None
    except AttributeError:
        pass  # también es válido: pyquotex lanza AttributeError
    # El camino nuevo (api.websocket) SÍ resuelve el socket vivo.
    assert client.api.websocket is not None


def test_keepalive_handles_closed_socket_gracefully():
    """Si el socket está cerrado / no disponible, no rompe el loop."""
    client = MagicMock()
    client.api = None  # sin api => _resolve_app_ws devuelve None
    assert _ws_send_text(client, _ENGINEIO_PING) is False

    class _Boom:
        def send(self, *a, **k):
            raise RuntimeError("socket closed")

    client2 = MagicMock()
    client2.api = MagicMock()
    client2.api.websocket = _Boom()
    assert _ws_send_text(client2, _ENGINEIO_PING) is False


async def _run_loop_for(client, loop, seconds):
    """Arranca el loop, espera `seconds`, lo detiene y cancela limpio."""
    task = asyncio.create_task(loop.run())
    try:
        await asyncio.sleep(seconds)
        loop.stop()
        await asyncio.wait_for(task, timeout=2.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


@pytest.mark.asyncio
async def test_caffeine_loop_sends_ping_periodically(monkeypatch):
    """En un intervalo corto, el loop manda al menos un '2' de texto."""
    monkeypatch.setattr(_config, "CAFFEINE_ENABLED", True)
    monkeypatch.setattr(_config, "CAFFEINE_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(_config, "CAFFEINE_JITTER_SEC", 0.0)
    monkeypatch.setattr(_config, "CAFFEINE_TICK_AFTER_IDLE_SEC", 999.0)

    client = _FakeClient()
    loop = CaffeineLoop(client)
    await _run_loop_for(client, loop, 0.25)

    pings = [p for (p, op) in client.api.websocket_client.wss.sent if p == "2" and op is None]
    assert len(pings) >= 1, "El loop debe haber mandado al menos un café de texto."


@pytest.mark.asyncio
async def test_caffeine_loop_sends_tick_after_idle(monkeypatch):
    """Tras inactividad, manda 42['tick'] para mantener viva la sesión socket.io."""
    monkeypatch.setattr(_config, "CAFFEINE_ENABLED", True)
    monkeypatch.setattr(_config, "CAFFEINE_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(_config, "CAFFEINE_JITTER_SEC", 0.0)
    monkeypatch.setattr(_config, "CAFFEINE_TICK_AFTER_IDLE_SEC", 0.01)

    client = _FakeClient()
    loop = CaffeineLoop(client)
    # Forzamos inactividad larga desde el arranque.
    loop._last_traffic_ts = time.time() - 100.0
    await _run_loop_for(client, loop, 0.25)

    ticks = [p for (p, op) in client.api.websocket_client.wss.sent if p == _SOCKETIO_TICK]
    assert len(ticks) >= 1, "Tras idle debe mandar un 42['tick']."


@pytest.mark.asyncio
async def test_caffeine_disabled_does_nothing(monkeypatch):
    monkeypatch.setattr(_config, "CAFFEINE_ENABLED", False)
    client = _FakeClient()
    loop = CaffeineLoop(client)
    await loop.run()
    assert client.api.websocket_client.wss.sent == []


@pytest.mark.asyncio
async def test_caffeine_respects_reconnect_lock(monkeypatch):
    """No manda tráfico mientras otra ruta sostiene _RECONNECT_LOCK (RT-02)."""
    from connection import _RECONNECT_LOCK

    monkeypatch.setattr(_config, "CAFFEINE_ENABLED", True)
    monkeypatch.setattr(_config, "CAFFEINE_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(_config, "CAFFEINE_JITTER_SEC", 0.0)
    monkeypatch.setattr(_config, "CAFFEINE_TICK_AFTER_IDLE_SEC", 999.0)

    client = _FakeClient()
    loop = CaffeineLoop(client)

    # Tomamos el lock en otro task y lo sostenemos un rato.
    async def _hold_lock():
        async with _RECONNECT_LOCK:
            await asyncio.sleep(0.3)

    holder = asyncio.create_task(_hold_lock())
    task = asyncio.create_task(loop.run())
    # Mientras el lock está tomado (0.3s), el loop debe estar bloqueado esperando.
    await asyncio.sleep(0.2)
    loop.stop()
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        task.cancel()
        try:
            await task
        except Exception:
            pass
    await holder

    # Durante los ~0.3s que el lock estuvo tomado, NO debió mandar nada.
    assert client.api.websocket_client.wss.sent == [], (
        "Caffeine no debe enviar mientras el lock de reconexión está tomado."
    )


# ── Tests del ConnectionWatchdog (safety net de reconexión) ──────────────────

class _FakeClientWD:
    """Cliente pyquotex falso con check_connect() configurable y .api vivo."""

    def __init__(self, up=True):
        self._up = up
        self.api = object()  # no-None => _is_up intenta check_connect

    async def check_connect(self):
        return self._up


async def _run_watchdog_for(wd, seconds):
    task = asyncio.create_task(wd.run())
    try:
        await asyncio.sleep(seconds)
        wd.stop()
        await asyncio.wait_for(task, timeout=2.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        task.cancel()
        try:
            await task
        except Exception:
            pass


@pytest.mark.asyncio
async def test_watchdog_recovers_when_socket_down(monkeypatch):
    """Si el socket cae, el watchdog llama ensure_connection y registra recovery."""
    monkeypatch.setattr(_config, "WATCHDOG_ENABLED", True)
    monkeypatch.setattr(_config, "WATCHDOG_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(_config, "WATCHDOG_JITTER_SEC", 0.0)
    monkeypatch.setattr(_config, "WATCHDOG_GRACE_SEC", 0.0)

    client = _FakeClientWD(up=False)  # siempre caído
    recovered = []

    async def _ensure():
        recovered.append(1)
        return True

    wd = ConnectionWatchdog(client, _ensure)
    await _run_watchdog_for(wd, 0.25)

    assert len(recovered) >= 1, "El watchdog debe haber llamado ensure_connection."
    assert wd.stats["recoveries"] >= 1
    assert wd.stats["checks"] >= 1


@pytest.mark.asyncio
async def test_watchdog_leaves_socket_alone_when_up(monkeypatch):
    """Si el socket está bien, el watchdog NO llama ensure_connection."""
    monkeypatch.setattr(_config, "WATCHDOG_ENABLED", True)
    monkeypatch.setattr(_config, "WATCHDOG_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(_config, "WATCHDOG_JITTER_SEC", 0.0)
    monkeypatch.setattr(_config, "WATCHDOG_GRACE_SEC", 0.0)

    client = _FakeClientWD(up=True)  # siempre arriba
    calls = []

    async def _ensure():
        calls.append(1)
        return True

    wd = ConnectionWatchdog(client, _ensure)
    await _run_watchdog_for(wd, 0.25)

    assert calls == [], "Con socket arriba, no debe reconectar."
    assert wd.stats["recoveries"] == 0


@pytest.mark.asyncio
async def test_watchdog_disabled_does_nothing(monkeypatch):
    monkeypatch.setattr(_config, "WATCHDOG_ENABLED", False)
    client = _FakeClientWD(up=False)
    calls = []

    async def _ensure():
        calls.append(1)
        return True

    wd = ConnectionWatchdog(client, _ensure)
    await wd.run()
    assert calls == [], "Watchdog deshabilitado no debe reconectar."


@pytest.mark.asyncio
async def test_watchdog_handles_check_connect_exception(monkeypatch):
    """Si check_connect lanza (api rota), el watchdog lo traga y reintenta."""
    monkeypatch.setattr(_config, "WATCHDOG_ENABLED", True)
    monkeypatch.setattr(_config, "WATCHDOG_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(_config, "WATCHDOG_JITTER_SEC", 0.0)
    monkeypatch.setattr(_config, "WATCHDOG_GRACE_SEC", 0.0)

    client = MagicMock()
    client.api = object()

    async def _boom():
        raise RuntimeError("api dead")

    client.check_connect = _boom
    recovered = []

    async def _ensure():
        recovered.append(1)
        return True

    wd = ConnectionWatchdog(client, _ensure)
    await _run_watchdog_for(wd, 0.25)

    # check_connect lanzó => _is_up False => debe intentar recovery.
    assert wd.stats["recoveries"] >= 1
    assert len(recovered) >= 1


# ── Test de cableado al call site real (patrón de main()) ────────────────────

class _FakeBot:
    """Bot mínimo que replica el wiring de main(): client + ensure_connection."""

    def __init__(self, up=True):
        self.account_type = "PRACTICE"
        self.client = _FakeClientWD(up=up)
        self.reconnects = 0

    async def ensure_connection(self) -> bool:
        self.reconnects += 1
        return True


@pytest.mark.asyncio
async def test_watchdog_wiring_like_main_runs_and_stops(monkeypatch):
    """Replica el snippet de main(): ConnectionWatchdog(client, bot.ensure_connection).

    Audita que el CALL SITE real (mismo patrón que consolidation_bot.main) arranca
    el watchdog y que shutdown (stop + cancel) lo termina limpio sin quedar colgado.
    """
    monkeypatch.setattr(_config, "WATCHDOG_ENABLED", True)
    monkeypatch.setattr(_config, "WATCHDOG_INTERVAL_SEC", 0.05)
    monkeypatch.setattr(_config, "WATCHDOG_JITTER_SEC", 0.0)
    monkeypatch.setattr(_config, "WATCHDOG_GRACE_SEC", 0.0)

    bot = _FakeBot(up=False)
    from caffeine import ConnectionWatchdog

    # == snippet idéntico a main() ==
    watchdog = ConnectionWatchdog(
        bot.client, bot.ensure_connection, account_type=bot.account_type
    )
    task = asyncio.create_task(watchdog.run(), name="conn-watchdog")

    await asyncio.sleep(0.2)
    watchdog.stop()
    task.cancel()
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass

    assert task.done(), "El watchdog debe terminar tras stop()/cancel()."
    assert bot.reconnects >= 1, "Debe haber llamado bot.ensure_connection."
    assert watchdog.stats["recoveries"] >= 1
