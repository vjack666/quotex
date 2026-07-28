"""Estudio del estocástico en zona OS/OB — teoría de Rubén (versión corregida).

Corrección empírica (2026-07-28): el empuje no ocurre DENTRO de la zona, sino
en la SALIDA de ella (%K abandona OS/OB). En binarias solo se mantiene 1 vela
M15 (15 min), así que el horizonte es fwd=1, no 10.

Para cada vela M15 se registra:
  - zona: fuera / OS (%K<=os) / OB (%K>=ob)
  - estado_lineas: PEGADAS (|K-D|<=peg_max) / SEPARADAS (>=sep_min) / ENTRE
  - cruce: +1 K cruza D hacia arriba, -1 hacia abajo, 0 sin cruce
  - salida: +1 %K salió de OS hacia arriba (empuje alcista), -1 salió de OB
    hacia abajo (empuje bajista), 0 sin salida
  - en_zona_sep: ambas líneas en zona Y separadas (métrica vieja, para auditar)

Y la métrica de binaria: tras la SALIDA de zona, ¿el precio se mueve en el
sentido del empuje en fwd velas? Eso es la operación binaria de 15 min.

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
    salida: np.ndarray            # 0, +1 (sale OS arriba), -1 (sale OB abajo)
    en_zona_sep: np.ndarray       # bool: ambas lineas en zona Y separadas


def _classify(z: np.ndarray, os: float, ob: float) -> np.ndarray:
    out = np.zeros(len(z), dtype=int)
    out[z <= os] = 1
    out[z >= ob] = 2
    return out


def classify(k: np.ndarray, d: np.ndarray, close: np.ndarray,
             cfg: dict[str, Any]) -> ZonaLabels:
    n = len(k)
    gap = np.abs(k - d)
    estado = np.where(gap <= cfg["peg_max"], 0,
              np.where(gap >= cfg["sep_min"], 2, 1)).astype(int)

    diff = k - d
    s_prev = np.sign(diff[:-1])
    s_curr = np.sign(diff[1:])
    cruce = np.zeros(n, dtype=int)
    cruce[1:][(s_prev < 0) & (s_curr >= 0)] = 1
    cruce[1:][(s_prev > 0) & (s_curr <= 0)] = -1

    zona = _classify(k, cfg["os"], cfg["ob"])
    in_prev = zona[:-1]
    exited = (in_prev != 0) & (zona[1:] == 0)
    salida = np.zeros(n, dtype=int)
    salida[1:][exited & (in_prev == 1)] = 1     # salió de OS hacia arriba
    salida[1:][exited & (in_prev == 2)] = -1    # salió de OB hacia abajo

    zona_d = _classify(d, cfg["os"], cfg["ob"])
    en_zona = ((zona != 0) & (zona_d != 0) & (zona == zona_d))
    en_zona_sep = en_zona & (estado == 2)

    return ZonaLabels(zona=zona, estado_lineas=estado, cruce=cruce,
                      salida=salida, en_zona_sep=en_zona_sep)


def binary_stats(k: np.ndarray, d: np.ndarray, close: np.ndarray,
                 cfg: dict[str, Any], cruce_en_salida: bool = False) -> dict[str, float]:
    """Win-rate de la operación binaria de 15 min tras la SALIDA de zona.

    Señal: %K sale de OS (alcista) u OB (bajista). Opcional: exigir |K-D|>=sep
    y/o cruce %K/%D en la salida. Win: en fwd velas el precio se mueve >= min_pips
    en el sentido del empuje.
    """
    lab = classify(k, d, close, cfg)
    fwd = int(cfg["fwd"])
    min_p = float(cfg["rebote_min_pips"]) * 1e-4
    sep = float(cfg.get("sep_min_barrido", cfg.get("sep_min", 0.0)))
    n = len(close)
    idx_all = np.arange(n)
    sig = (lab.salida != 0) & (idx_all + fwd < n)
    if sep > 0:
        sig = sig & (np.abs(k - d) >= sep)
    if cruce_en_salida:
        sig = sig & (lab.cruce != 0)

    def _wr(mask: np.ndarray) -> tuple[int, float]:
        ix = np.where(mask)[0]
        if len(ix) == 0:
            return 0, 0.0
        move = close[ix + fwd] - close[ix]
        win = (np.sign(move) == np.sign(lab.salida[ix])) & (np.abs(move) >= min_p)
        return int(len(ix)), float(win.mean())

    n_all, wr_all = _wr(sig)
    n_os, wr_os = _wr(sig & (lab.salida > 0))
    n_ob, wr_ob = _wr(sig & (lab.salida < 0))
    return {"n": n_all, "wr": wr_all, "n_os": n_os, "wr_os": wr_os,
            "n_ob": n_ob, "wr_ob": wr_ob}


def magnitude_stats(k: np.ndarray, d: np.ndarray, close: np.ndarray,
                    cfg: dict[str, Any], rng: np.random.Generator | None = None
                    ) -> dict[str, float]:
    """Magnitud del empuje tras la SALIDA de zona (no dirección).

    Mide |movimiento| en fwd velas tras salir de OS/OB, y lo compara contra
    una base aleatoria (mismas velas, índices al azar) para ver si el empuje
    es real como EXPLOSIÓN DE VOLATILIDAD y no solo ruido direccional.
    """
    lab = classify(k, d, close, cfg)
    fwd = int(cfg["fwd"])
    n = len(close)
    idx = np.where((lab.salida != 0) & (np.arange(n) + fwd < n))[0]
    rng = rng or np.random.default_rng(20260728)
    if len(idx) == 0:
        return {"n": 0, "mean_abs_salida": 0.0, "mean_abs_base": 0.0,
                "ratio": 0.0, "p_value": 1.0}
    abs_sal = np.abs(close[idx + fwd] - close[idx])
    hi = n - fwd
    base_idx = rng.integers(0, hi, size=len(idx))
    abs_base = np.abs(close[base_idx + fwd] - close[base_idx])
    mean_sal = float(abs_sal.mean())
    mean_base = float(abs_base.mean())
    ratio = mean_sal / mean_base if mean_base else 0.0
    n_perm = 200
    ge = 0
    for _ in range(n_perm):
        b = rng.integers(0, hi, size=len(idx))
        if np.abs(close[b + fwd] - close[b]).mean() >= mean_sal:
            ge += 1
    p = (ge + 1) / (n_perm + 1)
    return {"n": int(len(idx)), "mean_abs_salida": mean_sal / 1e-4,
            "mean_abs_base": mean_base / 1e-4, "ratio": ratio, "p_value": p}
