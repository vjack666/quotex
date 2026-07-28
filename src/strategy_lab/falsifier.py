"""falsifier — placebo / p-valor por paso (SL-R5).

Baraja (permuta) las etiquetas de rebote y re-mide el edge de la variante;
el p-valor es la fracción de permutaciones cuyo edge >= el real. Solo se
retiene un paso con p < corte.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from strategy_lab.backtester import score_variant
from strategy_lab.strategy_parser import ParsedStrategy, primitive_predicate
from strategy_lab.variant_searcher import Variant


@dataclass(frozen=True)
class FalsifyRow:
    step_index: int
    step_name: str
    p_value: float


def falsify(variant: Variant, ps: ParsedStrategy, feats: Any, cfg: dict[str, Any],
            time_idx: np.ndarray, n_perm: int = 200) -> list[FalsifyRow]:
    """p-valor por permutación de etiquetas de rebote (placebo)."""
    rng = np.random.default_rng(cfg["seed"])
    real = score_variant(variant, ps, feats, cfg, time_idx, cfg["split_year"])
    real_edge = real.edge_train
    if real.direction == "dn":
        target = feats.rebote_dn.astype(float)
    elif real.direction == "up":
        target = feats.rebote_up.astype(float)
    else:
        target = (feats.rebote_up | feats.rebote_dn).astype(float)
    n = len(target)
    fwd = int(cfg["rebote"]["fwd"])
    mask = np.ones(n, dtype=bool)
    for i in variant.order:
        step = ps.steps[i]
        if step.is_law():
            continue
        mask = mask & np.asarray(primitive_predicate(step, feats, cfg), dtype=bool)
    sig_idx = np.where(mask[:-fwd])[0]
    if len(sig_idx) == 0:
        return [FalsifyRow(i, ps.steps[i].name, 1.0) for i in variant.order]
    base = target[sig_idx + fwd]
    ge = 0
    for _ in range(n_perm):
        perm = rng.permutation(base)
        if perm.mean() >= real_edge - 1e-12:
            ge += 1
    p = (ge + 1) / (n_perm + 1)
    return [FalsifyRow(i, ps.steps[i].name, p) for i in variant.order]
