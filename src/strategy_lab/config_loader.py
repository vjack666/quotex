"""Carga la config versionada del Strategy Lab (sin literales en código)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class StrategyLabConfig:
    seed: int
    split_year: int
    min_sample: int
    min_contribution: float
    p_cut: float
    max_depth: int
    stochastic: dict[str, Any] = field(default_factory=dict)
    impulse: dict[str, Any] = field(default_factory=dict)
    brake: dict[str, Any] = field(default_factory=dict)
    rebote: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "StrategyLabConfig":
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        return cls(
            seed=int(raw["seed"]),
            split_year=int(raw["split_year"]),
            min_sample=int(raw["min_sample"]),
            min_contribution=float(raw["min_contribution"]),
            p_cut=float(raw["p_cut"]),
            max_depth=int(raw["max_depth"]),
            stochastic=raw.get("stochastic", {}),
            impulse=raw.get("impulse", {}),
            brake=raw.get("brake", {}),
            rebote=raw.get("rebote", {}),
        )


def default_config_path() -> Path:
    return Path(__file__).resolve().parent / "config" / "strategy_lab_v1.yaml"
