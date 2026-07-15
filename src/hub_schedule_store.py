"""Persist hub schedule / auto-full settings across process restarts.

Schedule fields in the Consola are *unknowns* filled from the web UI
(Consola → Configuración del bot → Guardar). This module is the disk bridge:

  hub form  →  data/hub_schedule.json  →  config.* + BotRunner._config

Without this file a hub restart resets schedule mode to manual defaults.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = _ROOT / "data" / "hub_schedule.json"

# Keys written by Consola → schedule / sesión block
SCHEDULE_KEYS = (
    "schedule_mode",
    "duration_min",
    "max_consecutive_sessions",
    "work_block_hours",
    "rest_hours",
    "max_sessions_per_day",
    "session_max_min",
)

DEFAULT_SCHEDULE: dict[str, Any] = {
    "schedule_mode": "manual",
    "duration_min": 5,
    "max_consecutive_sessions": 3,
    "work_block_hours": 2.0,
    "rest_hours": 1.0,
    "max_sessions_per_day": 0,
    "session_max_min": 60,
}


def duration_min_to_sec(duration_min: int | float) -> int:
    """Map user-facing minutes to order duration seconds (floor 60s)."""
    return max(60, int(duration_min) * 60)


def load_schedule(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        out: dict[str, Any] = {}
        for k in SCHEDULE_KEYS:
            if k in raw:
                out[k] = raw[k]
        return out
    except Exception as exc:
        log.warning("No se pudo leer schedule hub %s: %s", path, exc)
        return {}


def save_schedule(settings: dict[str, Any], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: settings[k] for k in SCHEDULE_KEYS if k in settings}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info(
        "Schedule hub persistido en %s → mode=%s duration_min=%s consec=%s "
        "work=%.1fh rest=%.1fh max_day=%s session_max=%s",
        path.name,
        payload.get("schedule_mode"),
        payload.get("duration_min"),
        payload.get("max_consecutive_sessions"),
        float(payload.get("work_block_hours", 0) or 0),
        float(payload.get("rest_hours", 0) or 0),
        payload.get("max_sessions_per_day"),
        payload.get("session_max_min"),
    )
