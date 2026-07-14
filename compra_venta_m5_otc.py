"""TEST DE FUNCIONAMIENTO: lanza CALL + PUT a 5 min (300s) al mismo tiempo en un
activo OTC de QUOTEX PRACTICE, para verificar que la conexion responde.

NO es estrategia: no mira velas ni indicadores. Solo confirma que
client.buy() acepta una operacion CALL y otra PUT de forma concurrente.

Uso:
    python compra_venta_m5_otc.py            # elige un OTC abierto del allowlist
    python compra_venta_m5_otc.py EURUSD_otc # fuerza un activo

Cuenta: PRACTICE (demo). Nunca toca cuenta real.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from dotenv import load_dotenv

load_dotenv()

from pyquotex.stable_api import Quotex
from connection import get_open_assets
from otc_trader import enviar_orden

# OTC conocidos que QUOTEX acepta aislados (de probe_allowlist.py).
ALLOWLIST_OTC = [
    "USDZAR_otc", "USDEGP_otc", "BRLUSD_otc", "USDIDR_otc", "USDCOP_otc",
    "USDNGN_otc", "XAUUSD_otc", "EURUSD_otc", "GBPUSD_otc", "USDARS_otc",
    "USDTHB_otc", "USDTRY_otc",
]

DURATION_SEC = 300  # 5 minutos
AMOUNT = 1.0        # monto demo (PRACTICE)


async def lanzar_direccion(client, asset: str, direction: str) -> tuple[str, tuple]:
    """Lanza una unica operacion y devuelve (direccion, (status, info, dt))."""
    t0 = time.time()
    ok, info = await enviar_orden(client, asset, direction, AMOUNT, DURATION_SEC)
    return direction, (ok, info, time.time() - t0)


async def main() -> None:
    asset_arg = sys.argv[1] if len(sys.argv) > 1 else None

    email = os.environ.get("QUOTEX_EMAIL", "")
    password = os.environ.get("QUOTEX_PASSWORD", "")
    if not email or not password:
        print(">> FALTA QUOTEX_EMAIL / QUOTEX_PASSWORD en .env")
        return

    client = Quotex(email=email, password=password)
    print(">> conectando...")
    ok, reason = await client.connect()
    print(f">> connected={ok} reason={reason}")
    if not ok:
        return

    await client.change_account("PRACTICE")
    print(">> cuenta: PRACTICE (demo)")

    # Elegir activo: el del arg, o el primero del allowlist que este abierto.
    asset = asset_arg
    if not asset:
        try:
            open_assets = await get_open_assets(client, 80)
            open_syms = {sym for sym, _ in open_assets}
            for cand in ALLOWLIST_OTC:
                if cand in open_syms:
                    asset = cand
                    break
        except Exception as exc:  # noqa: BLE001
            print(f">> get_open_assets EXC {exc} (uso fallback del allowlist)")
        if not asset:
            asset = ALLOWLIST_OTC[0]
    print(f">> activo OTC: {asset}  |  5 min (300s)  |  monto {AMOUNT}")

    # Lanzar CALL y PUT al MISMO TIEMPO (concurrentes).
    print(">> lanzando CALL + PUT concurrentes...")
    t0 = time.time()
    resultados = await asyncio.gather(
        lanzar_direccion(client, asset, "call"),
        lanzar_direccion(client, asset, "put"),
    )
    print(f">> ambas retornaron en {time.time() - t0:.2f}s")
    for direction, (status, info, dt) in resultados:
        print(f"   {direction.upper():4} -> status={status}  ({dt:.2f}s)  info={info}")

    await client.close()
    print(">> done")


if __name__ == "__main__":
    asyncio.run(main())
