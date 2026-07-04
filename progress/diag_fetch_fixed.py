"""Quick test: fetch_candles after fix."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import CANDLES_LOOKBACK, MIN_PAYOUT, TF_5M
from connection import connect_with_retry, fetch_candles_with_retry, get_open_assets
from pyquotex.stable_api import Quotex  # type: ignore
from strat_a import compute_dynamic_range, detect_consolidation


async def main() -> None:
    client = Quotex(
        email=os.getenv("QUOTEX_EMAIL", ""),
        password=os.getenv("QUOTEX_PASSWORD", ""),
    )
    ok, _ = await connect_with_retry(client)
    if not ok:
        print("connect fail")
        return
    assets = await get_open_assets(client, min_payout=MIN_PAYOUT)
    sym = assets[0][0]
    c5 = await fetch_candles_with_retry(client, sym, TF_5M, CANDLES_LOOKBACK, timeout_sec=45)
    print(f"{sym}: 5m candles={len(c5)}")
    if len(c5) >= 14:
        dyn, _, _ = compute_dynamic_range(c5)
        z = detect_consolidation(c5, max_range_pct=dyn)
        print(f"zone={'YES' if z else 'NO'} range_pct={z.range_pct if z else 'n/a'}")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())