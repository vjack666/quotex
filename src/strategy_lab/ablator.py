"""ablator — importancia por ablation (SL-R6,R7).

Quita un paso de la variante y mide la caída de edge (Δedge). Paso con
Δedge < min_contribution se marca para ELIMINACIÓN ("¿qué parte sobra?").
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from strategy_lab.backtester import score_variant
from strategy_lab.strategy_parser import ParsedStrategy
from strategy_lab.variant_searcher import Variant


@dataclass(frozen=True)
class AblationRow:
    step_index: int
    step_name: str
    edge_full: float
    edge_without: float
    delta: float               # edge_full - edge_without (contribución)


def ablate(variant: Variant, ps: ParsedStrategy, feats: Any, cfg: dict[str, Any],
           time_idx: np.ndarray) -> list[AblationRow]:
    """Mide la contribución de cada paso quitándolo de la variante."""
    full = score_variant(variant, ps, feats, cfg, time_idx, cfg["split_year"])
    edge_full = full.edge_train  # medimos en train para la contribución
    rows: list[AblationRow] = []
    included = list(variant.order)
    for drop in included:
        kept = [i for i in included if i != drop]
        v_wo = Variant(order=tuple(kept), included=frozenset(kept))
        sc = score_variant(v_wo, ps, feats, cfg, time_idx, cfg["split_year"])
        edge_wo = sc.edge_train
        rows.append(AblationRow(
            step_index=drop,
            step_name=ps.steps[drop].name,
            edge_full=edge_full,
            edge_without=edge_wo,
            delta=edge_full - edge_wo,
        ))
    return rows
