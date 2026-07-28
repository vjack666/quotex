"""Espacio de features del Discovery Engine (CONTRATO T3).

Define ``FeatureSpec`` y construye el espacio de features a partir de un
``Episode`` (evolution + summary). Cero literales de umbral: todo nivel
(numérico o de corte) vive en ``config/discovery_v1.yaml``.

Regla R8: el PREDICTOR excluye ``end_reason``/``mfe``/``mae`` del summary.
``build_feature_space`` NO los incluye como features. Los buckets de
velocity/violence/curve_shape del summary se usan como DESCRIPTORES
categóricos (no predictor de end_reason).

``max_depth`` del cfg limita el nº total de features (compuestas incluidas).
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Callable

from .config_loader import load_config
from .types import Episode

# Referencia de volatilidad por asset para el percentil (R8/percentil por asset).
# Se poblA vía ``fit_volatility_reference`` (la llama el miner con el corpus).
_PCT_REFERENCE: dict[str, list[float]] = {}

# Categorías del summary que son DESCRIPTORES (no predictor de end_reason).
_DESCRIPTOR_FIELDS = ("velocity", "violence", "curve_shape")


@dataclass(frozen=True)
class FeatureSpec:
    """Especificación de una feature del espacio (CONTRATO)."""

    nombre: str
    tipo: str  # 'numeric' | 'categorical'
    extrae: Callable[[Episode], float | str]


# --------------------------------------------------------------------------
# Helpers de extracción (puros, deterministas, sin umbrales literales)
# --------------------------------------------------------------------------

def _distance_values(ep: Episode) -> list[float]:
    vals = []
    for row in ep.evolution:
        d = row.get("distance_pips")
        if d is not None:
            vals.append(float(d))
    return vals


def _mean_distance(ep: Episode) -> float:
    vals = _distance_values(ep)
    if not vals:
        return 0.0
    return statistics.fmean(vals)


def _distance_speed(ep: Episode) -> float:
    vals = _distance_values(ep)
    if len(vals) < 2:
        return 0.0
    diffs = [abs(vals[i] - vals[i - 1]) for i in range(1, len(vals))]
    return statistics.fmean(diffs)


def _state_changes(ep: Episode) -> float:
    prev = None
    changes = 0
    for row in ep.evolution:
        st = row.get("state")
        if st is not None and prev is not None and st != prev:
            changes += 1
        if st is not None:
            prev = st
    return float(changes)


def _volatility(ep: Episode) -> float:
    """Volatilidad del episodio: desv. típica de las primeras diferencias de distance."""
    vals = _distance_values(ep)
    if len(vals) < 2:
        return 0.0
    diffs = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
    return statistics.pstdev(diffs)


def _volatility_percentile(ep: Episode) -> float:
    """Percentil de volatilidad del episodio dentro de su asset (R8).

    Si no hay referencia cargada para el asset, devuelve la volatilidad cruda
    (determinista, degradación graceful sin corpus).
    """
    v = _volatility(ep)
    ref = _PCT_REFERENCE.get(ep.asset)
    if not ref:
        return v
    below = sum(1 for x in ref if x <= v)
    return below / len(ref)


def _duration_bars(ep: Episode) -> float:
    d = ep.summary.get("duration_bars")
    return float(d) if d is not None else 0.0


def _descriptor(field: str) -> Callable[[Episode], str]:
    def _extract(ep: Episode) -> str:
        val = ep.summary.get(field)
        return str(val) if val is not None else ""
    return _extract


# --------------------------------------------------------------------------
# Features compuestas (limitadas por max_depth)
# --------------------------------------------------------------------------

def _make_composite(name: str, a: FeatureSpec, b: FeatureSpec) -> FeatureSpec:
    def _extract(ep: Episode) -> float:
        va = a.extrae(ep)
        vb = b.extrae(ep)
        try:
            return float(va) * float(vb)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0
    return FeatureSpec(nombre=name, tipo="numeric", extrae=_extract)


# --------------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------------

def fit_volatility_reference(episodes: list[Episode]) -> None:
    """Puebla la referencia de volatilidad por asset para el percentil.

    Llamar una vez con el corpus completo (train) antes de enumerar features.
    """
    _PCT_REFERENCE.clear()
    for ep in episodes:
        _PCT_REFERENCE.setdefault(ep.asset, []).append(_volatility(ep))
    for asset in _PCT_REFERENCE:
        _PCT_REFERENCE[asset].sort()


def build_feature_space(cfg: dict | None = None) -> list[FeatureSpec]:
    """Construye el espacio de features respetando ``max_depth`` del cfg.

    Args:
        cfg: config cargada. Si None, se carga vía config_loader.

    Returns:
        lista de FeatureSpec (numéricas + descriptoras + compuestas),
        con nº total <= cfg['max_depth'].
    """
    if cfg is None:
        cfg = load_config()
    max_depth = int(cfg["max_depth"])

    # Features base numéricas derivadas de evolution.
    numerics: list[FeatureSpec] = [
        FeatureSpec("distance_pips_mean", "numeric", _mean_distance),
        FeatureSpec("distance_speed", "numeric", _distance_speed),
        FeatureSpec("state_changes", "numeric", _state_changes),
        FeatureSpec("volatility", "numeric", _volatility),
        FeatureSpec("volatility_pct", "numeric", _volatility_percentile),
        FeatureSpec("duration_bars", "numeric", _duration_bars),
    ]

    # Descriptores categóricos del summary (velocity/violence/curve_shape).
    descriptors: list[FeatureSpec] = [
        FeatureSpec(f"summary_{f}", "categorical", _descriptor(f))
        for f in _DESCRIPTOR_FIELDS
    ]

    space: list[FeatureSpec] = list(numerics) + list(descriptors)

    # Features compuestas (producto de pares numéricos) hasta max_depth.
    pair_idx = 0
    used_names = {fs.nombre for fs in space}
    for i in range(len(numerics)):
        for j in range(i + 1, len(numerics)):
            if len(space) >= max_depth:
                break
            a, b = numerics[i], numerics[j]
            name = f"composite_{a.nombre}__x__{b.nombre}"
            if name in used_names:
                continue
            space.append(_make_composite(name, a, b))
            used_names.add(name)
            pair_idx += 1
        if len(space) >= max_depth:
            break

    # Garantía dura: nunca superar max_depth.
    return space[:max_depth]


def enumerate_features(episode: Episode, cfg: dict | None = None) -> dict[str, float | str]:
    """Enumera todas las features de un episodio como dict nombre->valor.

    NO incluye ``end_reason``/``mfe``/``mae`` (R8): no son FeatureSpecs.
    """
    space = build_feature_space(cfg)
    out: dict[str, float | str] = {}
    for spec in space:
        out[spec.nombre] = spec.extrae(episode)
    return out


def feature_count(cfg: dict | None = None) -> int:
    """Nº de features del espacio (<= max_depth)."""
    return len(build_feature_space(cfg))
