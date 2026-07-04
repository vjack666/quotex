"""Prueba aislada: una sola vela fetch con delays."""
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
from connection import connect_with_retry, fetch_candles, get_open_assets
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
    print(f"Testing {sym}")

    for attempt in range(1, 4):
        await asyncio.sleep(3)
        t0 = time.monotonic()
        raw = await client.get_candles(sym, time.time(), CANDLES_LOOKBACK * TF_5M, TF_5M, timeout=20)
        dt = time.monotonic() - t0
        n_raw = len(raw) if raw else 0
        c5 = await fetch_candles(client, sym, TF_5M, CANDLES_LOOKBACK)
        print(f"  attempt {attempt}: raw={n_raw} fetch_candles={len(c5)} elapsed={dt:.1f}s")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())