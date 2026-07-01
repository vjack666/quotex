"""WebSocket Quotex: conexión, velas y envío de órdenes."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, List, Optional, Tuple

from pyquotex.stable_api import Quotex  # type: ignore

from config import (
    CF_403_BACKOFF_SEC,
    CONNECT_RETRIES,
    FETCH_RETRIES,
    FETCH_RETRY_BACKOFF_SEC,
    HEALTHCHECK_RECONNECT_RETRIES,
    MIN_PAYOUT,
    RECONNECT_TIMEOUT_SEC,
)
from models import Candle

log = logging.getLogger("connection")


def raw_to_candle(raw: dict) -> Optional[Candle]:
    try:
        return Candle(
            ts=int(raw["time"]),
            open=float(raw["open"]),
            high=float(raw["high"]),
            low=float(raw["low"]),
            close=float(raw["close"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


async def fetch_candles(
    client: Quotex,
    asset: str,
    tf_sec: int,
    count: int,
) -> List[Candle]:
    end_time = time.time()
    offset = count * tf_sec
    try:
        raw_list = await client.get_candles(asset, end_time, offset, tf_sec)
    except Exception as exc:
        log.debug("Error velas %s tf=%ss: %s", asset, tf_sec, exc)
        return []
    if not raw_list:
        return []
    candles = [raw_to_candle(r) for r in raw_list if isinstance(r, dict)]
    valid = [c for c in candles if c and c.high > 0]
    return sorted(valid, key=lambda c: c.ts)


async def fetch_candles_with_retry(
    client: Quotex,
    asset: str,
    tf_sec: int,
    count: int,
    timeout_sec: float,
    retries: int = FETCH_RETRIES,
) -> List[Candle]:
    attempts = max(1, int(retries))
    for attempt in range(1, attempts + 1):
        try:
            candles = await asyncio.wait_for(
                fetch_candles(client, asset, tf_sec, count),
                timeout=timeout_sec,
            )
            if candles:
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

    ok_reconnect, reconnect_reason = await force_reconnect(
        client, account_type, step_label="pre-orden", asset=asset, direction=direction, amount=amount,
    )
    if not ok_reconnect:
        return False, "", 0.0, 0, reconnect_reason

    t0 = time.time()
    try:
        status, info = await asyncio.wait_for(
            client.buy(amount=amount, asset=asset, direction=direction, duration=duration),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        return False, "", 0.0, 0, "buy_timeout_30s"
    except Exception as exc:
        first_reason = f"buy_exception:{exc}"
        if not looks_like_connection_issue(first_reason):
            return False, "", 0.0, 0, first_reason
        ok_reconnect, reconnect_reason = await force_reconnect(
            client, account_type, step_label="reintento", asset=asset, direction=direction, amount=amount,
        )
        if not ok_reconnect:
            return False, "", 0.0, 0, f"{first_reason} | {reconnect_reason}"
        try:
            status, info = await asyncio.wait_for(
                client.buy(amount=amount, asset=asset, direction=direction, duration=duration),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            return False, "", 0.0, 0, "buy_timeout_30s_retry"
        except Exception as retry_exc:
            return False, "", 0.0, 0, f"buy_exception_retry:{retry_exc}"

    elapsed = time.time() - t0
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
        reject_reason = str(
            info.get("message") or info.get("reason") or info.get("error") or reject_reason
        )
    elif info is not None:
        reject_reason = str(info)

    if looks_like_connection_issue(reject_reason):
        ok_reconnect, reconnect_reason = await force_reconnect(
            client, account_type, step_label="reintento", asset=asset, direction=direction, amount=amount,
        )
        if not ok_reconnect:
            return False, "", 0.0, 0, f"{reject_reason} | {reconnect_reason}"
        try:
            status_retry, info_retry = await asyncio.wait_for(
                client.buy(amount=amount, asset=asset, direction=direction, duration=duration),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            return False, "", 0.0, 0, "buy_timeout_30s_retry"
        except Exception as retry_exc:
            return False, "", 0.0, 0, f"buy_exception_retry:{retry_exc}"

        if status_retry and isinstance(info_retry, dict):
            order_ref = 0
            for key in ("id_number", "idNumber", "openOrderId", "ticket"):
                raw_val = info_retry.get(key)
                try:
                    if raw_val is not None:
                        order_ref = int(raw_val)
                        break
                except (TypeError, ValueError):
                    continue
            return True, info_retry.get("id", ""), float(info_retry.get("openPrice", 0)), order_ref, ""

        retry_reason = "broker_rejected_retry"
        if isinstance(info_retry, dict):
            retry_reason = str(
                info_retry.get("message")
                or info_retry.get("reason")
                or info_retry.get("error")
                or retry_reason
            )
        return False, "", 0.0, 0, retry_reason

    return False, "", 0.0, 0, reject_reason


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
            await asyncio.sleep(1.5)
    return False, str(reason)


class ConnectionManager:
    def __init__(self, client: Quotex):
        self.client = client

    async def ensure_connection(self, account_type: str) -> bool:
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
            await asyncio.sleep(2.0)
        return False