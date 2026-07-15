"""Persist hub bankroll settings across process restarts.

The bankroll fields in config.py are *unknowns* filled from the web UI
(Operación → Bankroll binarias → Guardar). This module is the disk bridge:

  hub form  →  data/hub_bankroll.json  →  config.* + BotRunner._config

Without this file a hub restart resets Massaniello to config.py fallbacks.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = _ROOT / "data" / "hub_bankroll.json"

# Keys written by the Operación → Bankroll card
BANKROLL_KEYS = (
    "massaniello_ops",
    "massaniello_wins",
    "massaniello_virtual_capital",
    "min_payout",
    "session_max_min",
)


def load_bankroll(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        out: dict[str, Any] = {}
        for k in BANKROLL_KEYS:
            if k in raw:
                out[k] = raw[k]
        return out
    except Exception as exc:
        log.warning("No se pudo leer bankroll hub %s: %s", path, exc)
        return {}


def save_bankroll(settings: dict[str, Any], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: settings[k] for k in BANKROLL_KEYS if k in settings}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info(
        "Bankroll hub persistido en %s → ops=%s ITM=%s capital=%s min_payout=%s",
        path.name,
        payload.get("massaniello_ops"),
        payload.get("massaniello_wins"),
        payload.get("massaniello_virtual_capital"),
        payload.get("min_payout"),
    )


def apply_bankroll_shape_to_manager(manager: Any, *, force: bool = False) -> None:
    """Push live config module ops/ITM onto manager when safe (no progress)."""
    import config as cfg

    played = int(getattr(manager, "wins", 0) or 0) + int(getattr(manager, "losses", 0) or 0)
    if played > 0 and not force:
        log.info(
            "Bankroll shape NO aplicado (sesión con progreso %dW/%dL) — se mantiene %d ops / %d ITM",
            getattr(manager, "wins", 0),
            getattr(manager, "losses", 0),
            getattr(manager, "operations", 0),
            getattr(manager, "expected_wins", 0),
        )
        return

    ops = int(cfg.MASSANIELLO_OPERATIONS)
    ew = int(cfg.MASSANIELLO_EXPECTED_WINS)
    if ew > ops:
        ew = ops
    manager.operations = ops
    manager.expected_wins = ew
    manager.session_max_min = int(cfg.SESSION_MAX_MIN)
    log.info(
        "Bankroll shape aplicado al manager: %d ops / %d ITM (desde config en vivo)",
        ops,
        ew,
    )
