"""Promotion Gate del Laboratorio.

Responsabilidad única: aplicar el tribunal de evidencia de forma declarativa.

No contiene reglas hardcodeadas.
Lee los criterios desde `tribunal_v1.yaml` y evalúa:
- EvidenceReport
- RobustnessReport
- Comparación contra baseline

Devuelve un GateDecision con lista de criterios fallidos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from strategy_lab.evidence import EvidenceReport
from strategy_lab.multiple_comparisons import AdjustedResult, adjust_pvalues
from strategy_lab.robustness import RobustnessReport


@dataclass(frozen=True)
class GateDecision:
    experiment_id: str
    verdict: str  # PASS | FAIL | INCONCLUSIVE
    criteria_passed: int
    criteria_failed: int
    failed_criteria: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


def _load_tribunal(path: Union[str, Path]) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def evaluate(
    experiment_id: str,
    evidence: EvidenceReport,
    robustness: RobustnessReport,
    baseline_comparison: Optional[Dict[str, Any]] = None,
    tribunal_path: Union[str, Path] = Path("src/strategy_lab/config/tribunal_v1.yaml"),
) -> GateDecision:
    tribunal = _load_tribunal(tribunal_path)
    failed: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    # Muestra mínima
    sample_min = tribunal.get("sample_min", {})
    min_individual = sample_min.get("individual_condition", 60)
    if not evidence.sample_ok:
        failed.append(f"sample_min: {evidence.events_total} < {min_individual}")
    details["sample_min"] = {"required": min_individual, "actual": evidence.events_total, "passed": evidence.sample_ok}

    # Poder estadístico
    power = tribunal.get("power_analysis", {})
    min_power = power.get("required_power", 0.8)
    if not evidence.power_ok:
        failed.append(f"power_min: power < {min_power}")
    details["power_min"] = {"required": min_power, "actual": evidence.details.get("power"), "passed": evidence.power_ok}

    # Significancia
    sig = tribunal.get("significance", {})
    p_max = sig.get("p_value_max", 0.05)
    if evidence.p_value_win_rate > p_max:
        failed.append(f"significance: p={evidence.p_value_win_rate:.4f} > {p_max}")
    details["significance"] = {"required": f"p<{p_max}", "actual": evidence.p_value_win_rate, "passed": evidence.p_value_win_rate <= p_max}

    # IC 95%
    ci = tribunal.get("confidence_intervals", {})
    null_values = ci.get("null_values", {})
    ic_failed = False
    ic_details = {}
    for metric_name in ["win_rate", "expected_value", "profit_factor"]:
        ci_tuple = getattr(evidence, f"{metric_name}_ci", None)
        if not isinstance(ci_tuple, (tuple, list)) or len(ci_tuple) != 2:
            continue
        null_val = null_values.get(metric_name)
        if null_val is None:
            continue
        includes_null = float(ci_tuple[0]) <= float(null_val) <= float(ci_tuple[1])
        ic_details[metric_name] = {"ci": ci_tuple, "null": null_val, "includes_null": includes_null, "passed": not includes_null}
        if includes_null:
            ic_failed = True
            failed.append(f"ci_{metric_name}: CI includes null {null_val}")
    details["confidence_intervals"] = ic_details
    if ic_failed:
        details["confidence_intervals_failed"] = True

    # Validación temporal / sobreajuste
    temporal = tribunal.get("temporal_validation", {})
    alarm_pp = temporal.get("train_test_divergence_alarm_pp", 10.0)
    if evidence.overfit_alarm:
        failed.append(f"train_test_divergence: {evidence.train_test_divergence_pp:+.2f}pp >= {alarm_pp}pp")
    details["train_test_divergence"] = {"alarm_pp": alarm_pp, "actual_pp": evidence.train_test_divergence_pp, "passed": not evidence.overfit_alarm}

    # Walk-forward
    wf = tribunal.get("walk_forward", {})
    wf_max_div = wf.get("max_divergence_percent", 10.0)
    wf_div = evidence.details.get("walk_forward_divergence")
    if wf_div is not None and wf_div > wf_max_div:
        failed.append(f"walk_forward: divergence {wf_div:.2f}% > {wf_max_div}%")
    details["walk_forward"] = {"max_divergence_percent": wf_max_div, "actual": wf_div, "passed": wf_div is None or wf_div <= wf_max_div}

    # Mejora mínima
    min_imp = tribunal.get("minimum_improvement", {})
    wr_min = min_imp.get("win_rate_pp_vs_baseline", 3.0)
    em_min = min_imp.get("expected_value_relative_percent", 10.0)
    pf_min = min_imp.get("profit_factor_min", 1.3)
    max_reduction = min_imp.get("max_event_reduction_percent", 50.0)

    if evidence.improvement_win_rate_pp is not None and evidence.improvement_win_rate_pp < wr_min:
        failed.append(f"improvement_win_rate: {evidence.improvement_win_rate_pp:+.2f}pp < {wr_min}pp")
    if evidence.improvement_expected_value_percent is not None and evidence.improvement_expected_value_percent < em_min:
        failed.append(f"improvement_em: {evidence.improvement_expected_value_percent:+.2f}% < {em_min}%")
    if evidence.profit_factor is not None and evidence.profit_factor < pf_min:
        failed.append(f"profit_factor_min: {evidence.profit_factor:.2f} < {pf_min}")
    details["minimum_improvement"] = {
        "win_rate_pp": {"required": wr_min, "actual": evidence.improvement_win_rate_pp},
        "expected_value_percent": {"required": em_min, "actual": evidence.improvement_expected_value_percent},
        "profit_factor_min": {"required": pf_min, "actual": evidence.profit_factor},
    }

    # Robustez
    rob = tribunal.get("robustness", {})
    min_passed = rob.get("min_passed", 3)
    if robustness.failed_count > 1:
        failed.append(f"robustness: {robustness.passed_count}/{robustness.total_tests} passed, {robustness.failed_count} failed")
    elif robustness.passed_count < min_passed:
        failed.append(f"robustness: {robustness.passed_count}/{robustness.total_tests} < {min_passed} required")
    details["robustness"] = {
        "required": min_passed,
        "passed": robustness.passed_count,
        "total": robustness.total_tests,
        "results": robustness.results,
    }

    # Impacto sistémico
    systemic = tribunal.get("systemic_impact", {})
    if systemic.get("required", False):
        systemic_ok = evidence.details.get("systemic_impact_assessed", False)
        if not systemic_ok:
            failed.append("systemic_impact: not assessed")
    details["systemic_impact"] = {"required": systemic.get("required", False), "assessed": evidence.details.get("systemic_impact_assessed", False)}

    # Reproducibilidad
    repro = tribunal.get("reproducibility", {})
    repro_ok = bool(evidence.details.get("dataset_checksum")) and bool(evidence.details.get("code_version"))
    if repro.get("verification", {}).get("clean_environment", False) and not repro_ok:
        warnings.append("Reproducibility fields incomplete")
    details["reproducibility"] = {"passed": repro_ok}

    if baseline_comparison is not None:
        details["baseline_comparison"] = baseline_comparison

    criteria_total = 7
    verdict = "PASS" if not failed else "FAIL"
    if any("sample_min" in c or "significance" in c or "ci_" in c for c in failed):
        verdict = "INCONCLUSIVE"

    return GateDecision(
        experiment_id=experiment_id,
        verdict=verdict,
        criteria_passed=criteria_total - len(failed),
        criteria_failed=len(failed),
        failed_criteria=failed,
        warnings=warnings,
        details=details,
    )


@dataclass(frozen=True)
class FamilyDecision:
    """Veredicto sobre una FAMILIA de hipótesis evaluadas a la vez.

    Cada miembro (p.ej. una firma de secuencia) recibe su GateDecision
    individual, pero el p-valor se ajusta por comparaciones múltiples
    (FDR/Bonferroni) ANTES de emitir el veredicto. Así el tribunal no
    promueve ruido por azar cuando se evalúan 36 firmas juntas.
    """

    method: str
    alpha: float
    n_tests: int
    adjusted: AdjustedResult
    per_member: List[GateDecision]
    promoted_members: List[str]
    inconclusive_members: List[str]
    refuted_members: List[str]


def evaluate_family(
    members: List[GateDecision],
    *,
    ids: Optional[List[str]] = None,
    method: str = "fdr_bh",
    alpha: float = 0.05,
    tribunal_path: Union[str, Path] = Path("src/strategy_lab/config/tribunal_v1.yaml"),
) -> FamilyDecision:
    """Aplica ajuste de comparaciones múltiples sobre una familia de veredictos.

    Flujo:
      1. Toma el p-valor crudo de cada miembro (significancia individual).
      2. Ajusta por FDR/Bonferroni usando `multiple_comparisons`.
      3. Sobrescribe el p-valor efectivo y, si el ajustado no pasa, marca
         `significance` como fallida en el GateDecision del miembro.
      4. Re-clasifica el veredicto: si la única falla era significancia cruda
         y el ajuste la hunde, baja a INCONCLUSIVE (no a REFUTADO: el ajuste
         por azar no prueba que la señal es falsa, solo que no es distinguible).

    `members` debe venir de `evaluate(...)` individual. Si no se pasan `ids`,
    se usan los `experiment_id` de cada GateDecision.
    """
    if not members:
        raise ValueError("evaluate_family requiere al menos un miembro")

    mc = _load_tribunal(tribunal_path).get("multiple_comparisons", {})
    if mc.get("enabled", True):
        method = mc.get("default_method", method)
    alpha = float(alpha)

    ids = ids or [m.experiment_id for m in members]
    raw_p = [float(m.details.get("significance", {}).get("actual", 1.0)) for m in members]
    # Si el detalle no trae el p-valor, lo reconstruimos del fallo de significancia
    for i, m in enumerate(members):
        if m.details.get("significance", {}).get("actual") is None:
            raw_p[i] = 1.0

    adjusted = adjust_pvalues(raw_p, method=method, alpha=alpha, ids=ids)

    per_member: List[GateDecision] = []
    promoted: List[str] = []
    inconclusive: List[str] = []
    refuted: List[str] = []

    for i, m in enumerate(members):
        adj_p = adjusted.adj_p[i]
        passed_adj = adj_p < alpha
        new_failed = list(m.failed_criteria)
        new_details = dict(m.details)
        new_details["significance"] = {
            "required": f"p<{alpha} (ajustado {method})",
            "actual": adj_p,
            "raw": raw_p[i],
            "passed": passed_adj,
        }
        # Si antes pasaba significancia cruda pero el ajuste la hunde:
        if not passed_adj:
            if not any("significance" in c for c in m.failed_criteria):
                new_failed.append(
                    f"significance_adjusted: p_adj={adj_p:.4f} >= {alpha} ({method})"
                )
            verdict = "INCONCLUSIVE"
        else:
            verdict = m.verdict

        per_member.append(
            GateDecision(
                experiment_id=m.experiment_id,
                verdict=verdict,
                criteria_passed=m.criteria_passed - (len(new_failed) - len(m.failed_criteria)),
                criteria_failed=len(new_failed),
                failed_criteria=new_failed,
                warnings=list(m.warnings),
                details=new_details,
            )
        )
        if verdict == "PASS":
            promoted.append(m.experiment_id)
        elif verdict == "INCONCLUSIVE":
            inconclusive.append(m.experiment_id)
        else:
            refuted.append(m.experiment_id)

    return FamilyDecision(
        method=method,
        alpha=alpha,
        n_tests=adjusted.n_tests,
        adjusted=adjusted,
        per_member=per_member,
        promoted_members=promoted,
        inconclusive_members=inconclusive,
        refuted_members=refuted,
    )
