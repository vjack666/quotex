"""Tests for compact bot logging helpers."""
from __future__ import annotations

import logging
import sys
from collections import Counter
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bot_logging import asset_detail, format_reject_summary, short_reason
import config as cfg


def test_log_verbose_default_is_off():
    assert cfg.LOG_VERBOSE is False
    assert cfg.SCAN_PHASE_LOG is False
    assert cfg.SCAN_PROGRESS_EVERY == 0


def test_short_reason_collapses_noise():
    assert short_reason("zona muy joven (2 < 3 velas M5)") == "zona joven"
    assert "M1" in short_reason("M1 no rechaza la banda (cierra fuera)")
    assert short_reason("M15 rango roto: no operar rebotes") == "M15 roto"


def test_format_reject_summary():
    c = Counter({"F:zona joven": 8, "F:M1 sin rechazo": 12, "A:payout bajo": 5})
    text = format_reject_summary(c)
    assert "M1 sin rechazo×12" in text
    assert "zona joven×8" in text


def test_asset_detail_uses_debug_when_not_verbose(caplog):
    logger = logging.getLogger("test_bot_logging_asset")
    with caplog.at_level(logging.DEBUG, logger="test_bot_logging_asset"):
        asset_detail(logger, "skip %s", "EURUSD")
    assert any("skip EURUSD" in r.message for r in caplog.records)
    # In default (non-verbose) mode the record level is DEBUG
    matching = [r for r in caplog.records if "skip EURUSD" in r.message]
    assert matching
    assert matching[0].levelno == logging.DEBUG
