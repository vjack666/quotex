"""Carga de configuración del Discovery Engine (CONTRATO T1).

Lee ``config/discovery_v1.yaml`` relativo a este paquete. NO usa rutas
absolutas: el archivo se localiza respecto a ``__file__`` de este módulo.
"""

from __future__ import annotations

import os
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependencia esencial
    raise ImportError(
        "PyYAML es requerido por config_loader (pip install pyyaml)"
    ) from exc

# Ruta al YAML relativa al paquete (sin rutas absolutas en el código).
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "discovery_v1.yaml")

# Campos obligatorios que debe exponer load_config().
_REQUIRED = (
    "min_sample",
    "p_cut",
    "min_freq",
    "max_depth",
    "seed",
    "split_year",
    "sources",
    "markets",
)


def load_config(path: str | None = None) -> dict[str, Any]:
    """Carga y valida la configuración del Discovery Engine.

    Args:
        path: ruta opcional al YAML. Si es None, usa el YAML empaquetado.

    Returns:
        dict con los campos documentados en el CONTRATO:
        min_sample, p_cut, min_freq, max_depth, seed, split_year,
        sources (list), markets (list).
    """
    cfg_path = path or _CONFIG_PATH
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    if not isinstance(cfg, dict):
        raise ValueError(f"Config inválida en {cfg_path}: no es un mapping")

    missing = [k for k in _REQUIRED if k not in cfg]
    if missing:
        raise KeyError(f"Config {cfg_path} omite campos requeridos: {missing}")

    # Normaliza listas.
    cfg["sources"] = list(cfg["sources"])
    cfg["markets"] = list(cfg["markets"])
    return cfg
