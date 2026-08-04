"""Experiment Runner del Laboratorio.

Responsabilidad única: orquestar el flujo completo de un experimento.

No contiene lógica científica.
No aplica el tribunal.
Solo coordina módulos especializados y consolida el informe.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

from strategy_lab.baseline_manager import BaselineManager
from strategy_lab.evidence import compute_evidence
from strategy_lab.promotion_gate import evaluate
from strategy_lab.registry import ExperimentRegistry
from strategy_lab.robustness import compute_robustness


@dataclass(frozen=True)
class ExperimentArtifacts:
    experiment_id: str
    events: Any
    evidence_report: Any
    robustness_report: Any
    baseline_comparison: Optional[Dict[str, Any]] = None
    gate_decision: Optional[Any] = None
    registry_record: Optional[Any] = None
    report_path: Optional[str] = None


def _dataset_checksum(events) -> str:
    if hasattr(events, "to_csv"):
        data = events.to_csv(index=False).encode("utf-8")
    else:
        data = str(events).encode("utf-8")
    return f"sha256:{hashlib.sha256(data).hexdigest()[:16]}"


def run_experiment(
    experiment_id: str,
    events,
    *,
    hypothesis: Optional[str] = None,
    tribunal_version: str = "1.0",
    baseline_id: Optional[str] = None,
    baseline_version: Optional[str] = None,
    tribunal_path: Union[str, Path] = Path("src/strategy_lab/config/tribunal_v1.yaml"),
    registry: Optional[ExperimentRegistry] = None,
    baseline_manager: Optional[BaselineManager] = None,
    report_dir: Optional[Path] = None,
    baseline_comparison: Optional[Dict[str, Any]] = None,
) -> ExperimentArtifacts:
    registry = registry or ExperimentRegistry(baseline_manager=baseline_manager or BaselineManager())
    baseline_manager = baseline_manager or registry._baseline_manager
    record = registry.create(
        experiment_id,
        hypothesis=hypothesis,
        tribunal_version=tribunal_version,
        baseline_id=baseline_id,
        baseline_version=baseline_version,
        tags=["lab"],
    )

    evidence = compute_evidence(
        events,
        experiment_id=experiment_id,
        tribunal_version=tribunal_version,
        baseline_win_rate=baseline_manager.get(baseline_id).metrics.get("win_rate") if baseline_id else None,
        baseline_expected_value=baseline_manager.get(baseline_id).metrics.get("expected_value") if baseline_id else None,
    )
    registry.attach_evidence(experiment_id, evidence)

    robustness = compute_robustness(
        experiment_id,
        events=evidence.details.get("events_train_df", events),
        baseline_value=baseline_manager.get(baseline_id).metrics.get("expected_value", 0.0) if baseline_id else 0.0,
        metric_fn=_default_metric_fn(),
    )
    registry.attach_robustness(experiment_id, robustness)

    if baseline_id and baseline_comparison is None:
        baseline_comparison = baseline_manager.compare(baseline_id, {
            "win_rate": float(evidence.win_rate),
            "expected_value": float(evidence.expected_value),
            "profit_factor": float(evidence.profit_factor) if evidence.profit_factor is not None else None,
        })
    if baseline_comparison is not None:
        registry.attach_baseline_comparison(experiment_id, baseline_comparison)

    decision = evaluate(
        experiment_id,
        evidence=evidence,
        robustness=robustness,
        baseline_comparison=baseline_comparison,
        tribunal_path=tribunal_path,
    )
    registry.attach_gate_decision(experiment_id, decision)

    report_path = None
    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = str(report_dir / f"{experiment_id}_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# {experiment_id}\n\n")
            f.write(f"## Tribunal\n\n- tribunal_version: {tribunal_version}\n- baseline_id: {baseline_id}\n- verdict: {decision.verdict}\n\n")
            f.write(f"## Evidence\n\n")
            f.write(f"- win_rate: {evidence.win_rate:.4f}\n")
            f.write(f"- expected_value: {evidence.expected_value:.4f}\n")
            f.write(f"- profit_factor: {evidence.profit_factor}\n")
            f.write(f"- p_value: {evidence.p_value_win_rate:.4f}\n")
            f.write(f"- power: {evidence.details.get('power')}\n\n")
            f.write(f"## Robustness\n\n")
            f.write(f"- passed: {robustness.passed_count}/{robustness.total_tests}\n\n")
            if baseline_comparison is not None:
                f.write(f"## Baseline Comparison\n\n")
                f.write(f"- baseline_id: {baseline_id}\n")
                f.write(f"- deltas: {baseline_comparison.get('deltas')}\n")

    return ExperimentArtifacts(
        experiment_id=experiment_id,
        events=events,
        evidence_report=evidence,
        robustness_report=robustness,
        baseline_comparison=baseline_comparison,
        gate_decision=decision,
        registry_record=registry.get(experiment_id),
        report_path=report_path,
    )


def _default_metric_fn():
    def metric(events):
        if hasattr(events, "__getitem__") and "profit" in events.columns:
            return float(events["profit"].sum())
        return 0.0

    return metric
