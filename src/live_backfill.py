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
MARGEN_PRE_SCAN_SEC = 10.0


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
        except Exception as exc:  # noqa: BLE001
            log.warning("[BACKFILL] estado.json corrupto, arrancando limpio: %s", exc)
            self._hechos = set()
            self._fallidos = {}

    def _guardar_estado(self) -> None:
        try:
            tmp = self._estado_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {"hechos": sorted(self._hechos), "fallidos": self._fallidos},
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
        mientras corre, el socket está ocupado. Devuelve el control con
        margen antes de que el loop vuelva a escanear.
        """
        deadline = time.monotonic() + max(max_seconds, 0.0)
        while self._pendientes:
            remaining = deadline - time.monotonic()
            if remaining <= MARGEN_PRE_SCAN_SEC:
                break
            asset, tf = self._pendientes[0]
            ok = await self._descargar_par(asset, tf, max_sec=remaining)
            if ok:
                self._pendientes.pop(0)
                self._hechos.add(f"{asset}|{tf}")
                self._guardar_estado()
            else:
                # No se pudo (timeout/error): rotar al final para reintentar
                # en una ventana futura y no bloquear el resto de la cola.
                self._pendientes.append(self._pendientes.pop(0))
                # Pequeño respiro entre reintentos de pares distintos.
                await asyncio.sleep(0.5)
                if time.monotonic() >= deadline:
                    break

    # ── Descarga ─────────────────────────────────────────────────────────

    def _csv_path(self, asset: str, tf: int) -> Path:
        return self.out_dir / f"{asset}_{tf}s.csv"

    async def _descargar_par(self, asset: str, tf: int, max_sec: float) -> bool:
        path = self._csv_path(asset, tf)
        if path.exists():
            return True
        dias = next((d for (t, d) in TFS if t == tf), 1)
        segundos = int(86400 * dias)
        timeout = min(TIMEOUT_PAR_SEC, max(5.0, max_sec - MARGEN_PRE_SCAN_SEC))
        datos = None
        try:
            # API del venv del bot (pyquotex clásica):
            #   get_candles(asset, end_from_time, offset, period)
            # end_from_time=ahora, offset=n velas hacia atrás, period=segundos.
            offset = max(1, int(segundos / tf))
            datos = await asyncio.wait_for(
                self.client.get_candles(asset, time.time(), offset, tf),
                timeout=timeout,
            )
            # get_candles descarta la vela en formación (calculate_candles
            # hace candles[:-1]); si dejó el stream abierto, lo cerramos para
            # no ensuciar el buzón del scan.
            try:
                await self.client.stop_candles_stream(asset)
            except Exception:
                pass
        except AttributeError:
            # pyquotex más nueva (replay 10/08): get_candles_deep(asset, seg, tf)
            try:
                datos = await asyncio.wait_for(
                    self.client.get_candles_deep(asset, segundos, tf),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                log.info("[BACKFILL] %s tf=%s: timeout (ventana corta) — reintento en próximo ciclo", asset, tf)
                self._marcar_fallido(asset, tf, "timeout")
                return False
            except Exception as exc:  # noqa: BLE001 — patrón replay: no tumba el bot
                log.warning("[BACKFILL] %s tf=%s: %s", asset, tf, exc)
                self._marcar_fallido(asset, tf, str(exc)[:60])
                return False
        except asyncio.TimeoutError:
            log.info("[BACKFILL] %s tf=%s: timeout (ventana corta) — reintento en próximo ciclo", asset, tf)
            self._marcar_fallido(asset, tf, "timeout")
            return False
        except Exception as exc:  # noqa: BLE001 — patrón replay: no tumba el bot
            log.warning("[BACKFILL] %s tf=%s: %s", asset, tf, exc)
            self._marcar_fallido(asset, tf, str(exc)[:60])
            return False
        if not datos:
            log.info("[BACKFILL] %s tf=%s: vacío — descartado", asset, tf)
            self._marcar_fallido(asset, tf, "empty")
            return False
        velas = [
            {
                "time": int(c["time"]),
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "ticks": int(c.get("ticks") or 0),
            }
            for c in datos
            if c.get("time") and c.get("close") is not None
        ]
        velas.sort(key=lambda c: c["time"])
        unicos: List[dict] = []
        for v in velas:
            if not unicos or unicos[-1]["time"] != v["time"]:
                unicos.append(v)
        if not unicos:
            log.info("[BACKFILL] %s tf=%s: sin velas válidas — descartado", asset, tf)
            self._marcar_fallido(asset, tf, "no_valid")
            return False
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
            return False
        log.info(
            "[BACKFILL] %s tf=%s -> %d velas (%s)",
            asset, tf, len(unicos), path.name,
        )
        return True

    def _marcar_fallido(self, asset: str, tf: int, razon: str) -> None:
        clave = f"{asset}|{tf}"
        self._fallidos[clave] = self._fallidos.get(clave, 0) + 1
