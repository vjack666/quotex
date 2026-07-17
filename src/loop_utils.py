"""Utilidades de temporización del loop principal."""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, TextIO

from config import ALIGN_SCAN_TO_CANDLE, SCAN_INTERVAL_SEC, SCAN_LEAD_SEC, TF_5M

log = logging.getLogger("consolidation_bot")

# Live clock goes to stderr so logging StreamHandler newlines on stdout
# cannot push the countdown onto a new line every second.
_VT_ENABLED = False


def _format_remaining(rem_sec: int) -> str:
    if rem_sec >= 60:
        return f"{rem_sec // 60}m{rem_sec % 60:02d}s"
    return f"{rem_sec:2d}s"


def _enable_windows_vt(stream: TextIO) -> None:
    """Enable ANSI escape processing on Windows consoles (Win10+)."""
    global _VT_ENABLED
    if _VT_ENABLED or sys.platform != "win32":
        return
    try:
        import ctypes

        # Prefer the real console handle behind TextIO wrappers.
        kernel32 = ctypes.windll.kernel32
        # STD_ERROR_HANDLE = -12 (countdown writes to stderr)
        handle = kernel32.GetStdHandle(-12)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        if mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING:
            _VT_ENABLED = True
            return
        if kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING):
            _VT_ENABLED = True
    except Exception:
        pass


def _countdown_stream() -> Optional[TextIO]:
    """Stream for in-place clock updates (must be a real TTY)."""
    for candidate in (getattr(sys, "__stderr__", None), sys.stderr, getattr(sys, "__stdout__", None), sys.stdout):
        if candidate is None:
            continue
        try:
            if candidate.isatty():
                return candidate
        except Exception:
            continue
    return None


def _terminal_cols(stream: TextIO) -> int:
    try:
        cols = int(shutil.get_terminal_size(fallback=(80, 24)).columns)
    except Exception:
        cols = 80
    # Leave 1 col margin so the line never wraps (wrap = looks like multi-line spam).
    return max(20, min(cols - 1, 120))


def _write_countdown_line(stream: TextIO, text: str) -> None:
    """Overwrite the current terminal line in place (clock-style)."""
    _enable_windows_vt(stream)
    cols = _terminal_cols(stream)
    # Truncate so one logical line cannot wrap to the next row.
    body = text if len(text) <= cols else text[: max(0, cols - 1)]
    try:
        if _VT_ENABLED or sys.platform != "win32":
            # CR + clear-to-end-of-line + text (single row, number changes only).
            stream.write(f"\r\033[K{body}")
        else:
            # Fallback: CR + pad with spaces to wipe previous longer text.
            stream.write(f"\r{body:<{cols}}")
        stream.flush()
    except Exception:
        pass


def _clear_countdown_line(stream: TextIO) -> None:
    try:
        if _VT_ENABLED or sys.platform != "win32":
            stream.write("\r\033[K")
        else:
            cols = _terminal_cols(stream)
            stream.write("\r" + (" " * cols) + "\r")
        stream.flush()
    except Exception:
        pass


async def sleep_with_inline_countdown(
    wait_seconds: float,
    label: str,
    *,
    should_abort=None,
) -> bool:
    """Sleep with countdown. Returns True if aborted early via should_abort()."""
    total = max(0.0, float(wait_seconds))
    if total <= 0.0:
        return False

    total_int = int(total + 0.999)
    # One durable line for file + console; no per-second log spam.
    log.info("⏳ %s | wait=%ss", label, total_int)

    end_at = time.monotonic() + total
    aborted = False
    tty = _countdown_stream()
    try:
        while True:
            if should_abort is not None and should_abort():
                aborted = True
                if tty is not None:
                    _clear_countdown_line(tty)
                log.info("⏹ %s interrumpido (sesión finalizada)", label)
                break
            remaining = max(0.0, end_at - time.monotonic())
            if tty is not None:
                rem_sec = int(remaining + 0.999)
                t_str = _format_remaining(rem_sec)
                _write_countdown_line(tty, f"⏳ {label}  {t_str}")

            if remaining <= 0.0:
                break
            await asyncio.sleep(min(1.0, remaining))
    finally:
        # Clear in place; next real log owns the newline (no forced blank line).
        if tty is not None:
            _clear_countdown_line(tty)
    return aborted


def open_trades_dict(bot) -> dict:
    """Return bot.trades only when it is a non-empty real dict."""
    trades = getattr(bot, "trades", None)
    if not isinstance(trades, dict) or not trades:
        return {}
    return trades


def _trade_remaining_sec(trade: object, now: float) -> float:
    opened = float(getattr(trade, "opened_at", now) or now)
    duration = float(getattr(trade, "duration_sec", 0) or 0)
    return max(0.0, opened + duration - now)


def _format_open_trades_summary(trades: dict, now: float) -> str:
    parts: list[str] = []
    for key, trade in trades.items():
        asset = getattr(trade, "asset", None) or (
            key.split("#", 1)[0] if isinstance(key, str) and "#" in key else key
        )
        direction = str(getattr(trade, "direction", "?")).upper()
        rem = int(_trade_remaining_sec(trade, now) + 0.999)
        dur = int(getattr(trade, "duration_sec", 0) or 0)
        if dur > 0:
            parts.append(f"{asset} {direction} {dur}s ~{rem}s left")
        else:
            parts.append(f"{asset} {direction} ~{rem}s")
    return " | ".join(parts)


def _min_trade_remaining_sec(trades: dict, now: float) -> float:
    if not trades:
        return 0.0
    return min(_trade_remaining_sec(t, now) for t in trades.values())


def _primary_trade_label(trades: dict) -> str:
    parts: list[str] = []
    for asset, trade in list(trades.items())[:2]:
        direction = str(getattr(trade, "direction", "?")).upper()
        parts.append(f"{asset} {direction}")
    return " ".join(parts)


async def wait_while_trade_open(bot) -> None:
    """Quiet wait while bot has open trades (no scan / stats spam).

    Logs once at start and once when trades clear. TTY gets a single-line
    countdown; non-TTY stays silent between those two durable logs.
    """
    trades = open_trades_dict(bot)
    if not trades:
        return

    now = time.time()
    summary = _format_open_trades_summary(trades, now)
    log.info("⏳ En espera de finalizar trade | %s", summary)

    tty = _countdown_stream()
    last_overtime_debug = 0.0
    last_conn_check = 0.0
    try:
        while True:
            open_trades = open_trades_dict(bot)
            if not open_trades:
                break
            now = time.time()
            remaining = _min_trade_remaining_sec(open_trades, now)

            # FIX B: the main loop's ensure_connection() only runs at the TOP of
            # each scan cycle, but we sit inside wait_while_trade_open (via
            # continue) for the whole trade lifetime. If the WS drops while we
            # wait (idle-timeout / Cloudflare), the background resolve tasks loop
            # on a dead socket and the trade never pops -> permanent hang.
            # Restore the shared socket periodically so resolution can finish.
            if now - last_conn_check >= 15.0:
                last_conn_check = now
                ensure_fn = getattr(bot, "ensure_connection", None)
                if ensure_fn is not None:
                    try:
                        await ensure_fn()
                    except Exception:
                        pass

            if tty is not None:
                if remaining > 0:
                    t_str = _format_remaining(int(remaining + 0.999))
                else:
                    t_str = "..."
                label = _primary_trade_label(open_trades)
                _write_countdown_line(
                    tty, f"⏳ En espera de finalizar trade  {t_str}  {label}"
                )

            if remaining > 0:
                await asyncio.sleep(min(1.0, remaining))
            else:
                # Broker lag past duration: quiet poll, debug at most every 10s.
                if now - last_overtime_debug >= 10.0:
                    log.debug(
                        "Trade still open past duration — waiting broker resolve…",
                    )
                    last_overtime_debug = now
                await asyncio.sleep(5.0)
    finally:
        if tty is not None:
            _clear_countdown_line(tty)

    log.info("✅ Trade finalizado — reanudando escaneo")


def seconds_until_next_scan(now_ts: Optional[float] = None) -> float:
    """Seconds to wait until the next scan trigger.

    When ALIGN_SCAN_TO_CANDLE is True:
    - SCAN_LEAD_SEC <= 0: fire exactly at the 5m candle open (phase==0 → 0.0).
    - SCAN_LEAD_SEC > 0: fire SCAN_LEAD_SEC seconds before the next open.
    When False: fixed SCAN_INTERVAL_SEC (min 5s).
    """
    now = time.time() if now_ts is None else float(now_ts)
    if not ALIGN_SCAN_TO_CANDLE:
        return max(5.0, SCAN_INTERVAL_SEC)

    phase = int(now) % TF_5M
    current_open = int(now) - phase
    next_open = current_open + TF_5M

    if SCAN_LEAD_SEC <= 0:
        # Exact open: scan immediately when already at phase 0.
        if phase == 0:
            return 0.0
        return max(0.0, next_open - now)

    # Legacy pre-open lead: target = next_open - lead; roll forward if past.
    target = next_open - SCAN_LEAD_SEC
    if target <= now:
        target = next_open + TF_5M - SCAN_LEAD_SEC
    return max(0.0, target - now)


# ── ProcessPool global para FASE 3 del scanner (parallel_scan_fase3) ──
# Se crea una vez al arrancar y se reusa entre ciclos (R2). Dimensionado a
# la mitad de los núcleos para no fundir la máquina. Degrada a None si no
# puede crearse (test mode / sin pickle) → el scan cae a serial (R6).
_SCAN_POOL: Optional[ProcessPoolExecutor] = None


def scan_pool_workers() -> int:
    """Workers = 50% de los núcleos (mínimo 1)."""
    return max(1, (os.cpu_count() or 1) // 2)


def init_scan_pool() -> None:
    """Crea el ProcessPoolExecutor global. Idempotente (no recrea si ya existe)."""
    global _SCAN_POOL
    if _SCAN_POOL is not None:
        return
    try:
        _SCAN_POOL = ProcessPoolExecutor(max_workers=scan_pool_workers())
        log.info("🧵 Scan pool listo: %d workers (50%% de %d núcleos).",
                 scan_pool_workers(), os.cpu_count() or 1)
    except Exception as exc:  # pragma: no cover - entorno sin fork/pickle
        _SCAN_POOL = None
        log.warning("⚠ No se pudo crear scan pool (%s) — FASE 3 va en serial.", exc)


def get_scan_pool() -> Optional[ProcessPoolExecutor]:
    """Devuelve el pool global o None (degradación serial, R6)."""
    return _SCAN_POOL


def shutdown_scan_pool() -> None:
    """Cierra el pool global si existe. Seguro llamar varias veces."""
    global _SCAN_POOL
    if _SCAN_POOL is not None:
        try:
            _SCAN_POOL.shutdown(wait=False)
        except Exception:
            pass
        _SCAN_POOL = None

