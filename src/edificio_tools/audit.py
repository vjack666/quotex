"""Audit — trazabilidad a experimento (R8).

TODO estado BUY/SELL/NO_TRADE DEBE ser reproducible hasta el conjunto de
herramientas y sus EXP-XXX que lo produjeron, con sus WR/n individuales y
combinados registrados en un reporte inmutable. Este modulo captura esa
traza a partir de la Decision del Ensamblador + el catalogo de herramientas.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .assembler import Decision
from .registry import Tool, active_tools


@dataclass
class AuditRecord:
    action: str
    direction: Optional[str]
    conflict: bool
    reason: str
    tools: List[Dict[str, object]] = field(default_factory=list)
    wr_combined: Optional[float] = None
    n_combined: Optional[int] = None

    def to_json(self) -> str:
        return json.dumps(self.__dict__, default=str, ensure_ascii=False)


def audit_decision(decision: Decision,
                   tools: Optional[List[Tool]] = None) -> AuditRecord:
    """Construye el registro de trazabilidad inmutable (R8)."""
    tools = tools or active_tools()
    tool_records: List[Dict[str, object]] = []
    wr_sum = 0.0
    n_sum = 0
    for ev in decision.evidences:
        t = next((t for t in tools if t.name == ev.tool), None)
        rec = {
            "tool": ev.tool,
            "direction": ev.direction,
            "strength": ev.strength,
            "confidence": ev.confidence,
        }
        if t is not None:
            rec["exp_ref"] = t.exp_ref
            rec["wr_pooled"] = t.wr_pooled
            rec["n"] = t.n
            rec["domain"] = t.domain
            wr_sum += t.wr_pooled
            n_sum += t.n
        tool_records.append(rec)
    n = len(tool_records)
    rec = AuditRecord(
        action=decision.action,
        direction=decision.direction,
        conflict=decision.conflict,
        reason=decision.reason,
        tools=tool_records,
        wr_combined=(wr_sum / n) if n else None,
        n_combined=(n_sum if n else None),
    )
    return rec
