"""System monitors: battery, power events.

Lifespan-scoped background tasks that watch OS-level conditions
and trigger graceful shutdown when critical thresholds are hit.

Uses Win32 GetSystemPowerStatus — zero new dependencies.
"""
from __future__ import annotations

import asyncio
import ctypes
import logging
import sys
from typing import Awaitable, Callable, Optional

log = logging.getLogger("system_monitor")

# ── Win32 GetSystemPowerStatus ──────────────────────────────────────────────

# https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-system_power_status
# typedef struct _SYSTEM_POWER_STATUS {
#   BYTE ACLineStatus;        // 0=offline, 1=online, 255=unknown
#   BYTE BatteryFlag;         // 1=HIGH, 2=LOW, 4=CRITICAL, 8=CHARGING, 128=NO_BATTERY
#   BYTE BatteryLifePercent;  // 0-100, 255=unknown
#   ...
# }
class _SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_int32),
        ("BatteryFullLifeTime", ctypes.c_int32),
    ]


_AC_ONLINE = 1
_BATTERY_CRITICAL = 4
_BATTERY_NO_BATTERY = 128
_PERCENT_UNKNOWN = 255


def get_battery_status() -> dict:
    """Return battery info dict. Works on Windows; returns safe defaults elsewhere."""
    if sys.platform != "win32":
        return {"available": False}
    try:
        status = _SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)) == 0:
            return {"available": False}
        pct = status.BatteryLifePercent
        return {
            "available": status.BatteryFlag & _BATTERY_NO_BATTERY == 0,
            "ac_online": status.ACLineStatus == _AC_ONLINE,
            "percent": pct if pct != _PERCENT_UNKNOWN else None,
            "critical": bool(status.BatteryFlag & _BATTERY_CRITICAL),
            "charging": bool(status.BatteryFlag & 8),
            "life_time_sec": status.BatteryLifeTime if status.BatteryLifeTime > 0 else None,
        }
    except Exception:
        return {"available": False}


# ── Async monitor ───────────────────────────────────────────────────────────

async def battery_monitor(
    *,
    threshold_pct: float = 2.0,
    poll_interval_sec: float = 30.0,
    on_critical: Callable[[], Awaitable[None]],
) -> None:
    """Poll battery status every *poll_interval_sec* seconds.

    Calls *on_critical()* once when battery drops to *threshold_pct* or below
    while on AC power is OFF (i.e. actually running on battery).

    Skips polling entirely when AC is online or when no battery is present.
    Calls *on_critical()* at most once — after that the task exits.
    """
    if sys.platform != "win32":
        log.info("Battery monitor: not Windows — skipped")
        return

    log.info(
        "Battery monitor started — threshold=%s%% poll=%ss",
        threshold_pct,
        poll_interval_sec,
    )
    triggered = False
    consecutive_critical = 0
    # Require 2 consecutive readings to avoid false positives from transient dips.
    REQUIRED_CONFIRMATIONS = 2

    while not triggered:
        await asyncio.sleep(poll_interval_sec)
        info = get_battery_status()

        # No battery present (desktop, VM, etc.) — nothing to do.
        if not info.get("available"):
            return

        # On AC power — battery is not at risk.
        if info.get("ac_online"):
            consecutive_critical = 0
            continue

        pct = info.get("percent")
        if pct is None:
            continue

        if pct <= threshold_pct or info.get("critical"):
            consecutive_critical += 1
            log.warning(
                "Battery CRITICAL: %s%% (confirmation %d/%d)",
                pct,
                consecutive_critical,
                REQUIRED_CONFIRMATIONS,
            )
            if consecutive_critical >= REQUIRED_CONFIRMATIONS:
                log.error(
                    "Battery ≤%s%% confirmed — triggering emergency shutdown",
                    threshold_pct,
                )
                triggered = True
                try:
                    await on_critical()
                except Exception as exc:
                    log.error("Battery monitor on_critical() failed: %s", exc)
        else:
            if consecutive_critical > 0:
                log.info("Battery recovered to %s%% — cancelling shutdown", pct)
            consecutive_critical = 0

    log.info("Battery monitor exiting")
