"""Feature 29 — Market Geometry Context (Experience Engine).

Contexto geométrico PURO del mercado OTC para el día actual. Este módulo
NO decide compra/venta ni aplica reglas hardcoded (FVG/OB/3-toques/roles
fijos). Solo describe la geometría (swings, bias estructural crudo, zonas
S/R candidatas) usando ``smc_analysis`` sobre velas M15 OTC, filtrando
swings falsos típicos del OTC (cuerpos planos, toques insuficientes).

Las IAs del bot SOLO LEEN el dict resultante; nunca escriben memoria aquí.

Uso típico:
    ctx = GEOMETRY_CACHE.get("EURJPY_otc", candles_15m)
    role = level_role(ctx, price)
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Optional, Sequence

from models import Candle
from smc_analysis import Bias, detect_structure

# TTL = 1 barra M15 (900 s). Recalcular por barra, no por candidato.
GEOMETRY_TTL_SEC = 900
_CACHE_MAXSIZE = 32

# Filtros anti-swing-falso OTC (métricas relativas, no reglas de decisión).
_MIN_BODY_PCT = 0.0003          # cuerpo mínimo relativo al precio del swing
_TOUCH_TOL_PCT = 0.0006         # tolerancia para contar un "toque" a un nivel
_MIN_TOUCHES = 2                # un nivel válido debe tocarse al menos 2 veces


def _to_candle(c: Any) -> Candle:
    """Acepta Candle o dict {ts,o,h,l,c} (tests sintéticos)."""
    if isinstance(c, Candle):
        return c
    return Candle(
        ts=int(c["ts"]),
        open=float(c["o"]),
        high=float(c["h"]),
        low=float(c["l"]),
        close=float(c["c"]),
    )


def _normalize(candles: Sequence[Any]) -> List[Candle]:
    return [_to_candle(c) for c in candles]


def _count_touches(candles: Sequence[Candle], price: float, is_high: bool) -> int:
    """Cuántas velas rozan ``price`` dentro de tolerancia relativa."""
    if price == 0:
        return 0
    tol = abs(price) * _TOUCH_TOL_PCT
    touches = 0
    for c in candles:
        extreme = c.high if is_high else c.low
        if abs(extreme - price) <= tol:
            touches += 1
    return touches


def compute_daily_geometry(candles_15m: Sequence[Any], asset: str) -> Dict[str, Any]:
    """Geometría cruda del día a partir de ~96 velas M15 OTC.

    Devuelve un dict libre con swings filtrados, bias estructural crudo y
    zonas S/R candidatas. NO etiqueta compra/venta.
    """
    candles = _normalize(candles_15m)

    result = detect_structure(candles)

    swing_highs: List[Dict[str, Any]] = []
    swing_lows: List[Dict[str, Any]] = []

    for sw in result.swings:
        candle = candles[sw.index]
        price = sw.price
        if price == 0:
            continue
        # Filtro 1: cuerpo mínimo relativo (descarta velas planas OTC).
        body_pct = candle.body / abs(price)
        if body_pct < _MIN_BODY_PCT:
            continue
        # Filtro 2: al menos N toques al nivel a lo largo del día.
        touches = _count_touches(candles, price, sw.is_high)
        if touches < _MIN_TOUCHES:
            continue

        entry = {
            "index": sw.index,
            "ts": sw.ts,
            "price": price,
            "touches": touches,
            "body_pct": body_pct,
        }
        if sw.is_high:
            swing_highs.append(entry)
        else:
            swing_lows.append(entry)

    # Zonas S/R candidatas = niveles de swings filtrados (solo métricas).
    sr_levels = [
        {"price": s["price"], "kind": "resistance", "touches": s["touches"]}
        for s in swing_highs
    ] + [
        {"price": s["price"], "kind": "support", "touches": s["touches"]}
        for s in swing_lows
    ]

    last_ts = candles[-1].ts if candles else 0

    return {
        "asset": asset,
        "bias": result.bias.value if isinstance(result.bias, Bias) else str(result.bias),
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
        "sr_levels": sr_levels,
        "n_candles": len(candles),
        "last_ts": last_ts,
    }


def level_role(ctx: Dict[str, Any], price: float) -> Dict[str, Any]:
    """Métricas de ``price`` respecto a los swings más cercanos.

    Solo métricas geométricas; no decide dirección.
    """
    highs = ctx.get("swing_highs", [])
    lows = ctx.get("swing_lows", [])
    all_swings = [(s, True) for s in highs] + [(s, False) for s in lows]

    result: Dict[str, Any] = {
        "nearest_swing": None,
        "distance_pct": None,
        "is_support": False,
        "is_resistance": False,
        "touches": 0,
    }
    if not all_swings or price == 0:
        return result

    nearest, is_high = min(
        all_swings, key=lambda item: abs(item[0]["price"] - price)
    )
    swing_price = nearest["price"]
    distance_pct = abs(swing_price - price) / abs(price)
    near = distance_pct <= _TOUCH_TOL_PCT

    result.update({
        "nearest_swing": nearest,
        "distance_pct": distance_pct,
        "is_support": bool(near and not is_high),
        "is_resistance": bool(near and is_high),
        "touches": nearest.get("touches", 0),
    })
    return result


class GeometryCache:
    """LRU por asset con TTL. Recalcula solo si miss o vela más reciente cambió.

    Evita recalcular por cada candidato dentro de la misma barra M15.
    ``time_fn`` inyectable para tests deterministas.
    """

    def __init__(self, ttl_sec: int = GEOMETRY_TTL_SEC, maxsize: int = _CACHE_MAXSIZE,
                 time_fn=None):
        self._ttl = ttl_sec
        self._maxsize = maxsize
        self._store: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        if time_fn is None:
            import time
            time_fn = time.monotonic
        self._time_fn = time_fn

    def get(self, asset: str, candles_15m: Sequence[Any]) -> Dict[str, Any]:
        candles = _normalize(candles_15m)
        last_ts = candles[-1].ts if candles else 0
        now = self._time_fn()

        cached = self._store.get(asset)
        if cached is not None:
            fresh = (now - cached["_cached_at"]) < self._ttl
            same_bar = cached["ctx"].get("last_ts") == last_ts
            if fresh and same_bar:
                self._store.move_to_end(asset)
                return cached["ctx"]

        ctx = compute_daily_geometry(candles, asset)
        self._store[asset] = {"ctx": ctx, "_cached_at": now}
        self._store.move_to_end(asset)
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)
        return ctx

    def clear(self) -> None:
        self._store.clear()


# Instancia compartida por el bot.
GEOMETRY_CACHE = GeometryCache()
