"""Tests para el módulo de session awareness."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.session_awareness import (
    SESSIONS,
    detect_session,
    get_current_session_info,
    get_effective_min_score,
    get_min_score,
    get_session_config,
    should_block,
)


# ── detect_session: hours ──────────────────────────────────────────────

class TestDetectSessionHours:
    def test_hour_4_returns_asian(self):
        assert detect_session(4) == "asian"

    def test_hour_12_returns_london(self):
        assert detect_session(12) == "london"

    def test_hour_18_returns_new_york(self):
        assert detect_session(18) == "new_york"

    def test_hour_22_returns_off_hours(self):
        assert detect_session(22) == "off_hours"


# ── detect_session: exact boundaries ───────────────────────────────────

class TestDetectSessionBoundaries:
    def test_hour_0_returns_asian(self):
        assert detect_session(0) == "asian"

    def test_hour_8_returns_london(self):
        assert detect_session(8) == "london"

    def test_hour_16_returns_new_york(self):
        assert detect_session(16) == "new_york"

    def test_hour_21_returns_off_hours(self):
        assert detect_session(21) == "off_hours"


# ── get_min_score ──────────────────────────────────────────────────────

class TestGetMinScore:
    def test_asian_score(self):
        assert get_min_score("asian") == SESSIONS["asian"]["min_score"]

    def test_london_score(self):
        assert get_min_score("london") == SESSIONS["london"]["min_score"]

    def test_new_york_score(self):
        assert get_min_score("new_york") == SESSIONS["new_york"]["min_score"]

    def test_off_hours_score(self):
        assert get_min_score("off_hours") == SESSIONS["off_hours"]["min_score"]


# ── should_block ───────────────────────────────────────────────────────

class TestShouldBlock:
    def test_off_hours_disabled_blocks(self):
        assert should_block("off_hours") is True

    def test_london_enabled_does_not_block(self):
        assert should_block("london") is False

    def test_asian_enabled_does_not_block(self):
        assert should_block("asian") is False

    def test_new_york_enabled_does_not_block(self):
        assert should_block("new_york") is False


# ── get_effective_min_score ────────────────────────────────────────────

class TestGetEffectiveMinScore:
    def test_awareness_enabled_returns_session_score(self):
        result = get_effective_min_score(60, "asian")
        assert result == SESSIONS["asian"]["min_score"]

    def test_awareness_disabled_returns_default(self):
        with patch("src.session_awareness.SESSION_AWARENESS_ENABLED", False):
            result = get_effective_min_score(60, "asian")
            assert result == 60

    def test_awareness_disabled_returns_default_for_london(self):
        with patch("src.session_awareness.SESSION_AWARENESS_ENABLED", False):
            result = get_effective_min_score(70, "london")
            assert result == 70


# ── get_current_session_info ───────────────────────────────────────────

class TestGetCurrentSessionInfo:
    def test_returns_all_keys(self):
        info = get_current_session_info()
        assert "session" in info
        assert "min_score" in info
        assert "enabled" in info
        assert "blocked" in info
        assert "hour_utc" in info

    def test_session_matches_hour(self):
        info = get_current_session_info()
        detected = detect_session(info["hour_utc"])
        assert info["session"] == detected

    def test_mocked_hour(self):
        with patch("src.session_awareness.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 12
            mock_dt.now.return_value = type("H", (), {"hour": 12})()
            info = get_current_session_info()
            assert info["session"] == "london"


# ── detect_session: None (uses current UTC) ────────────────────────────

class TestDetectSessionCurrentTime:
    def test_none_uses_current_utc(self):
        with patch("src.session_awareness.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 18
            assert detect_session() == "new_york"

    def test_none_off_hours(self):
        with patch("src.session_awareness.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 22
            assert detect_session() == "off_hours"
