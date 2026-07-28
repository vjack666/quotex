"""orderer — compara secuencias alternativas de pasos (SL-R8).

Dadas varias variantes (mismos pasos, distinto orden), mide edge walk-forward
y reporta la de mayor edge. El orden óptimo se DESCUBRE, no se asume.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from strategy_lab.backtester import Score, score_variant
from strategy_lab.strategy_parser import ParsedStrategy
from strategy_lab.variant_searcher import Variant


@dataclass(frozen=True)
class OrderResult:
    best: Variant
    best_edge: float
    ranked: list[tuple[Variant, float]]   # (variante, edge_test) ordenado desc


def rank_orders(variants: list[Variant], ps: ParsedStrategy, feats: Any,
                cfg: dict[str, Any], time_idx: np.ndarray) -> OrderResult:
    ranked: list[tuple[Variant, float]] = []
    for v in variants:
        sc: Score = score_variant(v, ps, feats, cfg, time_idx, cfg["split_year"])
        ranked.append((v, sc.edge_test))
    ranked.sort(key=lambda x: x[1], reverse=True)
    best_v, best_e = ranked[0]
    return OrderResult(best=best_v, best_edge=best_e, ranked=ranked)
