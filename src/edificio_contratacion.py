"""Edificio de Contratación — Sistema de 3 pisos para selección de activos.

Cada activo que pasa los filtros básicos entra al edificio y sube piso por piso:

  P1 (Recepción)     → paga bien
  P2 (Cerebro)       → freno OK + extremo OK
  P3 (Sala de Espera) → espera cruce K/D limpio
  CONTRATADO         → entrada al trade

El activo NO puede saltarse pisos. Cada piso emite un POI que certifica
que la condición fue verificada en ese nivel.

Fase actual: solo P1 activa.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

log = logging.getLogger("edificio_contratacion")

# ── Estados del edificio ──────────────────────────────────────────────

PISO_FUERA = 0
PISO_1 = 1     # Recepción: paga bien
PISO_2 = 2     # Cerebro: freno OK + extremo OK
PISO_3 = 3     # Sala de espera: listo para cruce K/D
CONTRATADO = 4  # Entrada al trade

PISO_LABELS = {
    PISO_FUERA: "Fuera",
    PISO_1: "P1 — Recepción",
    PISO_2: "P2 — Cerebro",
    PISO_3: "P3 — Sala de Espera",
    CONTRATADO: "CONTRATADO",
}

PISO_SHORT = {
    PISO_FUERA: "fuera",
    PISO_1: "P1",
    PISO_2: "P2",
    PISO_3: "P3",
    CONTRATADO: "OK",
}


@dataclass
class BuildingCard:
    """Carnet de un activo dentro del edificio.

    Mantiene el estado del activo a través de los ciclos de scan.
    """

    asset: str
    piso: int = PISO_FUERA
    direction: Optional[str] = None  # "call" | "put"

    # POIs — timestamp de cuando se aprobó cada piso
    p1_at: Optional[float] = None  # Recepción aprobada
    p2_at: Optional[float] = None  # Cerebro aprobado
    p3_at: Optional[float] = None  # Sala de espera
    contratado_at: Optional[float] = None  # Entrada ejecutada

    # Condiciones actuales
    payout_ok: bool = False
    brake_ok: bool = False
    extreme_ok: bool = False
    cross_ok: bool = False
    cross_sticky: bool = False  # True si el cruce es pegajoso (no confiable)

    # Stoch M15 snapshot
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None

    # Metadatos
    payout: int = 0
    score: float = 0.0
    reason: str = ""  # Por qué está en el piso actual
    last_updated: float = field(default_factory=time.time)
    entered_piso_2_at: Optional[float] = None  # cuándo entró a P2
    entered_piso_3_at: Optional[float] = None  # cuándo entró a P3

    # Estado de la orden enviada al broker (solo cuando piso == CONTRATADO)
    order_id: str = ""        # id devuelto por el broker
    order_status: str = ""    # pending | sent | failed

    @property
    def has_poi_p1(self) -> bool:
        return self.p1_at is not None

    @property
    def has_poi_p2(self) -> bool:
        return self.p2_at is not None

    @property
    def has_poi_p3(self) -> bool:
        return self.p3_at is not None

    @property
    def p2_puerta(self) -> bool:
        return self.has_poi_p1 and self.piso == PISO_1

    @property
    def all_pois(self) -> bool:
        return self.has_poi_p1 and self.has_poi_p2 and self.has_poi_p3

    def piso_label(self) -> str:
        return PISO_LABELS.get(self.piso, f"Piso {self.piso}")

    def piso_short(self) -> str:
        return PISO_SHORT.get(self.piso, f"P{self.piso}")


@dataclass
class ContratadoEvent:
    """Un activo que salió del edificio y debe entrar a trade."""

    asset: str
    direction: str
    payout: int
    score: float
    card: Optional[BuildingCard] = None
    timestamp: float = field(default_factory=time.time)
    tries: int = 0         # intentos de envío de la orden
    order_id: str = ""     # id devuelto por el broker
    order_status: str = ""  # pending | sent | failed


class EdificioContratacion:
    """Gestor del edificio de contratación.

    Mantiene el estado de todos los activos que están en el edificio,
    evalúa transiciones entre pisos cada ciclo, y emite eventos cuando
    un activo está listo para contratar.

    Los eventos se consumen con pop_contratados() y la orden real la
    envía el BOT (src/edificio_executor.execute_contratados) usando el
    socket único. Si el envío falla, se re-encola con requeue().
    """

    def __init__(self) -> None:
        self._cards: Dict[str, BuildingCard] = {}
        self._contratados: List[ContratadoEvent] = []
        self._cycle_count: int = 0

    # ── API pública ────────────────────────────────────────────────

    def evaluate(
        self,
        *,
        asset: str,
        direction: str,
        payout: int,
        payout_ok: bool,
        brake_ok: bool = False,
        extreme_ok: bool = False,
        cross_ok: bool = False,
        cross_sticky: bool = False,
        stoch_k: Optional[float] = None,
        stoch_d: Optional[float] = None,
        score: float = 0.0,
    ) -> str:
        """Evalúa un activo en el edificio.

        Fase actual: P1 y P2 activas.
        """
        self._cycle_count += 1
        now = time.time()

        # Obtener o crear carnet
        card = self._cards.get(asset)
        if card is None:
            card = BuildingCard(
                asset=asset,
                piso=PISO_FUERA,
                direction=direction,
                payout=payout,
                score=score,
            )
            self._cards[asset] = card

        # Actualizar condiciones
        card.payout = payout
        card.payout_ok = payout_ok
        card.brake_ok = brake_ok
        card.extreme_ok = extreme_ok
        card.cross_ok = cross_ok
        card.cross_sticky = cross_sticky
        card.stoch_k = stoch_k
        card.stoch_d = stoch_d
        card.score = score
        card.last_updated = now
        if not card.direction and direction:
            card.direction = direction.upper()

        # Si no paga bien → expulsado
        if not payout_ok and card.piso > PISO_FUERA:
            log.info(
                "[EDIFICIO] %s: expulsado — dejó de pagar (payout=%d%%)",
                asset, payout,
            )
            card.reason = f"Payout insuficiente ({payout}%)"
            return self._expulsar(asset)

        # Recepción: entrar si paga bien; si ya entró, se queda
        if card.piso == PISO_FUERA:
            if payout_ok:
                card.piso = PISO_1
                card.p1_at = now
                card.reason = f"Paga bien ({payout}%)"
                log.info("[EDIFICIO] %s → P1 (payout=%d%%)", asset, payout)
                return "subio"
            card.reason = f"Esperando pago ≥ mínimo ({payout}%)"
            return "stay"

        if card.piso == PISO_1:
            if not payout_ok:
                return self._expulsar(asset)
            if brake_ok and extreme_ok:
                card.piso = PISO_2
                card.p2_at = now
                card.reason = f"P2 OK — brake+extremo ({payout}%)"
                log.info("[EDIFICIO] %s → P2 (payout=%d%%)", asset, payout)
                return "subio"
            card.reason = f"P1 OK — esperando brake+extremo ({payout}%)"
            return "stay"

        if card.piso == PISO_2:
            if not payout_ok:
                return self._expulsar(asset)
            if cross_ok or cross_sticky:
                card.piso = PISO_3
                card.p3_at = now
                card.reason = f"P3 OK — cruce {'pegajoso' if cross_sticky else 'confirmado'} ({payout}%)"
                log.info("[EDIFICIO] %s → P3 (payout=%d%%)", asset, payout)
                return "subio"
            if brake_ok and extreme_ok:
                card.reason = f"P2 OK — esperando cruce K/D ({payout}%)"
                return "stay"
            card.reason = f"P2 pendiente — brake+extremo ({payout}%)"
            return "stay"

        if card.piso == PISO_3:
            if not payout_ok:
                return self._expulsar(asset)
            contract_now = (
                card.direction in {"CALL", "PUT"}
                and (cross_ok or cross_sticky)
                and extreme_ok
            )
            if contract_now:
                if not card.direction:
                    card.reason = "CONTRATADO bloqueado: direction vacía"
                    return "stay"
                card.piso = CONTRATADO
                card.contratado_at = now
                card.p3_at = card.p3_at or now
                card.order_status = "pending"
                card.reason = f"CONTRATADO — {card.direction} ({payout}%)"
                log.info("[EDIFICIO] %s → CONTRATADO direction=%s payout=%d%%", asset, card.direction, payout)
                self._contratados.append(
                    ContratadoEvent(
                        asset=asset,
                        direction=card.direction,
                        payout=payout,
                        score=score,
                        card=card,
                        timestamp=now,
                    )
                )
                return "contratado"
            card.reason = f"P3 listo — esperando contratar ({payout}%)"
            return "stay"

        # Si ya entró o volvió atrás, no baja de P1 en esta fase
        card.reason = "P1 OK"
        return "stay"

    def pop_contratados(self) -> List[ContratadoEvent]:
        events = list(self._contratados)
        self._contratados.clear()
        return events

    def requeue(self, event: ContratadoEvent) -> None:
        """Vuelve a encolar un evento cuyo envío de orden falló.

        El timestamp original se conserva: el cleanup (10 min) sigue
        aplicando desde el momento en que se generó el evento.
        """
        if event not in self._contratados:
            self._contratados.append(event)

    def reset_contratados_recientes(self) -> int:
        count = len(self._contratados)
        self._contratados.clear()
        return count

    def get_card(self, asset: str) -> Optional[BuildingCard]:
        """Obtiene el carnet de un activo."""
        return self._cards.get(asset)

    def get_state(self) -> dict:
        """Devuelve el estado completo del edificio para el hub."""
        return {
            "cycle": self._cycle_count,
            "cards": {
                asset: {
                    "asset": card.asset,
                    "piso": card.piso,
                    "piso_label": card.piso_label(),
                    "piso_short": card.piso_short(),
                    "direction": card.direction,
                    "payout": card.payout,
                    "score": card.score,
                    "reason": card.reason,
                    "brake_ok": card.brake_ok,
                    "extreme_ok": card.extreme_ok,
                    "cross_ok": card.cross_ok,
                    "cross_sticky": card.cross_sticky,
                    "stoch_k": card.stoch_k,
                    "stoch_d": card.stoch_d,
                    "p1_at": card.p1_at,
                    "p2_at": card.p2_at,
                    "p3_at": card.p3_at,
                    "contratado_at": card.contratado_at,
                    "last_updated": card.last_updated,
                    "has_poi_p1": card.has_poi_p1,
                    "has_poi_p2": card.has_poi_p2,
                    "has_poi_p3": card.has_poi_p3,
                    "p2_puerta": card.p2_puerta,
                    "order_id": card.order_id,
                    "order_status": card.order_status,
                }
                for asset, card in self._cards.items()
                if card.piso >= PISO_1
            },
            "contratados_recientes": [
                {
                    "asset": e.asset,
                    "direction": e.direction,
                    "payout": e.payout,
                    "score": e.score,
                    "timestamp": e.timestamp,
                    "tries": e.tries,
                    "order_id": e.order_id,
                    "order_status": e.order_status,
                }
                for e in self._contratados
            ],
            "resumen": self._build_resumen(),
        }

    def get_by_piso(self, piso: int) -> List[BuildingCard]:
        """Obtiene todos los activos en un piso específico."""
        return [
            card for card in self._cards.values()
            if card.piso == piso
        ]

    def get_all_active(self) -> List[BuildingCard]:
        """Obtiene todos los activos actualmente en el edificio."""
        return [
            card for card in self._cards.values()
            if PISO_1 <= card.piso <= PISO_3
        ]

    def cleanup(self, max_age_sec: float = 7200) -> None:
        """Limpia activos que llevan demasiado tiempo sin actualizarse."""
        now = time.time()
        stale = [
            asset for asset, card in self._cards.items()
            if card.piso < CONTRATADO
            and now - card.last_updated > max_age_sec
        ]
        for asset in stale:
            log.info("[EDIFICIO] Limpieza: %s expirado (%.0fs sin update)", asset, max_age_sec)
            del self._cards[asset]
        # Limpiar contratados viejos (>10 min)
        self._contratados = [
            e for e in self._contratados
            if now - e.timestamp < 600
        ]

    def reset(self) -> None:
        """Resetea el edificio completo."""
        self._cards.clear()
        self._contratados.clear()
        self._cycle_count = 0
        log.info("[EDIFICIO] Reset completo")

    # ── Internos ───────────────────────────────────────────────────

    def _expulsar(self, asset: str) -> str:
        card = self._cards.get(asset)
        if card is not None:
            old_piso = card.piso
            card.piso = PISO_FUERA
            card.reason = "Expulsado del edificio"
            log.info("[EDIFICIO] %s: expulsado (estaba en %s)", asset, PISO_LABELS.get(old_piso, f"P{old_piso}"))
        return "expulsado"

    def _build_resumen(self) -> dict:
        counts = {PISO_1: 0, PISO_2: 0, PISO_3: 0, CONTRATADO: 0}
        for card in self._cards.values():
            if card.piso in counts:
                counts[card.piso] += 1
        return {
            "en_p1": counts[PISO_1],
            "en_p2": counts[PISO_2],
            "en_p3": counts[PISO_3],
            "contratados": counts[CONTRATADO],
            "total_dentro": counts[PISO_1] + counts[PISO_2] + counts[PISO_3],
        }


# Singleton global
_edificio: Optional[EdificioContratacion] = None


def get_edificio() -> EdificioContratacion:
    global _edificio
    if _edificio is None:
        _edificio = EdificioContratacion()
    return _edificio


def reset_edificio() -> None:
    global _edificio
    if _edificio is not None:
        _edificio.reset()
    _edificio = None
