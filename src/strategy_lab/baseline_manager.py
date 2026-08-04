"""Baseline Manager del Laboratorio.

Responsabilidad única: administrar baselines oficiales, versiones,
comparaciones contra experimentos y historial de reemplazos.

No evalúa experimentos. No consulta el tribunal.
Solo garantiza que toda comparación sea consistente y trazable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Baseline:
    id: str
    version: str
    created_at: str
    author: str
    description: str
    metrics: Dict[str, Any]
    dataset_checksum: str
    superseded_by: Optional[str] = None
    status: str = "active"


class BaselineManager:
    """Administra baselines oficiales del Laboratorio."""

    def __init__(self) -> None:
        self._baselines: Dict[str, Baseline] = {}
        self._replacement_history: List[Dict[str, Any]] = []

    def register(self, baseline: Baseline) -> None:
        if baseline.id in self._baselines:
            raise ValueError(f"Baseline already registered: {baseline.id}")
        self._baselines[baseline.id] = baseline

    def get(self, baseline_id: str) -> Baseline:
        if baseline_id not in self._baselines:
            raise KeyError(f"Baseline not found: {baseline_id}")
        return self._baselines[baseline_id]

    def list_active(self) -> List[Baseline]:
        return [b for b in self._baselines.values() if b.status == "active"]

    def supersede(self, baseline_id: str, new_baseline: Baseline, reason: str) -> None:
        old = self.get(baseline_id)
        if old.status != "active":
            raise ValueError(f"Cannot supersede non-active baseline: {baseline_id}")
        if old.id == new_baseline.id:
            raise ValueError("Baseline cannot supersede itself")
        object.__setattr__(old, "status", "superseded")
        object.__setattr__(old, "superseded_by", new_baseline.id)
        self._replacement_history.append(
            {
                "old_id": old.id,
                "old_version": old.version,
                "new_id": new_baseline.id,
                "new_version": new_baseline.version,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    def compare(self, baseline_id: str, experiment_metrics: Dict[str, Any]) -> Dict[str, Any]:
        baseline = self.get(baseline_id)
        if baseline.status != "active":
            raise ValueError(f"Baseline is not active: {baseline_id}")
        comparison: Dict[str, Any] = {
            "baseline_id": baseline.id,
            "baseline_version": baseline.version,
            "experiment_metrics": experiment_metrics,
            "deltas": {},
        }
        for key, value in experiment_metrics.items():
            if key in baseline.metrics and isinstance(value, (int, float)) and isinstance(baseline.metrics[key], (int, float)):
                comparison["deltas"][key] = float(value) - float(baseline.metrics[key])
        comparison["delta_count"] = len(comparison["deltas"])
        return comparison

    def history(self) -> List[Dict[str, Any]]:
        return list(self._replacement_history)
