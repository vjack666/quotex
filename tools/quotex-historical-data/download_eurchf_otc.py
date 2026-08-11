"""Descarga EURCHF_otc M1 desde Quotex (cuenta demo, .env local).
Un solo par. Luego se agrega a M5 para el grafico POI.
No es parte del motor del Edificio: es adquisicion de datos en disco.
"""
import os
import sys
import asyncio
import csv
import logging
from datetime import datetime

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
    print("ERROR: QUOTEX_EMAIL / QUOTEX_PASSWORD no encontrados en .env")
    sys.exit(1)

ASSET = "EURCHF_otc"
DIAS = 120
PERIOD = 60          # M1
REINTENTOS = 3
ESPERA = 5


async def descargar():
    for intento in range(1, REINTENTOS + 1):
        client = Quotex(email=EMAIL, password=PASSWORD, lang="en")
        client.debug_ws_enable = False
        try:
            ok, msg = await client.connect()
            if not ok:
                print(f"[!] connect fallo intento {intento}: {msg}")
                await asyncio.sleep(ESPERA)
                continue
            print(f"[*] {ASSET}: conectado (intento {intento})", flush=True)
            candles = await client.get_candles_deep(ASSET, int(86400 * DIAS), PERIOD)
            if candles:
                safe = ASSET.replace("/", "_")
                fn = f"{safe}_{PERIOD}s_{DIAS}days.csv"
                written = 0
                with open(fn, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["timestamp", "datetime", "open", "high", "low", "close", "ticks"])
                    prev = None
                    for c in candles:
                        op, hi, lo, cl = c.get("open"), c.get("high"), c.get("low"), c.get("close")
                        if None in (op, hi, lo, cl):
                            continue
                        ts = int(c.get("time", 0))
                        if prev is not None and ts <= prev:
                            continue  # descarta duplicados/desorden
                        prev = ts
                        dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                        w.writerow([ts, dt, op, hi, lo, cl, c.get("ticks", 0)])
                        written += 1
                print(f"[+] {ASSET}: {written:,} velas -> {fn}", flush=True)
                await client.close()
                return written
            else:
                print(f"[!] sin velas intento {intento}")
        except Exception as e:
            print(f"[!] error intento {intento}: {e}", flush=True)
        finally:
            try:
                await client.close()
            except Exception:
                pass
        await asyncio.sleep(ESPERA)
    print(f"[!] {ASSET}: FALLO tras {REINTENTOS} intentos", flush=True)
    return 0


if __name__ == "__main__":
    asyncio.run(descargar())
