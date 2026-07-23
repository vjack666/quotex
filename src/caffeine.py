"""Caffeine — keepalive de APLICACIÓN para el WebSocket de Quotex.

Por qué existe (modo dumi)
--------------------------
El bot y Quotex se hablan por engine.io v3 (socket.io). Para que el servidor
no corte la llamada por inactividad (Cloudflare idle-timeout ~60-75s), hay que
mandarle la palabra "2" por el tubo de TEXTO de vez en cuando: eso es el café.

El problema que arregla
-----------------------
pyquotex deja el keepalive en manos de la librería websocket-client
(ping_interval=24). Pero websocket-client 1.9.0 manda ese "2" como un
*WebSocket ping frame binario*, que Quotex (engine.io) ignora a efectos de
"estoy vivo". Resultado: en idle real nadie le manda "2" de texto al server,
Cloudflare cierra, y el bot se duerme ("Connection to remote host was lost").

Solución
--------
Un loop async propio que cada ~CAFFEINE_INTERVAL_SEC manda el "2" como TEXTO
plano por el WebSocket, y además un `42["tick"]` si lleva rato sin tráfico
(para mantener viva la sesión socket.io cuando no hay ticks de precio).
No depende de pyquotex: usa el socket subyacente directamente.

Comparte `_RECONNECT_LOCK` con ensure_connection/force_reconnect para no mandar
tráfico mientras otra ruta está reconstruyendo el socket (RT-02).
"""

from __future__ import annotations

import asyncio
import logging
import random
import time

import config
from connection import _RECONNECT_LOCK

log = logging.getLogger("caffeine")

# Mensajes engine.io / socket.io que SÍ son "café" (texto, no ping frame).
_ENGINEIO_PING = "2"                 # engine.io v3 ping de aplicación
_SOCKETIO_TICK = '42["tick"]'        # mantiene viva la sesión socket.io


def _resolve_app_ws(client):
    """Resuelve el WebSocketApp VIVO de pyquotex (el que corre el run_forever).

    En pyquotex la jerarquía es::

        Quotex (client)
          .api                       -> QuotexAPI   (None hasta connect())
            .websocket_client        -> WebsocketClient
              .wss                   -> websocket.WebSocketApp  (el socket real)

    ``Quotex.websocket`` (client.websocket) devuelve ``self.websocket_client.wss``
    PERO ``Quotex.websocket_client`` se queda en None (nunca se asigna en la clase
    ``Quotex``); lo que pyquotex crea es ``client.api.websocket_client``. Por eso
    ``client.websocket`` lanza AttributeError y caffeine no mandaba ni un "2".

    Por eso resolvemos SIEMPRE ``client.api.websocket_client.wss`` (propiedad
    ``client.api.websocket``), FRESCO en cada llamada: tras una reconexión
    pyquotex crea un WebsocketClient nuevo, así que cachear el socket al inicio
    dejaría a caffeine escribiendo en un socket ya cerrado.

    Devuelve el WebSocketApp o None si aún no hay conexión / está reconstruyéndose.
    """
    try:
        api = getattr(client, "api", None)
        if api is None:
            return None
        # QuotexAPI.websocket -> self.websocket_client.wss (el WebSocketApp real).
        wss = getattr(api, "websocket", None)
        if wss is None:
            return None
        return wss
    except Exception as exc:  # api None, sin websocket_client, etc.
        log.debug("caffeine no pudo resolver el WS (%s): %s", type(exc).__name__, exc)
        return None


def _ws_send_text(client, payload: str) -> bool:
    """Envía ``payload`` como TEXTO por el WebSocket subyacente VIVO.

    Devuelve True si se despachó. Usa el socket real (WebSocketApp.wss de
    pyquotex), NO el ping frame de websocket-client, que es lo que ignora Quotex.

    Cualquier excepción (socket cerrado, reconectando, sin api) se traga y
    devuelve False para que el loop siga vivo y lo intente en el próximo ciclo.
    """
    try:
        wss = _resolve_app_ws(client)
        if wss is None:
            return False
        # WebSocketApp.send(data) con opcode por defecto (text) manda TEXTO.
        wss.send(payload)
        return True
    except Exception as exc:  # socket cerrado, no conectado, etc.
        log.debug("caffeine send falló (%s): %s", type(exc).__name__, exc)
        return False


class CaffeineLoop:
    """Repartidor de café: mantiene viva la conexión en idle.

    Uso::

        loop = CaffeineLoop(bot.client)
        task = asyncio.create_task(loop.run(), name="caffeine")
        ...
        loop.stop()
        await task
    """

    def __init__(self, client, *, account_type: str = "PRACTICE"):
        self.client = client
        self.account_type = account_type
        self._stop = False
        self._last_traffic_ts = time.time()
        self._pings_sent = 0
        self._ticks_sent = 0
        self._last_error_ts = 0.0

    # API para que el resto del bot avise "hubo tráfico" (on_message, sends).
    def mark_traffic(self) -> None:
        self._last_traffic_ts = time.time()

    @property
    def stats(self) -> dict:
        return {
            "enabled": config.CAFFEINE_ENABLED,
            "pings_sent": self._pings_sent,
            "ticks_sent": self._ticks_sent,
            "last_traffic_ts": self._last_traffic_ts,
            "secs_since_traffic": time.time() - self._last_traffic_ts,
        }

    def stop(self) -> None:
        self._stop = True

    async def run(self) -> None:
        if not config.CAFFEINE_ENABLED:
            log.info("Caffeine deshabilitado (CAFFEINE_ENABLED=False)")
            return
        log.info(
            "☕ Caffeine arrancado — ping app cada %.0fs, tick tras %.0fs idle",
            config.CAFFEINE_INTERVAL_SEC, config.CAFFEINE_TICK_AFTER_IDLE_SEC,
        )
        while not self._stop:
            # Jitter para no sincronizar con otros clientes/keepalives.
            jitter = random.uniform(0.0, max(0.0, config.CAFFEINE_JITTER_SEC))
            try:
                await asyncio.sleep(config.CAFFEINE_INTERVAL_SEC + jitter)
            except asyncio.CancelledError:
                break
            if self._stop:
                break

            # No mandar tráfico mientras otra ruta (ensure_connection / hub
            # reconnect) está reconstruyendo el socket: compartimos el lock RT-02.
            async with _RECONNECT_LOCK:
                if self._stop:
                    break
                ok = _ws_send_text(self.client, _ENGINEIO_PING)
                if ok:
                    self._pings_sent += 1
                    # El ping de app es salida nuestra: NO cuenta como tráfico de
                    # entrada del servidor (ver _last_traffic_ts / mark_traffic).
                else:
                    # Socket no disponible ahora: será la reconexión quien lo fixee.
                    continue

                # Si llevamos rato sin tráfico de ENTRADA del servidor, mandamos un
                # tick para mantener viva la sesión socket.io (equivalente a on_open).
                # Se basa en _last_traffic_ts (actualizado por mark_traffic/on_message),
                # no en nuestros propios pings de salida.
                idle = time.time() - self._last_traffic_ts
                if idle >= config.CAFFEINE_TICK_AFTER_IDLE_SEC:
                    if _ws_send_text(self.client, _SOCKETIO_TICK):
                        self._ticks_sent += 1
                        log.debug("caffeine tick enviado (idle %.0fs)", idle)

        log.info(
            "☕ Caffeine detenido — pings=%d ticks=%d",
            self._pings_sent, self._ticks_sent,
        )


def install_traffic_hook(client, caffeine: "CaffeineLoop") -> None:
    """Engancha mark_traffic() al on_message de pyquotex para medir inactividad real.

    Envuelve el on_message existente del WebSocketApp VIVO (client.api.websocket).
    Si por cualquier razón no se puede enganchar, el loop sigue funcionando (solo
    no mide tráfico entrante fino, pero el ping periódico ya basta para no dormirse).
    """
    try:
        wss = _resolve_app_ws(client)
        if wss is None or not hasattr(wss, "on_message"):
            return
        _orig = wss.on_message

        def _wrapped(ws, msg):
            caffeine.mark_traffic()
            if _orig is not None:
                try:
                    _orig(ws, msg)
                except Exception as exc:  # nunca dejar que el hook rompa el flujo
                    log.debug("caffeine on_message hook exc: %s", exc)

        wss.on_message = _wrapped
    except Exception as exc:
        log.debug("caffeine no pudo instalar traffic hook: %s", exc)


class ConnectionWatchdog:
    """SAFETY NET: detecta el socket caído YA y lo levanta.

    El loop principal de trading hace ``check_connect`` cada ~60s (ciclo de scan).
    Si el socket se apaga entre ciclos, el bot tarda hasta 60s en darse cuenta.
    Este watchdog hace ``client.check_connect()`` cada ``WATCHDOG_INTERVAL_SEC``
    y, si cae, llama a ``ensure_connection`` (que cierra y reconecta con backoff).

    Comparte ``_RECONNECT_LOCK`` (RT-02) con caffeine y force_reconnect: mientras
    otra ruta reconstruye el socket, el watchdog espera su turno y no manda nada
    al aire. Es un safety net, NO reemplaza al loop principal — coexisten.

    No inventa un segundo motor de reconexión: delega en ``ensure_connection``
    del bot (el método canónico ya cableado al ConnectionManager).

    Uso::

        wd = ConnectionWatchdog(bot.client, bot.ensure_connection, account_type)
        task = asyncio.create_task(wd.run(), name="conn-watchdog")
        ...
        wd.stop(); await task
    """

    def __init__(self, client, ensure_connection, *, account_type: str = "PRACTICE"):
        self.client = client
        self.ensure_connection = ensure_connection
        self.account_type = account_type
        self._stop = False
        self._checks = 0
        self._recoveries = 0
        self._last_down_ts = 0.0
        self._down = False

    @property
    def stats(self) -> dict:
        return {
            "enabled": config.WATCHDOG_ENABLED,
            "checks": self._checks,
            "recoveries": self._recoveries,
            "down": self._down,
            "last_down_ts": self._last_down_ts,
        }

    def stop(self) -> None:
        self._stop = True

    async def _is_up(self) -> bool:
        """check_connect() de pyquotex: False si api es None o el socket cayó."""
        try:
            if self.client is None or self.client.api is None:
                return False
            return bool(await self.client.check_connect())
        except Exception as exc:  # api rota, sin state, etc.
            log.debug("watchdog check_connect exc (%s): %s", type(exc).__name__, exc)
            return False

    async def run(self) -> None:
        if not config.WATCHDOG_ENABLED:
            log.info("ConnectionWatchdog deshabilitado (WATCHDOG_ENABLED=False)")
            return
        log.info(
            "🔌 ConnectionWatchdog arrancado — check cada %.0fs",
            config.WATCHDOG_INTERVAL_SEC,
        )
        await asyncio.sleep(config.WATCHDOG_GRACE_SEC)
        while not self._stop:
            jitter = random.uniform(0.0, max(0.0, config.WATCHDOG_JITTER_SEC))
            try:
                await asyncio.sleep(config.WATCHDOG_INTERVAL_SEC + jitter)
            except asyncio.CancelledError:
                break
            if self._stop:
                break

            self._checks += 1
            up = await self._is_up()
            if up:
                self._down = False
                continue

            # Socket caído: marcamos y levantamos, compartiendo el lock RT-02.
            self._down = True
            self._last_down_ts = time.time()
            log.warning("🔌 Watchdog: socket caído — intentando reconexión")
            async with _RECONNECT_LOCK:
                if self._stop:
                    break
                try:
                    ok = await self.ensure_connection()
                except Exception as exc:
                    log.debug("watchdog ensure_connection exc: %s", exc)
                    ok = False
                if ok:
                    self._recoveries += 1
                    self._down = False
                    log.info("🔌 Watchdog: reconexión exitosa")
                else:
                    log.warning("🔌 Watchdog: reconexión falló (retry en próximo ciclo)")

        log.info(
            "🔌 ConnectionWatchdog detenido — checks=%d recoveries=%d",
            self._checks, self._recoveries,
        )
