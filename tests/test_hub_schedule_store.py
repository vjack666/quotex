"""Hub schedule disk persistence + duration_min mapping."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hub_schedule_store import (
    DEFAULT_SCHEDULE,
    SCHEDULE_KEYS,
    duration_min_to_sec,
    load_schedule,
    save_schedule,
)


def test_save_and_load_schedule(tmp_path: Path):
    path = tmp_path / "hub_schedule.json"
    save_schedule(
        {
            "schedule_mode": "auto_full",
            "duration_min": 5,
            "max_consecutive_sessions": 3,
            "work_block_hours": 2.0,
            "rest_hours": 1.0,
            "max_sessions_per_day": 0,
            "session_max_min": 60,
            "ignored_key": "nope",
        },
        path=path,
    )
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "ignored_key" not in raw
    loaded = load_schedule(path)
    assert loaded["schedule_mode"] == "auto_full"
    assert loaded["duration_min"] == 5
    assert loaded["max_consecutive_sessions"] == 3
    assert loaded["work_block_hours"] == 2.0
    assert loaded["rest_hours"] == 1.0
    assert loaded["max_sessions_per_day"] == 0
    assert loaded["session_max_min"] == 60
    for k in SCHEDULE_KEYS:
        assert k in loaded


def test_load_missing_returns_empty(tmp_path: Path):
    assert load_schedule(tmp_path / "missing.json") == {}


def test_load_corrupt_returns_empty(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_schedule(path) == {}


def test_duration_min_to_sec_mapping():
    assert duration_min_to_sec(5) == 300
    assert duration_min_to_sec(1) == 60
    assert duration_min_to_sec(0) == 60  # floor
    assert duration_min_to_sec(10) == 600


def test_default_schedule_keys():
    for k in SCHEDULE_KEYS:
        assert k in DEFAULT_SCHEDULE
