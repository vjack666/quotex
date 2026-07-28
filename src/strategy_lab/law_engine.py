"""law_engine — motor de ejecucion de leyes para STRAT-F (Capa Estratega).

Filosofia (Ruben 2026-07-28): STRAT-F NO conoce reglas. Es un ejecutor de
conocimiento. El Discovery Engine (Capa 2.5) DESCRUBRE las leyes; este motor
las INTERPRETA y el bot las EJECUTA.

Diseno (motor de leyes, no pipeline fijo):
    leyes_ordenadas = sort(leys, key=priority desc)
    confianza = 0.0
    passed = []
    for ley in leyes_ordenadas:
        if not all(req in passed for req in ley.requires):
            continue                      # dependencia no cumplida -> se salta
        r = ley.evaluar(ctx)
        if not r.ok:
            return EngineResult(ok=False, failed_at=ley.id, ...)
        confianza += r.weight
        passed.append(ley.id)
    return EngineResult(ok=True, confianza=..., passed=...)

Ventaja sobre pipeline fijo: cuando el Discovery emita Ley #37 dentro de un
ano, solo se REGISTRA (priority + requires). STRAT-F no se toca. Cero deuda.

Candados (heredados de discovery-engine-dev):
- CERO imports a scanner/strat_fractal/bot.
- CERO time.time()/datetime.now(): el ctx trae ts de datos.
- Umbrales NO hardcodeados: vienen de weight_provider / cfg.
- Deterministico: misma ley + mismo ctx => mismo resultado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import numpy as np


@dataclass
class LawContext:
    """Datos de mercado que reciben las leyes. Sin I/O, sin reloj.

    Las velas vienen como numpy arrays float (OHLC). stoch_* son dicts con
    k/d/k_vals/d_vals cuando el scanner los pasa.
    """
    sym: Optional[str] = ""
    payout: int = 80
    # M15 (contexto mayor, donde vive el freno)
    o15: Any = None
    h15: Any = None
    l15: Any = None
    c15: Any = None
    # M5 (estructura)
    o5: Any = None
    h5: Any = None
    l5: Any = None
    c5: Any = None
    # M1 (ejecucion)
    o1: Any = None
    h1: Any = None
    l1: Any = None
    c1: Any = None
    stoch_m15: dict = field(default_factory=dict)
    stoch_m5: dict = field(default_factory=dict)
    zone: Any = None
    ts15: Any = None
    direction_hint: Optional[str] = None   # la dir que el motor va descubriendo


@dataclass
class LawResult:
    """Salida de una ley al evaluarse."""
    ok: bool
    weight: float = 0.0           # aporte a la confianza (viene de evidencia)
    detail: str = ""
    direction: Optional[str] = None   # CALL/PUT si la ley aporta direccion
    extra: dict = field(default_factory=dict)


@dataclass
class ExecutableLaw:
    """Ley EJECUTABLE: une el conocimiento (id) con su comportamiento.

    El `id` coincide con la Ley #N del Discovery Store. `priority` define el
    orden (mayor = antes). `requires` = leyes que deben haber pasado antes
    (si no pasaron, esta ley se SALTA, no rompe el flujo).
    """
    id: str
    priority: int
    evaluar: Callable[[LawContext], LawResult]
    requires: tuple[str, ...] = ()


@dataclass
class EngineResult:
    ok: bool
    confianza: float = 0.0
    passed: list[str] = field(default_factory=list)
    failed_at: Optional[str] = None
    direction: Optional[str] = None
    detail: str = ""


class LawEngine:
    """Ejecuta leyes por prioridad con dependencias.

    weight_provider: callable(id, default) -> float. Fuente de pesos = el
    Discovery (probability de la ley). Si la ley aun no esta en el store,
    devuelve el default (peso semilla). NUNCA se hardcodea el peso en la ley.
    """

    def __init__(self, laws: list[ExecutableLaw],
                 weight_provider: Callable[[str, float], float]):
        self.laws = sorted(laws, key=lambda lw: -lw.priority)
        self.weight_provider = weight_provider

    def evaluate(self, ctx: LawContext) -> EngineResult:
        confianza = 0.0
        passed: list[str] = []
        direction: Optional[str] = None
        for law in self.laws:
            if not all(req in passed for req in law.requires):
                continue  # dependencia no cumplida -> ley no aplica (skip)
            r = law.evaluar(ctx)
            if not r.ok:
                return EngineResult(
                    ok=False, confianza=confianza, passed=passed,
                    failed_at=law.id, direction=direction,
                    detail=f"{law.id}: {r.detail}",
                )
            w = self.weight_provider(law.id, r.weight)
            confianza += w
            if r.direction is not None:
                direction = r.direction
                ctx.direction_hint = direction   # propaga a leyes dependientes
            passed.append(law.id)
        return EngineResult(
            ok=True, confianza=confianza, passed=passed, direction=direction,
            detail=";".join(passed),
        )


def _as_array(x) -> np.ndarray:
    if x is None:
        return np.array([])
    return np.asarray(x, float)
