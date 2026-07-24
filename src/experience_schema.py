"""Experience Engine — schema del arco de experiencia (sin I/O).

Unidad de información del Experience Engine: NO es un snapshot fotográfico, es un
ARCO completo del mercado:

    contexto_previo -> evento -> evolucion -> resultado -> consecuencias

El capturador NO etiqueta "soporte/resistencia/FVG". Guarda el arco TAL CUAL; las
IAs (que solo leen) descubren las etiquetas. Ver docs/experience_engine_concept.md.

Este módulo es puro: no toca disco, no importa pesos, no tiene reglas. Solo define
la forma del arco y su serialización round-trip (para que cualquier almacenamiento
lo persista y cualquier IA lo reconstruya íntegro).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class MarketExperience:
    """Una experiencia completa del mercado.

    Los campos *ctx/evento/evolucion/resultado/consecuencias* son dicts LIBRES a
    propósito: el capturador no impone esquema de detección. Cualquier IA futura
    lee lo que necesita. `raw` guarda lo crudo (velas/indicadores) por si una IA
    quiere recalcular algo que hoy no previmos.
    """

    # Identidad
    id: str = ""                       # fingerprint estable (ver fingerprint())
    ts: int = 0                        # timestamp del EVENTO (no del cierre)
    asset: str = ""
    tf: str = "M15"                    # marco del evento

    # Arco
    contexto_previo: Dict[str, Any] = field(default_factory=dict)
    evento: Dict[str, Any] = field(default_factory=dict)
    evolucion: Dict[str, Any] = field(default_factory=dict)
    resultado: Dict[str, Any] = field(default_factory=dict)
    consecuencias: Dict[str, Any] = field(default_factory=dict)

    # Crudo (velas/indicadores tal cual) — reutilizable por IAs futuras
    raw: Dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        """Hash estable de la experiencia (idempotente para el mismo arco)."""
        if self.id:
            return self.id
        payload = json.dumps(
            {
                "ts": self.ts,
                "asset": self.asset,
                "tf": self.tf,
                "evento": self.evento,
                "contexto_previo": self.contexto_previo,
            },
            sort_keys=True,
            default=str,
        )
        self.id = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
        return self.id

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d.get("id"):
            d["id"] = self.fingerprint()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MarketExperience":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        clean = {k: v for k, v in d.items() if k in known}
        exp = cls(**clean)
        if not exp.id:
            exp.id = exp.fingerprint()
        return exp

    def is_closed(self) -> bool:
        """Un arco está cerrado cuando tiene resultado medible."""
        return bool(self.resultado.get("decision") in ("WIN", "LOSS"))
