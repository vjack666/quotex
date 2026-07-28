"""backtester — mide el edge walk-forward de una variante sobre velas M15.

SL-R4: aplica la secuencia de pasos primitivos como filtros (AND en orden) y
mide la tasa de REBOTE en la ventana `fwd` tras la señal. Split temporal
(train antes de split_year, hold-out después). Reusa estándar LAB-001.

La "señal" es la conjunción de los predicados de los pasos primitivos. El
rebote se mide en la dirección coherente: si la señal es de impulso alcista +
freno + sobrecompra -> rebote BAJISTA (rebote_dn); si impulso bajista + freno +
sobreventa -> rebote ALCISTA (rebote_up). Si no hay dirección clara, usa el
rebote neto (up o dn).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from strategy_lab.strategy_parser import ParsedStrategy, primitive_predicate
from strategy_lab.variant_searcher import Variant


@dataclass(frozen=True)
class Score:
    edge_train: float
    edge_test: float
    n_train: int
    n_test: int
    direction: str          # "dn" | "up" | "net"


def _signal_mask(variant: Variant, ps: ParsedStrategy, feats: Any, cfg: dict[str, Any]) -> np.ndarray:
    mask = np.ones(len(feats.impulse_net), dtype=bool)
    for i in variant.order:
        step = ps.steps[i]
        if step.is_law():
            continue  # law_ref no aporta máscara propia en backtest de velas
        pred = primitive_predicate(step, feats, cfg)
        mask = mask & np.asarray(pred, dtype=bool)
    return mask


def _direction_of(variant: Variant, ps: ParsedStrategy) -> str:
    prims = [ps.steps[i].spec.get("primitive") for i in variant.order
             if not ps.steps[i].is_law()]
    if "impulse_up" in prims or "stoch_overbought" in prims:
        return "dn"   # impulso alcista + freno + sobrecompra -> rebote bajista
    if "impulse_dn" in prims or "stoch_oversold" in prims:
        return "up"
    return "net"


def score_variant(variant: Variant, ps: ParsedStrategy, feats: Any,
                  cfg: dict[str, Any], time_idx: np.ndarray,
                  split_year: int) -> Score:
    """Mide tasa de rebote tras señal, dividida en train/test por año."""
    mask = _signal_mask(variant, ps, feats, cfg)
    n = len(mask)
    fwd = int(cfg["rebote"]["fwd"])
    direction = _direction_of(variant, ps)

    # objetivo: rebote en la dirección correcta tras fwd velas
    if direction == "dn":
        target = feats.rebote_dn
    elif direction == "up":
        target = feats.rebote_up
    else:
        target = feats.rebote_up | feats.rebote_dn

    years = time_idx.astype("datetime64[Y]").astype(int) + 1970
    # indexar alineado: la señal en i predice rebote en i+fwd
    sig_idx = np.where(mask[:-fwd])[0]
    if len(sig_idx) == 0:
        return Score(0.0, 0.0, 0, 0, direction)
    tgt = target[sig_idx + fwd].astype(float)
    yrs = years[sig_idx]
    tr = yrs < split_year
    te = ~tr
    edge_train = float(tgt[tr].mean()) if tr.any() else 0.0
    edge_test = float(tgt[te].mean()) if te.any() else 0.0
    return Score(edge_train=edge_train, edge_test=edge_test,
                 n_train=int(tr.sum()), n_test=int(te.sum()), direction=direction)
