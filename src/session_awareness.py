"""Session awareness for trading session detection and threshold adjustment."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.config import (
    SESSION_AWARENESS_ENABLED,
    SESSION_ASIAN_MIN_SCORE,
    SESSION_LONDON_MIN_SCORE,
    SESSION_NEWYORK_MIN_SCORE,
    SESSION_OFF_HOURS_ENABLED,
    SESSION_OFFHOURS_MIN_SCORE,
)

# Session definitions (UTC hours)
SESSIONS = {
    "asian": {"start": 0, "end": 8, "min_score": SESSION_ASIAN_MIN_SCORE, "enabled": True},
    "london": {"start": 8, "end": 16, "min_score": SESSION_LONDON_MIN_SCORE, "enabled": True},
    "new_york": {"start": 16, "end": 21, "min_score": SESSION_NEWYORK_MIN_SCORE, "enabled": True},
    "off_hours": {"start": 21, "end": 24, "min_score": SESSION_OFFHOURS_MIN_SCORE, "enabled": SESSION_OFF_HOURS_ENABLED},
}


def detect_session(utc_hour: int | None = None) -> str:
    """Detectar la sesión actual a partir de la hora UTC.

    Devuelve 'asian', 'london', 'new_york' o 'off_hours'.
    Si utc_hour es None usa la hora UTC actual.
    """
    if utc_hour is None:
        utc_hour = datetime.now(timezone.utc).hour
    for name, cfg in SESSIONS.items():
        if cfg["start"] <= utc_hour < cfg["end"]:
            return name
    return "off_hours"


def get_session_config(session: str | None = None) -> dict:
    """Obtener la configuración de una sesión.

    Si session es None detecta la sesión actual.
    """
    if session is None:
        session = detect_session()
    return SESSIONS[session]


def should_block(session: str | None = None) -> bool:
    """Devuelve True si la sesión debe bloquear operaciones.

    Bloquea cuando off_hours tiene enabled=False o cuando la sesión
    tiene enabled=False.
    """
    cfg = get_session_config(session)
    return not cfg["enabled"]


def get_min_score(session: str | None = None) -> int:
    """Obtener el min_score efectivo para la sesión."""
    cfg = get_session_config(session)
    return cfg["min_score"]


def get_effective_min_score(default_min_score: int, session: str | None = None) -> int:
    """Devolver el min_score con-awareness de sesión.

    Si la awareness está deshabilitada retorna default_min_score.
    """
    if not SESSION_AWARENESS_ENABLED:
        return default_min_score
    return get_min_score(session)


def get_current_session_info() -> dict:
    """Devolver un dict con info de la sesión actual: session, min_score, enabled, blocked, hour_utc."""
    hour = datetime.now(timezone.utc).hour
    session = detect_session(hour)
    cfg = SESSIONS[session]
    return {
        "session": session,
        "min_score": cfg["min_score"],
        "enabled": cfg["enabled"],
        "blocked": should_block(session),
        "hour_utc": hour,
    }
