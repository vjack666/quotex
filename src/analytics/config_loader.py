"""Carga la config del estudio estocástico-zona (sin literales en código)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ZonaConfig:
    os: float
    ob: float
    peg_max: float
    sep_min: float
    fwd: int
    rebote_min_pips: float

    @classmethod
    def load(cls, path: str | Path) -> "ZonaConfig":
        with open(path, "r", encoding="utf-8") as fh:
            d = yaml.safe_load(fh)
        z = d["zona"]
        return cls(
            os=float(z["os"]), ob=float(z["ob"]),
            peg_max=float(z["peg_max"]), sep_min=float(z["sep_min"]),
            fwd=int(z["fwd"]), rebote_min_pips=float(z["rebote_min_pips"]),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "os": self.os, "ob": self.ob, "peg_max": self.peg_max,
            "sep_min": self.sep_min, "fwd": self.fwd,
            "rebote_min_pips": self.rebote_min_pips,
        }


def default_config_path() -> Path:
    return Path(__file__).resolve().parent / "config" / "estocastico_zona_v1.yaml"
