"""Watchdog de garantía de envío DEMO (Feature 41).

Plan del CEO:
  1. Espera hasta 15 min vigilando si el bot envió alguna orden a mercado
     (consulta /api/state del hub cada 30s).
  2. Si en 15 min NO se envió ninguna orden por el flujo natural, FUERZA
     "condiciones perfectas": conecta el cliente demo y envía UNA orden
     real a la cuenta PRACTICE para demostrar que el pipeline llega al broker.

No inventa éxito: si la red al broker no responde (DNS/WS bloqueado en el
sandbox), reporta el fallo explícitamente. En la máquina del usuario con
red, la orden SÍ sale a cuenta demo.

Uso:  python scripts/force_order_demo_watchdog.py [--hub-url URL] [--timeout 900]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import urllib.request

HUB_URL = "http://127.0.0.1:8091"
TIMEOUT_SEC = 900  # 15 min


def _load_env() -> dict:
    """Lee credenciales demo del .env sin imprimirlas."""
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _any_order_sent(hub_url: str) -> bool:
    """True si el estado del hub muestra alguna orden enviada/resultada."""
    try:
        with urllib.request.urlopen(f"{hub_url}/api/state", timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return False
    ed = data.get("edificio") or {}
    cards = ed.get("cards") or {}
    for c in cards.values():
        st = (c.get("order_status") or "").lower()
        if st in ("sent", "won", "lost", "pending"):
            return True
    rec = ed.get("contratados_recientes") or []
    return len(rec) > 0


def _force_demo_order() -> dict:
    """Fuerza una orden demo real vía pyquotex con las credenciales del .env.

    Devuelve un dict con el resultado (ok / motivo). No inventa.
    """
    env = _load_env()
    email = env.get("QUOTEX_EMAIL")
    password = env.get("QUOTEX_PASSWORD")
    demo_ssid = env.get("QUOTEX_DEMO_SSID")
    if not email or not password:
        return {"ok": False, "reason": "sin_credenciales_en_env"}

    try:
        from pyquotex.stable_api import Quotex
    except Exception as e:  # pragma: no cover
        return {"ok": False, "reason": f"pyquotex_no_disponible:{e}"}

    async def _run():
        client = Quotex(email=email, password=password, lang="en")
        # Cargar SSID demo para cuenta PRACTICE (salta login HTTP 403).
        try:
            from src.connection import _apply_demo_ssid
            _apply_demo_ssid(client)
        except Exception:
            pass
        connected = False
        try:
            connected = await client.connect()
        except Exception as e:
            return {"ok": False, "reason": f"connect_exception:{e}"}
        if not connected:
            return {"ok": False, "reason": "broker_no_responde_dns_o_ws_bloqueado"}

        try:
            from src.connection import place_order
            result = await place_order(
                client=client,
                asset="ATOUSD_otc",
                direction="call",
                amount=1.0,
                duration=60,
                dry_run=False,
                account_type="PRACTICE",
            )
            return {"ok": bool(result[0]) if result else False,
                    "broker": result, "reason": "orden_demo_enviada" if (result and result[0]) else "broker_rechazo"}
        except Exception as e:
            return {"ok": False, "reason": f"place_order_exception:{e}"}
        finally:
            try:
                await client.close()
            except Exception:
                pass

    try:
        return asyncio.run(_run())
    except Exception as e:
        return {"ok": False, "reason": f"async_exception:{e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hub-url", default=HUB_URL)
    ap.add_argument("--timeout", type=int, default=TIMEOUT_SEC)
    args = ap.parse_args()

    print(f"[WATCHDOG] Inicio. Vigilando envío natural de órdenes por {args.timeout}s en {args.hub_url}")
    start = time.time()
    last_check = 0.0
    while time.time() - start < args.timeout:
        if time.time() - last_check >= 30:
            last_check = time.time()
            if _any_order_sent(args.hub_url):
                print(f"[WATCHDOG] ✅ El flujo natural YA envió una orden a mercado antes de forzar. Garantía cumplida.")
                return 0
            elapsed = int(time.time() - start)
            print(f"[WATCHDOG] {elapsed}s transcurridos — aún sin orden natural.")
        time.sleep(5)

    print(f"[WATCHDOG] ⏰ 15 min sin orden natural. FORZANDO condiciones perfectas -> orden DEMO a mercado...")
    res = _force_demo_order()
    print(f"[WATCHDOG] Resultado del envío forzado: {json.dumps(res, ensure_ascii=False)}")
    if res.get("ok"):
        print("[WATCHDOG] ✅ Orden DEMO enviada al broker en cuenta PRACTICE. Pipeline extremo-a-extremo confirmado.")
        return 0
    print("[WATCHDOG] ⚠️ No se pudo enviar la orden. Motivo real arriba (probablemente red al broker bloqueada en este sandbox).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
