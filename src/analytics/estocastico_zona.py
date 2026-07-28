"""Estudio del estocástico en zona de sobrecompra/sobreventa (teoría de Rubén).

Para cada vela M15 registra CON NÚMEROS tu secuencia:
  - zona: fuera / OS (sobreventa) / OB (sobrecompra)
  - estado_lineas: PEGADAS (|K-D|<=peg_max) / SEPARADAS (>=sep_min) / ENTRE
  - cruce: +1 K cruza D hacia arriba, -1 hacia abajo, 0 sin cruce
  - en_zona_y_separadas: K y D ambas en la zona Y separadas de verdad
  - despegue_precio: a fwd velas el precio se movió >= rebote_min_pips en el
    sentido del cruce (la "vela que sale volando")

Sin wallclock. Reusa el estocástico Full de feature_calc.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from strategy_lab import feature_calc as fc


@dataclass(frozen=True)
class ZonaLabels:
    zona: np.ndarray              # 0 fuera, 1 OS, 2 OB
    estado_lineas: np.ndarray     # 0 pegadas, 1 entre, 2 separadas
    cruce: np.ndarray             # -1,0,+1
    en_zona_sep: np.ndarray       # bool: ambas lineas en zona Y separadas
    despegue: np.ndarray          # bool: precio se movio >= min en sentido cruce


def _classify(z: np.ndarray, os: float, ob: float) -> np.ndarray:
    out = np.zeros(len(z), dtype=int)
    out[z <= os] = 1
    out[z >= ob] = 2
    return out


def label_series(k: np.ndarray, d: np.ndarray, close: np.ndarray,
                 cfg: dict[str, Any]) -> ZonaLabels:
    n = len(k)
    gap = np.abs(k - d)
    estado = np.where(gap <= cfg["peg_max"], 0,
              np.where(gap >= cfg["sep_min"], 2, 1)).astype(int)
    # cruce K vs D (signo del diferencial previo vs actual)
    diff = k - d
    s_prev = np.sign(diff[:-1])
    s_curr = np.sign(diff[1:])
    cruce = np.zeros(n, dtype=int)
    cruce[1:][(s_prev < 0) & (s_curr >= 0)] = 1
    cruce[1:][(s_prev > 0) & (s_curr <= 0)] = -1

    zona_k = _classify(k, cfg["os"], cfg["ob"])
    zona_d = _classify(d, cfg["os"], cfg["ob"])
    en_zona = ((zona_k != 0) & (zona_d != 0) & (zona_k == zona_d))
    en_zona_sep = en_zona & (estado == 2)

    # despegue: a fwd velas, el precio se aleja >= min_pips en el sentido del cruce
    fwd = int(cfg["fwd"])
    min_p = float(cfg["rebote_min_pips"]) * 1e-4
    despegue = np.zeros(n, dtype=bool)
    move = np.zeros(n)
    move[:n - fwd] = close[fwd:] - close[:-fwd]
    sense = np.where(cruce > 0, 1, np.where(cruce < 0, -1, 0))
    despegue = (sense != 0) & (np.abs(move) >= min_p)
    # el despegue solo cuenta si ocurrio estando en zona separada
    despegue = despegue & en_zona_sep

    return ZonaLabels(
        zona=zona_k, estado_lineas=estado, cruce=cruce,
        en_zona_sep=en_zona_sep, despegue=despegue,
    )


def classify(k: np.ndarray, d: np.ndarray, close: np.ndarray, cfg: dict[str, Any]) -> ZonaLabels:
    return label_series(k, d, close, cfg)
