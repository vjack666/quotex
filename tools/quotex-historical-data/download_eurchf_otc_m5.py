"""Temp ad-hoc: descarga EURCHF_otc en M5 (period=300) desde Quotex via pyquotex.
Reusa get_candles_deep del pyquotex local. Lee credenciales de .env local.
Se borra tras usar. NO toca src/."""
import os, sys, asyncio, csv, logging
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, ".")
from pyquotex.stable_api import Quotex

logging.basicConfig(level=logging.WARNING)
EMAIL = os.getenv("QUOTEX_EMAIL", "")
PASSWORD = os.getenv("QUOTEX_PASSWORD", "")
if not EMAIL or not PASSWORD:
    print("ERROR: credenciales no encontradas en .env")
    sys.exit(1)

ASSET = "EURCHF_otc"
DIAS = 120
PERIOD = 300  # M5

async def main():
    client = Quotex(email=EMAIL, password=PASSWORD, lang="en")
    client.debug_ws_enable = False
    ok, msg = await client.connect()
    if not ok:
        print(f"ERROR connect: {msg}")
        return
    print(f"[*] conectado {EMAIL[:3]}***")
    candles = await client.get_candles_deep(ASSET, int(86400 * DIAS), PERIOD)
    if not candles:
        print("[!] sin velas")
        await client.close()
        return
    safe = ASSET.replace("/", "_")
    fn = f"{safe}_{PERIOD}s_{DIAS}days.csv"
    written = 0
    with open(fn, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "datetime", "open", "high", "low", "close", "ticks"])
        for c in candles:
            op, hi, lo, cl = c.get("open"), c.get("high"), c.get("low"), c.get("close")
            if None in (op, hi, lo, cl):
                continue
            dt = datetime.fromtimestamp(c["time"]).strftime("%Y-%m-%d %H:%M:%S")
            w.writerow([c["time"], dt, op, hi, lo, cl, c.get("ticks", 0)])
            written += 1
    print(f"[+] {ASSET} M5: {written:,} velas -> {fn}")
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
