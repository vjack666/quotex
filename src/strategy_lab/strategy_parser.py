"""strategy_parser — descompone la estrategia PROPUESTA en pasos atómicos.

SL-R2 / SL-R12 / SL-R14: cada paso es un predicado sobre primitivas de
feature_calc (impulse_up, brake, stoch_overbought, rebote_down, ...) o una
referencia a una Ley #N de la Memoria. Valida que toda referencia a ley
exista en la Memoria (lectura). No inventa pasos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Primitivas soportadas (deben coincidir con feature_calc + la teoría de Rubén).
KNOWN_PRIMITIVES = {
    "impulse_up", "impulse_dn",
    "brake",                       # freno del impulso (LAB-001)
    "stoch_overbought", "stoch_oversold",
    "poi_zone",                    # nivel de reversión (POI)
    "rebote_up", "rebote_dn",
}


@dataclass(frozen=True)
class Step:
    name: str
    kind: str                     # "primitive" | "law_ref"
    spec: dict[str, Any] = field(default_factory=dict)

    def is_law(self) -> bool:
        return self.kind == "law_ref"


@dataclass(frozen=True)
class ParsedStrategy:
    name: str
    steps: list[Step]


class UnknownStepError(ValueError):
    """Paso que no es primitiva conocida ni referencia de ley válida."""


def parse_strategy(proposed: dict[str, Any], known_law_ids: set[str]) -> ParsedStrategy:
    """Convierte la estrategia propuesta (dict) en pasos validados.

    Formato de `proposed`:
      {"name": str, "steps": [ {"name": str, "primitive": str} |
                                {"name": str, "law_ref": "#1"} , ... ]}
    """
    name = proposed.get("name", "unnamed")
    raw_steps = proposed.get("steps", [])
    steps: list[Step] = []
    for s in raw_steps:
        sname = s.get("name", "?")
        if "primitive" in s:
            prim = s["primitive"]
            if prim not in KNOWN_PRIMITIVES:
                raise UnknownStepError(f"primitiva desconocida: {prim!r} en paso {sname!r}")
            steps.append(Step(name=sname, kind="primitive", spec={"primitive": prim}))
        elif "law_ref" in s:
            ref = s["law_ref"]
            if ref not in known_law_ids:
                raise UnknownStepError(f"referencia a ley inexistente: {ref!r} en paso {sname!r}")
            steps.append(Step(name=sname, kind="law_ref", spec={"law_ref": ref}))
        else:
            raise UnknownStepError(f"paso {sname!r} no es primitiva ni law_ref")
    return ParsedStrategy(name=name, steps=steps)


def primitive_predicate(step: Step, feats: Any, cfg: dict[str, Any]) -> Any:
    """Devuelve la máscara booleana de un paso primitivo sobre Features.

    SL-R14: mapea el nombre de primitiva a feature_calc. Para estocástico usa
    los umbrales de cfg (overbought/oversold).
    """
    prim = step.spec["primitive"]
    st = cfg["stochastic"]
    if prim == "impulse_up":
        return feats.impulse_net > float(cfg["impulse"]["min_pips"]) * 1e-4
    if prim == "impulse_dn":
        return feats.impulse_net < -float(cfg["impulse"]["min_pips"]) * 1e-4
    if prim == "brake":
        return feats.brake_mask
    if prim == "stoch_overbought":
        return feats.stoch_k_prev >= st["overbought"]
    if prim == "stoch_oversold":
        return feats.stoch_k_prev <= st["oversold"]
    if prim == "rebote_up":
        return feats.rebote_up
    if prim == "rebote_dn":
        return feats.rebote_dn
    if prim == "poi_zone":
        # POI se modela como freno + rebote en la misma dirección (zona de reversión)
        return feats.brake_mask & (feats.rebote_up | feats.rebote_dn)
    raise UnknownStepError(f"primitiva sin predicado: {prim!r}")
