"""Utilidades de temporización del loop principal."""
from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Optional

from config import ALIGN_SCAN_TO_CANDLE, SCAN_INTERVAL_SEC, SCAN_LEAD_SEC, TF_5M

log = logging.getLogger("consolidation_bot")


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

    end_at = time.monotonic() + total
    last_logged_sec: Optional[int] = None
    aborted = False
    try:
        while True:
            if should_abort is not None and should_abort():
                aborted = True
                log.info("⏹ %s interrumpido (sesión finalizada)", label)
                break
            remaining = max(0.0, end_at - time.monotonic())
            rem_sec = int(remaining + 0.999)
            if rem_sec >= 60:
                t_str = f"{rem_sec // 60}m{rem_sec % 60:02d}s"
            else:
                t_str = f"{rem_sec:>3d}s"
            sys.stdout.write(f"\r[INFO] {label} en {t_str}   ")
            sys.stdout.flush()

            if rem_sec != last_logged_sec and (rem_sec % 10 == 0 or rem_sec <= 5):
                log.info("⏳ %s en %s", label, t_str.strip())
                last_logged_sec = rem_sec

            if remaining <= 0.0:
                break
            await asyncio.sleep(min(1.0, remaining))
    finally:
        sys.stdout.write("\r" + (" " * 100) + "\r\n")
        sys.stdout.flush()
    return aborted


def seconds_until_next_scan(now_ts: Optional[float] = None) -> float:
    now = time.time() if now_ts is None else float(now_ts)
    if ALIGN_SCAN_TO_CANDLE:
        next_open = ((int(now) // TF_5M) + 1) * TF_5M
        target_scan = next_open - SCAN_LEAD_SEC
        if target_scan <= now:
            target_scan += TF_5M
        return max(1.0, target_scan - now)
    return max(5.0, SCAN_INTERVAL_SEC)