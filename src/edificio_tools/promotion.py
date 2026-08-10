"""Promotion — candados de dominio y robustez (R9 / R10).

R9 (Charter Art. 10/13): si una herramienta solo tiene evidencia en REAL, no se
promueve a OTC sin validacion OTC previa. REAL es microscopio, OTC es ensayo
clinico.

R10 (no promocion por WR aislada): no se promueve usando solo WR; se exige n,
holdout/OOS, y (para composiciones) n combinado (R7).

Este modulo NO reemplaza el Promotion Gate del laboratorio (strategy_lab/
promotion_gate.py): es la capa de la fabrica que aplica esos mismos principios
a las herramientas del Edificio antes de CONTRATAR en un dominio dado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .registry import Tool


@dataclass(frozen=True)
class PromotionVerdict:
    allowed: bool
    domain: str
    failed: List[str]
    reason: str


# Dominios validos
REAL = "REAL"
OTC = "OTC"
BOTH = "BOTH"


def check_promotion(tools: List[Tool], target_domain: str,
                    min_n: int = 100,
                    require_combined_n: bool = False,
                    combined_min_n: int = 1000) -> PromotionVerdict:
    """Evalua si el conjunto de herramientas puede promoverse a target_domain.

    R9: ninguna herramienta activa puede promoverse a OTC si su evidencia es
        solo REAL (salvo que el target sea REAL).
    R10: cada herramienta activa debe cumplir n >= min_n; si es composicion,
        exige n combinado >= combined_min_n.
    """
    failed: List[str] = []
    target = target_domain.upper()

    for t in tools:
        if not t.active:
            continue
        # R9: dominio
        if target == OTC and t.domain == REAL:
            failed.append(f"{t.name}: evidencia solo REAL, no promover a OTC")
            continue
        # R10: n minimo individual
        if t.n < min_n:
            failed.append(f"{t.name}: n={t.n} < min_n={min_n}")
        # R10: composicion exige n combinado
        if require_combined_n and t.n < combined_min_n:
            failed.append(f"{t.name}: n combinado={t.n} < requerido {combined_min_n}")

    if failed:
        return PromotionVerdict(
            allowed=False, domain=target, failed=failed,
            reason="candados de promocion fallidos (R9/R10)",
        )
    return PromotionVerdict(
        allowed=True, domain=target, failed=[],
        reason="promocion permitida en dominio " + target,
    )
