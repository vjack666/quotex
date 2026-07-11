"""Diagnóstico SOLO LECTURA: ¿qué campos trae get_candles de Quotex?

Imprime las claves del dict crudo de una vela y el valor de 'volume'/'atime'
para confirmar si Quotex envía volumen (ticks) y si nuestro bot lo captura.

No envía ninguna orden. Requiere .env con QUOTEX_EMAIL / QUOTEX_PASSWORD.
Correr: python progress/diag_volume.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import CANDLES_LOOKBACK, MIN_PAYOUT, TF_5M
from connection import connect_with_retry, get_open_assets
from pyquotex.stable_api import Quotex  # type: ignore


async def main() -> None:
    client = Quotex(
        email=os.getenv("QUOTEX_EMAIL", ""),
        password=os.getenv("QUOTEX_PASSWORD", ""),
    )
    ok, reason = await connect_with_retry(client)
    if not ok:
        print("connect fail:", reason)
        return
    assets = await get_open_assets(client, min_payout=MIN_PAYOUT)
    sym = assets[0][0]
    print(f"Asset: {sym}")

    await asyncio.sleep(2)
    raw = await client.get_candles(sym, time.time(), CANDLES_LOOKBACK * TF_5M, TF_5M, timeout=20)
    if not raw:
        print("get_candles devolvió vacío")
        await client.close()
        return

    last = raw[-1]
    print("Claves del dict crudo de UNA vela:")
    for k, v in last.items():
        print(f"  {k!r}: {v!r}")
    print()
    print("¿Trae 'volume'?", "volume" in last, "-> valor:", last.get("volume"))
    print("¿Trae 'atime'?", "atime" in last, "-> valor:", last.get("atime"))
    print("¿Trae 'time'?", "time" in last, "-> valor:", last.get("time"))
    # Muestra los volúmenes de las últimas 5 velas para ver si varían / vienen en 0
    print()
    print("Volumen (campo 'volume') de últimas 5 velas:")
    for r in raw[-5:]:
        print(f"  ts={r.get('time')} volume={r.get('volume')} close={r.get('close')}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
