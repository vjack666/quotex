"""Tests del módulo alerter (TelegramAlerter)."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from alerter import TelegramAlerter


@pytest.fixture
def alerter() -> TelegramAlerter:
    """Alerter habilitado con tokens falsos."""
    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "123:fake", "TELEGRAM_CHAT_ID": "-456"}):
        a = TelegramAlerter()
        a._last_alert.clear()  # cooldown fresco
        return a


@pytest.fixture
def alerter_disabled() -> TelegramAlerter:
    """Alerter sin tokens — debe no-operar."""
    with patch.dict("os.environ", {}, clear=True):
        return TelegramAlerter()


# ── R1: send_message success ─────────────────────────────────────────────────


def test_send_message_success(alerter: TelegramAlerter):
    """send_message retorna True cuando requests.post es exitoso."""
    with patch("alerter.requests.post") as mock_post:
        mock_post.return_value = MagicMock(ok=True, status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()

        result = alerter.send_message("Hello", event_type="test")

    assert result is True
    mock_post.assert_called_once_with(
        ANY,
        json={
            "chat_id": "-456",
            "text": "Hello",
            "parse_mode": "HTML",
        },
        timeout=10,
    )


# ── R2: disabled when no env vars ────────────────────────────────────────────


def test_send_message_disabled_when_no_env(alerter_disabled: TelegramAlerter):
    """Sin TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID, send_message retorna False."""
    result = alerter_disabled.send_message("should not send")
    assert result is False


# ── R3: uses requests (no new deps) — implicitly covered by all tests


# ── R4: alert_session_complete format ────────────────────────────────────────


def test_alert_session_complete(alerter: TelegramAlerter):
    """alert_session_complete llama send_message con el texto esperado."""
    with patch.object(alerter, "send_message", return_value=True) as mock_send:
        result = alerter.alert_session_complete(wins=3, capital=150.0)

    assert result is True
    mock_send.assert_called_once_with(
        "\U0001f3af <b>SESI\u00d3N CUMPLIDA</b>\n3 ITM alcanzados\nCapital: $150.00",
        event_type="session_complete",
    )


# ── R5: alert_losing_streak format ───────────────────────────────────────────


def test_alert_losing_streak(alerter: TelegramAlerter):
    """alert_losing_streak llama send_message con el texto esperado."""
    with patch.object(alerter, "send_message", return_value=True) as mock_send:
        result = alerter.alert_losing_streak(losses=3, capital=40.0)

    assert result is True
    mock_send.assert_called_once_with(
        "\U0001f494 <b>RACHA DE P\u00c9RDIDAS</b>\n3 p\u00e9rdidas consecutivas\nCapital: $40.00",
        event_type="losing_streak",
    )


# ── R6: alert_connection_lost format ─────────────────────────────────────────


def test_alert_connection_lost(alerter: TelegramAlerter):
    """alert_connection_lost llama send_message con el texto esperado."""
    with patch.object(alerter, "send_message", return_value=True) as mock_send:
        result = alerter.alert_connection_lost()

    assert result is True
    mock_send.assert_called_once_with(
        "\u26a0\ufe0f <b>CONEXI\u00d3N PERDIDA</b>\nEl bot ha perdido la conexi\u00f3n con el broker.",
        event_type="connection_lost",
    )


# ── R7: alert_stop_loss format ───────────────────────────────────────────────


def test_alert_stop_loss(alerter: TelegramAlerter):
    """alert_stop_loss llama send_message con el texto esperado."""
    with patch.object(alerter, "send_message", return_value=True) as mock_send:
        result = alerter.alert_stop_loss(drawdown_pct=20.5, capital=80.0)

    assert result is True
    mock_send.assert_called_once_with(
        "\U0001f6d1 <b>STOP-LOSS ACTIVADO</b>\nDrawdown: 20.5%\nCapital: $80.00",
        event_type="stop_loss",
    )


# ── R8: tests with mock ─── implicit — all tests above use mocks


# ── R9: HTML parse_mode ─── verified in test_send_message_success


# ── R10: cooldown ────────────────────────────────────────────────────────────


def test_cooldown_suppresses_duplicates(alerter: TelegramAlerter):
    """Llamadas rápidas con el mismo event_type son suprimidas por cooldown."""
    alerter.COOLDOWNS["test_cooldown"] = 60  # 60s de cooldown

    with patch("alerter.requests.post") as mock_post:
        mock_post.return_value = MagicMock(ok=True, status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()

        # Primera llamada pasa
        first = alerter.send_message("first", event_type="test_cooldown")
        # Segunda llamada inmediata — debe ser suprimida
        second = alerter.send_message("second", event_type="test_cooldown")

    assert first is True
    assert second is False
    mock_post.assert_called_once()  # solo una llamada real


def test_cooldown_per_event_type(alerter: TelegramAlerter):
    """Eventos de diferente tipo no comparten cooldown."""
    alerter.COOLDOWNS["type_a"] = 120
    alerter.COOLDOWNS["type_b"] = 120

    with patch("alerter.requests.post") as mock_post:
        mock_post.return_value = MagicMock(ok=True, status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()

        r1 = alerter.send_message("a1", event_type="type_a")
        r2 = alerter.send_message("b1", event_type="type_b")

    assert r1 is True
    assert r2 is True
    assert mock_post.call_count == 2


def test_connection_lost_cooldown_longer(alerter: TelegramAlerter):
    """connection_lost tiene cooldown de 300s (R10)."""
    assert alerter.COOLDOWNS["connection_lost"] == 300


def test_send_message_http_error(alerter: TelegramAlerter):
    """send_message retorna False si requests.post lanza HTTPError."""
    with patch("alerter.requests.post") as mock_post:
        mock_post.return_value = MagicMock(ok=False, status_code=403)
        mock_post.return_value.raise_for_status.side_effect = Exception("403 Forbidden")

        result = alerter.send_message("fail")

    assert result is False


def test_send_message_timeout(alerter: TelegramAlerter):
    """send_message retorna False si requests.post timeout."""
    with patch("alerter.requests.post", side_effect=Exception("timeout")):
        result = alerter.send_message("timeout")

    assert result is False
