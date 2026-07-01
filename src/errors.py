"""Excepciones del dominio del bot de trading."""
from __future__ import annotations


class BotError(Exception):
    """Base para errores del bot."""


class ConnectionError(BotError):
    """Error de conexión con el broker."""


class StrategyError(BotError):
    """Error en lógica de estrategia."""


class RiskError(BotError):
    """Violación de límite de riesgo."""