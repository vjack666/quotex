"""Envío simple y robusto de órdenes OTC a QUOTEX.

Extrae la lógica que ya comprobamos funcionando en cuenta demo
(compra_venta_m5_otc.py): conectar -> client.buy() de ALTO nivel con
time_mode="TIMER" para OTC -> devolver (status, info).

Es la ÚNICA fuente de verdad para enviar una orden. Tanto el script suelto
de prueba como el executor del bot la usan, para no duplicar el buy().

Fix F6: pyquotex.buy() de alto nivel ya devuelve (status, info) con el id en
info["id"]; NO usar client.api.buy() + wait manual de buy_id (el broker
rechaza con broker_rejected). Para OTC forzamos time_mode="TIMER" porque el
broker exige optionType=100 (binary) con duración en segundos.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Tuple

log = logging.getLogger("otc_trader")

_ORDER_TIMEOUT_SEC = 60.0  # mi script funcionaba en <2s; 60s es holgura real.


async def enviar_orden(
    client: Any,
    asset: str,
    direction: str,  # "call" | "put"
    amount: float,
    duration: int,  # segundos (300 = 5 min)
) -> Tuple[bool, dict]:
    """Envía UNA orden OTC y devuelve (ok, info).

    `direction` debe ser "call" (compra) o "put" (venta) en minúsculas,
    igual que espera pyquotex.
    """
    time_mode = "TIMER" if asset.endswith("_otc") else "TIME"
    # Fix: strat_fractal genera "CALL"/"PUT" (mayus) pero pyquotex espera
    # "call"/"put" (minus). Normalizar para que el broker no rechace silencioso.
    direction = direction.lower()
    try:
        status, info = await asyncio.wait_for(
            client.buy(amount, asset, direction, duration, time_mode=time_mode),
            timeout=_ORDER_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        log.error("  ⚠ enviar_orden TIMEOUT (%ss) en %s %s",
                  _ORDER_TIMEOUT_SEC, direction.upper(), asset)
        return False, {"message": f"buy_timeout_{int(_ORDER_TIMEOUT_SEC)}s"}
    except Exception as exc:  # noqa: BLE001
        log.error("  ⚠ enviar_orden EXC en %s %s: %s",
                  direction.upper(), asset, exc)
        return False, {"message": f"buy_exception:{exc}"}

    if not status:
        reject = info.get("message") or info.get("reason") or info.get("error") or "broker_rejected"
        log.warning("  ⚠ %s %s rechazada: %s", direction.upper(), asset, reject)
        return False, info if isinstance(info, dict) else {"message": str(info)}
    return True, info if isinstance(info, dict) else {}
