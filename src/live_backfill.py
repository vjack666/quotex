"""LiveBackfill — descarga velas históricas del broker en los huecos entre scans.

Corre DENTRO del proceso del bot usando el MISMO WebSocket (regla de oro: socket
único; pyquotex usa un buzón compartido para velas, así que NUNCA debe haber dos
coroutines pidiendo velas a la vez). Por eso este módulo NO es una task
independiente: el main loop lo invoca con `work_window()` durante la espera
entre ciclos, y devuelve el control antes del próximo scan. Cero carrera.

Patrón de descarga heredado de
tools/quotex-historical-data/replay_edificio_2026-08-10.py (cargar_o_descargar):
get_candles_deep + cache CSV por par (asset, tf) + dedupe por ts.

Prioridad: activos que entraron a P1 (de la caja negra más reciente); si no hay
DB o está vacía, una lista por defecto de OTC comunes.
"""

from __future__ import annotations

import asyncio
import csv
import glob
import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple

log = logging.getLogger("live_backfill")

ROOT = Path(__file__).resolve().parent.parent
BACKFILL_DIR = ROOT / "tools" / "quotex-historical-data" / "backfill"
ESTADO_PATH = BACKFILL_DIR / "estado.json"

# (timeframe_sec, dias_ventana) — ventanas chicas para no pisar el scan.
TFS: List[Tuple[int, int]] = [
    (60, 1),    # M1: 1 día (warmup estocástico alcanza)
    (300, 2),   # M5: 2 días
    (900, 3),   # M15: 3 días
]

# Fallback si no hay caja negra con datos.
DEFAULT_ASSETS: List[str] = [
    "NZDUSD_otc", "NZDCAD_otc", "USDINR_otc", "USDPHP_otc", "AVAUSD_otc",
    "BCHUSD_otc", "BNBUSD_otc", "BRLUSD_otc", "DASUSD_otc", "GBPNZD_otc",
    "AUDNZD_otc", "CADCHF_otc", "ZECUSD_otc", "DOTUSD_otc", "ETCUSD_otc",
    "USDARS_otc", "LTCUSD_otc", "USDBDT_otc", "SOLUSD_otc", "USDIDR_otc",
    "TONUSD_otc", "EURNZD_otc", "USDNGN_otc", "USCrude_otc", "XRPUSD_otc",
    "AXSUSD_otc", "ETHUSD_otc", "AUDUSD_otc", "EURCHF_otc", "EURJPY_otc",
]

# Máximo tiempo por par y margen de seguridad antes del próximo scan.
TIMEOUT_PAR_SEC = 100.0
# Colchón mínimo para no pisar el scan del bot. El main loop NUNCA descuenta
# este margen (lo hace work_window internamente): así el margen se aplica una
# sola vez, sin importar quién invoque work_window.
MARGEN_PRE_SCAN_SEC = 3.0
# Intentos antes de descartar un par imposible (activo no listado, etc.).
MAX_REINTENTOS_PAR = 3


def _pares_desde_caja_negra() -> List[str]:
    """Activos PISO1_SNAPSHOT de la caja negra más reciente (si existe)."""
    try:
        dbs = sorted(glob.glob(str(ROOT / "data" / "db" / "black_box_strat_*.db")))
        if not dbs:
            return []
        import sqlite3
        con = sqlite3.connect(dbs[-1])
        try:
            rows = con.execute(
                "SELECT DISTINCT asset FROM scan_candidates "
                "WHERE decision='PISO1_SNAPSHOT' AND asset IS NOT NULL"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001 — fallback silencioso
        log.debug("No se pudo leer caja negra para backfill: %s", exc)
        return []


class LiveBackfill:
    """Descarga por pares (asset, tf) en ventanas entre scans del bot."""

    def __init__(
        self,
        client: Any,
        out_dir: Path = BACKFILL_DIR,
        assets: Optional[List[str]] = None,
    ) -> None:
        self.client = client
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._estado_path = self.out_dir / "estado.json"
        self._hechos: set[str] = set()
        self._fallidos: dict[str, int] = {}
        self._progreso: dict[str, dict] = {}  # clave asset|tf -> {"next_end": ts}
        self._pendientes: List[Tuple[str, int]] = []
        self._cargar_estado()
        self._armar_cola(assets)
        self._total_inicial = len(self._pendientes)

    # ── Setup ─────────────────────────────────────────────────────────────

    def _cargar_estado(self) -> None:
        try:
            if self._estado_path.exists():
                with open(self._estado_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._hechos = set(data.get("hechos", []))
                self._fallidos = {k: int(v) for k, v in data.get("fallidos", {}).items()}
                self._progreso = data.get("progreso", {}) or {}
        except Exception as exc:  # noqa: BLE001
            log.warning("[BACKFILL] estado.json corrupto, arrancando limpio: %s", exc)
            self._hechos = set()
            self._fallidos = {}
            self._progreso = {}

    def _guardar_estado(self) -> None:
        try:
            tmp = self._estado_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "hechos": sorted(self._hechos),
                        "fallidos": self._fallidos,
                        "progreso": self._progreso,
                    },
                    f, ensure_ascii=False, indent=1,
                )
            tmp.replace(self._estado_path)
        except Exception as exc:  # noqa: BLE001
            log.warning("[BACKFILL] no se pudo guardar estado: %s", exc)

    def _armar_cola(self, assets: Optional[List[str]]) -> None:
        activos = list(dict.fromkeys(assets or _pares_desde_caja_negra() or DEFAULT_ASSETS))
        for asset in activos:
            for tf, dias in TFS:
                clave = f"{asset}|{tf}"
                if clave in self._hechos:
                    continue
                self._pendientes.append((asset, tf))
        log.info(
            "[BACKFILL] cola lista: %d activos → %d pares pendientes "
            "(M1=1d, M5=2d, M15=3d)",
            len(activos), len(self._pendientes),
        )

    # ── API para el main loop ────────────────────────────────────────────

    def quedan_pares(self) -> bool:
        return bool(self._pendientes)

    def progreso(self) -> dict:
        return {
            "hechos": len(self._hechos),
            "pendientes": len(self._pendientes),
            "total_inicial": self._total_inicial,
            "fallidos": self._fallidos,
        }

    async def work_window(self, max_seconds: float) -> None:
        """Descarga pares durante la ventana libre entre scans.

        SOLO debe llamarse desde el main loop (nunca como task suelta):
        mientras corre, el socket está ocupado. work_window descuenta
        MARGEN_PRE_SCAN_SEC internamente (el caller NO debe hacerlo) y
        devuelve el control antes de que el loop vuelva a escanear.

        Resultados de _descargar_par:
          - "ok": CSV completo -> pasa a hechos.
          - "progreso": hubo avance pero la ventana se acabó -> se guarda
            next_end y el par queda para la próxima ventana SIN contar fallo.
          - "error": fallo real (activo no listado, sin historia) -> rotar con
            contador; tras MAX_REINTENTOS_PAR se descarta definitivamente.
        """
        deadline = time.monotonic() + max(max_seconds, 0.0)
        while self._pendientes:
            remaining = deadline - time.monotonic()
            if remaining <= MARGEN_PRE_SCAN_SEC:
                break
            asset, tf = self._pendientes[0]
            clave = f"{asset}|{tf}"
            resultado = await self._descargar_par(asset, tf, max_sec=remaining)
            if resultado == "ok":
                self._pendientes.pop(0)
                self._hechos.add(clave)
                self._progreso.pop(clave, None)
                self._guardar_estado()
                continue
            if resultado == "error":
                reintentos = self._fallidos.get(clave, 0)
                if reintentos >= MAX_REINTENTOS_PAR:
                    # Descartar definitivamente: no rotar infinitamente un par
                    # imposible (activo no listado, sin historia, etc.).
                    log.info(
                        "[BACKFILL] %s tf=%s: %d intentos fallidos — descartado",
                        asset, tf, reintentos,
                    )
                    self._pendientes.pop(0)
                    self._progreso.pop(clave, None)
                    self._guardar_estado()
                else:
                    # Reintentar en una ventana futura sin bloquear el resto.
                    self._pendientes.append(self._pendientes.pop(0))
                    await asyncio.sleep(0.5)
            else:  # "progreso": no cuenta como fallo, retoma en la próxima ventana
                self._pendientes.append(self._pendientes.pop(0))
                if time.monotonic() >= deadline:
                    break

    # ── Descarga ─────────────────────────────────────────────────────────

    def _csv_path(self, asset: str, tf: int) -> Path:
        return self.out_dir / f"{asset}_{tf}s.csv"

    async def _descargar_par(self, asset: str, tf: int, max_sec: float) -> str:
        """Devuelve "ok" (CSV completo), "progreso" (ventana corta, hay next_end)
        o "error" (fallo real: activo no listado / sin historia)."""
        path = self._csv_path(asset, tf)
        if path.exists():
            return "ok"
        dias = next((d for (t, d) in TFS if t == tf), 1)
        total_deseadas = max(1, int(86400 * dias / tf))
        # El broker responde ~200 velas por request; paginamos hacia atrás.
        # El LOCK de connection.py serializa con el HTF scanner / scan del bot:
        # los buzones compartidos de pyquotex no distinguen activo ni tf, y dos
        # pedidos en vuelo se roban respuestas (causa raíz 2026-07-28, y el
        # colgado que se vio al correr el backfill SIN el lock).
        from connection import _CANDLES_FETCH_LOCK  # import local: evita ciclo
        chunk = 200
        timeout = min(TIMEOUT_PAR_SEC, max(5.0, max_sec - MARGEN_PRE_SCAN_SEC))
        deadline = time.monotonic() + timeout
        velas: dict[int, dict] = {}
        # Resumible: si la ventana anterior se cortó a mitad, retomamos desde
        # el ts más viejo ya bajado (next_end) en vez de volver a pedir todo.
        clave = f"{asset}|{tf}"
        prog = self._progreso.get(clave) or {}
        end_time = prog.get("next_end") or time.time()
        try:
            while len(velas) < total_deseadas and time.monotonic() < deadline:
                offset = chunk
                remaining = deadline - time.monotonic()
                if remaining <= MARGEN_PRE_SCAN_SEC:
                    break
                async with _CANDLES_FETCH_LOCK:
                    datos = await asyncio.wait_for(
                        self.client.get_candles(asset, end_time, offset, tf),
                        timeout=min(30.0, max(2.0, remaining)),
                    )
                if not datos:
                    # El broker no tiene más historia hacia atrás.
                    break
                n_bajadas = 0
                for c in datos:
                    if c.get("time") and c.get("close") is not None:
                        velas[int(c["time"])] = c
                        n_bajadas += 1
                # Retroceder al hueco anterior para la siguiente página.
                # OJO: el broker devuelve ~199 velas por request (no 200):
                # por eso NO cortamos con n_bajadas < offset — solo con vacío.
                ts_min = min(int(c["time"]) for c in datos if c.get("time"))
                end_time = ts_min - tf
                if n_bajadas == 0:
                    break
            # get_candles deja el stream abierto; cerrarlo para no ensuciar el
            # buzón del scan (el HTF/scan piden velas con el MISMO client).
            try:
                await self.client.stop_candles_stream(asset)
            except Exception:
                pass
        except asyncio.TimeoutError:
            log.info(
                "[BACKFILL] %s tf=%s: request expiró (ventana corta) — retoma próximo ciclo",
                asset, tf,
            )
            return self._guardar_progreso(asset, tf, velas, end_time)
        except Exception as exc:  # noqa: BLE001 — patrón replay: no tumba el bot
            log.warning("[BACKFILL] %s tf=%s: %s", asset, tf, exc)
            self._marcar_fallido(asset, tf, str(exc)[:60])
            return "error"
        if not velas:
            log.info("[BACKFILL] %s tf=%s: vacío — descartado", asset, tf)
            self._marcar_fallido(asset, tf, "empty")
            return "error"
        if len(velas) < total_deseadas:
            # No alcanzó la ventana completa (días pedidos): guardar progreso
            # y retomar en una ventana futura. NO cuenta como fallo.
            log.info(
                "[BACKFILL] %s tf=%s: %d/%d velas — continúa en próximo ciclo",
                asset, tf, len(velas), total_deseadas,
            )
            return self._guardar_progreso(asset, tf, velas, end_time)
        unicos: List[dict] = []
        for v_time in sorted(velas):
            c = velas[v_time]
            unicos.append({
                "time": int(c["time"]),
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "ticks": int(c.get("ticks") or 0),
            })
        try:
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["time", "open", "high", "low", "close", "ticks"])
                writer.writeheader()
                writer.writerows(unicos)
            tmp.replace(path)
        except Exception as exc:  # noqa: BLE001
            log.warning("[BACKFILL] %s tf=%s: no se pudo escribir CSV: %s", asset, tf, exc)
            self._marcar_fallido(asset, tf, "csv_write")
            return "error"
        log.info(
            "[BACKFILL] %s tf=%s -> %d velas (%s)",
            asset, tf, len(unicos), path.name,
        )
        return "ok"

    def _guardar_progreso(self, asset: str, tf: int, velas: dict, end_time: float) -> str:
        """Persiste el avance de una descarga incompleta y devuelve "progreso"."""
        clave = f"{asset}|{tf}"
        if not velas:
            # No se bajó NADA en esta pasada pero tampoco es un error duro
            # (ej. request expiró): guardar igual para no entrar en bucle.
            self._progreso[clave] = {"next_end": end_time}
        else:
            self._progreso[clave] = {"next_end": end_time}
        self._guardar_estado()
        return "progreso"

    def _marcar_fallido(self, asset: str, tf: int, razon: str) -> None:
        clave = f"{asset}|{tf}"
        self._fallidos[clave] = self._fallidos.get(clave, 0) + 1
