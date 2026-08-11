"""Wrapper robusto: descarga historico OTC de Quotex en M1 para varios pares.
- Reconecta por cada par (la conexion WS se cae a veces).
- Reintenta N veces por par.
- No aborta todo si un par falla.
Usa el .env local (QUOTEX_EMAIL / QUOTEX_PASSWORD). Cuenta demo.
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

PARES = ["GBPUSD_otc", "USDJPY_otc", "XAUUSD_otc"]
DIAS = 120           # pedimos 120; el broker da lo que tiene (~50-90 dias)
PERIOD = 60          # M1
REINTENTOS = 3
ESPERA = 5           # seg entre reintentos


async def descargar_un_par(asset, days, period):
    """Intenta descargar un par; reconecta en cada intento. Devuelve n velas."""
    last_err = None
    for intento in range(1, REINTENTOS + 1):
        client = Quotex(email=EMAIL, password=PASSWORD, lang="en")
        client.debug_ws_enable = False
        try:
            ok, msg = await client.connect()
            if not ok:
                last_err = f"connect:{msg}"
                await asyncio.sleep(ESPERA)
                continue
            print(f"[*] {asset}: conectado (intento {intento})", flush=True)
            candles = await client.get_candles_deep(asset, int(86400 * days), period)
            if candles:
                safe = asset.replace("/", "_")
                fn = f"{safe}_{period}s_{days}days.csv"
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
                print(f"[+] {asset}: {written:,} velas -> {fn}", flush=True)
                await client.close()
                return written
            else:
                last_err = "sin velas"
        except Exception as e:
            last_err = str(e)
            print(f"[!] {asset}: error intento {intento}: {e}", flush=True)
        finally:
            try:
                await client.close()
            except Exception:
                pass
        await asyncio.sleep(ESPERA)
    print(f"[!] {asset}: FALLO tras {REINTENTOS} intentos ({last_err})", flush=True)
    return 0


async def main():
    print(f"[*] Cuenta: {EMAIL[:3]}*** | pares: {len(PARES)} | dias pedidos: {DIAS}", flush=True)
    for asset in PARES:
        n = await descargar_un_par(asset, DIAS, PERIOD)
        print(f"[=] {asset}: {n:,} velas", flush=True)
    print("[*] Descarga completa.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
