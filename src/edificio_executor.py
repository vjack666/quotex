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
import csv
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from config import (
    EDIFICIO_ACCOUNT_TYPE,
    EDIFICIO_MAX_EVENT_AGE_SEC,
    EDIFICIO_MAX_ORDER_TRIES,
    EDIFICIO_ORDER_AMOUNT,
    EDIFICIO_ORDER_DURATION_SEC,
    EDIFICIO_RULE_VERSION,
    EDIFICIO_SEND_ORDERS_ENABLED,
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
        if not EDIFICIO_SEND_ORDERS_ENABLED:
            edificio.requeue(ev)
            continue
        # Gate de frescura: una señal que esperó demasiado ya no es válida.
        # Se descarta el evento (sin orden obsoleta) y el activo vuelve a P3.
        if now - ev.timestamp > max_event_age_sec:
            _expire_event(edificio, ev, age_sec=now - ev.timestamp)
            continue
        card = ev.card if ev.card is not None else edificio.get_card(ev.asset)
        if card is not None and getattr(card, "entry_pending", False):
            pending_since = getattr(card, "pending_since", None)
            if pending_since is not None and pending_since + duration / 3 > now:
                log.info(
                    "[EDIFICIO] %s: delay ejecución activo (%.0fs restantes) — re-encolado",
                    ev.asset,
                    pending_since + duration / 3 - now,
                )
                edificio.requeue(ev)
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
        card.entry_pending = False
        card.pending_since = None
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
            "brake_ts": getattr(card, "brake_witness_ts", None),
            "piso_previa": getattr(card, "piso", None),
            "brake_confirmed_at": getattr(card, "brake_confirmed_at", None),
            "p3_at": getattr(card, "p3_at", None),
            "contract_at": getattr(card, "contratado_at", None),
            "cross_separation_since": getattr(card, "cross_separation_since", None),
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


def _candles_to_dicts(candles: Any) -> List[dict]:
    """Serializa velas (objetos Candle o dicts) a dicts JSON serializables."""
    out: List[dict] = []
    for c in candles or []:
        if isinstance(c, dict):
            out.append(c)
        else:
            out.append(
                {
                    "ts": getattr(c, "ts", None),
                    "open": getattr(c, "open", None),
                    "high": getattr(c, "high", None),
                    "low": getattr(c, "low", None),
                    "close": getattr(c, "close", None),
                    "ticks": getattr(c, "ticks", 0),
                }
            )
    return out


def _record_sent_to_black_box(
    edificio: Any,
    ev: ContratadoEvent,
    card: Any,
    direction: str,
    amount: float,
    duration: int,
) -> None:
    """Registra el envío confirmado en la caja negra (strategy="EDIFICIO")."""
    global _EDIFICIO_SCAN_SEQ
    if not ev.order_id:
        return
    try:
        _EDIFICIO_SCAN_SEQ += 1
        bb = get_black_box()
        scan_id = bb.record_scan_start("EDIFICIO", _EDIFICIO_SCAN_SEQ)
        _stoch_full = getattr(card, "stoch_m15_full", None) or {}
        if not isinstance(_stoch_full, dict) or "k" not in _stoch_full:
            _stoch_full = {"k": getattr(card, "stoch_k", None), "d": getattr(card, "stoch_d", None)}
        # |K-D| al momento de la evaluación (caja negra / análisis de separación).
        _k = _stoch_full.get("k") if isinstance(_stoch_full, dict) else None
        _d = _stoch_full.get("d") if isinstance(_stoch_full, dict) else None
        if _k is None:
            _k = getattr(card, "stoch_k", None)
        if _d is None:
            _d = getattr(card, "stoch_d", None)
        _kd_distance = None
        try:
            if _k is not None and _d is not None:
                _kd_distance = abs(float(_k) - float(_d))
        except (TypeError, ValueError):
            _kd_distance = None
        # Cruce limpio (no sticky): la puerta que el edificio exige para contratar.
        _cross_limpieza_ok = bool(getattr(card, "cross_ok", False) and not getattr(card, "cross_sticky", False))
        _pattern_5m = getattr(card, "pattern_5m", None)
        _candles_15m = _candles_to_dicts(getattr(card, "candles_15m_snap", []) or [])
        _candles_5m = _candles_to_dicts(getattr(card, "candles_5m_snap", []) or [])
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
            "kd_distance": _kd_distance,
            "cross_limpieza_ok": int(_cross_limpieza_ok),
            "pattern_5m": _pattern_5m,
            "brake_verdict": getattr(card, "brake_verdict", None),
            "brake_ratio": getattr(card, "brake_ratio", None),
            "brake_ref_range": getattr(card, "brake_reference_range", None),
            "brake_witness_ts": getattr(card, "brake_witness_ts", None),
            "brake_rule_version": EDIFICIO_RULE_VERSION,
            "direction_source": getattr(card, "direction_source", None),
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
                "kd_distance": float(getattr(card, "kd_distance", 0) or 0) if getattr(card, "kd_distance", None) is not None else None,
                "cross_limpieza_ok": bool(getattr(card, "cross_ok", False) and not getattr(card, "cross_sticky", False)),
                "stoch_m15": getattr(card, "stoch_m15_full", None)
                or {"k": getattr(card, "stoch_k", None), "d": getattr(card, "stoch_d", None)},
                "stoch_m5": getattr(card, "stoch_m5_full", None) or {},
                "body_5m": getattr(card, "body_5m", None),
                "piso_previa": getattr(card, "piso", None),
                "rule_version": EDIFICIO_RULE_VERSION,
                "filters_applied": [
                    "payout>=80",
                    "brake+extreme",
                    "cross+separacion_K/D",
                    "body_5m>0.03|martillo_M5",
                ],
                "post_brake_body_ratio": float(getattr(card, "post_brake_body_ratio", 0) or 0) if getattr(card, "post_brake_body_ratio", None) is not None else None,
                "post_brake_would_pass": bool(getattr(card, "post_brake_would_pass", False)) if getattr(card, "post_brake_would_pass", None) is not None else None,
                "post_brake_measured_at": float(getattr(card, "post_brake_measured_at", 0) or 0) if getattr(card, "post_brake_measured_at", None) is not None else None,
            },
        })
        log.info("[EDIFICIO] %s: registrado en caja negra (scan=%d)", ev.asset, scan_id)
    except Exception as exc:
        log.warning("[EDIFICIO] %s: no se pudo registrar en caja negra (no bloquea): %s", ev.asset, exc)


def _record_failed_send_to_black_box(
    edificio: Any,
    ev: ContratadoEvent,
    card: Any,
    direction: str,
    amount: float,
    duration: int,
    broker_error: str = "",
) -> None:
    """Registra un envío fallido/descartado en caja negra para trazabilidad."""
    global _EDIFICIO_SCAN_SEQ
    if not ev.order_id:
        return
    try:
        _EDIFICIO_SCAN_SEQ += 1
        bb = get_black_box()
        scan_id = bb.record_scan_start("EDIFICIO", _EDIFICIO_SCAN_SEQ)
        bb.record_candidate(scan_id, "EDIFICIO", {
            "asset": ev.asset,
            "direction": direction,
            "score": float(card.score or 0.0),
            "confidence": 0.0,
            "payout": int(card.payout or 0),
            "decision": "NO_SEND",
            "decision_reason": "edificio_failed_send",
            "order_id": ev.order_id,
            "duration_sec": int(duration),
            "agent_tag": "BOT",
            "reject_reason": broker_error or "BROKER_REJECTED",
            "strategy_details": {
                "amount": float(amount),
                "order_ref": ev.order_ref,
                "candle_15m_prev": getattr(card, "candle_15m_prev", None),
                "candle_5m_prev": getattr(card, "candle_5m_prev", None),
                "brake_ok": bool(getattr(card, "brake_ok", False)),
                "extreme_ok": bool(getattr(card, "extreme_ok", False)),
                "cross_ok": bool(getattr(card, "cross_ok", False)),
                "cross_sticky": bool(getattr(card, "cross_sticky", False)),
                "kd_distance": float(getattr(card, "kd_distance", 0) or 0) if getattr(card, "kd_distance", None) is not None else None,
                "cross_limpieza_ok": bool(getattr(card, "cross_ok", False) and not getattr(card, "cross_sticky", False)),
                "stoch_m15": getattr(card, "stoch_m15_full", None)
                or {"k": getattr(card, "stoch_k", None), "d": getattr(card, "stoch_d", None)},
                "stoch_m5": getattr(card, "stoch_m5_full", None) or {},
                "body_5m": getattr(card, "body_5m", None),
                "piso_previa": getattr(card, "piso", None),
                "rule_version": EDIFICIO_RULE_VERSION,
                "filters_applied": [
                    "payout>=80",
                    "brake+extreme",
                    "cross+separacion_K/D",
                    "body_5m>0.03|martillo_M5",
                ],
                "send_error": broker_error,
                "post_brake_body_ratio": float(getattr(card, "post_brake_body_ratio", 0) or 0) if getattr(card, "post_brake_body_ratio", None) is not None else None,
                "post_brake_would_pass": bool(getattr(card, "post_brake_would_pass", False)) if getattr(card, "post_brake_would_pass", None) is not None else None,
                "post_brake_measured_at": float(getattr(card, "post_brake_measured_at", 0) or 0) if getattr(card, "post_brake_measured_at", None) is not None else None,
            },
        })
    except Exception as exc:
        log.warning("[EDIFICIO] %s: no se pudo registrar envio fallido en caja negra (no bloquea): %s", ev.asset, exc)


# ── Trazabilidad: resolvedor por ticket (F2) ─────────────────────────────

def _infer_loss_reason(edificio: Any, info: dict) -> str:
    """Infiere la razon de perdida desde la card del edificio."""
    asset = str(info.get("asset", ""))
    card = edificio.get_card(asset) if asset else None
    if card is None:
        return "UNRESOLVED"
    if float(getattr(card, "payout", 0) or 0) <= 0:
        return "NO_PAYOUT"
    if not getattr(card, "brake_ok", False):
        return "NO_BRAKE"
    if not getattr(card, "extreme_ok", False):
        return "NO_EXTREME"
    if not getattr(card, "cross_ok", False):
        return "NO_CROSS"
    if getattr(card, "cross_sticky", False):
        return "STICKY_CROSS"
    body_5m = getattr(card, "body_5m", None)
    if isinstance(body_5m, (int, float)) and float(body_5m) <= 0.03:
        return "BODY_FILTER"
    return "UNRESOLVED"


def _update_order_loss_reason(order_id: str, loss_reason: str) -> None:
    """Marca la fila de caja negra con la razon de perdida y trazabilidad."""
    ts = datetime.now(timezone.utc).isoformat()
    bb = get_black_box()
    try:
        con = sqlite3.connect(bb.db_path)
        cur = con.cursor()
        cur.execute(
            "UPDATE scan_candidates SET loss_reason = ?, agent_tag = ?, updated_at = ? "
            "WHERE order_id = ?",
            (loss_reason, "AGENT_LOSS_REASON", ts, order_id),
        )
        con.commit()
    except Exception as exc:
        log.warning("[EDIFICIO] %s: no se pudo marcar loss_reason=%s: %s", order_id, loss_reason, exc)
    finally:
        try:
            con.close()
        except Exception:
            pass


_AUDIT_CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "exports" / "edificio_order_audit.csv"
_AUDIT_CSV_HEADER = [
    "sent_at","asset","direction","amount","duration_sec","order_id","order_ref",
    "resolved_at","outcome","profit","delta_sec","loss_reason",
    "brake_ts","brake_confirmed_at","p3_at","contract_at","piso_previa"
]


def _append_order_audit(edificio: Any, info: dict, outcome: str, profit: float) -> None:
    """Append a row to the Edificio order audit CSV (best effort)."""
    sent_at = info.get("sent_at")
    resolved_at = time.time()
    delta_sec = None
    try:
        if sent_at is not None:
            delta_sec = round(float(resolved_at) - float(sent_at), 3)
    except Exception:
        delta_sec = None
    loss_reason = ""
    try:
        if outcome == "LOSS":
            loss_reason = _infer_loss_reason(edificio, info)
    except Exception:
        loss_reason = ""
    row = [
        sent_at,
        info.get("asset"),
        info.get("direction"),
        info.get("amount"),
        info.get("duration_sec"),
        info.get("order_id"),
        info.get("order_ref"),
        resolved_at,
        outcome,
        profit,
        delta_sec,
        loss_reason,
        info.get("brake_ts"),
        info.get("brake_confirmed_at"),
        info.get("p3_at"),
        info.get("contract_at"),
        info.get("piso_previa"),
        info.get("cross_separation_since"),
    ]
    try:
        _AUDIT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_header = not _AUDIT_CSV_PATH.exists() or _AUDIT_CSV_PATH.stat().st_size == 0
        with _AUDIT_CSV_PATH.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(_AUDIT_CSV_HEADER)
            w.writerow(row)
    except Exception:
        pass


async def _record_close_context(
    client: Any,
    order_id: str,
    info: dict,
) -> None:
    """Best-effort close-context capture moved off the resolver path."""
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
        log.warning(
            "[EDIFICIO] %s: no se pudo registrar cierre background (no bloquea): %s",
            order_id,
            exc,
        )


async def resolve_contratados(
    bot: Any,
    *,
    max_attempts: Optional[int] = None,
) -> int:
    """Resuelve el resultado (WIN/LOSS) de las órdenes del edificio ya vencidas.

    Corre en el loop del BOT (socket único, regla de oro), llamado desde el
    scanner junto a execute_contratados. Consulta el resultado con TICKET y/o
    ID usando la misma mecánica que STRAT-F:
    - profit == 0 NO es LOSS (lag del broker)
    - 1 intento por llamada: si no liquida, queda pendiente para el próximo scan

    Returns:
        Cantidad de órdenes resueltas en esta llamada.
    """
    edificio = getattr(bot, "edificio", None)
    client = getattr(bot, "client", None)
    if edificio is None or client is None:
        return 0

    sent_orders = edificio.sent_pending()
    now = time.time()

    # Primera orden vencida sin resolver (una por llamada).
    target_id: Optional[str] = None
    target_info: Optional[dict] = None
    for order_id, info in sent_orders.items():
        if info.get("resolved"):
            continue
        if now < float(info.get("sent_at", 0) or 0) + int(info.get("duration_sec", 0) or 0) + 1:
            continue
        target_id, target_info = order_id, info
        break

    log.info(
        "[EDIFICIO][resolve_contratados] pending=%d now=%.3f target=%s",
        sum(1 for i in sent_orders.values() if not i.get("resolved")),
        now,
        target_id or "-",
    )
    if target_id is None or target_info is None:
        return 0

    # Siempre 1 intento por llamada para no bloquear el loop.
    outcome, profit = await _resolve_one(bot, client, edificio, target_id, target_info, max_attempts=1)
    if outcome not in {"WIN", "LOSS"}:
        return 0

    # Actualizar card (si sigue en el edificio) para el hub.
    card = edificio.get_card(str(target_info.get("asset", "")))
    if card is not None:
        card.order_status = "won" if outcome == "WIN" else "lost"
        card.reason = f"Resultado: {outcome} ({profit:+.2f})"

    # Poblar loss_reason para LOSS (diagnóstico)
    if outcome == "LOSS":
        loss_reason = _infer_loss_reason(edificio, target_info)
        _update_order_loss_reason(target_id, loss_reason)
        log.info("[EDIFICIO] %s: loss_reason=%s", target_info.get("asset"), loss_reason)

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

    # CSV auditoría órdenes (no bloquea; fallback silencioso si falla)
    try:
        _append_order_audit(edificio, target_info, outcome, profit)
    except Exception:
        pass

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
    """Reintenta consultar el resultado por ticket y/o id hasta liquidar.

    Sigue la mecánica anterior de STRAT-F:
    - Path A: check_win(order_ref) cuando hay ticket numérico.
    - Path B: get_result(order_id) como fallback cuando el ticket no alcanza.
    - profit == 0 nunca es LOSS (lag del broker); se reintenta.

    Returns:
        (outcome, profit) — outcome "UNRESOLVED" si se agotaron los intentos;
        (None, 0.0) si aún no hay que resolver (el caller reintenta otro ciclo).
    """
    order_ref = int(info.get("order_ref") or 0)
    amount = float(info.get("amount") or 0.0)
    payout_pct = int(info.get("payout") or 80)
    attempts = int(info.get("attempts") or 0)
    has_ref = order_ref > 0
    has_id = bool(order_id)

    for attempt in range(1, max_attempts + 1):
        info["attempts"] = attempts + attempt
        interpreted = None
        try:
            if has_ref:
                # Path A: check_win blocks until game_state==1; give it real time.
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
                        info.get("asset"),
                        win_val,
                        attempt,
                        max_attempts,
                    )
            elif has_id:
                # Path B: consulta por id cuando no hay ticket usable.
                status, payload = await asyncio.wait_for(
                    client.get_result(order_id),
                    timeout=MARTIN_RESOLVE_TIMEOUT_SEC,
                )
                interpreted = interpret_broker_result(
                    status=status,
                    payload=payload,
                    trade_amount=amount,
                    payout_pct=payout_pct,
                )
                if interpreted is None:
                    log.info(
                        "⏳ [EDIFICIO] %s: ticket sin PnL final (status=%r profit=%s) intento %d/%d",
                        info.get("asset"),
                        status,
                        (payload or {}).get("profitAmount") if isinstance(payload, dict) else None,
                        attempt,
                        max_attempts,
                    )
        except asyncio.TimeoutError:
            log.info(
                "⏳ [EDIFICIO] %s: timeout esperando liquidación intento %d/%d",
                info.get("asset"),
                attempt,
                max_attempts,
            )
        except Exception as exc:
            log.warning(
                "No se pudo obtener resultado de %s / ref=%s intento %d/%d: %s",
                order_id,
                order_ref,
                attempt,
                max_attempts,
                exc,
            )

        if interpreted is not None:
            outcome, profit = interpreted
            try:
                get_black_box().record_order_result(order_id, outcome, float(profit))
            except Exception as exc:
                log.warning(
                    "[EDIFICIO] %s: no se pudo actualizar caja negra (no bloquea): %s",
                    order_id,
                    exc,
                )
            try:
                asyncio.get_running_loop().create_task(
                    _record_close_context(client, order_id, info)
                )
            except Exception as exc:
                log.warning(
                    "[EDIFICIO] %s: no se pudo lanzar registro de cierre (no bloquea): %s",
                    order_id,
                    exc,
                )
            info["resolved"] = True
            return outcome, float(profit)

        if attempt < max_attempts:
            await asyncio.sleep(MARTIN_RESOLVE_RETRY_SEC)

    log.warning(
        "⚠ [EDIFICIO] %s: quedó UNRESOLVED (no se forzó LOSS). Se reintentará en otro ciclo.",
        info.get("asset"),
    )
    # NO marcar resolved=True: la orden sigue pendiente para reintentar en el
    # próximo scan, igual que STRAT-F con pending reconciliation.
    return "UNRESOLVED", 0.0
