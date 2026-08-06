import pytest

from strategy_lab.evidence import EvidenceReport
from strategy_lab.multiple_comparisons import (
    AdjustedResult,
    adjust_pvalues,
    benjamini_hochberg,
    bonferroni,
)
from strategy_lab.promotion_gate import evaluate, evaluate_family
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


# --- PASO 1 del plan (PLAN_MANANA_FASE5_FDR.md): comparaciones múltiples (FDR/Bonferroni) ---


def test_bonferroni_scales_pvalues():
    p = [0.01, 0.02, 0.30]
    res = bonferroni(p, alpha=0.05)
    assert res.n_tests == 3
    # 0.01*3, 0.02*3, 0.30*3 (=0.9, no llega al cap de 1.0)
    assert res.adj_p[0] == 0.03
    assert res.adj_p[1] == 0.06
    assert res.adj_p[2] == pytest.approx(0.9)
    # solo la primera pasa el umbral ajustado
    assert res.rejected_indices == [0]


def test_benjamini_hochberg_monotone_and_correct():
    p = [0.001, 0.008, 0.039, 0.041, 0.042]
    res = benjamini_hochberg(p, alpha=0.05)
    # p_ajustados deben ser monotonicos no-crecientes al retroceder
    assert res.adj_p == sorted(res.adj_p, reverse=True)
    # el mas pequeno: (5/1)*0.001 = 0.005 < 0.05 => rechazado
    assert 0 in res.rejected_indices
    # formula: para N=5, alpha*k/N; el umbral mas exigente es k=1 => 0.01
    # 0.042*5/5 = 0.042 < 0.05 => tambien rechazado (todas <= alpha*k/N)
    assert len(res.rejected_indices) >= 1


def test_evaluate_family_rejects_noise_under_multiple_comparisons():
    """Cuando se evalúan 36 firmas, una con p=0.04 crudo NO debe promoverse.

    Con Bonferroni (alpha/36 ≈ 0.0014) o FDR-BH, un p crudo de 0.04 es ruido
    por azar y el ajuste lo hunde -> INCONCLUSIVE, no PASS.
    """
    good = _good_evidence()
    object.__setattr__(good, "p_value_win_rate", 0.04)
    object.__setattr__(good, "details", {**good.details, "p_value": 0.04})

    # simulamos 36 firmas: 35 con p=1.0 (ruido) + 1 con p=0.04 (la "candidata")
    members = []
    for i in range(36):
        ev = _good_evidence()
        p = 0.04 if i == 0 else 1.0
        object.__setattr__(ev, "p_value_win_rate", p)
        object.__setattr__(ev, "details", {**ev.details, "p_value": p})
        d = evaluate(f"FIRMA-{i:02d}", evidence=ev, robustness=_good_robustness())
        members.append(d)

    fam = evaluate_family(members, method="bonferroni")
    # la firma 0 (p=0.04 crudo) no debe promoverse tras ajuste
    assert "FIRMA-00" not in fam.promoted_members
    assert fam.promoted_members == []
    assert "FIRMA-00" in fam.inconclusive_members


def test_evaluate_family_promotes_strong_signal_only():
    """Una señal REAL (p crudo 1e-6) sobrevive el ajuste BH y se promueve."""
    members = []
    for i in range(10):
        ev = _good_evidence()
        p = 1e-6 if i == 0 else 0.80
        object.__setattr__(ev, "p_value_win_rate", p)
        object.__setattr__(ev, "details", {**ev.details, "p_value": p})
        d = evaluate(f"SIG-{i:02d}", evidence=ev, robustness=_good_robustness())
        members.append(d)

    fam = evaluate_family(members, method="fdr_bh")
    assert "SIG-00" in fam.promoted_members
    # las de ruido no se promueven
    assert all(f"sig-{i:02d}".upper() not in fam.promoted_members for i in range(1, 10))
