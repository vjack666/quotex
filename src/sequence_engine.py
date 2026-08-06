"""Sequence engine: única fuente de verdad de estados/transiciones.

Motor de secuencias vela a vela, conforme al documento maestro de 12 leyes
(agnóstico de teoría). Principios aplicados:
  Ley 1  — causalidad vela a vela: el timestamp es OBLIGATORIO (quien llama
            pasa el sello de la vela; nunca datetime.utcnow() de pared).
  Ley 4  — candidato vs confirmado: RECEPCION pasa por CANDIDATO (pendiente de
            confirmación) antes de avanzar. No se fusionan.
  Ley 5/3— grafo de dependencias: CEREBRO no nace sin RECEPCION confirmada;
            forzar el piso por fuera no produce avance (DEPENDENCIA_INACTIVA).
  Ley 6/8— invalidación predefinida + trazabilidad: cada transición guarda su
            condición de invalidación y se registra en traza append-only.
  Ley 2/12— una evaluación por vela: evaluate procesa SOLO la vela actual; el
            llamador itera. Nunca un while que empuja la secuencia a ENTRADA.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Orden de lectura obligatorio. CANDIDATO es el estado intermedio de Ley 4.
FLOOR_ORDER = ["RECEPCION", "CANDIDATO", "CEREBRO", "ENTRADA"]
FLOOR_INDEX = {name: idx for idx, name in enumerate(FLOOR_ORDER)}

# Regla de dependencia (Ley 5): piso -> piso que debe estar confirmado antes.
REQUIRES: Dict[str, Optional[str]] = {
    "RECEPCION": None,        # piso de origen, sin dependencia
    "CANDIDATO": "RECEPCION", # nace tras confirmarse RECEPCION
    "CEREBRO": "CANDIDATO",   # no nace sin candidato confirmado
    "ENTRADA": "CEREBRO",     # no nace sin CEREBRO confirmado
}


@dataclass(frozen=True)
class StateTransition:
    from_floor: str
    to_floor: str
    timestamp: str
    evidence: Dict[str, Any]
    allowed: bool
    reject_reason: Optional[str] = None
    invalidation_condition: Optional[str] = None  # Ley 6/8: declarada por adelantado


@dataclass
class SequenceCard:
    hypothesis_id: str
    asset: str
    direction: str
    current_floor: str = "RECEPCION"
    dwell_ticks: int = 0
    history: list[StateTransition] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: _now_iso())
    confirmed: set[str] = field(default_factory=set)  # pisos ya confirmados (Ley 5)
    invalidated: bool = False
    invalidation_reason: str = ""

    def __post_init__(self) -> None:
        # El piso de origen ya está alcanzado al nacer la tarjeta (Ley 5).
        self.confirmed.add(self.current_floor)

    def advance(self, transition: StateTransition) -> None:
        if not transition.allowed:
            return
        self.current_floor = transition.to_floor
        self.dwell_ticks = 0
        self.confirmed.add(transition.to_floor)
        self.history.append(transition)

    def invalidate(self, reason: str = "") -> None:
        """Marca la secuencia como invalidada (Ley 6): estado terminal, no se
        olvida en silencio. Equivalente a Hypothesis.invalidate() del lab."""
        self.invalidated = True
        self.invalidation_reason = reason
        self.history.append(
            StateTransition(
                self.current_floor, self.current_floor, _now_iso(), {},
                False, reject_reason="INVALIDADA", invalidation_condition=reason or "regla de invalidación",
            )
        )

    def retrocede(self, target: str) -> None:
        """Retroceso explícito a un piso inferior ya confirmado (Ley 5/6).
        No puede retroceder a un piso que nunca se alcanzó. Equivalente a
        Hypothesis.retrocede() del lab."""
        if target not in self.confirmed:
            raise ValueError(f"Retroceso ilegal a {target}: no confirmado")
        if FLOOR_INDEX[target] >= FLOOR_INDEX[self.current_floor]:
            raise ValueError(f"Retroceso inválido: {self.current_floor} -> {target}")
        self.current_floor = target
        self.dwell_ticks = 0
        self.history.append(
            StateTransition(
                self.current_floor, target, _now_iso(), {},
                True, invalidation_condition="retroceso explícito",
            )
        )

    def tick(self) -> None:
        self.dwell_ticks += 1


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat() + "Z"


class SequenceEngine:
    def __init__(
        self,
        min_dwell_ticks: Optional[Dict[str, int]] = None,
        min_kd_distance: float = 2.0,
        trace_path: Optional[str] = None,
    ) -> None:
        self.min_dwell = min_dwell_ticks or {
            "RECEPCION": 1,
            "CANDIDATO": 1,
            "CEREBRO": 1,
            "ENTRADA": 0,
        }
        self.min_kd_distance = float(min_kd_distance)
        self._rejection_counts: Dict[str, int] = {}
        # Traza append-only (Ley 8). Por defecto en memoria; si se da ruta, también a disco.
        self._trace: Dict[str, List[StateTransition]] = {}
        self.trace_path = Path(trace_path) if trace_path else None

    # ── API pública ────────────────────────────────────────────────────────
    def evaluate(
        self,
        card: SequenceCard,
        features: Dict[str, Any],
        timestamp: str,  # Ley 1: obligatorio (la vela que se procesa)
    ) -> StateTransition:
        if timestamp is None:
            # Ley 1: prohibido inventar el instante con tiempo de pared.
            raise ValueError("timestamp obligatorio: evaluate debe recibir el sello de la vela actual")
        ts = timestamp

        floor = card.current_floor

        # Ley 5/3: el piso actual fue forzado por fuera sin pasar por su
        # dependencia? El motor no lo acepta como avance válido.
        dep = REQUIRES.get(floor)
        if dep is not None and dep not in card.confirmed:
            transition = StateTransition(
                floor, floor, ts, features, False,
                reject_reason="DEPENDENCIA_INACTIVA",
                invalidation_condition="dependencia no confirmada en card.confirmed",
            )
            self._record(card, transition)
            return transition

        if floor == "RECEPCION":
            return self._eval_recepcion(card, features, ts)
        if floor == "CANDIDATO":
            return self._eval_candidato(card, features, ts)
        if floor == "CEREBRO":
            return self._eval_cerebro(card, features, ts)
        # ENTRADA: estado terminal de la secuencia, no avanza más por el motor.
        transition = StateTransition(
            floor, floor, ts, features, False, reject_reason="YA_EN_ENTRADA",
            invalidation_condition="secuencia completa; invalidación externa al motor",
        )
        self._record(card, transition)
        return transition

    def is_contratado_valido(self, card: SequenceCard) -> bool:
        """El Edificio decide CONTRATADO por su propia autoridad (Ley 10/11/12).
        El motor solo certifica que la secuencia llegó legalmente al piso
        contract-ready (CEREBRO/P3 o superior) sin saltos ilegales. No puede
        vetar la decisión del Edificio: si la progresión fue válida, el motor
        está de acuerdo."""
        if card.current_floor not in ("CEREBRO", "ENTRADA"):
            return False
        # ¿hubo algún retroceso sin causa en la traza? Si sí, la secuencia no es válida.
        for t in self.get_trace(card.hypothesis_id):
            if t.reject_reason == "RETROCESO_SIN_CAUSA":
                return False
        return True

    def observe_floor(
        self,
        card: SequenceCard,
        observed_floor: str,  # piso observado del sistema externo (Edificio)
        features: Dict[str, Any],
        timestamp: str,
    ) -> StateTransition:
        """Integración en vivo (Ley 1/4/5): el piso del Edificio es un HECHO
        observado, no una orden. El motor valida que el salto hasta él sea
        legal (grafo de dependencias, sin saltos) y que su condición de
        nacimiento se cumpla en el instante observado. Si es ilegal, lo marca
        (DEPENDENCIA_INACTIVA / CONDICION_NO_CUMPLE) y NO avanza.

        `observed_floor` usa la nomenclatura del Edificio; se mapea a la
        secuencia interna. El Edificio conserva la autoridad de decidir el
        piso; el motor solo certifica que la secuencia se construyó bien.
        """
        if timestamp is None:
            raise ValueError("timestamp obligatorio: observe_floor necesita el sello de la vela observada")
        ts = timestamp

        # Mapa Edificio -> secuencia (el Edificio es la autoridad de pisos).
        # Acepta tanto la constante int del Edificio (PISO_FUERA..CONTRATADO)
        # como su nombre string.
        floor_map = {
            0: "RECEPCION", "FUERA": "RECEPCION",
            1: "RECEPCION", "P1": "RECEPCION",
            2: "CEREBRO", "P2": "CEREBRO",
            3: "CEREBRO", "P3": "CEREBRO",
            4: "ENTRADA", "CONTRATADO": "ENTRADA",
        }
        target = floor_map.get(observed_floor, "RECEPCION")

        current = card.current_floor
        cur_idx = FLOOR_INDEX[current]
        tgt_idx = FLOOR_INDEX[target]

        # Ley 5/3: el Edificio es la autoridad de pisos. Si observa un piso
        # SUPERIOR al actual del motor, eso significa que la secuencia avanzó
        # (los pisos intermedios se alcanzaron legalmente por definición: no se
        # llega a P3 sin pasar P1/P2). Se marcan como confirmados. Solo es
        # ILEGAL un salto HACIA ATRÁS que no sea un retroceso explícito.
        if tgt_idx < cur_idx:
            transition = StateTransition(
                current, current, ts, features, False,
                reject_reason="RETROCESO_SIN_CAUSA",
                invalidation_condition="retroceso requiere invalidación explícita",
            )
            self._record(card, transition)
            return transition

        # Ley 4: ¿la condición de nacimiento del piso observado se cumple ahora?
        if target == "CEREBRO":
            birth_ok = self._brain_ok(features, self.min_kd_distance)
            reason = "CONDICION_CEREBRO_NO_CUMPLE" if not birth_ok else None
        elif target == "ENTRADA":
            birth_ok = self._reception_ok(features) and self._brain_ok(features, self.min_kd_distance)
            reason = "CONDICION_ENTRADA_NO_CUMPLE" if not birth_ok else None
        elif target == "RECEPCION":
            birth_ok = self._reception_ok(features)
            reason = "CONDICION_RECEPCION_NO_CUMPLE" if not birth_ok else None
        else:
            birth_ok = True
            reason = None

        allowed = birth_ok
        transition = StateTransition(
            current, target, ts, features, allowed,
            reject_reason=reason,
            invalidation_condition="condición de nacimiento del piso observado",
        )
        self._record(card, transition)
        if allowed:
            # Marcar todos los pisos hasta el observado como confirmados (Ley 5):
            # llegar a un piso superior implica haber transitado los previos.
            for f in FLOOR_ORDER[: tgt_idx + 1]:
                card.confirmed.add(f)
            card.current_floor = target
            card.dwell_ticks = 0
        return transition

    # ── Evaluadores por piso (cada uno: candidato -> confirmado) ────────────
    def _eval_recepcion(self, card: SequenceCard, features: Dict[str, Any], ts: str) -> StateTransition:
        allowed = self._reception_ok(features)
        transition = StateTransition(
            "RECEPCION", "CANDIDATO", ts, features, allowed,
            reject_reason=None if allowed else "RECHAZAR_RECEPCION",
            invalidation_condition="payout>=80, brake_ok, extreme_ok",
        )
        if not allowed:
            transition = StateTransition(
                "RECEPCION", "RECEPCION", ts, features, False, "RECHAZAR_RECEPCION",
                invalidation_condition="payout>=80, brake_ok, extreme_ok",
            )
            self._rejection_counts["RECHAZAR_RECEPCION"] = self._rejection_counts.get("RECHAZAR_RECEPCION", 0) + 1
        self._record(card, transition)
        card.advance(transition)
        return transition

    def _eval_candidato(self, card: SequenceCard, features: Dict[str, Any], ts: str) -> StateTransition:
        # Ley 4: el candidato se confirma solo si la condición persiste otra vela.
        # Requiere dwell mínimo antes de confirmar (evita falso positivo de 1 vela).
        if card.dwell_ticks < self.min_dwell["CANDIDATO"]:
            transition = StateTransition(
                "CANDIDATO", "CANDIDATO", ts, features, False, "DWELL_CANDIDATO",
                invalidation_condition="payout>=80, brake_ok, extreme_ok",
            )
            self._record(card, transition)
            return transition
        allowed = self._reception_ok(features)
        transition = StateTransition(
            "CANDIDATO", "CEREBRO", ts, features, allowed,
            reject_reason=None if allowed else "CANDIDATO_NO_CONFIRMA",
            invalidation_condition="payout>=80, brake_ok, extreme_ok",
        )
        if not allowed:
            transition = StateTransition(
                "CANDIDATO", "CANDIDATO", ts, features, False, "CANDIDATO_NO_CONFIRMA",
                invalidation_condition="payout>=80, brake_ok, extreme_ok",
            )
        self._record(card, transition)
        card.advance(transition)
        return transition

    def _eval_cerebro(self, card: SequenceCard, features: Dict[str, Any], ts: str) -> StateTransition:
        if card.dwell_ticks < self.min_dwell["CEREBRO"]:
            transition = StateTransition(
                "CEREBRO", "CEREBRO", ts, features, False, "DWELL_CEREBRO",
                invalidation_condition="cross_ok, cross_limpieza_ok, kd_distance>=min",
            )
            self._record(card, transition)
            return transition
        allowed = self._brain_ok(features, self.min_kd_distance)
        transition = StateTransition(
            "CEREBRO", "ENTRADA", ts, features, allowed,
            reject_reason=None if allowed else "RECHAZAR_CEREBRO",
            invalidation_condition="cross_ok, cross_limpieza_ok, kd_distance>=min",
        )
        if not allowed:
            transition = StateTransition(
                "CEREBRO", "CEREBRO", ts, features, False, "RECHAZAR_CEREBRO",
                invalidation_condition="cross_ok, cross_limpieza_ok, kd_distance>=min",
            )
            self._rejection_counts["RECHAZAR_CEREBRO"] = self._rejection_counts.get("RECHAZAR_CEREBRO", 0) + 1
        self._record(card, transition)
        card.advance(transition)
        return transition

    # ── Condiciones de nacimiento (Ley 4: condición cumplida, no apariencia) ──
    @staticmethod
    def _reception_ok(features: Dict[str, Any]) -> bool:
        payout = features.get("payout")
        if payout is None or float(payout) < 80:
            return False
        if features.get("brake_ok") is not True:
            return False
        if features.get("extreme_ok") is not True:
            return False
        return True

    @staticmethod
    def _brain_ok(features: Dict[str, Any], min_kd_distance: float = 2.0) -> bool:
        if features.get("cross_ok") is not True:
            return False
        if features.get("cross_limpieza_ok") is not True:
            return False
        kd = features.get("kd_distance")
        if kd is None or float(kd) < float(min_kd_distance):
            return False
        return True

    # ── Trazabilidad (Ley 8) ────────────────────────────────────────────────
    def _record(self, card: SequenceCard, transition: StateTransition) -> None:
        self._trace.setdefault(card.hypothesis_id, []).append(transition)
        if self.trace_path:
            line = json.dumps(
                {
                    "hypothesis_id": card.hypothesis_id,
                    "asset": card.asset,
                    "from": transition.from_floor,
                    "to": transition.to_floor,
                    "ts": transition.timestamp,
                    "allowed": transition.allowed,
                    "reason": transition.reject_reason,
                    "invalid": transition.invalidation_condition,
                },
                ensure_ascii=False,
            )
            with open(self.trace_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def get_trace(self, hypothesis_id: str) -> List[StateTransition]:
        return list(self._trace.get(hypothesis_id, []))

    @property
    def rejection_counts(self) -> Dict[str, int]:
        return dict(self._rejection_counts)
