"""Analisis de ZONA ADAPTATIVA para USDPKR (y generico).

Muestra por que una banda fija de pips falla en activos exoticos y como
medir la zona por el COMPORTAMIENTO del precio (rango reciente), no por
pips fijos. Reusa fetch_candles + compute_stoch reales.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
from config import EMAIL, PASSWORD  # type: ignore
from connection import fetch_candles_with_retry  # type: ignore
from stochastic_m15 import compute_stoch  # type: ignore
from pyquotex.stable_api import Quotex  # type: ignore


def _adapt_zone(candles, frac=0.5, lookback=40):
    """Zona adaptativa: el rango de los ultimos `lookback` candles, pero solo
    la MITAD superior o inferior segun el extremo. Devuelve (lo, hi, ancho_pips,
    ancho_pct). NO usa pips fijos: el ancho es % del precio."""
    cs = list(candles[-lookback:])
    highs = [float(c.high) for c in cs]
    lows = [float(c.low) for c in cs]
    hi = max(highs)
    lo = min(lows)
    mid = (hi + lo) / 2
    rng = hi - lo
    # zona = franja central de amplitud frac*rng alrededor de mid (como tu rectangulo)
    zhi = mid + frac * rng / 2
    zlo = mid - frac * rng / 2
    return zlo, zhi, (zhi - zlo), (zhi - zlo) / mid * 100.0


async def analyze(asset: str):
    client = Quotex(email=EMAIL, password=PASSWORD)
    ok, reason = await client.connect()
    if not ok:
        print(f"{asset}: NO conecto ({reason})")
        return
    m15 = await fetch_candles_with_retry(client, asset, 900, 60, timeout_sec=40)
    await client.close()
    if not m15:
        print(f"{asset}: sin velas")
        return
    zlo, zhi, ancho_pips, ancho_pct = _adapt_zone(m15)
    st = compute_stoch(m15, direction="PUT")
    print(f"\n=== {asset} ===")
    print(f"  ultimo precio ~ {float(m15[-1].close):.5f}")
    print(f"  ZONA adaptativa (frac=0.5, 40 velas): {zlo:.5f} .. {zhi:.5f}")
    print(f"  ancho = {ancho_pips:.5f} pips  |  {ancho_pct:.3f}% del precio")
    print(f"  >> banda fija 0.0008*precio habria sido: {float(m15[-1].close)*0.0008:.5f}")
    print(f"  estocastico M15: k={st['k']:.1f} d={st['d']:.1f} {st['estado']} cruce={st['cruce']} cross_ago={st['cross_ago']}")
    # ¿el precio esta DENTRO o FUERA de la zona?
    last = float(m15[-1].close)
    print(f"  precio {last:.5f} esta {'DENTRO' if zlo <= last <= zhi else 'FUERA'} de la zona")


async def main():
    for a in ["USDPKR_otc", "USDPKR", "AUDUSD_otc"]:
        try:
            await analyze(a)
        except Exception as e:
            print(f"{a}: error {e}")


if __name__ == "__main__":
    asyncio.run(main())
