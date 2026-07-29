"""Postmortem REAL de la venta AUDUSD_otc — lo que el humano no puede ver.

Baja el historico REAL de velas M1/M5/M15 de AUDUSD_otc (Quotex lo mantiene
disponible) y reconstruye, usando las LINEAS QUE EL USUARIO DIBUJO como
referencia:
  - Tamano de la RESISTENCIA (rango de precios donde el precio reboto / se
    agoto en la zona alta).
  - Comportamiento de las VELAS DENTRO del soporte (respeta las lineas).
  - Estocastico M5 vs M15 lado a lado (donde el humano solo ve uno).
  - La pelicula completa del agotamiento: Z5 -> cruce -> vela de indecision.

Reusa la LOGICA REAL del bot (compute_stoch, stoch_exhaustion, fetch_candles).
"""

from __future__ import annotations

import asyncio
import sys
from collections import Counter
from datetime import datetime, timezone
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
from stoch_exhaustion import classify_exhaustion_candle  # type: ignore
from pyquotex.stable_api import Quotex  # type: ignore

# Lineas que el usuario dibujo (referencia)
RESIST = 0.70145      # linea azul arriba
MID = 0.69916         # linea punteada de abajo (confirmar)
BELL = 0.70005        # campana / apertura de la vela clave


def _stamp(c) -> str:
    return datetime.fromtimestamp(float(c.ts), tz=timezone.utc).strftime("%H:%M")


async def main() -> None:
    client = Quotex(email=EMAIL, password=PASSWORD)
    ok, reason = await client.connect()
    if not ok:
        raise RuntimeError(f"no conecto: {reason}")

    # bajar historicos reales
    m1 = await fetch_candles_with_retry(client, "AUDUSD_otc", 60, 120, timeout_sec=40)
    m5 = await fetch_candles_with_retry(client, "AUDUSD_otc", 300, 80, timeout_sec=40)
    m15 = await fetch_candles_with_retry(client, "AUDUSD_otc", 900, 60, timeout_sec=40)
    await client.close()

    print(f"velas bajadas: M1={len(m1)} M5={len(m5)} M15={len(m15)}")
    print(f"LINEAS referencia: resist={RESIST} mid={MID} bell={BELL}")
    print("=" * 70)

    # 1) TAMANO DE LA RESISTENCIA: velas M15 que tocaron >= RESIST
    toques = [c for c in m15 if float(c.high) >= RESIST - 0.0002]
    if toques:
        hs = [float(c.high) for c in toques]
        print(f"\n[RESISTENCIA] {len(toques)} velas M15 tocaron >= {RESIST}:")
        print(f"  high maximo = {max(hs):.5f}  high minimo = {min(hs):.5f}"
              f"  ancho = {max(hs)-min(hs):.5f}")
        for c in toques[-6:]:
            print(f"   {_stamp(c)} open={float(c.open):.5f} high={float(c.high):.5f}"
                  f" low={float(c.low):.5f} close={float(c.close):.5f}")
    else:
        print(f"\n[RESISTENCIA] ninguna vela M15 toco {RESIST} en la ventana")

    # 2) VELAS DENTRO DEL SOPORTE (entre BELL y MID) y su forma
    soporte = [c for c in m1 if float(c.low) <= BELL + 0.0003 and float(c.high) >= MID - 0.0003]
    formas = Counter()
    for c in soporte:
        f = classify_exhaustion_candle(c, "CALL") or "normal"
        formas[f] += 1
    print(f"\n[SOPORTE] velas M1 en la franja soporte (entre {MID} y {BELL}): {len(soporte)}")
    if soporte:
        closes = [float(c.close) for c in soporte]
        print(f"  close min={min(closes):.5f} max={max(closes):.5f}")
        print(f"  formas de vela: {dict(formas)}")
        for c in soporte[-8:]:
            print(f"   {_stamp(c)} H={float(c.high):.5f} L={float(c.low):.5f}"
                  f" C={float(c.close):.5f} forma={classify_exhaustion_candle(c,'CALL') or 'normal'}")

    # 3) ESTOCASTICO M5 vs M15 lado a lado (los ultimos 12 cruces)
    print("\n[ESTOCASTICO M15] (lo que el bot vio):")
    s15 = compute_stoch(m15, direction="PUT")
    print(f"  k={s15['k']:.1f} d={s15['d']:.1f} estado={s15['estado']}"
          f" cruce={s15['cruce']} cross_ago={s15['cross_ago']}")
    print("\n[ESTOCASTICO M5] (lo que el humano no ve en paralelo):")
    s5 = compute_stoch(m5, direction="PUT")
    print(f"  k={s5['k']:.1f} d={s5['d']:.1f} estado={s5['estado']}"
          f" cruce={s5['cruce']} cross_ago={s5['cross_ago']}")

    # 4) pelicula: ultimas 10 velas M15 con su estocastico local
    print("\n[PELICULA M15] ultimas 10 velas con estocastico por vela:")
    for i in range(max(0, len(m15) - 10), len(m15)):
        ss = compute_stoch(m15[: i + 1], direction="PUT")
        c = m15[i]
        print(f"  {_stamp(c)} k={ss['k']:.1f} d={ss['d']:.1f} {ss['estado'][:4]}"
              f" close={float(c.close):.5f}")


if __name__ == "__main__":
    asyncio.run(main())
