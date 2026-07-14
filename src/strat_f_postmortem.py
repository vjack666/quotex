"""Post-mortem automático STRAT-F (Fase 4).

Dado el snapshot ANTES (velas 1m al entrar) y DESPUÉS (velas 1m post-expiry),
más el resultado real, deriva:
- loss_reason: por qué perdió (texto corto, para agrupar en stats).
- improvement_hint: sugerencia de calibración derivada de datos (no de fe).

Clave para la pregunta del usuario: en caso de pérdida, evalúa si en las velas
1m POST-expiry hubo un patrón de reversión en la dirección correcta — o sea,
si HABÍA OTRA MEJOR ENTRADA pocos minutos después. Eso alimenta la caja negra
y, vía stats.py, el bucle de calibración (y un reporte exportable a IA).

No importa de dónde vengan las velas: recibe listas de dicts
{"ts","o","h","l","c"} (formato en que las graba scanner.py) o Candle.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

# Reutiliza el detector de patrones del repo (misma lógica que el scan en vivo).
try:
    from candle_patterns import detect_reversal_pattern, CandleSignal
except Exception:  # pragma: no cover
    detect_reversal_pattern = None
    CandleSignal = None


def _to_candle(d: Dict[str, Any]):
    from models import Candle
    return Candle(
        ts=int(d.get("ts", 0)),
        open=float(d.get("o", d.get("open", 0))),
        high=float(d.get("h", d.get("high", 0))),
        low=float(d.get("l", d.get("low", 0))),
        close=float(d.get("c", d.get("close", 0))),
    )


def _as_candles(seq: Optional[Sequence[Any]]) -> List[Any]:
    if not seq:
        return []
    out = []
    for item in seq:
        if isinstance(item, dict):
            out.append(_to_candle(item))
        else:
            out.append(item)  # ya es Candle
    return out


def _best_reversal_in_window(candles, direction: str) -> Optional[CandleSignal]:
    """Busca el patrón de reversión más fuerte en la ventana post-cierre."""
    if detect_reversal_pattern is None or len(candles) < 3:
        return None
    best: Optional[CandleSignal] = None
    # Evalúa ventanas deslizantes: cada sub-secuencia de 3+ velas desde el inicio.
    for end in range(3, len(candles) + 1):
        sig = detect_reversal_pattern(candles[:end], direction)
        if sig and sig.confirms_direction and (best is None or sig.strength > best.strength):
            best = sig
    return best


def analyze_postmortem(
    before_candles_1m: Optional[Sequence[Any]],
    after_candles_1m: Optional[Sequence[Any]],
    direction: str,
    outcome: str,
    entry_price: Optional[float] = None,
    exit_price: Optional[float] = None,
) -> Tuple[str, str]:
    """Devuelve (loss_reason, improvement_hint).

    Para WIN/UNRESOLVED: loss_reason vacío, hint genérico.
    Para LOSS: cruza ANTES vs DESPUÉS para clasificar la pérdida.
    """
    if outcome != "LOSS":
        reason = "" if outcome == "WIN" else "unresolved"
        hint = "ok" if outcome == "WIN" else "sin datos de resultado"
        return reason, hint

    before = _as_candles(before_candles_1m)
    after = _as_candles(after_candles_1m)

    # 1) ¿Entró en la dirección equivocada? (precio fue al revés post-cierre)
    if entry_price is not None and exit_price is not None:
        moved = exit_price - entry_price
        if direction == "call" and moved < 0:
            # CALL pero el precio cayó => dirección mala O entró temprano
            pass
        elif direction == "put" and moved > 0:
            pass

    # 2) ¿Había OTRA MEJOR ENTRADA en las velas 1m post-expiry?
    #    Buscamos un patrón de reversión en la MISMA dirección que la entrada,
    #    pocos minutos después => "entró temprano, mejor entrada posterior".
    better_same = _best_reversal_in_window(after, direction) if after else None
    #    Y un patrón en la dirección OPUESTA => "dirección equivocada".
    opp = "put" if direction == "call" else "call"
    better_opp = _best_reversal_in_window(after, opp) if after else None

    if better_opp and (better_same is None or better_opp.strength >= better_same.strength):
        reason = "direccion_equivocada"
        hint = (
            f"en 1m post-cierre apareció reversión {better_opp.pattern_name} "
            f"(fuerza {better_opp.strength:.2f}) en dirección opuesta — "
            "revisar filtro de contexto M15 / confirmación por cuerpo"
        )
        return reason, hint

    if better_same:
        reason = "entro_temprano"
        hint = (
            f"en 1m post-cierre hubo mejor entrada {better_same.pattern_name} "
            f"(fuerza {better_same.strength:.2f}) en la MISMA dirección — "
            "esperar confirmación de cuerpo 1-2 velas más"
        )
        return reason, hint

    # 3) Sin patrón claro post-cierre => rango/ruido o slippage de timing.
    reason = "rango_sin_reversion"
    hint = (
        "post-cierre no mostró reversión clara en 1m — "
        "posible ruido de rango; considerar filtro de volatilidad (ATR) "
        "o evitar assets planos"
    )
    return reason, hint
