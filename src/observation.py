"""Observación en vivo del Experience Engine (Feature 27).

Construye el ARCO de experiencia (contexto_previo -> evento -> evolucion ->
resultado -> consecuencias) desde objetos EN MEMORIA del bot, igual que
scripts/seed_experience_memory.py pero sin SQLite.

REGLA DURA: este módulo es un CAPTURADOR. No etiqueta soporte/resistencia/FVG,
no llama a ninguna IA y el único write-path a la memoria es ExperienceMemory.record()
(desde el hook en black_box_recorder). Aquí solo se construye el arco.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from experience_schema import MarketExperience


def _json(x: Any) -> Optional[Any]:
    if x is None:
        return None
    if isinstance(x, (dict, list)):
        return x
    try:
        return json.loads(x)
    except Exception:
        return None


def _stoch_level(stoch: Optional[dict]) -> Dict[str, Any]:
    if not stoch:
        return {}
    return {
        "zone": stoch.get("estado"),
        "k": stoch.get("k"),
        "d": stoch.get("d"),
        "cruce": stoch.get("cruce"),
        "divergencia": stoch.get("divergencia"),
    }


def _hour_dow(ts: float) -> Dict[str, int]:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return {"hour_utc": dt.hour, "dow": dt.weekday()}


def _pips(entry: Optional[float], exit_: Optional[float], direction: str) -> Optional[float]:
    if not entry or not exit_:
        return None
    raw = (exit_ - entry) * (1.0 if direction == "CALL" else -1.0)
    return round(raw * 10000.0, 1)


def _candles_to_dicts(candles: Any) -> List[dict]:
    """Serializa velas (objetos Candle o dicts) a lista de dicts crudos."""
    out: List[dict] = []
    for c in candles or []:
        if isinstance(c, dict):
            out.append(c)
        else:
            out.append({
                "ts": getattr(c, "ts", None),
                "o": getattr(c, "open", None),
                "h": getattr(c, "high", None),
                "l": getattr(c, "low", None),
                "c": getattr(c, "close", None),
            })
    return out


def build_entry_experience(
    candidate: Any = None,
    strategy_details: Optional[dict] = None,
    stoch_m15: Optional[dict] = None,
    candles_15m: Any = None,
    order_result: Optional[str] = None,
    profit: Optional[float] = None,
    entry_price: Optional[float] = None,
    exit_price: Optional[float] = None,
    loss_reason: Optional[str] = None,
    improvement_hint: Optional[str] = None,
    *,
    asset: Optional[str] = None,
    direction: Optional[str] = None,
    ts: Optional[float] = None,
    payout: Optional[Any] = None,
    duration_sec: Optional[int] = None,
    decision_scan: Optional[str] = None,
    stoch_m5: Optional[dict] = None,
    stoch_m1: Optional[dict] = None,
    score: Optional[float] = None,
) -> Optional[MarketExperience]:
    """Construye el arco de experiencia de UNA entrada del bot.

    Tolerante a None en todo. Devuelve None si faltan datos mínimos
    (dirección o asset). El capturador NO juzga: guarda TAL CUAL.
    """
    try:
        # Datos base desde el candidato (si viene) con fallback a kwargs
        asset = asset or getattr(candidate, "asset", None)
        direction = (direction or getattr(candidate, "direction", "") or "").upper()
        if not asset or direction not in ("CALL", "PUT"):
            return None
        ts = float(ts or time.time())

        sd = _json(strategy_details) or {}
        s15 = _json(stoch_m15) or {}
        candles15 = _candles_to_dicts(
            candles_15m if candles_15m is not None else getattr(candidate, "candles_15m", None)
        )
        if score is None:
            score = getattr(candidate, "score", None)
        if payout is None:
            payout = getattr(candidate, "payout", None)

        # ── contexto_previo (TAL CUAL, sin etiquetar soporte/resistencia) ──
        ctx = {
            "stoch_m15": _stoch_level(s15),
            "stoch_m5": _stoch_level(_json(stoch_m5) or {}),
            "stoch_m1": _stoch_level(_json(stoch_m1) or {}),
            "structure_ctx": sd.get("ctx"),
            "event_pattern": sd.get("event"),
            "pattern": sd.get("pattern"),
            "score_static": score,
            **_hour_dow(ts),
        }

        # ── evento ──
        last = candles15[-1] if candles15 else None
        level = entry_price or (last.get("c") if last else None)
        evento = {
            "tipo": "entrada",
            "direccion": direction,
            "nivel": level,
            "payout": payout,
            "duration_sec": duration_sec,
            "decision_scan": decision_scan,
        }

        # ── evolucion + resultado (desde el outcome resuelto) ──
        result = (order_result or "").upper()
        pips = _pips(entry_price, exit_price, direction)
        evolucion = {
            "pips_recorridos": pips,
            "tiempo_a_invalidacion_s": duration_sec,
            "loss_reason": loss_reason,
        }
        resultado = {
            "decision": result if result in ("WIN", "LOSS") else None,
            "pips_netos": pips,
            "profit": profit,
        }
        consecuencias = {
            "improvement_hint": improvement_hint,
            "loss_reason": loss_reason,
        }

        return MarketExperience(
            ts=int(ts),
            asset=str(asset),
            tf="M15",
            contexto_previo=ctx,
            evento=evento,
            evolucion=evolucion,
            resultado=resultado,
            consecuencias=consecuencias,
            raw={"candles_15m": candles15},
        )
    except Exception:
        return None


def build_experience_from_candidate_row(row: Dict[str, Any]) -> Optional[MarketExperience]:
    """Construye el arco desde una fila (dict) de scan_candidates ya resuelta.

    Es el puente para el hook post-trade de black_box_recorder (T7): al llegar
    order_result WIN/LOSS ya tenemos toda la fila persistida.
    """
    try:
        return build_entry_experience(
            candidate=None,
            strategy_details=_json(row.get("strategy_details")),
            stoch_m15=_json(row.get("stoch_m15")),
            candles_15m=_json(row.get("candles_15m")),
            order_result=row.get("order_result"),
            profit=row.get("profit"),
            entry_price=row.get("entry_price"),
            exit_price=row.get("exit_price"),
            loss_reason=row.get("loss_reason"),
            improvement_hint=row.get("improvement_hint"),
            asset=row.get("asset"),
            direction=row.get("direction"),
            ts=row.get("ts"),
            payout=row.get("payout"),
            duration_sec=row.get("duration_sec"),
            decision_scan=row.get("decision"),
            stoch_m5=_json(row.get("stoch_m5")),
            stoch_m1=_json(row.get("stoch_m1")),
            score=row.get("score"),
        )
    except Exception:
        return None
