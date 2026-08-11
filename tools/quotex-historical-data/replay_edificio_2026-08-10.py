"""Replay del Edificio de Contratación — señales reales del 2026-08-10.

Para cada señal que el Edificio registró en el log (P2/P3), reconstruye la
dirección EXACTAMENTE como la calcula `src/scanner.py` (estocástico FULL
14,3,3 M15 + tendencia %K M1) y simula la operación a 900 segundos
(EDIFICIO_ORDER_DURATION_SEC) contra velas reales del broker descargadas
con PyQuotex (get_candles_deep).

Regla de dirección replicada de scanner.py:1484-1502:
  - si hay >= 17 velas M1: k_now > k_3ago y k_M15 < 80  -> CALL (source M1)
                           k_now < k_3ago y k_M15 > 20  -> PUT  (source M1)
  - si no hay dirección M1: k >= 80 -> PUT | k <= 20 -> CALL
                            k > d y k < 50 -> CALL | k < d y k > 50 -> PUT (source M15)

Simulación de la operación:
  - entry = open de la primera vela M1 con ts >= instante de la señal
  - exit  = close de la primera vela M1 con ts >= instante + 900 s
  - WIN: CALL y exit > entry | PUT y exit < entry

Salidas (en tools/quotex-historical-data/replay_2026-08-10/):
  - velas M1 (60s) y M15 (900s) por activo, en CSV
  - reporte por señal (WIN/LOSS hipotético) + resumen global

Uso: .venv\\Scripts\\python.exe tools\\quotex-historical-data\\replay_edificio_2026-08-10.py
"""

from __future__ import annotations

import asyncio
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# salida en UTF-8 para consolas Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "src"
OUT_DIR = ROOT / "tools" / "quotex-historical-data" / "replay_2026-08-10"
OUT_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SRC))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:  # noqa: BLE001
    pass

EMAIL = os.getenv("QUOTEX_EMAIL", "")
PASSWORD = os.getenv("QUOTEX_PASSWORD", "")
if not EMAIL or not PASSWORD:
    print("ERROR: QUOTEX_EMAIL / QUOTEX_PASSWORD no encontrados en .env")
    sys.exit(1)

from pyquotex.stable_api import Quotex  # noqa: E402

from models import Candle  # noqa: E402
from stochastic_m15 import compute_stoch  # noqa: E402

# ── Parámetros ───────────────────────────────────────────────────────────────
DURACION_SEC = 900  # EDIFICIO_ORDER_DURATION_SEC
DIAS_VENTANA = 1  # 1 día alcanza: cubre el día de señales + warmup del estocástico
DIA_SENALES = "2026-08-10"

# (asset, hora_local "HH:MM:SS", piso alcanzado, ratio de compresión, payout %)
# Extraídas de data/logs/runtime/consolidation_bot.log del 10/08.
SIGNALS: List[Tuple[str, str, str, float, int]] = [
    # P2 — tarjeta de acceso emitida (freno CONFIRMED)
    ("DOTUSD_otc", "14:56:59", "P2", 0.69, 92),
    ("DOTUSD_otc", "14:59:59", "P2", 0.69, 92),
    ("ETHUSD_otc", "15:10:59", "P2", 0.54, 92),
    ("USDPKR_otc", "15:17:04", "P2", 0.52, 93),
    ("AUDCHF_otc", "15:17:04", "P2", 0.59, 91),
    ("ETHUSD_otc", "16:02:10", "P2", 0.34, 92),
    ("LINUSD_otc", "16:02:10", "P2", 0.48, 92),
    ("USDARS_otc", "16:07:18", "P2", 0.65, 93),
    ("LINUSD_otc", "16:10:23", "P2", 0.48, 92),
    ("ETCUSD_otc", "16:16:01", "P2", 0.50, 92),
    ("LINUSD_otc", "16:17:07", "P2", 0.03, 92),
    ("USCrude_otc", "16:23:01", "P2", 0.58, 92),
    ("XRPUSD_otc", "16:26:01", "P2", 0.63, 92),
    ("AXSUSD_otc", "16:47:00", "P2", 0.42, 92),
    ("XRPUSD_otc", "16:49:12", "P2", 0.60, 92),
    ("ETHUSD_otc", "17:23:00", "P2", 0.34, 92),
    ("AUDJPY_otc", "17:26:00", "P2", 0.48, 92),
    ("NZDCAD_otc", "17:31:48", "P2", 0.29, 94),
    ("TRUUSD_otc", "17:41:02", "P2", 0.41, 92),
    ("SOLUSD_otc", "17:45:55", "P2", 0.61, 92),
    ("SOLUSD_otc", "17:49:58", "P2", 0.61, 92),
    ("LINUSD_otc", "18:36:01", "P2", 0.69, 92),
    ("USDBDT_otc", "18:43:02", "P2", 0.46, 93),
    ("BTCUSD_otc", "18:51:02", "P2", 0.58, 92),
    ("BTCUSD_otc", "18:54:01", "P2", 0.58, 92),
    ("BRLUSD_otc", "19:06:01", "P2", 0.68, 92),
    # P3 — separación confirmada (la señal a un paso de contratar)
    ("USCrude_otc", "16:26:01", "P3", 0.58, 92),
    ("BTCUSD_otc", "18:57:01", "P3", 0.58, 92),
    ("SOLUSD_otc", "18:58:01", "P3", 0.61, 93),
]

ACTIVOS: List[str] = sorted({s[0] for s in SIGNALS})


def ts_local(hora: str) -> int:
    """Hora local del log -> epoch UTC (timestamp() interpreta la zona local)."""
    h, m, s = (int(x) for x in hora.split(":"))
    return int(datetime(int(DIA_SENALES[:4]), int(DIA_SENALES[5:7]), int(DIA_SENALES[8:10]), h, m, s).timestamp())


# ── Conexión (patrón del bot: SSID demo + reintentos + cuenta PRACTICE) ─────
def apply_demo_ssid(client: Quotex) -> bool:
    """Carga QUOTEX_DEMO_SSID en session_data para saltar el login HTTP (403).

    Mismo mecanismo que src/connection.py:_apply_demo_ssid: pyquotex solo hace
    authenticate() por HTTP (bloqueado con 403) cuando session_data está vacío;
    con el token cargado, autentica por WS directamente.
    """
    sess = getattr(client, "session_data", None)
    if not isinstance(sess, dict) or sess.get("token"):
        return bool(sess and sess.get("token"))
    ssid = os.environ.get("QUOTEX_DEMO_SSID") or os.environ.get("QUOTEX_SSID")
    if not ssid:
        return False
    sess["token"] = ssid
    return True


async def conectar(client: Quotex, max_intentos: int = 4) -> Tuple[bool, str]:
    apply_demo_ssid(client)
    for intento in range(1, max_intentos + 1):
        ok, reason = await client.connect()
        if ok:
            try:
                await client.change_account("PRACTICE")
            except Exception:  # noqa: BLE001
                pass
            return True, ""
        print(f"  [conexión {intento}/{max_intentos}] rechazada: {reason}", flush=True)
        await asyncio.sleep(3)
    return False, "connect_failed"


# ── Descarga / cache ─────────────────────────────────────────────────────────
def _candles_to_dicts(candles: List[Candle]) -> List[dict]:
    return [
        {"time": c.ts, "open": c.open, "high": c.high, "low": c.low, "close": c.close, "ticks": c.ticks}
        for c in candles
    ]


def _csv_path(asset: str, tf: int) -> Path:
    return OUT_DIR / f"{asset}_{tf}s.csv"


async def cargar_o_descargar(client: Quotex, asset: str, tf: int, max_reintentos: int = 4) -> List[Candle]:
    """Cache en CSV; si no existe, descarga con get_candles_deep y reconexión por par."""
    path = _csv_path(asset, tf)
    if path.exists():
        velas: List[Candle] = []
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                velas.append(
                    Candle(ts=int(row["time"]), open=float(row["open"]), high=float(row["high"]),
                           low=float(row["low"]), close=float(row["close"]), ticks=int(row.get("ticks") or 0))
                )
        velas.sort(key=lambda c: c.ts)
        return velas

    segundos = int(86400 * DIAS_VENTANA)
    ultimo_error = None
    for intento in range(1, max_reintentos + 1):
        try:
            datos = await client.get_candles_deep(asset, segundos, tf)
            if not datos:
                raise RuntimeError(f"get_candles_deep devolvió vacío ({asset} tf={tf})")
            velas = [
                Candle(ts=int(c["time"]), open=float(c["open"]), high=float(c["high"]),
                       low=float(c["low"]), close=float(c["close"]), ticks=int(c.get("ticks") or 0))
                for c in datos
                if c.get("time") and c.get("close") is not None
            ]
            # dedupe por ts y orden ascendente
            velas.sort(key=lambda c: c.ts)
            unicos: List[Candle] = []
            for v in velas:
                if not unicos or unicos[-1].ts != v.ts:
                    unicos.append(v)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["time", "open", "high", "low", "close", "ticks"])
                writer.writeheader()
                writer.writerows(_candles_to_dicts(unicos))
            print(f"  [descarga] {asset} tf={tf} -> {len(unicos)} velas ({path.name})", flush=True)
            return unicos
        except Exception as exc:  # noqa: BLE001 — reconexión por par (patrón download_otc)
            ultimo_error = exc
            print(f"  [reintento {intento}/{max_reintentos}] {asset} tf={tf}: {exc}", flush=True)
            await asyncio.sleep(3 * intento)
            try:
                await client.connect()
            except Exception:  # noqa: BLE001
                pass
    raise RuntimeError(f"No se pudo descargar {asset} tf={tf}: {ultimo_error}")


# ── Reconstrucción de dirección (regla scanner.py:1484-1502) ─────────────────
def reconstruir_direccion(m15_cerradas: List[Candle], m1_cerradas: List[Candle]) -> Tuple[str, str]:
    stoch = compute_stoch(m15_cerradas) if m15_cerradas else {"k": None, "d": None}
    k = stoch.get("k")
    d = stoch.get("d")
    if k is None:
        return "", ""
    direction, source = "", ""
    if len(m1_cerradas) >= 17:
        stoch_m1 = compute_stoch(m1_cerradas)
        k_vals = stoch_m1.get("k_vals") or []
        if len(k_vals) >= 4:
            k_now = float(k_vals[-1])
            k_3ago = float(k_vals[-4])
            if k_now > k_3ago and float(k) < 80.0:
                direction, source = "CALL", "M1"
            elif k_now < k_3ago and float(k) > 20.0:
                direction, source = "PUT", "M1"
    if not direction:
        if float(k) >= 80.0:
            direction, source = "PUT", "M15"
        elif float(k) <= 20.0:
            direction, source = "CALL", "M15"
        elif d is not None and float(k) > float(d) and float(k) < 50:
            direction, source = "CALL", "M15"
        elif d is not None and float(k) < float(d) and float(k) > 50:
            direction, source = "PUT", "M15"
    return direction, source


# ── Simulación de la operación a 900 s ───────────────────────────────────────
def simular_operacion(ts_senal: int, m1: List[Candle]) -> Tuple[Optional[float], Optional[float], str]:
    """entry = open de la 1ª vela M1 con ts >= señal; exit = close de la 1ª vela con ts >= señal+900."""
    entry_v = next((c for c in m1 if c.ts >= ts_senal), None)
    if entry_v is None:
        return None, None, "NO_ENTRY"
    exit_v = next((c for c in m1 if c.ts >= ts_senal + DURACION_SEC), None)
    if exit_v is None:
        return entry_v.open, None, "NO_EXIT"
    return entry_v.open, exit_v.close, "OK"


# ── Reporte ──────────────────────────────────────────────────────────────────
async def main() -> None:
    print("=" * 78)
    print(f"REPLAY EDIFICIO DE CONTRATACIÓN — señales del {DIA_SENALES}")
    print("=" * 78)

    # 1) conectar
    client = Quotex(email=EMAIL, password=PASSWORD, lang="en")
    client.debug_ws_enable = False
    conectado, _ = await conectar(client)
    if not conectado:
        print("FALLO de conexión a Quotex. Revisar .env (QUOTEX_EMAIL/QUOTEX_PASSWORD/QUOTEX_DEMO_SSID).")
        sys.exit(1)
    print(f"Conectado: {EMAIL[:3]}***", flush=True)

    # 2) descargar velas por activo (M1 y M15)
    velas_m1: dict = {}
    velas_m15: dict = {}
    for asset in ACTIVOS:
        print(f"[{asset}]", flush=True)
        velas_m1[asset] = await cargar_o_descargar(client, asset, 60)
        velas_m15[asset] = await cargar_o_descargar(client, asset, 900)
    print(f"Velas descargadas/recuperadas para {len(ACTIVOS)} activos.\n", flush=True)

    # 3) simular cada señal
    filas: List[dict] = []
    for asset, hora, piso, ratio, payout in SIGNALS:
        ts = ts_local(hora)
        m1 = velas_m1[asset]
        m15 = velas_m15[asset]
        # velas CERRADAS hasta el instante de la señal (como las veía el scanner)
        m15_cerradas = [c for c in m15 if c.ts + 900 <= ts]
        m1_cerradas = [c for c in m1 if c.ts + 60 <= ts]
        direccion, source = reconstruir_direccion(m15_cerradas, m1_cerradas)
        entry, exit_p, estado = simular_operacion(ts, m1)

        resultado = ""
        if estado == "OK" and direccion and entry is not None and exit_p is not None:
            if (direccion == "CALL" and exit_p > entry) or (direccion == "PUT" and exit_p < entry):
                resultado = "WIN"
            elif exit_p == entry:
                resultado = "DRAW"
            else:
                resultado = "LOSS"
        elif estado != "OK":
            resultado = estado
        elif not direccion:
            resultado = "SIN_DIR"

        filas.append({
            "hora": hora, "asset": asset, "piso": piso, "ratio": ratio, "payout": payout,
            "direccion": direccion or "-", "source": source or "-",
            "entry": f"{entry:.5f}" if entry is not None else "-",
            "exit": f"{exit_p:.5f}" if exit_p is not None else "-",
            "resultado": resultado,
        })
        e = f"{entry:.5f}" if entry is not None else "-"
        x = f"{exit_p:.5f}" if exit_p is not None else "-"
        print(f"  {hora} {asset:12s} {piso} ratio={ratio:.2f} dir={direccion or '-':4s}({source or '-':3s}) "
              f"entry={e} exit={x} -> {resultado}", flush=True)

    # 4) resumen
    total = len(filas)
    wins = sum(1 for f in filas if f["resultado"] == "WIN")
    losses = sum(1 for f in filas if f["resultado"] == "LOSS")
    draws = sum(1 for f in filas if f["resultado"] == "DRAW")
    sin_dir = sum(1 for f in filas if f["resultado"] == "SIN_DIR")
    no_data = sum(1 for f in filas if f["resultado"] in ("NO_ENTRY", "NO_EXIT"))
    pnl = 0.0
    for f in filas:
        if f["resultado"] == "WIN":
            pnl += f["payout"] / 100.0  # ganancia bruta de la opción (stake 1.0 se devuelve)
        elif f["resultado"] in ("LOSS", "DRAW"):
            pnl -= 1.0

    resumen = [
        "",
        "=" * 78,
        f"RESUMEN — {total} señales (stake 1.0, expiración {DURACION_SEC}s)",
        "-" * 78,
        f"  WIN : {wins}  ({100 * wins / total:.1f}%)",
        f"  LOSS: {losses}",
        f"  DRAW: {draws}",
        f"  SIN_DIR: {sin_dir} | SIN_DATOS: {no_data}",
        f"  P&L hipotético: {pnl:+.2f} unidades de stake",
        "",
        "Por piso:",
    ]
    for piso in ("P2", "P3"):
        fs = [f for f in filas if f["piso"] == piso]
        if not fs:
            continue
        w = sum(1 for f in fs if f["resultado"] == "WIN")
        p = sum(1 for f in fs if f["resultado"] in ("LOSS", "DRAW"))
        resumen.append(f"  {piso}: {len(fs)} señales | WIN {w} | LOSS/DRAW {p}")
    resumen.append("")

    # 5) guardar reporte y CSV de resultados
    reporte = OUT_DIR / "reporte_2026-08-10.txt"
    with open(reporte, "w", encoding="utf-8") as f:
        f.write("\n".join(resumen))
        f.write("\n")
        f.write(f"{'hora':9s} {'asset':12s} {'piso':4s} {'ratio':6s} {'payout':7s} {'dir':6s} {'src':4s} {'entry':12s} {'exit':12s} {'resultado':10s}\n")
        for r in filas:
            f.write(
                f"{r['hora']:9s} {r['asset']:12s} {r['piso']:4s} {r['ratio']:.2f}  {r['payout']:3d}%   "
                f"{r['direccion']:4s} {r['source']:3s} {r['entry']:>12s} {r['exit']:>12s} {r['resultado']:10s}\n"
            )
    print("\n".join(resumen))
    print(f"Reporte guardado en {reporte}", flush=True)

    await client.close()
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
