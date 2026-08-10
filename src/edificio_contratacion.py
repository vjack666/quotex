"""Edificio de Contratación — Sistema de 3 pisos para selección de activos.

Cada activo que pasa los filtros básicos entra al edificio y sube piso por piso:

  P1 (Recepción)     → paga bien
  P2 (Cerebro)       → freno OK + extremo OK, espera retorno del estocástico a su línea
  P3 (Cámara presión) → válvula: K sale del extremo en dirección del trade Y la
                        separación K-D abre (presión acumulada); o cruce limpio (modo viejo)
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
    EDIFICIO_POST_BRAKE_MIN_RATIO,
    EDIFICIO_SEPARATION_WAIT_SEC,
    EDIFICIO_SMALLBODY_MAX_BODY_RATIO,
    EDIFICIO_SMALLBODY_WICK_DOMINANCE,
    EDIFICIO_P3_MODE,
    EDIFICIO_P2_MAX_HOLD_VELAS,
    EDIFICIO_DESCARTE_STICKY_THRESHOLD,
    EDIFICIO_P3_NO_5M_GATE,
    EDIFICIO_P3_GATE_MODE,
    EDIFICIO_P3_DESVIO_K,
    EDIFICIO_P3_EVOLVE_WINDOW,
    EDIFICIO_P3_PAPER_ENTRY_OFFSET,
    EDIFICIO_P3_PAPER_EXIT_OFFSET,
)
from sequence_engine import SequenceEngine, SequenceCard

log = logging.getLogger("edificio_contratacion")

# Fabrica de herramientas del Edificio (feature 40, SDD fabrica_herramientas_edificio).
# Capa de decision de ORDEN (ensamblador/inspector/gobernador) que se anade al
# final del embudo del edificio. La fabrica es parte del repo (src/edificio_tools),
# por lo que el import es directo: si falta, el error es real y visible.
import edificio_tools as _fab

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
    stoch_k_prev: Optional[float] = None  # K de la vela anterior (evolución válvula)
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

    # Telemetría Fase A: origen de la dirección del trade en el scanner.
    direction_source: Optional[str] = None     # "M1" | "M15" | ""

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
    # ── Leyes de permanencia/descarte P2 (2026-08-08) ──────────────────
    # "Historia del estocástico": al entrar a P2 se graba la zona de extremo
    # (20 CALL / 80 PUT) y la dirección. La promoción a P3 ocurre cuando el
    # estocástico REGRESA a esa línea habiendo SALIDO antes de la zona.
    p2_entry_extreme: Optional[float] = None    # 20.0 (CALL) o 80.0 (PUT) al entrar a P2
    p2_left_zone: bool = False                 # True si el stoch salió de [20,80] estando en P2
    p2_hold_velas: int = 0                     # velas M15 en P2 sin retorno al extremo
    p2_descartado: bool = False                # Ley de descarte: candidatura inválida
    p2_descartado_motivo: Optional[str] = None # razón del descarte (caja negra)
    p3_kd_history: list = field(default_factory=list)  # últimas |K-D| en P3 (válvula: evolución)
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


def _as_dict_candles(candles) -> list[dict]:
    """Normaliza velas a dicts: el Edificio siempre las lee con .get().

    Acepta dicts ya serializados o dataclasses Candle (models.Candle), que es
    lo que entrega el scanner. Sin esto, `'Candle' object has no attribute
    'get'` rompe la evaluación del activo.
    """
    out: list[dict] = []
    for c in candles or []:
        if isinstance(c, dict):
            out.append(c)
            continue
        o, h, l, cl = (
            float(getattr(c, "open", 0.0)),
            float(getattr(c, "high", 0.0)),
            float(getattr(c, "low", 0.0)),
            float(getattr(c, "close", 0.0)),
        )
        out.append({
            "ts": int(getattr(c, "ts", 0) or 0),
            "open": o, "high": h, "low": l, "close": cl,
            "body": abs(cl - o), "range": h - l,
        })
    return out


def _detect_small_body_rejection(
    candle: Optional[dict],
    direction: str,
    max_body_ratio: float,
    wick_dominance: float,
) -> bool:
    """Vela de 'cuerpo pequeño con rechazo direccional' (alternativa al martillo).

    Pasa si el cuerpo es pequeño (body/range <= max_body_ratio) Y la mecha
    dominante apunta en la dirección del trade:
      CALL → mecha INFERIOR dominante (rechazo de mínimos).
      PUT  → mecha SUPERIOR dominante (rechazo de máximos).
    La mecha dominante debe ser >= wick_dominance × la otra (menos rígido que
    el viejo martillo: sin exigir cola >= 2× body ni otra < 0.3× rango).
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
    rng = h - l
    if rng <= 0:
        return False
    if (body / rng) > max_body_ratio:
        return False
    upper = h - max(o, c)
    lower = min(o, c) - l
    direction = (direction or "").upper()
    if direction == "CALL":
        return lower >= wick_dominance * upper
    if direction == "PUT":
        return upper >= wick_dominance * lower
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
        self._sent_orders: Dict[str, Dict[str, Any]] = {}
        self._sequence_engine = SequenceEngine(
            min_dwell_ticks={"RECEPCION": 1, "CEREBRO": 1, "ENTRADA": 0},
            min_kd_distance=2.0,
        )
        self._sequence_cards: Dict[str, SequenceCard] = {}

    def _get_sequence_card(self, asset: str, direction: str, payout: int) -> SequenceCard:
        if asset not in self._sequence_cards:
            self._sequence_cards[asset] = SequenceCard(
                hypothesis_id=asset,
                asset=asset,
                direction=direction,
            )
        seq_card = self._sequence_cards[asset]
        if direction and not seq_card.direction:
            seq_card.direction = direction
        if payout:
            seq_card.hypothesis_id = f"{asset}:{payout}%"
        return seq_card

    def _sync_sequence_card(self, asset: str, now_ts: str) -> SequenceCard:
        """Adapta el estado del Edificio a la secuencia, vela a vela (Ley 1/2/5/12).

        No fuerza `current_floor` por fuera (Ley 5/3): el motor decide el
        avance según sus propias condiciones. El piso real del Edificio se pasa
        como feature `edificio_floor` para que el motor lo use como contexto, no
        como comando. Una sola evaluación por llamada (Ley 2/12): quien llama
        itera vela a vela; nunca un while que empuja la secuencia a ENTRADA.
        """
        card = self._cards.get(asset)
        seq_card = self._get_sequence_card(
            asset=asset,
            direction=getattr(card, "direction", "") or "",
            payout=int(getattr(card, "payout", 0) or 0),
        )
        features = {
            "payout": float(getattr(card, "payout", 0) or 0),
            "brake_ok": bool(getattr(card, "brake_ok", False)),
            "extreme_ok": bool(getattr(card, "extreme_ok", False)),
            "cross_ok": bool(getattr(card, "cross_ok", False)),
            "cross_limpieza_ok": not bool(getattr(card, "cross_sticky", False)),
            "kd_distance": float(getattr(card, "kd_distance", 0) or 0) if getattr(card, "kd_distance", None) is not None else None,
            "edificio_floor": getattr(card, "piso", PISO_FUERA),
        }
        # Una sola evaluación de la vela actual (Ley 2/12). El motor recibe el
        # piso REAL del Edificio como hecho observado y valida que la secuencia
        # se construyó legalmente (Ley 5/3/4); el llamador repite por cada vela.
        edificio_floor = getattr(card, "piso", PISO_FUERA)
        self._sequence_engine.observe_floor(seq_card, edificio_floor, features, timestamp=now_ts)
        return seq_card

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
        card.stoch_k_prev = card.stoch_k   # K de la vela anterior (para evolución de válvula)
        card.stoch_k = stoch_k
        card.stoch_d = stoch_d
        if stoch_k is not None and stoch_d is not None:
            card.kd_distance = abs(float(stoch_k) - float(stoch_d))
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
            card.candles_15m_snap = _as_dict_candles(candles_15m)[-24:]
        if candles_5m:
            card.candles_5m_snap = _as_dict_candles(candles_5m)[-24:]

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
            # Tarjeta de acceso al P2: el FRENO. El extremo se espera DENTRO de
            # P2 (Prueba B), no es requisito de la puerta. El freno es una
            # ALERTA de preparación: el par quedó listo para esperar el cruce.
            if brake_ok:
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
                    # Ley de permanencia: grabar la zona de extremo del stoch
                    # al entrar a P2 (la "historia" que debe cerrarse al volver).
                    # Dirección ya definida por el scanner; extremo según dir.
                    card.p2_entry_extreme = 20.0 if (direction or "").upper() == "CALL" else 80.0
                    card.p2_left_zone = False
                    card.p2_hold_velas = 0
                    card.p2_descartado = False
                    card.p2_descartado_motivo = None
                    # Ley de descarte (anti-falsa entrada): si el cruce fue
                    # pegajoso al entrar a P2, la candidatura es inválida.
                    if abs(float(stoch_k or 0) - float(stoch_d or 0)) < EDIFICIO_DESCARTE_STICKY_THRESHOLD:
                        card.p2_descartado = True
                        card.p2_descartado_motivo = (
                            f"cruce pegajoso al entrar a P2 (|K-D|<{EDIFICIO_DESCARTE_STICKY_THRESHOLD})"
                        )
                    card.reason = f"P2 OK — tarjeta de acceso: freno CONFIRMED con vela M15 cerrada ({payout}%)"
                    log.info(
                        "[EDIFICIO] %s → P2 (tarjeta de acceso: freno CONFIRMED ratio=%.2f, payout=%d%%)",
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
            # Se perdió el freno antes del cierre de la vela: cancelar la candidatura.
            if card.brake_at is not None:
                card.brake_verdict = "CANCELLED"
                log.info("[EDIFICIO] %s: freno CANCELLED (se perdió el brake)", asset)
            card.brake_at = None
            card.brake_confirmed_at = None
            self._brake_clear_reference(card)
            card.reason = f"P1 OK — esperando freno (tarjeta de acceso a P2) ({payout}%)"
            return "stay"

        if card.piso == PISO_2:
            if not payout_ok:
                return self._expulsar(asset)
            # ── Ley de descarte (anti-falsa entrada) ──────────────────────
            if card.p2_descartado:
                card.reason = f"P2 descartado — {card.p2_descartado_motivo or 'inválido'} ({payout}%)"
                log.info("[EDIFICIO] %s: P2 descartado (%s), baja a P1", asset, card.p2_descartado_motivo)
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
                return "bajo"
            # Modo de puerta P2→P3
            if EDIFICIO_P3_MODE == "return_to_extreme":
                return self._p2_return_to_extreme(asset, direction, payout, brake_ok,
                                                  extreme_ok, cross_ok, cross_sticky, now, card)
            # Modo original: cruce limpio + separación 60s
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
            # Estadía en P2: se sostiene con la tarjeta (freno CONFIRMED con vela
            # cerrada) + extremo vigente como contexto del cruce. El brake_ok
            # instantáneo (vela en formación) NO revoca la tarjeta — es ruidoso.
            if card.brake_verdict == "CONFIRMED" and extreme_ok:
                card.reason = f"P2 OK — esperando cruce K/D ({payout}%)"
                return "stay"
            if card.brake_verdict != "CONFIRMED":
                card.reason = f"P2 pendiente — sin tarjeta de acceso ({payout}%)"
                log.info("[EDIFICIO] %s: baja a P1 (sin freno CONFIRMED)", asset)
            else:
                card.reason = f"P2 pendiente — extremo perdido ({payout}%)"
                log.info("[EDIFICIO] %s: baja a P1 (extremo perdido)", asset)
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
            # ── Disparador de entrada (rama por modo de puerta P3) ──
            if EDIFICIO_P3_GATE_MODE == "cruce_limpio":
                if not cross_ok or cross_sticky:
                    card.reason = f"P3 OK — esperando cruce limpio ({payout}%)"
                    return "stay"
            else:  # "valvula" (2026-08-08): P3 = cámara de presión
                if not self._p3_valve_open(card, k=float(stoch_k or 0), d=float(stoch_d or 0), direction=direction):
                    card.reason = f"P3 OK — válvula cerrada (esperando salida+separación K/D) ({payout}%)"
                    return "stay"
            # Gate vela 5m: solo para modo cruce_limpio (la válvula ya filtra).
            if EDIFICIO_P3_GATE_MODE == "cruce_limpio" and not EDIFICIO_P3_NO_5M_GATE:
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
                    _next = self._cards.get(asset)
                    if _next is None or _next.piso != PISO_3:
                        card.entry_pending = False
                        card.pending_since = None
                        card.reason = (
                            f"P3 OK — asset no vigente al contratar "
                            f"({('ausente' if _next is None else f'piso={_next.piso}')}) ({payout}%)"
                        )
                        log.info("[EDIFICIO] %s: descartado CONTRATADO — asset no vigente", asset)
                        return "stay"
                    from datetime import datetime, timezone
                    _ts = datetime.now(timezone.utc).isoformat() + "Z"
                    seq_card = self._sync_sequence_card(asset, now_ts=_ts)
                    if not self._sequence_engine.is_contratado_valido(seq_card):
                        reject_reason = getattr(seq_card, "reject_reason", None)
                        if hasattr(seq_card, "history") and seq_card.history:
                            last = seq_card.history[-1]
                            reject_reason = last.reject_reason if hasattr(last, "reject_reason") else reject_reason
                        card.entry_pending = False
                        card.pending_since = None
                        card.reason = (
                            f"CONTRATADO bloqueado por secuencia "
                            f"({reject_reason or 'secuencia_no_valida'}) ({payout}%)"
                        )
                        log.info(
                            "[EDIFICIO] %s: CONTRATADO bloqueado por secuencia (%s)",
                            asset,
                            reject_reason or "secuencia_no_valida",
                        )
                        return "stay"
                    card.piso = CONTRATADO
                    card.contratado_at = now
                    card.order_status = "pending"
                    card.reason = f"CONTRATADO — delay ejecución cumplido ({payout}%)"

                    # ── CAPA FABRICA DE HERRAMIENTAS (feature 40, R3/R4/R5/R6/R8) ──
                    # Fail-safe: si la fabrica no esta disponible o falla, el edificio
                    # conserva su comportamiento original (el CONTRATADO ya ocurrió).
                    if card.direction:
                        try:
                            decision = _fab.assemble_from_tools(card.direction)
                            if decision.action == "NO_TRADE":
                                card.piso = PISO_3
                                card.contratado_at = None
                                card.order_status = ""
                                card.reason = (
                                    f"CONTRATADO bloqueado por FABRICA: "
                                    f"{decision.reason} ({payout}%)"
                                )
                                log.info(
                                    "[EDIFICIO] %s: CONTRATADO bloqueado por fabrica (%s)",
                                    asset, decision.reason,
                                )
                                return "stay"
                            # Gobernador: veto por drawdown proyectado (R6)
                            tools = _fab.active_tools()
                            wr_comb = sum(t.wr_pooled for t in tools) / max(1, len(tools))
                            gov = _fab.Governor(bankroll=1000.0, dd_limit=0.20, payout=payout / 100.0)
                            sizing = gov.size(wr=wr_comb / 100.0, n=200)
                            if not sizing.allowed:
                                card.piso = PISO_3
                                card.contratado_at = None
                                card.order_status = ""
                                card.reason = (
                                    f"CONTRATADO bloqueado por GOBERNADOR: {sizing.reason}"
                                )
                                log.info(
                                    "[EDIFICIO] %s: bloqueado por Gobernador (%s)",
                                    asset, sizing.reason,
                                )
                                return "stay"
                            # Auditoria inmutable (R8) — registra la traza del BUY/SELL
                            rec = _fab.audit_decision(decision, tools)
                            card.reason = (
                                f"CONTRATADO — fabrica OK ({decision.action}, "
                                f"WRcomb={rec.wr_combined}, ncomb={rec.n_combined}) ({payout}%)"
                            )
                        except Exception as _fab_err:  # pragma: no cover - fail-safe
                            log.warning(
                                "[EDIFICIO] fabrica fallo en CONTRATADO (%s) — se conserva original",
                                _fab_err,
                            )

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

    def _p2_return_tracking(self, card: BuildingCard, k: Optional[float], extreme: Optional[float]) -> tuple:
        """Sigue la 'historia del estocástico' en P2 (medido en velas, no tiempo).

        Devuelve (retorno, expirado):
          - retorno=True  si el stoch volvió a la zona de extremo habiendo
            salido antes (la historia se cerró → promover a P3).
          - expirado=True si lleva EDIFICIO_P2_MAX_HOLD_VELAS velas en P2 sin
            retorno (ley de permanencia → descarte).
        """
        # Detectar salida de la zona de EXTREMO (no del rango medio).
        # Zona de extremo = k<=20 (CALL) o k>=80 (PUT). "Salir" = k sube de 20
        # (CALL) o baja de 80 (PUT). El retorno = volver a tocar la línea.
        in_zone = (k is not None) and (float(k) <= 20.0 or float(k) >= 80.0)
        # El estocástico "salió" si estuvo fuera de [20,80] después de entrar a P2.
        if not in_zone:
            card.p2_left_zone = True
        # Retorno a la línea de extremo de entrada
        if extreme is not None and k is not None:
            if extreme == 20.0 and float(k) <= 20.0 and card.p2_left_zone:
                return True, False
            if extreme == 80.0 and float(k) >= 80.0 and card.p2_left_zone:
                return True, False
        return False, False
    def _p2_return_to_extreme(self, asset, direction, payout, brake_ok,
                              extreme_ok, cross_ok, cross_sticky, now, card) -> str:
        """Puerta P2→P3 modo 'return_to_extreme' (2026-08-08).

        El estocástico que entró en extremo al P2 debe REGRESAR a esa línea
        (habiendo salido antes). Sin cronómetro: se cuenta en velas M15. Si no
        regresa en EDIFICIO_P2_MAX_HOLD_VELAS velas → ley de permanencia:
        descarte (baja a P1).
        """
        k = card.stoch_k
        extreme = card.p2_entry_extreme
        # Incrementar el contador de permanencia por ciclo (1 ciclo = 1 vela M15)
        card.p2_hold_velas += 1
        retorno, _ = self._p2_return_tracking(card, k, extreme)
        if retorno:
            card.piso = PISO_3
            card.p3_at = now
            card.reason = f"P3 OK — estocástico regresó a extremo {extreme:.0f} ({payout}%)"
            log.info("[EDIFICIO] %s → P3 (retorno a extremo %.0f, payout=%d%%)", asset, extreme, payout)
            return "subio"
        # Ley de permanencia: plazo agotado sin retorno → descarte
        if card.p2_hold_velas >= EDIFICIO_P2_MAX_HOLD_VELAS:
            card.p2_descartado = True
            card.p2_descartado_motivo = (
                f"sin retorno a extremo en {EDIFICIO_P2_MAX_HOLD_VELAS} velas M15"
            )
            card.reason = f"P2 descartado — {card.p2_descartado_motivo} ({payout}%)"
            log.info("[EDIFICIO] %s: P2 descartado (permanencia agotada), baja a P1", asset)
            card.piso = PISO_1
            card.p2_at = None
            return "bajo"
        card.reason = f"P2 OK — esperando retorno a extremo {extreme:.0f} ({payout}%)"
        return "stay"

    def _p3_valve_open(self, card: BuildingCard, k: float, d: float, direction: str) -> bool:
        """Válvula P3→CONTRATADO (modo 'valvula', 2026-08-08).

        P3 es cámara de presión: el stoch ya regresó a su línea (puerta P2→P3).
        La válvula se ABRE cuando AMBAS condiciones se dan en la vela actual:
          (a) SALIDA DEL EXTREMO en dirección del trade:
              CALL → K > 20 y K >= K_prev (sale y sigue subiendo)
              PUT  → K < 80 y K <= K_prev (sale y sigue bajando)
          (b) SEPARACIÓN K-D abre con presión acumulada:
              |K-D| >= EDIFICIO_P3_DESVIO_K  Y  la separación viene subiendo
              en las últimas EDIFICIO_P3_EVOLVE_WINDOW velas (no un salto aislado).
        Si vuelve a pegarse o al extremo → la válvula se cierra (sigue en P3,
        no descarta: es permanencia, no descarte).
        """
        extreme = card.p2_entry_extreme
        # (a) salida del extremo en dirección del trade
        if extreme == 20.0:  # CALL
            if not (k > 20.0 and k >= float(getattr(card, "stoch_k_prev", k))):
                return False
        elif extreme == 80.0:  # PUT
            if not (k < 80.0 and k <= float(getattr(card, "stoch_k_prev", k))):
                return False
        else:
            return False
        # (b) separación K-D con evolución (presión acumulada)
        sep = abs(k - d)
        card.p3_kd_history.append(sep)
        if len(card.p3_kd_history) > EDIFICIO_P3_EVOLVE_WINDOW + 1:
            card.p3_kd_history.pop(0)
        if sep < EDIFICIO_P3_DESVIO_K:
            return False
        # evolución: las últimas ventanas deben venir subiendo (no ruido)
        if len(card.p3_kd_history) >= 2:
            recent = card.p3_kd_history[-EDIFICIO_P3_EVOLVE_WINDOW:]
            growing = all(recent[i] <= recent[i + 1] for i in range(len(recent) - 1))
            if not growing:
                return False
        return True

    def _5m_gate_pass(self, candle: Optional[dict], direction: str) -> bool:
        """Vela 5m válida para contratar en P3.

        Pasa si el body es fuerte (body_pct >= EDIFICIO_BODY_FILTER_MIN_RATIO)
        o si es una vela de cuerpo pequeño respecto a la mecha (doji/spinning
        top: body/range <= EDIFICIO_SMALLBODY_MAX_BODY_RATIO). Dirección-agnóstico:
        reemplaza al martillo direccional. Sin contexto 5m (None) no bloquea.
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
        return _detect_small_body_rejection(
            candle, direction,
            EDIFICIO_SMALLBODY_MAX_BODY_RATIO, EDIFICIO_SMALLBODY_WICK_DOMINANCE,
        )

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
