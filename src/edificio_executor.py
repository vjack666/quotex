"""Ejecutor de contratados del Edificio de Contratación.

Conecta el evento CONTRATADO (src/edificio_contratacion.py) con la orden
real al broker. Corre en el loop del BOT (mismo proceso, socket único —
regla de oro de este proyecto): NO crea un cliente Quotex fresco.

Flujo:
  scanner alimenta el edificio → un activo llega a CONTRATADO
  → execute_contratados() consume la cola y envía place_order(client)
  → si el broker confirma: card.order_status = "sent"
  → si falla: re-encola con tries+1; al superar el máximo, descarta.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from config import (
    EDIFICIO_ACCOUNT_TYPE,
    EDIFICIO_MAX_EVENT_AGE_SEC,
    EDIFICIO_MAX_ORDER_TRIES,
    EDIFICIO_ORDER_AMOUNT,
    EDIFICIO_ORDER_DURATION_SEC,
)
from connection import place_order
from edificio_contratacion import CONTRATADO, PISO_3, ContratadoEvent

log = logging.getLogger("edificio_contratacion")


def is_sticky_cross(k: Optional[float], d: Optional[float], threshold: float = 3.0) -> bool:
    """True si K y D están tan pegadas que el cruce no es confiable.

    Regla del edificio: si K y D están muy juntas, cualquier movimiento
    chiquito genera un cruce falso → no se debe confiar en él.
    """
    if k is None or d is None:
        return False
    return abs(k - d) < threshold


async def execute_contratados(
    bot: Any,
    *,
    account_type: Optional[str] = None,
    amount: Optional[float] = None,
    duration: Optional[int] = None,
    max_tries: Optional[int] = None,
    max_event_age_sec: Optional[float] = None,
) -> int:
    """Consume la cola de contratados y envía la orden real al broker.

    Args:
        bot: instancia de ConsolidationBot (client, edificio, trades).
        account_type: PRACTICE | REAL (default EDIFICIO_ACCOUNT_TYPE).
        amount: monto del contrato (default EDIFICIO_ORDER_AMOUNT).
        duration: vencimiento en segundos (default EDIFICIO_ORDER_DURATION_SEC).
        max_tries: reintentos máximos antes de descartar un evento.
        max_event_age_sec: ventana de validez del evento. Si esperó más que
            esto (p.ej. por un trade abierto), la señal ya no es fresca:
            NO se envía la orden obsoleta y el activo vuelve a P3.

    Returns:
        Cantidad de órdenes enviadas con éxito (confirmadas por el broker).
    """
    edificio = getattr(bot, "edificio", None)
    if edificio is None:
        return 0

    events = edificio.pop_contratados()
    if not events:
        return 0

    account_type = account_type or EDIFICIO_ACCOUNT_TYPE
    amount = max(float(amount or EDIFICIO_ORDER_AMOUNT), 0.01)
    duration = max(int(duration or EDIFICIO_ORDER_DURATION_SEC), 60)
    max_tries = int(max_tries if max_tries is not None else EDIFICIO_MAX_ORDER_TRIES)
    max_event_age_sec = float(
        max_event_age_sec if max_event_age_sec is not None else EDIFICIO_MAX_EVENT_AGE_SEC
    )

    # Máximo 1 trade concurrente: si hay operaciones abiertas, esperar al
    # próximo ciclo (el evento se conserva; caduca a los 10 min).
    trades_abiertos = getattr(bot, "trades", None)
    if trades_abiertos:
        for ev in events:
            edificio.requeue(ev)
        log.info("[EDIFICIO] %d contratado(s) re-encolados — hay trade(s) abiertos", len(events))
        return 0

    client = getattr(bot, "client", None)
    if client is None:
        for ev in events:
            edificio.requeue(ev)
        log.error("[EDIFICIO] %d contratado(s) re-encolados — bot sin client", len(events))
        return 0

    enviadas = 0
    now = time.time()
    for ev in events:
        # Gate de frescura: una señal que esperó demasiado ya no es válida.
        # Se descarta el evento (sin orden obsoleta) y el activo vuelve a P3.
        if now - ev.timestamp > max_event_age_sec:
            _expire_event(edificio, ev, age_sec=now - ev.timestamp)
            continue
        ok, result = await _send_one(
            bot, client, edificio, ev,
            account_type=account_type, amount=amount, duration=duration,
            max_tries=max_tries,
        )
        if ok:
            enviadas += 1
    return enviadas


def _expire_event(edificio: Any, ev: ContratadoEvent, *, age_sec: float) -> None:
    """Evento vencido: no se envía. El activo vuelve a P3 (sala de espera)
    con sus POIs intactos para re-contratar solo con una señal fresca."""
    card = ev.card if ev.card is not None else edificio.get_card(ev.asset)
    if card is not None:
        card.piso = PISO_3
        card.order_status = ""
        card.reason = f"Señal expirada ({age_sec:.0f}s esperando) — devuelto a P3"
    log.info(
        "[EDIFICIO] %s: señal expirada (%.0fs > ventana) — no se envía, vuelve a P3",
        ev.asset, age_sec,
    )


async def _send_one(
    bot: Any,
    client: Any,
    edificio: Any,
    ev: ContratadoEvent,
    *,
    account_type: str,
    amount: float,
    duration: int,
    max_tries: int,
) -> tuple[bool, dict]:
    """Envía una orden para un único evento contratado. Maneja reintentos.

    Returns:
        (ok, detalle) — ok True solo si el broker confirmó la orden.
    """
    card = ev.card if ev.card is not None else edificio.get_card(ev.asset)
    if card is None or card.piso != CONTRATADO:
        log.warning("[EDIFICIO] %s: card no está en CONTRATADO — evento descartado", ev.asset)
        return False, {"reason": "not_contratado"}

    direction = str(ev.direction or "").upper()
    if direction not in {"CALL", "PUT"}:
        log.warning("[EDIFICIO] %s: direction inválida (%r) — evento descartado", ev.asset, ev.direction)
        card.reason = f"CONTRATADO descartado: direction inválida ({ev.direction})"
        card.order_status = "failed"
        return False, {"reason": "bad_direction"}

    try:
        order_result = await place_order(
            client=client,
            asset=ev.asset,
            direction=direction,
            amount=amount,
            duration=duration,
            dry_run=False,
            account_type=account_type,
        )
    except Exception as exc:
        log.error("[EDIFICIO] %s: excepción en place_order: %s", ev.asset, exc)
        return _retry_or_drop(edificio, card, ev, max_tries, reason=f"order_exception:{exc}")

    ok = bool(order_result[0]) if order_result else False
    error = order_result[4] if len(order_result) > 4 else ""
    if ok:
        order_id = order_result[1] if len(order_result) > 1 else ""
        card.order_id = order_id
        card.order_status = "sent"
        card.reason = f"CONTRATADO — orden enviada ({direction}, id={order_id})"
        ev.order_id = order_id
        ev.order_status = "sent"
        log.info(
            "[EDIFICIO] %s: ORDEN ENVIADA %s $%.2f %ds → id=%s",
            ev.asset, direction, amount, duration, order_id,
        )
        return True, {"order_id": order_id}

    log.warning(
        "[EDIFICIO] %s: broker rechazó %s — %r",
        ev.asset, direction, error or "broker_rejected",
    )
    return _retry_or_drop(edificio, card, ev, max_tries, reason=error or "broker_rejected")


def _retry_or_drop(
    edificio: Any,
    card: Any,
    ev: ContratadoEvent,
    max_tries: int,
    *,
    reason: str,
) -> tuple[bool, dict]:
    """Re-encola el evento si quedan intentos; si no, lo descarta."""
    ev.tries += 1
    if ev.tries > max_tries:
        card.order_status = "failed"
        card.reason = f"CONTRATADO falló ({ev.tries} intentos) — {reason}"
        log.error(
            "[EDIFICIO] %s: descartado tras %d intentos — %s",
            ev.asset, ev.tries, reason,
        )
        return False, {"reason": f"dropped_after_{ev.tries}_tries", "detail": reason}
    edificio.requeue(ev)
    log.info("[EDIFICIO] %s: re-encolado (intento %d/%d) — %s", ev.asset, ev.tries, max_tries + 1, reason)
    return False, {"reason": "retry", "tries": ev.tries}
