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

import asyncio
import logging
import time
from typing import Any, Optional

from config import (
    EDIFICIO_ACCOUNT_TYPE,
    EDIFICIO_MAX_EVENT_AGE_SEC,
    EDIFICIO_MAX_ORDER_TRIES,
    EDIFICIO_ORDER_AMOUNT,
    EDIFICIO_ORDER_DURATION_SEC,
    MARTIN_RESOLVE_MAX_ATTEMPTS,
    MARTIN_RESOLVE_RETRY_SEC,
    MARTIN_RESOLVE_TIMEOUT_SEC,
)
from connection import interpret_broker_result, place_order
from edificio_contratacion import CONTRATADO, PISO_3, ContratadoEvent
from black_box_recorder import get_black_box

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
        order_ref = int(order_result[3] or 0) if len(order_result) > 3 else 0
        card.order_id = order_id
        card.order_ref = order_ref
        card.order_status = "sent"
        card.reason = f"CONTRATADO — orden enviada ({direction}, id={order_id})"
        ev.order_id = order_id
        ev.order_ref = order_ref
        ev.order_status = "sent"
        log.info(
            "[EDIFICIO] %s: ORDEN ENVIADA %s $%.2f %ds → id=%s (ticket=%s)",
            ev.asset, direction, amount, duration, order_id, order_ref,
        )
        _record_sent_to_black_box(edificio, ev, card, direction, amount, duration)
        edificio.register_sent(order_id, {
            "asset": ev.asset,
            "direction": direction,
            "amount": float(amount),
            "payout": int(card.payout or 0),
            "order_ref": order_ref,
            "sent_at": time.time(),
            "duration_sec": int(duration),
            "resolved": False,
            "attempts": 0,
        })
        return True, {"order_id": order_id, "order_ref": order_ref}

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


# ── Trazabilidad: caja negra (F1) ────────────────────────────────────────
# Contador de scans EDIFICIO en la caja negra (por proceso).
_EDIFICIO_SCAN_SEQ = 0


def _record_sent_to_black_box(
    edificio: Any,
    ev: ContratadoEvent,
    card: Any,
    direction: str,
    amount: float,
    duration: int,
) -> None:
    """Registra el envío confirmado en la caja negra (strategy="EDIFICIO").

    La fila queda en scan_candidates con order_id → el resolvedor la actualiza
    con WIN/LOSS vía record_order_result(order_id, ...). Nunca debe romper el
    envío: todo error es solo un warning de log.
    """
    global _EDIFICIO_SCAN_SEQ
    if not ev.order_id:
        return
    try:
        _EDIFICIO_SCAN_SEQ += 1
        bb = get_black_box()
        scan_id = bb.record_scan_start("EDIFICIO", _EDIFICIO_SCAN_SEQ)
        # Contexto de auditoría desde la card (snapshot del momento de evaluación).
        _stoch_full = getattr(card, "stoch_m15_full", None) or {}
        if not isinstance(_stoch_full, dict) or "k" not in _stoch_full:
            _stoch_full = {"k": getattr(card, "stoch_k", None), "d": getattr(card, "stoch_d", None)}
        _candles_15m = [c for c in getattr(card, "candles_15m_snap", []) or []]
        _candles_5m = [c for c in getattr(card, "candles_5m_snap", []) or []]
        bb.record_candidate(scan_id, "EDIFICIO", {
            "asset": ev.asset,
            "direction": direction,
            "score": float(card.score or 0.0),
            "confidence": 0.0,
            "payout": int(card.payout or 0),
            "decision": "BUY",
            "decision_reason": "edificio_contratado",
            "order_id": ev.order_id,
            "duration_sec": int(duration),
            "agent_tag": "BOT",
            "stoch_m15": _stoch_full,
            "extreme_read": int(getattr(card, "extreme_read", 0) or 0),
            "candles_15m": _candles_15m,
            "candles_5m": _candles_5m,
            "strategy_details": {
                "amount": float(amount),
                "order_ref": ev.order_ref,
                "candle_15m_prev": getattr(card, "candle_15m_prev", None),
                "candle_5m_prev": getattr(card, "candle_5m_prev", None),
                "brake_ok": bool(getattr(card, "brake_ok", False)),
                "extreme_ok": bool(getattr(card, "extreme_ok", False)),
                "cross_ok": bool(getattr(card, "cross_ok", False)),
                "cross_sticky": bool(getattr(card, "cross_sticky", False)),
                "piso_previa": getattr(card, "piso", None),
            },
        })
        log.info("[EDIFICIO] %s: registrado en caja negra (scan=%d)", ev.asset, scan_id)
    except Exception as exc:
        log.warning("[EDIFICIO] %s: no se pudo registrar en caja negra (no bloquea): %s", ev.asset, exc)


# ── Trazabilidad: resolvedor por ticket (F2) ─────────────────────────────

async def resolve_contratados(
    bot: Any,
    *,
    max_attempts: Optional[int] = None,
) -> int:
    """Resuelve el resultado (WIN/LOSS) de las órdenes del edificio ya vencidas.

    Corre en el loop del BOT (socket único, regla de oro), llamado desde el
    scanner junto a execute_contratados. Consulta el resultado con el TICKET
    numérico (check_win) usando la misma mecánica que el pipeline STRAT-F:
    profit == 0 NO es LOSS (lag del broker) → se reintenta en el próximo ciclo.

    Decisión: se resuelve UNA orden vencida por llamada para no bloquear el
    loop (check_win bloquea hasta que el broker liquida); el resto se resuelve
    en el siguiente scan.

    Returns:
        Cantidad de órdenes resueltas en esta llamada.
    """
    edificio = getattr(bot, "edificio", None)
    client = getattr(bot, "client", None)
    if edificio is None or client is None:
        return 0

    max_attempts = int(max_attempts if max_attempts is not None else MARTIN_RESOLVE_MAX_ATTEMPTS)
    sent_orders = edificio.sent_pending()
    now = time.time()

    # Primera orden vencida sin resolver (una por llamada — ver docstring).
    target_id: Optional[str] = None
    target_info: Optional[dict] = None
    for order_id, info in sent_orders.items():
        if info.get("resolved"):
            continue
        if now < float(info.get("sent_at", 0) or 0) + int(info.get("duration_sec", 0) or 0) + 1:
            continue
        target_id, target_info = order_id, info
        break

    if target_id is None or target_info is None:
        return 0

    outcome, profit = await _resolve_one(bot, client, edificio, target_id, target_info, max_attempts)
    if outcome not in {"WIN", "LOSS"}:
        return 0

    # Actualizar card (si sigue en el edificio) para el hub.
    card = edificio.get_card(str(target_info.get("asset", "")))
    if card is not None:
        card.order_status = "won" if outcome == "WIN" else "lost"
        card.reason = f"Resultado: {outcome} ({profit:+.2f})"

    # Secuencia combinada cronológica (hub "Secuencia (W/L)").
    history = getattr(bot, "outcome_history", None)
    if history is not None:
        history.append("W" if outcome == "WIN" else "L")

    # Alimentar el panel "Balance" del hub: sus contadores W/L y win rate
    # salen de la sesión Massaniello (server._enrich_with_bot → session_status),
    # no de outcome_history. Sin esto el panel queda en "–" / "0 / 0" aunque
    # haya órdenes resueltas (desacople detectado 2026-07-31). Mejor esfuerzo:
    # nunca debe bloquear la resolución.
    try:
        mgr = getattr(bot, "massaniello", None)
        if mgr is not None and hasattr(mgr, "register_win") and hasattr(mgr, "register_loss"):
            amount = float(info.get("amount") or 0.0)
            payout_pct = int(info.get("payout") or 80)
            if outcome == "WIN":
                mgr.register_win(amount, payout_pct)
            else:
                mgr.register_loss(amount)
    except Exception as exc:
        log.warning("[EDIFICIO] no se pudo registrar %s en sesión Massaniello (no bloquea): %s", outcome, exc)

    log.info(
        "[EDIFICIO] %s: resultado %s %+.2f (ticket=%s)",
        target_info.get("asset"), outcome, profit, target_info.get("order_ref"),
    )
    return 1


async def _resolve_one(
    bot: Any,
    client: Any,
    edificio: Any,
    order_id: str,
    info: dict,
    max_attempts: int,
) -> tuple[Optional[str], float]:
    """Reintenta check_win por ticket hasta liquidar o agotar intentos.

    Returns:
        (outcome, profit) — outcome "UNRESOLVED" si se agotaron los intentos;
        (None, 0.0) si aún no hay que resolver (el caller reintenta otro ciclo).
    """
    order_ref = int(info.get("order_ref") or 0)
    amount = float(info.get("amount") or 0.0)
    payout_pct = int(info.get("payout") or 80)
    attempts = int(info.get("attempts") or 0)

    for attempt in range(1, max_attempts + 1):
        info["attempts"] = attempts + attempt
        interpreted = None
        try:
            if order_ref > 0:
                # check_win blocks until game_state==1; give it real time.
                win_val = await asyncio.wait_for(
                    client.check_win(order_ref),
                    timeout=MARTIN_RESOLVE_TIMEOUT_SEC,
                )
                interpreted = interpret_broker_result(
                    win_val,
                    trade_amount=amount,
                    payout_pct=payout_pct,
                )
                if interpreted is None:
                    log.info(
                        "⏳ [EDIFICIO] %s: aún no liquidado (check_win=%r) intento %d/%d",
                        info.get("asset"), win_val, attempt, max_attempts,
                    )
        except asyncio.TimeoutError:
            log.info(
                "⏳ [EDIFICIO] %s: timeout esperando liquidación intento %d/%d",
                info.get("asset"), attempt, max_attempts,
            )
        except Exception as exc:
            log.warning(
                "No se pudo obtener resultado de %s / ref=%s intento %d/%d: %s",
                order_id, order_ref, attempt, max_attempts, exc,
            )

        if interpreted is not None:
            outcome, profit = interpreted
            try:
                get_black_box().record_order_result(order_id, outcome, float(profit))
            except Exception as exc:
                log.warning("[EDIFICIO] %s: no se pudo actualizar caja negra (no bloquea): %s", order_id, exc)
            # Auditoría de cierre: cómo quedaron las velas 5m/15m cuando se
            # liquidó. Fetch NO bloqueante (mejor esfuerzo, nunca rompe la
            # resolución). Usa el socket único del bot.
            try:
                from candle_patterns import last_closed_shape
                from connection import fetch_candles
                from stochastic_m15 import compute_stoch

                _asset = str(info.get("asset", ""))
                _c15 = await fetch_candles(client, _asset, 900, 16, timeout_sec=10) if _asset else []
                _c5 = await fetch_candles(client, _asset, 300, 16, timeout_sec=10) if _asset else []
                _close_ctx = {
                    "candle_15m": last_closed_shape(_c15) if _c15 else None,
                    "candle_5m": last_closed_shape(_c5) if _c5 else None,
                    "stoch_m15_close": compute_stoch(_c15) if _c15 else None,
                    "exit_price": float(_c15[-1].close) if _c15 else None,
                }
                get_black_box().record_order_close_context(order_id, **_close_ctx)
            except Exception as exc:
                log.warning("[EDIFICIO] %s: no se pudo registrar cierre (no bloquea): %s", order_id, exc)
            info["resolved"] = True
            return outcome, float(profit)

        if attempt < max_attempts:
            await asyncio.sleep(MARTIN_RESOLVE_RETRY_SEC)

    log.warning(
        "⚠ [EDIFICIO] %s: quedó UNRESOLVED (no se forzó LOSS). Se reintentará en otro ciclo.",
        info.get("asset"),
    )
    info["resolved"] = True
    return "UNRESOLVED", 0.0
