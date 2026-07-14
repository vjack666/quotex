"""Logging helpers — keep console signal-to-noise high.

Normal mode (default): cycle headers, prefetch timing, accepted signals,
entries, wins/losses, session lifecycle.

Verbose mode (BOT_LOG_VERBOSE=1): per-asset rejects, phase markers, OB/MA
detail, progress ticks.
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from config import LOG_VERBOSE


def is_verbose() -> bool:
    return bool(LOG_VERBOSE)


def asset_detail(logger: logging.Logger, msg: str, *args: Any) -> None:
    """Per-asset chatter: INFO only when verbose, else DEBUG."""
    if LOG_VERBOSE:
        logger.info(msg, *args)
    else:
        logger.debug(msg, *args)


def format_reject_summary(counts: Counter[str], *, limit: int = 6) -> str:
    """Turn Counter of reject reasons into a short readable string."""
    if not counts:
        return "—"
    items = counts.most_common(limit)
    parts = [f"{reason}×{n}" for reason, n in items]
    extra = len(counts) - len(items)
    if extra > 0:
        parts.append(f"+{extra} más")
    return ", ".join(parts)


def short_reason(reason: str, *, max_len: int = 42) -> str:
    """Collapse long reject strings for cycle summaries."""
    text = (reason or "unknown").strip()
    # Drop asset-specific numbers noise where possible
    if "zona muy joven" in text.lower():
        return "zona joven"
    if "no rechaza la banda" in text.lower():
        return "M1 sin rechazo"
    if "rango roto" in text.lower():
        return "M15 roto"
    if "contra tendencia" in text.lower():
        return "contra M15"
    if "payout" in text.lower() and "<" in text:
        return "payout bajo"
    if "demasiado joven" in text.lower():
        return "zona joven"
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text
