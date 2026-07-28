"""optimizer — orquesta el Strategy Lab (SL-R3..R9,R13).

Flujo: parse → enumera variantes → backtest walk-forward → ablation/falsify
por paso → elimina pasos inútiles (Δedge < min_contribution o p >= corte) →
ordena las secuencias restantes → emite la estrategia óptima. Solo variantes
de la propuesta (no inventa). Une las respuestas: ¿en qué leyes se apoya?,
¿qué aporta más?, ¿qué sobra?, ¿qué orden es óptimo?
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from strategy_lab.strategy_parser import ParsedStrategy, parse_strategy
from strategy_lab.variant_searcher import enumerate_variants, variant_from_included, Variant
from strategy_lab.backtester import score_variant
from strategy_lab.ablator import ablate
from strategy_lab.falsifier import falsify
from strategy_lab.orderer import rank_orders
from strategy_lab.strategy_store import StrategyStore, OptimizedStrategy


@dataclass
class OptimizeResult:
    optimized: OptimizedStrategy
    dropped_steps: list[str]
    ablation: list[Any] = field(default_factory=list)
    falsify: list[Any] = field(default_factory=list)


def optimize(proposed: dict[str, Any], feats: Any, cfg: dict[str, Any],
             time_idx: Any, known_law_ids: set[str]) -> OptimizeResult:
    ps = parse_strategy(proposed, known_law_ids)
    # 1) variante "full" (todos los pasos en orden original) para medir contribución
    full_inc = list(range(len(ps.steps)))
    full_v = variant_from_included(ps, full_inc)
    abl = ablate(full_v, ps, feats, cfg, time_idx)
    fal = falsify(full_v, ps, feats, cfg, time_idx)

    # 2) elimina pasos inútiles (baja contribución o p >= corte)
    dropped: list[str] = []
    for r in abl:
        if r.delta < cfg["min_contribution"]:
            dropped.append(r.step_name)
    for r in fal:
        if r.p_value >= cfg["p_cut"]:
            if r.step_name not in dropped:
                dropped.append(r.step_name)
    kept = [i for i in full_inc if ps.steps[i].name not in dropped]

    # 3) entre las variantes que usan solo los pasos keep, encuentra el orden óptimo
    kept_variants = [v for v in enumerate_variants(ps, cfg)
                     if set(v.order).issubset(set(kept)) and len(v.order) >= 1]
    if not kept_variants:           # evidencia descartó TODO: estrategia vacía (sin edge)
        empty_v = Variant(order=(), included=frozenset())
        kept_variants = [empty_v]
    order_res = rank_orders(kept_variants, ps, feats, cfg, time_idx)
    best_v = order_res.best
    best_sc = score_variant(best_v, ps, feats, cfg, time_idx, cfg["split_year"])

    optimized = StrategyStore.build(
        name=ps.name, parsed=ps, variant=best_v, score=best_sc,
        dropped=dropped, cfg=cfg,
    )
    return OptimizeResult(optimized=optimized, dropped_steps=dropped,
                          ablation=abl, falsify=fal)
