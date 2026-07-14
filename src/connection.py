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
    MIN_PAYOUT,
    RECONNECT_TIMEOUT_SEC,
)
from models import Candle

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


def raw_to_candle(raw: dict) -> Optional[Candle]:
    try:
        return Candle(
            ts=int(raw["time"]),
            open=float(raw["open"]),
            high=float(raw["high"]),
            low=float(raw["low"]),
            close=float(raw["close"]),
            ticks=int(raw.get("ticks", 0) or 0),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _min_expected_candles(count: int) -> int:
    return max(3, int(count * 0.5))


def _candles_from_raw(raw_list: list) -> List[Candle]:
    candles = [raw_to_candle(r) for r in raw_list if isinstance(r, dict)]
    valid = [c for c in candles if c and c.high > 0]
    return sorted(valid, key=lambda c: c.ts)


async def fetch_candles(
    client: Quotex,
    asset: str,
    tf_sec: int,
    count: int,
    *,
    timeout_sec: Optional[float] = None,
) -> List[Candle]:
    min_expected = _min_expected_candles(count)
    end_time = time.time()
    offset = count * tf_sec
    valid: List[Candle] = []
    try:
        raw_list = await client.get_candles(asset, end_time, offset, tf_sec)
    except Exception as exc:
        log.debug("Error velas %s tf=%ss: %s", asset, tf_sec, exc)
        raw_list = None
    if raw_list:
        valid = _candles_from_raw(raw_list)
        if len(valid) >= min_expected:
            return valid
    got = len(valid)
    if hasattr(client, "get_historical_candles"):
        log.debug(
            "%s tf=%ss: get_candles returned %d<%d, using get_historical_candles",
            asset, tf_sec, got, min_expected,
        )
        amount_of_seconds = count * tf_sec
        hist_timeout = int(timeout_sec) if timeout_sec is not None else 30
        try:
            historical = await client.get_historical_candles(
                asset, amount_of_seconds, tf_sec, timeout=hist_timeout,
            )
            if historical:
                valid_hist = _candles_from_raw(historical)
                if len(valid_hist) > count:
                    valid_hist = valid_hist[-count:]
                if valid_hist:
                    return valid_hist
        except Exception as exc:
            log.debug(
                "Error get_historical_candles %s tf=%ss: %s", asset, tf_sec, exc,
            )
    return valid


async def fetch_candles_with_retry(
    client: Quotex,
    asset: str,
    tf_sec: int,
    count: int,
    timeout_sec: float,
    retries: int = FETCH_RETRIES,
) -> List[Candle]:
    attempts = max(1, int(retries))
    min_expected = _min_expected_candles(count)
    for attempt in range(1, attempts + 1):
        try:
            candles = await asyncio.wait_for(
                fetch_candles(client, asset, tf_sec, count, timeout_sec=timeout_sec),
                timeout=timeout_sec,
            )
            if candles and len(candles) >= min_expected:
                return candles
        except asyncio.TimeoutError:
            log.debug(
                "%s: timeout local velas tf=%ss intento %d/%d (%.1fs)",
                asset, tf_sec, attempt, attempts, timeout_sec,
            )
        except Exception as exc:
            log.debug(
                "%s: error velas tf=%ss intento %d/%d: %s",
                asset, tf_sec, attempt, attempts, exc,
            )
        if attempt < attempts:
            await asyncio.sleep(FETCH_RETRY_BACKOFF_SEC * attempt)
    return []


async def get_open_assets(
    client: Quotex,
    min_payout: int = MIN_PAYOUT,
) -> List[Tuple[str, int]]:
    try:
        instruments = await client.get_instruments()
    except Exception:
        return []
    if not instruments:
        return []

    result: list[tuple[str, int]] = []
    for i in instruments:
        try:
            sym = str(i[1])
            is_open = bool(i[14])
            payout = int(i[18]) if len(i) > 18 else 0
        except (IndexError, TypeError, ValueError):
            continue
        if sym.endswith("_otc") and is_open and payout >= min_payout:
            result.append((sym, payout))
    result.sort(key=lambda x: -x[1])
    return result


def looks_like_connection_issue(reason: str) -> bool:
    text = (reason or "").lower()
    conn_hints = (
        "websocket", "handshake", "403", "connect", "connection",
        "session", "closed", "disconnect", "network", "socket",
        "reconnect", "timeout", "remote host was lost",
    )
    return any(hint in text for hint in conn_hints)


async def force_reconnect(
    client: Quotex,
    account_type: str,
    *,
    step_label: str = "reconnect",
    asset: str = "",
    direction: str = "",
    amount: float = 0.0,
) -> Tuple[bool, str]:
    # RT-02: una sola reconexión a la vez en todo el proceso.
    async with _RECONNECT_LOCK:
        return await _force_reconnect_locked(
            client, account_type,
            step_label=step_label, asset=asset, direction=direction, amount=amount,
        )


async def _force_reconnect_locked(
    client: Quotex,
    account_type: str,
    *,
    step_label: str = "reconnect",
    asset: str = "",
    direction: str = "",
    amount: float = 0.0,
) -> Tuple[bool, str]:
    log.info(
        "Reconexión %s: %s %s $%.2f",
        step_label, asset, direction.upper() if direction else "", amount,
    )
    last_reason = ""
    for attempt in range(1, CONNECT_RETRIES + 1):
        try:
            await client.close()
        except Exception:
            pass

        await asyncio.sleep(1.0)
        try:
            ok_conn, reason_conn = await asyncio.wait_for(
                client.connect(),
                timeout=RECONNECT_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            last_reason = f"reconnect_timeout_connect_{RECONNECT_TIMEOUT_SEC:.0f}s"
            continue
        except Exception as exc:
            last_reason = f"reconnect_exception_connect:{exc}"
            continue

        if not ok_conn:
            last_reason = f"reconnect_failed:{reason_conn}"
            continue

        try:
            await asyncio.wait_for(
                client.change_account(account_type),
                timeout=RECONNECT_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            last_reason = f"reconnect_timeout_change_account_{RECONNECT_TIMEOUT_SEC:.0f}s"
            continue
        except Exception as exc:
            last_reason = f"reconnect_exception_change_account:{exc}"
            continue

        await asyncio.sleep(0.6)
        return True, ""

    return False, last_reason or "reconnect_failed_without_reason"


async def _send_order(client, asset, direction, amount, duration, time_mode):
    """Envía la orden y espera la confirmación del broker.

    Usa client.buy() de ALTO nivel (igual que las pruebas aisladas que
    confirman en <2s). NO usar client.api.buy() + wait manual de buy_id:
    ese flujo de bajo nivel hace que el broker rechace con broker_rejected
    (status=False, info=None). client.buy() ya devuelve (status, info) con
    el id de la orden en info["id"].
    """
    try:
        status, info = await client.buy(
            amount, asset, direction, duration, time_mode=time_mode
        )
    except Exception as exc:
        return False, {"message": str(exc)}
    if not status:
        return False, info if isinstance(info, dict) else {"message": str(info)}
    return True, info


def _handle_order_result(status, info, trade_client) -> Tuple[bool, str, float, int, str]:
    """Convierte el (status, info) de pyquotex en la tupla de retorno de place_order."""
    if status and isinstance(info, dict):
        order_ref = 0
        for key in ("id_number", "idNumber", "openOrderId", "ticket"):
            raw_val = info.get(key)
            try:
                if raw_val is not None:
                    order_ref = int(raw_val)
                    break
            except (TypeError, ValueError):
                continue
        return True, info.get("id", ""), float(info.get("openPrice", 0)), order_ref, ""
    reject_reason = "broker_rejected"
    if isinstance(info, dict):
        reject_reason = str(info.get("message") or info.get("reason") or info.get("error") or reject_reason)
    elif info is not None:
        reject_reason = str(info)
    else:
        try:
            api = getattr(trade_client, "api", None)
            log.warning(
                "  [DIAG F6] status=%s info=%r buy_id=%r buy_successful=%r ws_err=%r",
                status, info,
                getattr(api, "buy_id", None),
                getattr(api, "buy_successful", None),
                getattr(getattr(api, "state", None), "websocket_error_reason", None),
            )
        except Exception:
            pass
    return False, "", 0.0, 0, reject_reason


async def place_order(
    client: Quotex,
    asset: str,
    direction: str,
    amount: float,
    duration: int,
    dry_run: bool,
    account_type: str = "PRACTICE",
) -> Tuple[bool, str, float, int, str]:
    if dry_run:
        log.info("  [DRY-RUN] %s %s $%.2f %ds", direction.upper(), asset, amount, duration)
        return True, f"DRY-{int(time.time())}", 0.0, 0, ""

    _EQUITY_OTC_MARKERS = (
        "MCD", "JNJ", "AXP", "AMZN", "AAPL", "GOOGL", "MSFT", "TSLA",
        "NFLX", "META", "NVDA", "BAC", "GS", "V", "WMT",
    )
    if any(asset.upper().startswith(m) for m in _EQUITY_OTC_MARKERS):
        log.warning("  Activo equity OTC (%s) — puede tener restricciones de horario.", asset)

    # Fix F6: Quotex exige optionType=100 (binary) con duración en segundos para
    # activos OTC; pyquotex con time_mode="TIME" (default) manda optionType=1 con
    # timestamp absoluto y el broker rechaza la orden (reason=unexpected). Forzamos
    # TIMER en OTC para que el payload lleve optionType=100 + time=duration.
    time_mode = "TIMER" if asset.endswith("_otc") else "TIME"

    # Envío simple y comprobado (otc_trader.enviar_orden): client.buy() de
    # alto nivel con time_mode="TIMER" para OTC. Es la misma lógica que el
    # script de prueba que funciona en demo. Reemplaza el _send_order frágil.
    from otc_trader import enviar_orden

    ok, info = await enviar_orden(client, asset, direction, amount, duration)
    return _handle_order_result(ok, info, client)


async def connect_with_retry(client: Quotex) -> Tuple[bool, str]:
    reason = ""
    for attempt in range(1, CONNECT_RETRIES + 1):
        ok, reason = await client.connect()
        if ok:
            return True, ""
        reason_txt = str(reason)
        if "403" in reason_txt or "cloudflare" in reason_txt.lower() or "cf-mitigated" in reason_txt.lower():
            await asyncio.sleep(CF_403_BACKOFF_SEC)
        else:
            await asyncio.sleep(CONNECT_RETRY_DELAY_SEC)
    return False, str(reason)


class ConnectionManager:
    def __init__(self, client: Quotex):
        self.client = client

    async def ensure_connection(self, account_type: str) -> bool:
        # RT-02: una sola reconexión a la vez en todo el proceso (watchdog y
        # loop de trading comparten este lock con force_reconnect).
        async with _RECONNECT_LOCK:
            return await self._ensure_connection_locked(account_type)

    async def _ensure_connection_locked(self, account_type: str) -> bool:
        try:
            if await asyncio.wait_for(self.client.check_connect(), timeout=3.0):
                return True
        except Exception:
            pass

        for attempt in range(1, HEALTHCHECK_RECONNECT_RETRIES + 1):
            try:
                try:
                    await asyncio.wait_for(self.client.close(), timeout=2.0)
                except Exception:
                    pass

                ok, reason = await asyncio.wait_for(
                    self.client.connect(),
                    timeout=RECONNECT_TIMEOUT_SEC,
                )
                if ok:
                    await asyncio.wait_for(
                        self.client.change_account(account_type),
                        timeout=RECONNECT_TIMEOUT_SEC,
                    )
                    log.warning("Reconexión exitosa durante loop 24/7")
                    return True
                reason_txt = str(reason)
                if "403" in reason_txt or "cloudflare" in reason_txt.lower():
                    await asyncio.sleep(CF_403_BACKOFF_SEC)
                    continue
            except asyncio.TimeoutError:
                pass
            except Exception as exc:
                log.warning("Excepción en reconexión: %s", exc)
            await asyncio.sleep(CONNECT_RETRY_DELAY_SEC)
        return False


async def create_trading_client(
    email: str, password: str, account_type: str = "PRACTICE",
) -> Tuple[Optional[Quotex], str]:
    """Crea y conecta un cliente Quotex LIMPIO dedicado a enviar órdenes.

    Fix F6 (raíz): el bot usaba UN solo WebSocket para scanner/HTF (streams de
    velas en vivo de ~29 activos en M1+M5) y para buy(). Esa combinación de
    streams en vivo en el mismo socket deja orders/open sin respuesta (el broker
    da 'unexpected' o pyquotex hace timeout 185s). Separar datos de trading en dos
    conexiones elimina la competencia por el socket y buy() confirma en <2s.
    """
    client = Quotex(email=email, password=password)
    try:
        ok, reason = await asyncio.wait_for(client.connect(), timeout=RECONNECT_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        return None, "trading_client_connect_timeout"
    except Exception as exc:
        return None, f"trading_client_connect_exc:{exc}"
    if not ok:
        return None, f"trading_client_connect_failed:{reason}"
    try:
        await asyncio.wait_for(client.change_account(account_type), timeout=RECONNECT_TIMEOUT_SEC)
    except Exception:
        pass
    return client, ""