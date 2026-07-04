"""Comparar métodos de fetch de velas pyquotex."""
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
    client.get_all_asset_name()
    assets = await get_open_assets(client, min_payout=MIN_PAYOUT)
    sym = assets[0][0]
    offset = CANDLES_LOOKBACK * TF_5M
    end = time.time()
    print(f"Asset={sym} offset={offset}")

    methods = [
        ("get_candles", lambda: client.get_candles(sym, end, offset, TF_5M, timeout=25)),
        ("get_candles progressive", lambda: client.get_candles(sym, end, offset, TF_5M, progressive=True, timeout=25)),
        ("get_candle_v2", lambda: client.get_candle_v2(sym, TF_5M, timeout=25)),
    ]
    if sym in client.codes_asset:
        methods.append(
            ("get_history_line", lambda: client.get_history_line(sym, end, offset, timeout=25)),
        )
    else:
        print(f"codes_asset missing for {sym}, keys sample={list(client.codes_asset)[:3]}")

    for name, fn in methods:
        await asyncio.sleep(4)
        try:
            result = await fn()
            if result is None:
                print(f"  {name}: None")
            elif isinstance(result, list):
                print(f"  {name}: list len={len(result)}")
            elif isinstance(result, dict):
                print(f"  {name}: dict keys={len(result)}")
            else:
                print(f"  {name}: type={type(result).__name__}")
        except Exception as exc:
            print(f"  {name}: ERROR {exc}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())