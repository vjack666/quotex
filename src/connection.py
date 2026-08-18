"""WebSocket Quotex: conexión, velas y envío de órdenes."""
from __future__ import annotations

import asyncio
import calendar
import logging
import os
import time
from typing import Any, List, Optional, Tuple

from pyquotex.stable_api import Quotex  # type: ignore

from config import (
    CF_403_BACKOFF_SEC,
    CONNECT_RETRIES,
    CONNECT_RETRY_DELAY_SEC,
    FETCH_RETRIES,
    FETCH_RETRY_BACKOFF_SEC,
    HEALTHCHECK_RECONNECT_RETRIES,
    MAX_CONSECUTIVE_RECONNECT_FAILURES,
    MAX_RECONNECT_BACKOFF_SEC,
    MIN_PAYOUT,
    RECONNECT_BACKOFF_BASE_SEC,
    RECONNECT_TIMEOUT_SEC,
)
from core.models import Candle

# Fix F6: pyquotex.buy() espera buy_id por (duration+5)s y SOLO al final lee
# websocket_error_reason. Para varios activos OTC el broker responde la confirmacion
# (o el error) en <2s, pero pyquotex no la procesa a tiempo y hace timeout 185s ->
# reason=broker_rejected. Replicamos buy() con un wait que detecta buy_id Y el error
# del broker en cada tick (abortando temprano), eliminando la condicion de carrera.
# (No importamos submodulos de pyquotex para evitar shadowing de 'pyquotex' como paquete;
#  get_timestamp() es equivalente a int(time.time()) en UTC epoch.)

log = logging.getLogger("connection")

# Lock de reconexión compartido (RT-02): evita que el watchdog de main.py y el
# loop de consolidation_bot.py reconecten el WebSocket a la vez y corrompan la
# sesión. Toda ruta de reconexión (force_reconnect / ConnectionManager) lo toma.
_RECONNECT_LOCK = asyncio.Lock()

# ── Reconnect state (for hub + diagnostics) ─────────────────────────────────
_reconnect_failures = 0        # consecutive failure counter
_reconnect_last_ts = 0.0       # timestamp of last reconnect attempt
_reconnect_last_ok = True      # last attempt succeeded?
_reconnect_recommended = False # True when max failures hit → recommend restart


def get_reconnect_state() -> dict: