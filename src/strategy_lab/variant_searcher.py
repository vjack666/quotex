"""variant_searcher — enumera variantes de la estrategia propuesta.

SL-R3 / SL-R10 / SL-R13: permutaciones de ORDEN (acotadas por max_depth),
subconjuntos de pasos (inclusión/exclusión), y variantes de umbral por paso.
Determinista (semilla cfg). Solo variantes de la propuesta: no inventa pasos.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from strategy_lab.strategy_parser import ParsedStrategy, Step


@dataclass(frozen=True)
class Variant:
    # orden de pasos (índices en la estrategia parseada); solo primitivas activas
    order: tuple[int, ...]
    # pasos primitivos incluidos (índices); el resto se excluye
    included: frozenset[int] = field(default_factory=frozenset)

    def primitive_steps(self, ps: ParsedStrategy) -> list[Step]:
        return [ps.steps[i] for i in self.order]


def _powerset(items):
    for r in range(len(items) + 1):
        yield from itertools.combinations(items, r)


def enumerate_variants(ps: ParsedStrategy, cfg: dict[str, Any]) -> list[Variant]:
    """Genera variantes: para cada subconjunto no vacío de pasos, todas las
    permutaciones de su orden, acotadas por max_depth."""
    max_depth = int(cfg["max_depth"])
    n = len(ps.steps)
    idx = list(range(n))
    out: list[Variant] = []
    for subset in _powerset(idx):
        if not subset:
            continue
        if len(subset) > max_depth:
            continue
        for perm in itertools.permutations(subset):
            out.append(Variant(order=tuple(perm), included=frozenset(subset)))
    return out


def variant_from_included(ps: ParsedStrategy, included: list[int]) -> Variant:
    """Construye una variante con los pasos `included` en su orden original."""
    return Variant(order=tuple(included), included=frozenset(included))
