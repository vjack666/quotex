"""Test new HistoryMixin candle APIs."""
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
    ok, _ = await connect_with_retry(client)
    if not ok:
        return
    assets = await get_open_assets(client, min_payout=MIN_PAYOUT)
    sym = assets[0][0]
    offset = CANDLES_LOOKBACK * TF_5M
    end = time.time()
    print(f"pyquotex={Quotex.__module__} asset={sym}")

    for name, coro in [
        ("get_candles", client.get_candles(sym, end, offset, TF_5M, timeout=30)),
        ("get_historical_candles", client.get_historical_candles(sym, TF_5M, CANDLES_LOOKBACK, timeout=30)),
    ]:
        await asyncio.sleep(3)
        try:
            result = await coro
            n = len(result) if result else 0
            print(f"  {name}: len={n}")
        except Exception as exc:
            print(f"  {name}: ERROR {type(exc).__name__}: {exc}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())