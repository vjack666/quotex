"""Carga de configuración versionada del Observador Fase B (D0)."""
from __future__ import annotations

import os

import yaml

_DEFAULT_KEY = "default"
_CONFIG_NAME = "evolution_v1.yaml"


def _config_path() -> str:
    return os.path.join(os.path.dirname(__file__), "config", _CONFIG_NAME)


def load_evolution_config(asset: str, path: str | None = None) -> dict:
    """Devuelve la cfg para `asset` (fallback a clave default), con version."""
    with open(path or _config_path(), "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    capture = raw.get("capture", {})
    per_asset = capture.get("per_asset", {})
    asset_cfg = per_asset.get(asset, per_asset.get(_DEFAULT_KEY, {}))
    return {
        "version": raw.get("version"),
        "vars": raw.get("vars", []),
        "capture": {
            "dimensions": capture.get("dimensions", []),
            "asset": asset_cfg,
        },
        "summary": raw.get("summary", {}),
    }
