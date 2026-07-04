"""Poll candle count after get_candles request."""
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
from pyquotex.expiration import get_timestamp
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

    client.api.candles.candles_data = None
    client.start_candles_stream(sym, TF_5M)
    client.api.get_candles(sym, get_timestamp(), end, offset, TF_5M)

    for i in range(50):
        await asyncio.sleep(0.5)
        prepared = client.prepare_candles(sym, TF_5M) or []
        raw = client.api.candles.candles_data if client.api.candles else None
        raw_len = len(raw) if isinstance(raw, list) else (len(raw) if raw else 0)
        print(f"  t={i*0.5:.1f}s prepared={len(prepared)} raw_type={type(raw).__name__} raw_len={raw_len}")
        if len(prepared) >= CANDLES_LOOKBACK:
            break

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())