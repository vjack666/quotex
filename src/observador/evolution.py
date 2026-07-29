"""EpisodeEvolutionWriter — traza barra a barra de un episodio (D2, Fase B).

Nunca usa reloj de pared: `ts` y `bar_index` provienen del evento (R12).
"""
from __future__ import annotations

import json

# Tamaño de pip fijo por ahora (T3); pasará a config por activo más adelante.
PIP_SIZE = 1e-4

# Versionado de las funciones de cambio del CaptureMonitor (D3, R5/R6/R7).
CAPTURE_CHANGE_VERSION = "capture_v1"

# Estados de cierre REAL del mercado (D4): fin natural → finished=1.
NATURAL_END_REASONS = frozenset(
    {"NEW_EXPANSION", "NEW_PRESSURE", "OPPOSITE_STRUCTURE", "CHAOS"})
CAPTURE_LIMIT = "CAPTURE_LIMIT"


class CaptureMonitor:
    """Decide cuándo dejar de observar (fin de captura, D3).

    Evalúa las dimensiones configurables del cfg (structural, pressure,
    energy, direction, volatility) sobre la ventana de silencio del activo.
    Devuelve True SOLO si TODAS reportan "sin cambio". Jamás corta por
    conteo fijo de barras: todos los umbrales vienen del cfg por activo.
    """

    def __init__(self, cfg_capture: dict):
        self.dimensions = list(cfg_capture.get("dimensions", []))
        asset_cfg = cfg_capture.get("asset", {})
        self.window = int(asset_cfg["silence_window_bars"])
        self._thr_pressure = float(asset_cfg["pressure_delta_threshold_pips"])
        self._thr_energy = float(asset_cfg["energy_delta_threshold_pips"])
        self._thr_direction = float(
            asset_cfg["direction_delta_threshold_pips"])
        self._thr_volatility = float(
            asset_cfg["volatility_range_threshold_pips"])
        self.change_version = cfg_capture.get(
            "change_version", CAPTURE_CHANGE_VERSION)

    # --- funciones de cambio versionadas (capture_v1) --------------------
    def _changed_structural(self, bars: list[dict]) -> bool:
        states = {b.get("state") for b in bars}
        return len(states) > 1

    def _changed_pressure(self, bars: list[dict]) -> bool:
        deltas = [abs(bars[i]["distance_pips"] - bars[i - 1]["distance_pips"])
                  for i in range(1, len(bars))]
        return max(deltas, default=0.0) > self._thr_pressure

    def _changed_energy(self, bars: list[dict]) -> bool:
        span = (max(b["distance_pips"] for b in bars)
                - min(b["distance_pips"] for b in bars))
        return span > self._thr_energy

    def _changed_direction(self, bars: list[dict]) -> bool:
        net = bars[-1]["distance_pips"] - bars[0]["distance_pips"]
        return abs(net) > self._thr_direction

    def _changed_volatility(self, bars: list[dict]) -> bool:
        span = (max(b["distance_pips"] for b in bars)
                - min(b["distance_pips"] for b in bars))
        return span > self._thr_volatility

    def should_stop(self, history_of_bars: list[dict]) -> bool:
        """True si TODAS las dimensiones reportan sin-cambio en la ventana."""
        if len(history_of_bars) < self.window:
            return False  # aún no hay ventana suficiente: seguir observando
        recent = history_of_bars[-self.window:]
        checks = {
            "structural": self._changed_structural,
            "pressure": self._changed_pressure,
            "energy": self._changed_energy,
            "direction": self._changed_direction,
            "volatility": self._changed_volatility,
        }
        for dim in self.dimensions:
            fn = checks.get(dim)
            if fn is not None and fn(recent):
                return False  # al menos una dimensión sigue viva
        return True


class EpisodeEvolutionWriter:
    def __init__(self, asset: str, origin_ts: float, origin_price: float,
                 vars_version: str):
        self.asset = asset
        self.origin_ts = origin_ts
        self.origin_price = origin_price
        self.vars_version = vars_version
        self._mfe = 0.0  # máximo a favor acumulado (pips)
        self._mae = 0.0  # máximo en contra acumulado (pips, <= 0)

    def record(self, bar_index: int, candle: dict, state: str,
               vars: dict | None = None) -> dict:
        price = candle["close"]
        distance_pips = (price - self.origin_price) / PIP_SIZE
        if distance_pips > self._mfe:
            self._mfe = distance_pips
        if distance_pips < self._mae:
            self._mae = distance_pips
        return {
            "bar_index": bar_index,
            "ts": candle["ts"],
            "price": price,
            "distance_pips": distance_pips,
            "mfe": self._mfe,
            "mae": self._mae,
            "state": state,
            "vars_json": json.dumps(vars) if vars is not None else None,
            "vars_version": self.vars_version,
        }

    # -- cierre (D4, T6): fin natural vs fin de captura --------------------
    def close(self, kind: str, confidence: float) -> dict:
        """Cierra el episodio; separa fin natural de fin de captura.

        kind en NATURAL_END_REASONS → finished=1, end_reason=kind.
        kind == CAPTURE_LIMIT → finished=0, end_reason=None, capture_limit=1.
        """
        natural = kind in NATURAL_END_REASONS
        return {
            "finished": 1 if natural else 0,
            "end_reason": kind if natural else None,
            "end_confidence": confidence,
            "capture_limit": 0 if natural else 1,
            "mfe": self._mfe,
            "mae": self._mae,
        }
