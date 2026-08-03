"""Edificio de Contratación — Sistema de 3 pisos para selección de activos.

Cada activo que pasa los filtros básicos entra al edificio y sube piso por piso:

  P1 (Recepción)     → paga bien
  P2 (Cerebro)       → freno OK + extremo OK, espera separación K/D limpia
  P3 (Sala de Espera) → cruce limpio confirmado + vela 5m válida (body o martillo)
  CONTRATADO         → entrada al trade

El activo NO puede saltarse pisos. Cada piso emite un POI que certifica
que la condición fue verificada en ese nivel.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import (
    EDIFICIO_BODY_FILTER_MIN_RATIO,
    EDIFICIO_BRAKE_CONFIRM_RATIO,
    EDIFICIO_HAMMER_MIN_TAIL_RATIO,
    EDIFICIO_POST_BRAKE_MIN_RATIO,
    EDIFICIO_SEPARATION_WAIT_SEC,
)

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
    cross_sticky: bool = False  # True si el cruce es pegajoso; usar como espera, no como veto
    # Puerta P2→P3: momento en que el cruce limpio (|K-D| >= sticky) apareció.
    # El cruce debe MANTENERSE EDIFICIO_SEPARATION_WAIT_SEC antes de promover.
    cross_separation_since: Optional[float] = None

    # Stoch M15 snapshot
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    # |K-D| en el momento de la evaluación (para caja negra / auditoría)
    kd_distance: Optional[float] = None

    # Body filter 5m
    body_5m: Optional[float] = None  # body/total_range de la última vela 5m cerrada
    # Patrón de la vela 5m en P3 (name del shape classifier) para caja negra
    pattern_5m: Optional[str] = None

    # Contexto de auditoría (caja negra) — snapshot del momento de evaluación
    stoch_m15_full: Optional[dict] = None      # dict completo de compute_stoch()
    extreme_read: int = 0                      # 1 si extremo (k<=20 CALL | k>=80 PUT)
    candle_15m_prev: Optional[dict] = None     # forma de la última vela 15m cerrada
    candle_5m_prev: Optional[dict] = None      # forma de la última vela 5m cerrada
    candles_15m_snap: list = field(default_factory=list)  # velas 15m crudas (últimas N)
    candles_5m_snap: list = field(default_factory=list)   # velas 5m crudas (últimas N)

    # Metadatos
    payout: int = 0
    score: float = 0.0
    reason: str = ""  # Por qué está en el piso actual
    last_updated: float = field(default_factory=time.time)
    entered_piso_2_at: Optional[float] = None  # cuándo entró a P2
    entered_piso_3_at: Optional[float] = None  # cuándo entró a P3

    # Estado de la orden enviada al broker (solo cuando piso == CONTRATADO)
    order_id: str = ""        # id devuelto por el broker
    order_ref: int = 0        # ticket numérico del broker (para resolver resultado)
    order_status: str = ""    # pending | sent | won | lost | failed

    # Espera post-freno / delay de ejecución
    brake_at: Optional[float] = None            # primera vez que brake+extremo OK en P1 (candidato)
    # Confirmación del freno con vela M15 CERRADA (deuda #1): al detectar el
    # candidato se guarda el rango/ts de la última vela 15m cerrada; cuando esa
    # vela cierra se compara range(nueva cerrada) < EDIFICIO_BRAKE_CONFIRM_RATIO
    # × range(referencia). Solo entonces se promueve a P2.
    brake_reference_range: Optional[float] = None  # range (high-low) de la vela 15m cerrada de referencia
    brake_reference_ts: Optional[float] = None     # ts de esa vela de referencia (para detectar el cierre)
    brake_verdict: Optional[str] = None            # CONFIRMED | REJECTED | CANCELLED (caja negra)
    brake_ratio: Optional[float] = None            # range(nueva cerrada) / range(referencia) al veredicto
    brake_witness_ts: Optional[float] = None       # ts de la vela que cerró y desencadenó el veredicto
    brake_confirmed_at: Optional[float] = None  # cuando pasó la confirmación con vela cerrada
    entry_pending: bool = False                 # P3 marcó entrada, esperando delay
    pending_since: Optional[float] = None       # timestamp del primer CONTRATADO elegible

    # Experimento body post-freno (sin veto todavía)
    post_brake_body_ratio: Optional[float] = None   # body/range primera vela M15 post-freno
    post_brake_would_pass: Optional[bool] = None    # True si supera corte actual
    post_brake_measured_at: Optional[float] = None  # ts vela usada para la medición

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
    order_ref: int = 0     # ticket numérico del broker (para resolver resultado)
    order_status: str = ""  # pending | sent | won | lost | failed


def _detect_hammer_pattern(
    candle: Optional[dict],
    direction: str,
    min_tail_ratio: float,
) -> bool:
    """True si la vela 5m es un martillo válido en la dirección del trade.

    CALL → martillo alcista: mecha inferior larga (rechazo de mínimos).
    PUT  → martillo invertido: mecha superior larga (rechazo de máximos).

    La mecha principal debe ser >= min_tail_ratio * body y el cuerpo debe
    quedar anclado al lado opuesto de la mecha. Requiere body > 0.
    """
    if not isinstance(candle, dict):
        return False
    try:
        o = float(candle.get("open") or 0.0)
        h = float(candle.get("high") or 0.0)
        l = float(candle.get("low") or 0.0)
        c = float(candle.get("close") or 0.0)
    except (TypeError, ValueError):
        return False
    body = abs(c - o)
    if body <= 0:
        return False
    rng = h - l
    if rng <= 0:
        return False
    upper = h - max(o, c)
    lower = min(o, c) - l
    direction = (direction or "").upper()
    if direction == "CALL":
        return lower >= min_tail_ratio * body and upper < 0.3 * rng
    if direction == "PUT":
        return upper >= min_tail_ratio * body and lower < 0.3 * rng
    return False


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
        # Órdenes confirmadas por el broker, pendientes de resolución WIN/LOSS.
        # key = order_id; value = {asset, direction, amount, payout, order_ref,
        # sent_at, duration_sec, resolved, attempts}
        self._sent_orders: Dict[str, Dict[str, Any]] = {}

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
        stoch_m15_full: Optional[dict] = None,
        extreme_read: int = 0,
        candle_15m_prev: Optional[dict] = None,
        candle_5m_prev: Optional[dict] = None,
        candles_15m: Optional[list] = None,
        candles_5m: Optional[list] = None,
        close_candle_5m: Optional[dict] = None,
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
        if stoch_k is not None and stoch_d is not None:
            card.kd_distance = abs(float(stoch_k) - float(stoch_d))
        else:
            card.kd_distance = None
        card.score = score
        card.last_updated = now
        if not card.direction and direction:
            card.direction = direction.upper()

        # Contexto de auditoría: snapshot del momento de evaluación.
        # Se conserva el del último scan (se sobrescribe a medida que llega).
        if stoch_m15_full is not None:
            card.stoch_m15_full = stoch_m15_full
        card.extreme_read = int(extreme_read or 0)
        if candle_15m_prev is not None:
            card.candle_15m_prev = candle_15m_prev
        if candle_5m_prev is not None:
            card.candle_5m_prev = candle_5m_prev
        if candles_15m:
            card.candles_15m_snap = list(candles_15m)[-24:]
        if candles_5m:
            card.candles_5m_snap = list(candles_5m)[-24:]

        # Patrón de la vela 5m cerrada (para caja negra / martillo M5).
        _c5 = close_candle_5m if isinstance(close_candle_5m, dict) else candle_5m_prev
        card.pattern_5m = str(_c5.get("name")) if isinstance(_c5, dict) and _c5.get("name") else None

        # Medición post-freno REINTENTABLE: si aún no hay vela M15 post-freno
        # cerrada en el snapshot, se reintenta en el próximo ciclo (no se pierde).
        if card.brake_confirmed_at is not None:
            self._measure_post_brake(card)

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
                # Nuevo candidato: capturar la vela 15m cerrada de referencia.
                if card.brake_at is None:
                    card.brake_at = now
                    card.brake_confirmed_at = None
                    card.brake_verdict = None
                    card.brake_ratio = None
                    card.brake_witness_ts = None
                    self._brake_set_reference(card)
                    card.reason = f"P1 OK — freno candidato, esperando vela M15 cerrada ({payout}%)"
                    log.info("[EDIFICIO] %s: freno candidato en P1, esperando vela M15 cerrada...", asset)
                    return "stay"
                # Candidato activo: asegurar referencia (por si el snapshot estaba vacío).
                self._brake_set_reference(card)
                # Confirmar el freno con la vela CERRADA (deuda #1): cuando la
                # vela en formación cierra, comparar su range contra la referencia.
                ratio, witness_ts = self._brake_confirm(card)
                if ratio is None:
                    # Sin vela nueva cerrada aún: esperar (no resetea).
                    card.reason = f"P1 OK — esperando cierre de vela M15 para freno ({payout}%)"
                    return "stay"
                card.brake_ratio = ratio
                card.brake_witness_ts = witness_ts
                if ratio < EDIFICIO_BRAKE_CONFIRM_RATIO:
                    card.brake_confirmed_at = now
                    card.brake_verdict = "CONFIRMED"
                    card.piso = PISO_2
                    card.p2_at = now
                    card.reason = f"P2 OK — freno confirmado con vela M15 cerrada + extremo ({payout}%)"
                    log.info(
                        "[EDIFICIO] %s → P2 (freno CONFIRMED ratio=%.2f, payout=%d%%)",
                        asset, ratio, payout,
                    )
                    # Experimento: medir body/ratio de la primera vela M15 post-freno
                    self._measure_post_brake(card)
                    return "subio"
                # La vela cerró sin compresión: rechazar y esperar un nuevo candidato.
                card.brake_verdict = "REJECTED"
                card.brake_at = None
                card.brake_confirmed_at = None
                self._brake_clear_reference(card)
                card.reason = f"P1 OK — freno sin compresión, esperando nuevo candidato ({payout}%)"
                log.info(
                    "[EDIFICIO] %s: freno RECHAZADO (ratio=%.2f ≥ %.2f)",
                    asset, ratio, EDIFICIO_BRAKE_CONFIRM_RATIO,
                )
                return "stay"
            # Se perdió brake o extremo antes del cierre de la vela: cancelar.
            if card.brake_at is not None:
                card.brake_verdict = "CANCELLED"
                log.info("[EDIFICIO] %s: freno CANCELLED (se perdió brake/extremo)", asset)
            card.brake_at = None
            card.brake_confirmed_at = None
            self._brake_clear_reference(card)
            card.reason = f"P1 OK — esperando brake+extremo ({payout}%)"
            return "stay"

        if card.piso == PISO_2:
            if not payout_ok:
                return self._expulsar(asset)
            if cross_ok and not cross_sticky:
                # Cruce limpio: el separación K/D debe MANTENERSE una vela M15
                # antes de promover a P3 (evita subir con un tick aislado).
                if card.cross_separation_since is None:
                    card.cross_separation_since = now
                    card.reason = f"P2 OK — separación K/D detectada, esperando confirmación ({payout}%)"
                    log.info(
                        "[EDIFICIO] %s: cruce limpio en P2, esperando separación (%.0fs)",
                        asset, EDIFICIO_SEPARATION_WAIT_SEC,
                    )
                    return "stay"
                if card.cross_separation_since + EDIFICIO_SEPARATION_WAIT_SEC < now:
                    card.piso = PISO_3
                    card.p3_at = now
                    card.cross_separation_since = None
                    card.reason = f"P3 OK — separación confirmada ({payout}%)"
                    log.info("[EDIFICIO] %s → P3 (separación confirmada, payout=%d%%)", asset, payout)
                    return "subio"
                card.reason = f"P2 OK — esperando confirmación separación ({(card.cross_separation_since + EDIFICIO_SEPARATION_WAIT_SEC - now):.0f}s, {payout}%)"
                return "stay"
            # Sin cruce limpio (sticky o sin cruce): la separación se reinicia.
            card.cross_separation_since = None
            if cross_sticky:
                card.reason = f"P2 OK — sticky: esperar separación K/D ({payout}%)"
                log.info("[EDIFICIO] %s: sticky en P2, quedando en espera", asset)
                return "stay"
            if brake_ok and extreme_ok:
                card.reason = f"P2 OK — esperando cruce K/D ({payout}%)"
                return "stay"
            card.reason = f"P2 pendiente — brake+extremo ({payout}%)"
            card.piso = PISO_1
            card.cross_separation_since = None
            card.entry_pending = False
            card.pending_since = None
            card.brake_at = None
            card.brake_confirmed_at = None
            card.brake_verdict = None
            card.brake_ratio = None
            card.brake_witness_ts = None
            card.p2_at = None
            log.info("[EDIFICIO] %s: baja a P1 (perdió brake+extremo)", asset)
            return "bajo"

        if card.piso == PISO_3:
            if not payout_ok:
                return self._expulsar(asset)
            if not brake_ok:
                card.piso = PISO_2
                card.reason = f"Baja a P2 — freno perdido ({payout}%)"
                log.info("[EDIFICIO] %s: baja a P2 (brake perdido)", asset)
                card.entry_pending = False
                card.pending_since = None
                return "bajo"
            if not extreme_ok:
                card.piso = PISO_2
                card.reason = f"Baja a P2 — extremo perdido ({payout}%)"
                log.info("[EDIFICIO] %s: baja a P2 (extremo perdido)", asset)
                card.entry_pending = False
                card.pending_since = None
                return "bajo"
            if not cross_ok:
                card.reason = f"P3 OK — esperando cruce limpio ({payout}%)"
                return "stay"
            # Gate vela 5m: body fuerte O martillo M5 en dirección del trade.
            # El filtro se aplica al MOMENTO de marcar la entrada; si la vela
            # no confirma, no se marca entrada y se espera la próxima vela.
            _c5 = close_candle_5m if isinstance(close_candle_5m, dict) else getattr(card, "candle_5m_prev", None)
            if not self._5m_gate_pass(_c5, direction):
                card.reason = (
                    f"P3 OK — vela 5m sin confirmar "
                    f"(body<{EDIFICIO_BODY_FILTER_MIN_RATIO} y no martillo) ({payout}%)"
                )
                log.info("[EDIFICIO] %s: vela 5m rechazada en P3 (patrón=%s)", asset, card.pattern_5m)
                return "stay"
            if card.entry_pending:
                if card.pending_since is None:
                    card.pending_since = now
                if card.pending_since + 300 < now:  # 5 min = inicio próxima vela 15m
                    card.piso = CONTRATADO
                    card.contratado_at = now
                    card.order_status = "pending"
                    card.reason = f"CONTRATADO — delay ejecución cumplido ({payout}%)"
                    log.info("[EDIFICIO] %s → CONTRATADO (delay ejecución OK, payout=%d%%)", asset, payout)
                    ev = ContratadoEvent(
                        asset=asset,
                        direction=card.direction or direction,
                        payout=payout,
                        score=card.score,
                        card=card,
                        timestamp=now,
                    )
                    self._contratados.append(ev)
                    return "contratado"
                card.reason = f"P3 OK — delay ejecución ({(card.pending_since + 300 - now):.0f}s restantes, {payout}%)"
                return "stay"
            card.entry_pending = True
            card.pending_since = now
            card.reason = f"P3 OK — entrada marcada, delay 5 min ({payout}%)"
            log.info("[EDIFICIO] %s: entrada marcada para próxima vela 15m (delay 5 min)", asset)
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

    def register_sent(self, order_id: str, info: Dict[str, Any]) -> None:
        """Registra una orden confirmada por el broker, pendiente de resolución."""
        if not order_id:
            return
        info.setdefault("resolved", False)
        info.setdefault("attempts", 0)
        self._sent_orders[order_id] = info

    def sent_pending(self) -> Dict[str, Dict[str, Any]]:
        """Órdenes enviadas que aún no se resolvieron (por order_id)."""
        return self._sent_orders

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
                    "cross_separation_since": card.cross_separation_since,
                    "stoch_k": card.stoch_k,
                    "stoch_d": card.stoch_d,
                    "kd_distance": card.kd_distance,
                    "pattern_5m": card.pattern_5m,
                    "brake_verdict": card.brake_verdict,
                    "brake_ratio": card.brake_ratio,
                    "brake_reference_ts": card.brake_reference_ts,
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

    def _brake_set_reference(self, card: BuildingCard) -> None:
        """Captura la vela 15m cerrada de referencia del candidato de freno.

        La referencia es la última vela CERRADA del snapshot (candles[-2];
        [-1] es la vela en formación) en el momento de la detección. Solo se
        captura UNA vez; si el snapshot aún no tiene vela cerrada, se reintenta
        en el próximo ciclo (no se pierde el candidato).
        """
        if card.brake_reference_ts is not None:
            return
        candles = list(getattr(card, "candles_15m_snap", []) or [])
        if len(candles) < 2:
            return
        ref = candles[-2]
        try:
            _ts = float(ref.get("ts", 0) or 0)
            _rng = float(ref.get("high", 0)) - float(ref.get("low", 0))
        except (TypeError, ValueError):
            return
        if _ts <= 0 or _rng <= 0:
            return
        card.brake_reference_ts = _ts
        card.brake_reference_range = _rng

    def _brake_confirm(self, card: BuildingCard) -> tuple:
        """Devuelve (ratio, witness_ts) si la vela M15 en formación ya cerró.

        La vela cierra cuando candles[-2] (última cerrada) deja de ser la de
        referencia: la nueva cerrada es esa vela. ratio = range(nueva cerrada)
        / range(referencia). Sin vela nueva cerrada → (None, None).
        """
        if card.brake_reference_ts is None or card.brake_reference_range is None:
            return None, None
        candles = list(getattr(card, "candles_15m_snap", []) or [])
        if len(candles) < 2:
            return None, None
        nueva = candles[-2]
        try:
            _ts = float(nueva.get("ts", 0) or 0)
            _rng = float(nueva.get("high", 0)) - float(nueva.get("low", 0))
        except (TypeError, ValueError):
            return None, None
        if _ts <= 0 or _ts == card.brake_reference_ts:
            return None, None  # la vela aún no cerró (misma última cerrada)
        if _rng <= 0:
            return None, None
        return _rng / card.brake_reference_range, _ts

    def _brake_clear_reference(self, card: BuildingCard) -> None:
        """Limpia la referencia del candidato de freno (rechazo o cancelación)."""
        card.brake_reference_range = None
        card.brake_reference_ts = None

    def _measure_post_brake(self, card: BuildingCard) -> None:
        """Mide el body/range de la primera vela M15 post-freno.

        REINTENTABLE: si la vela post-freno aún no está en el snapshot (recién
        se confirmó el freno), se reintenta en cada ciclo hasta lograrlo. Nunca
        veta la operación: solo audita (EDIFICIO_POST_BRAKE_MIN_RATIO = 0.0).
        """
        try:
            if card.post_brake_body_ratio is not None:
                return  # ya medido
            if card.brake_confirmed_at is None:
                return
            candles = list(getattr(card, "candles_15m_snap", []) or [])
            if not candles:
                return
            post = [c for c in candles if c.get("ts", 0) > card.brake_confirmed_at]
            if not post:
                log.debug(
                    "[EDIFICIO][EXPERIMENTO] %s: sin vela post-freno aún, reintentaré",
                    getattr(card, "asset", "?"),
                )
                return
            c = post[0]
            o = float(c.get("open", 0))
            h = float(c.get("high", 0))
            l = float(c.get("low", 0))
            c_ = float(c.get("close", 0))
            rng = h - l
            if rng <= 0:
                return
            body = abs(c_ - o) / rng
            card.post_brake_body_ratio = float(body)
            card.post_brake_would_pass = body >= EDIFICIO_POST_BRAKE_MIN_RATIO
            card.post_brake_measured_at = float(c.get("ts", 0))
            log.info(
                "[EDIFICIO][EXPERIMENTO] %s post_brake_body=%.2f pass=%s",
                card.asset,
                body,
                card.post_brake_would_pass,
            )
        except Exception as exc:
            log.debug("[EDIFICIO][EXPERIMENTO] %s medicion post-freno fallo: %s", getattr(card, "asset", "?"), exc)

    def _5m_gate_pass(self, candle: Optional[dict], direction: str) -> bool:
        """Vela 5m válida para contratar en P3.

        Pasa si el body es fuerte (body_pct >= EDIFICIO_BODY_FILTER_MIN_RATIO)
        o si es un martillo M5 en la dirección del trade. Sin contexto 5m
        (None) no bloquea: mantiene el comportamiento anterior.
        """
        if not isinstance(candle, dict):
            return True
        body_pct: Optional[float] = None
        try:
            body_pct = float(candle.get("body_pct") or 0.0)
        except (TypeError, ValueError):
            body_pct = None
        if body_pct is None:
            try:
                body = float(candle.get("body") or 0.0)
                rng = float(candle.get("total_range") or 0.0)
                body_pct = body / rng if rng > 0 else 0.0
            except (TypeError, ValueError):
                body_pct = 0.0
        if body_pct >= EDIFICIO_BODY_FILTER_MIN_RATIO:
            return True
        return _detect_hammer_pattern(candle, direction, EDIFICIO_HAMMER_MIN_TAIL_RATIO)

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
