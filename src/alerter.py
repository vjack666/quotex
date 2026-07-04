"""Alertas a Telegram para eventos del bot vía Bot API."""
from __future__ import annotations

import logging
import os
import time

import requests

log = logging.getLogger(__name__)


class TelegramAlerter:
    """Envía mensajes a un chat de Telegram vía Bot API.

    Lee TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID de variables de entorno.
    Si alguna falta, todos los métodos no-operan silenciosamente.

    Incluye cooldown por tipo de evento para evitar spam.
    """

    COOLDOWNS: dict[str, int] = {
        "connection_lost": 300,  # 5 minutos
        "default": 60,
    }

    def __init__(self) -> None:
        self._token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        self._enabled = bool(self._token and self._chat_id)
        if not self._enabled:
            log.info(
                "TelegramAlerter disabled — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID",
            )
        self._base_url = (
            f"https://api.telegram.org/bot{self._token}/sendMessage"
        )
        self._last_alert: dict[str, float] = {}

    def _can_alert(self, event_type: str) -> bool:
        """Check cooldown for event_type. Updates timestamp if allowed."""
        now = time.time()
        cooldown = self.COOLDOWNS.get(event_type, self.COOLDOWNS["default"])
        last = self._last_alert.get(event_type, 0.0)
        if now - last < cooldown:
            return False
        self._last_alert[event_type] = now
        return True

    def send_message(self, text: str, event_type: str | None = None) -> bool:
        """Send a raw text message to Telegram.

        Args:
            text: Message text (HTML parse_mode is used).
            event_type: Optional key for cooldown scoping.
                        If None, no cooldown is applied.

        Returns:
            True if sent successfully (or cooldown suppressed), False otherwise.
        """
        if not self._enabled:
            return False
        if event_type is not None and not self._can_alert(event_type):
            return False
        try:
            resp = requests.post(
                self._base_url,
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            log.warning("Telegram send_message failed: %s", exc)
            return False

    def alert_session_complete(self, wins: int, capital: float) -> bool:
        """Alerta: sesión Massaniello cumplida (R4)."""
        return self.send_message(
            f"\U0001f3af <b>SESI\u00d3N CUMPLIDA</b>\n"
            f"{int(wins)} ITM alcanzados\n"
            f"Capital: ${capital:.2f}",
            event_type="session_complete",
        )

    def alert_losing_streak(self, losses: int, capital: float) -> bool:
        """Alerta: racha de pérdidas / sesión fallida (R5)."""
        return self.send_message(
            f"\U0001f494 <b>RACHA DE P\u00c9RDIDAS</b>\n"
            f"{int(losses)} p\u00e9rdidas consecutivas\n"
            f"Capital: ${capital:.2f}",
            event_type="losing_streak",
        )

    def alert_connection_lost(self) -> bool:
        """Alerta: conexión perdida con el broker (R6)."""
        return self.send_message(
            "\u26a0\ufe0f <b>CONEXI\u00d3N PERDIDA</b>\n"
            "El bot ha perdido la conexi\u00f3n con el broker.",
            event_type="connection_lost",
        )

    def alert_stop_loss(self, drawdown_pct: float, capital: float) -> bool:
        """Alerta: stop-loss de sesión activado (R7)."""
        return self.send_message(
            f"\U0001f6d1 <b>STOP-LOSS ACTIVADO</b>\n"
            f"Drawdown: {drawdown_pct:.1f}%\n"
            f"Capital: ${capital:.2f}",
            event_type="stop_loss",
        )


# Module-level singleton para import directo desde otros módulos.
alerter = TelegramAlerter()
