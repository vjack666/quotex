"""Registry del Laboratorio.

Responsabilidad única: almacenar la evidencia completa de cada experimento
y garantizar trazabilidad total.

No evalúa, no promueve, no modifica.
Solo guarda, consulta y exporta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from strategy_lab.baseline_manager import BaselineManager
from strategy_lab.evidence import EvidenceReport
from strategy_lab.promotion_gate import GateDecision
from strategy_lab.robustness import RobustnessReport


@dataclass(frozen=True)
class ExperimentRecord:
    experiment_id: str
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: str = "created"
    tribunal_version: Optional[str] = None
    baseline_id: Optional[str] = None
    baseline_version: Optional[str] = None
    hypothesis: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    evidence_report: Optional[Dict[str, Any]] = None
    robustness_report: Optional[Dict[str, Any]] = None
    baseline_comparison: Optional[Dict[str, Any]] = None
    gate_decision: Optional[Dict[str, Any]] = None
    promotion_path: Optional[str] = None


class ExperimentRegistry:
    """Registry central del Laboratorio."""

    def __init__(self, baseline_manager: Optional[BaselineManager] = None) -> None:
        self._records: Dict[str, ExperimentRecord] = {}
        self._baseline_manager = baseline_manager or BaselineManager()

    def create(
        self,
        experiment_id: str,
        *,
        hypothesis: Optional[str] = None,
        tribunal_version: str = "1.0",
        baseline_id: Optional[str] = None,
        baseline_version: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ExperimentRecord:
        if baseline_id is not None and baseline_version is not None:
            baseline = self._baseline_manager.get(baseline_id)
            if baseline.version != baseline_version:
                raise ValueError(f"Baseline version mismatch: {baseline.version} != {baseline_version}")
        record = ExperimentRecord(
            experiment_id=experiment_id,
            tribunal_version=tribunal_version,
            baseline_id=baseline_id,
            baseline_version=baseline_version,
            hypothesis=hypothesis,
            tags=tags or [],
        )
        self._records[experiment_id] = record
        return record

    def get(self, experiment_id: str) -> ExperimentRecord:
        if experiment_id not in self._records:
            raise KeyError(f"Experiment not found: {experiment_id}")
        return self._records[experiment_id]

    def attach_evidence(self, experiment_id: str, evidence: EvidenceReport) -> ExperimentRecord:
        record = self._require(experiment_id)
        object.__setattr__(record, "evidence_report", evidence.__dict__)
        object.__setattr__(record, "status", "evidence_attached")
        return record

    def attach_robustness(self, experiment_id: str, robustness: RobustnessReport) -> ExperimentRecord:
        record = self._require(experiment_id)
        object.__setattr__(record, "robustness_report", robustness.__dict__)
        object.__setattr__(record, "status", "robustness_attached")
        return record

    def attach_baseline_comparison(self, experiment_id: str, comparison: Dict[str, Any]) -> ExperimentRecord:
        record = self._require(experiment_id)
        object.__setattr__(record, "baseline_comparison", comparison)
        return record

    def attach_gate_decision(self, experiment_id: str, decision: GateDecision) -> ExperimentRecord:
        record = self._require(experiment_id)
        object.__setattr__(record, "gate_decision", decision.__dict__)
        object.__setattr__(record, "status", decision.verdict.lower())
        object.__setattr__(record, "promotion_path", f"edificio/{decision.verdict}/{experiment_id}")
        return record

    def list_by_status(self, status: str) -> List[ExperimentRecord]:
        return [record for record in self._records.values() if record.status == status]

    def export(self, experiment_id: str) -> Dict[str, Any]:
        record = self.get(experiment_id)
        return {
            "experiment_id": record.experiment_id,
            "version": record.version,
            "created_at": record.created_at,
            "status": record.status,
            "tribunal_version": record.tribunal_version,
            "baseline_id": record.baseline_id,
            "baseline_version": record.baseline_version,
            "hypothesis": record.hypothesis,
            "tags": list(record.tags),
            "evidence_report": record.evidence_report,
            "robustness_report": record.robustness_report,
            "baseline_comparison": record.baseline_comparison,
            "gate_decision": record.gate_decision,
            "promotion_path": record.promotion_path,
        }

    def _require(self, experiment_id: str) -> ExperimentRecord:
        if experiment_id not in self._records:
            raise KeyError(f"Experiment not found: {experiment_id}")
        return self._records[experiment_id]
