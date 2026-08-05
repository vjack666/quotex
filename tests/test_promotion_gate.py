from strategy_lab.evidence import EvidenceReport
from strategy_lab.promotion_gate import evaluate
from strategy_lab.robustness import RobustnessReport


def _good_evidence() -> EvidenceReport:
    return EvidenceReport(
        experiment_id="EXP-001",
        tribunal_version="1.0",
        events_total=180,
        events_train=90,
        events_test=90,
        win_rate=0.58,
        win_rate_ci=(0.51, 0.65),
        expected_value=0.08,
        expected_value_ci=(0.02, 0.14),
        profit_factor=1.6,
        profit_factor_ci=(1.2, 2.0),
        p_value_win_rate=0.02,
        test_used="binomtest",
        train_test_divergence_pp=3.0,
        overfit_alarm=False,
        baseline_win_rate=0.50,
        baseline_expected_value=0.0,
        improvement_win_rate_pp=8.0,
        improvement_expected_value_percent=80.0,
        sample_ok=True,
        power_ok=True,
        evidence_level="Reproducida",
        warnings=[],
        details={
            "power": 0.85,
            "train_wr": 0.57,
            "test_wr": 0.59,
            "dataset_checksum": "sha256:abc",
            "code_version": "v1.0",
            "systemic_impact_assessed": True,
            "walk_forward_divergence": 4.0,
        },
    )


def _good_robustness() -> RobustnessReport:
    return RobustnessReport(
        experiment_id="EXP-001",
        tribunal_version="1.0",
        total_tests=5,
        min_required=3,
        passed_count=5,
        failed_count=0,
        inconclusive_count=0,
        results={
            "parameter_perturbation": {"passed": True, "passed_count": 8, "total": 10},
            "stress_period": {"passed": True, "regimes_passed": 5, "total": 5},
            "bootstrap_1000": {"passed": True, "ci": (0.01, 0.15), "null": 0.0},
            "multi_asset": {"passed": True, "passed_count": 2, "total_assets": 2},
            "multi_timeframe": {"passed": True, "passed_count": 2, "total_timeframes": 2},
        },
        warnings=[],
    )


def test_promotion_gate_passes_with_strong_evidence():
    decision = evaluate("EXP-001", evidence=_good_evidence(), robustness=_good_robustness())
    assert decision.verdict == "PASS"
    assert decision.criteria_failed == 0
    assert decision.criteria_passed > 0


def test_promotion_gate_fails_when_sample_is_small():
    evidence = _good_evidence()
    object.__setattr__(evidence, "events_total", 30)
    object.__setattr__(evidence, "sample_ok", False)
    decision = evaluate("EXP-001", evidence=evidence, robustness=_good_robustness())
    assert decision.verdict != "PASS"
    assert any("sample_min" in c for c in decision.failed_criteria)


def test_promotion_gate_fails_when_significance_is_weak():
    evidence = _good_evidence()
    object.__setattr__(evidence, "p_value_win_rate", 0.12)
    object.__setattr__(evidence, "power_ok", False)
    object.__setattr__(evidence, "details", {**evidence.details, "power": 0.4})
    decision = evaluate("EXP-001", evidence=evidence, robustness=_good_robustness())
    assert decision.verdict != "PASS"
    assert any("significance" in c for c in decision.failed_criteria)


def test_promotion_gate_fails_when_robustness_is_low():
    report = _good_robustness()
    robustness = RobustnessReport(
        experiment_id=report.experiment_id,
        tribunal_version=report.tribunal_version,
        total_tests=5,
        min_required=5,
        passed_count=3,
        failed_count=2,
        inconclusive_count=0,
        results={**report.results, "parameter_perturbation": {"passed": False, "value": -0.5, "baseline": 0.0}},
        warnings=list(report.warnings),
    )
    decision = evaluate("EXP-001", evidence=_good_evidence(), robustness=robustness)
    assert decision.verdict != "PASS"
    assert any("robustness" in c for c in decision.failed_criteria)


def test_promotion_gate_fails_when_ci_includes_null():
    evidence = _good_evidence()
    object.__setattr__(evidence, "win_rate_ci", (0.45, 0.61))
    decision = evaluate("EXP-001", evidence=evidence, robustness=_good_robustness())
    assert decision.verdict != "PASS"
    assert any("ci_win_rate" in c for c in decision.failed_criteria)


def test_promotion_gate_reports_baseline_comparison():
    decision = evaluate(
        "EXP-001",
        evidence=_good_evidence(),
        robustness=_good_robustness(),
        baseline_comparison={"baseline_id": "BASELINE-001", "deltas": {"win_rate": 0.05}},
    )
    assert decision.details.get("baseline_comparison") is not None
