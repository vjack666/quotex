"""Diagnóstico rápido: velas 5m/1m y detección de consolidación en vivo."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import CANDLES_LOOKBACK, MIN_CONSOLIDATION_BARS, MIN_PAYOUT, TF_5M
from connection import connect_with_retry, fetch_candles_with_retry, get_open_assets
from pyquotex.stable_api import Quotex  # type: ignore
from strat_a import compute_dynamic_range, detect_consolidation


async def main() -> None:
    email = os.getenv("QUOTEX_EMAIL", "")
    password = os.getenv("QUOTEX_PASSWORD", "")
    if not email or not password:
        print("ERROR: faltan credenciales en .env")
        return

    client = Quotex(email=email, password=password)
    ok, reason = await connect_with_retry(client)
    if not ok:
        print(f"ERROR conexión: {reason}")
        return
    assets = await get_open_assets(client, min_payout=MIN_PAYOUT)
    print(f"Activos OTC abiertos (payout>={MIN_PAYOUT}%): {len(assets)}")
    if not assets:
        await client.close()
        return

    sample = assets[:20]
    min_bars = MIN_CONSOLIDATION_BARS + 2
    zones = 0
    short_5m = 0
    short_1m = 0

    for sym, payout in sample:
        c5 = await fetch_candles_with_retry(client, sym, TF_5M, CANDLES_LOOKBACK, timeout_sec=10)
        c1 = await fetch_candles_with_retry(client, sym, 60, 36, timeout_sec=12)
        n5, n1 = len(c5), len(c1)
        if n5 < min_bars:
            short_5m += 1
        if n1 < 20:
            short_1m += 1
        zone = None
        if n5 >= min_bars:
            dyn, atr_pct, _ = compute_dynamic_range(c5)
            zone = detect_consolidation(c5, max_range_pct=dyn)
            if zone:
                zones += 1
                print(
                    f"  ZONA {sym} payout={payout}% range={zone.range_pct:.4f} "
                    f"dyn_max={dyn:.4f} atr_pct={atr_pct:.4f} bars={zone.bars_inside}"
                )
        else:
            print(f"  SHORT {sym}: 5m={n5} 1m={n1} payout={payout}%")

    print(
        f"\nResumen ({len(sample)} activos): zonas={zones} "
        f"short_5m={short_5m} short_1m={short_1m} min_bars_5m={min_bars}"
    )
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())