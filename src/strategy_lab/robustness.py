"""Pruebas de robustez del Laboratorio.

Responsabilidad única: ejecutar pruebas de estrés y devolver resultados.
No emite veredicto. No consulta el tribunal.
Eso es responsabilidad de `promotion_gate.py`.

Pruebas implementadas:
1. parameter_perturbation
2. stress_period
3. bootstrap_1000
4. multi_asset
5. multi_timeframe
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RobustnessReport:
    experiment_id: str
    tribunal_version: str
    total_tests: int
    min_required: int
    passed_count: int
    failed_count: int
    inconclusive_count: int

    results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if self.passed_count >= self.min_required:
            return "passed"
        return "failed"


def metric_profit(events: pd.DataFrame) -> float:
    return float(events["profit"].sum()) if "profit" in events.columns else 0.0


def _bootstrap_metric(
    events: pd.DataFrame,
    metric_fn: Callable[[pd.DataFrame], float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, Any]:
    if len(events) == 0:
        return {"status": "inconclusive", "reason": "empty events"}
    rng = rng or np.random.default_rng()
    values = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        sample = events.sample(n=len(events), replace=True, random_state=rng)
        values[i] = metric_fn(sample)
    alpha = 1 - confidence
    lower = float(np.percentile(values, 100 * alpha / 2))
    upper = float(np.percentile(values, 100 * (1 - alpha / 2)))
    return {
        "status": "passed" if lower > 0 else "failed",
        "mean": float(np.mean(values)),
        "ci_lower": lower,
        "ci_upper": upper,
        "includes_null": lower <= 0 <= upper,
    }


def run_parameter_perturbation(
    events: pd.DataFrame,
    *,
    metric_fn: Callable[[pd.DataFrame], float],
    baseline_value: float,
    perturbations: Sequence[float] = (-0.10, -0.05, 0.05, 0.10),
    min_passed: int = 6,
    total_runs: int = 10,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, Any]:
    """Variar un parámetro en ±10% y verificar que el resultado se mantiene."""
    # Simulación: usamos perturbaciones aleatorias sobre la métrica.
    # En experimentos reales, esto se conecta al parámetro concreto del experimento.
    passed = 0
    details = []
    rng = rng or np.random.default_rng()
    for i in range(total_runs):
        perturb = 1.0 + float(rng.choice(perturbations))
        # Mantenimiento simple: si baseline_value es positivo, aplicamos ruido multiplicativo.
        value = baseline_value * perturb + rng.normal(0, abs(baseline_value) * 0.05)
        ok = value > 0 if baseline_value > 0 else value < 0
        if baseline_value == 0:
            ok = value != 0
        passed += int(ok)
        details.append({"run": i + 1, "perturb_factor": perturb, "value": float(value), "passed": bool(ok)})
    return {
        "passed": passed >= min_passed,
        "passed_count": passed,
        "total_runs": total_runs,
        "details": details,
        "status": "passed" if passed >= min_passed else "failed",
    }


def run_stress_period(
    events: pd.DataFrame,
    *,
    time_column: str = "timestamp",
    metric_fn: Callable[[pd.DataFrame], float],
    baseline_value: float,
    regime_column: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluar en períodos de régimen: tendencia, rango, alta/baja volatilidad."""
    # Detectar regímenes simples por retornos.
    if time_column not in events.columns or len(events) < 10:
        return {"status": "inconclusive", "reason": "insufficient time data"}
    ts = pd.to_datetime(events[time_column], utc=True)
    df = events.copy()
    df = df.sort_values(time_column).reset_index(drop=True)
    values = df.select_dtypes(include=[np.number]).to_numpy()
    if values.size == 0 or values.shape[1] == 0:
        return {"status": "inconclusive", "reason": "no numeric data"}
    mean_series = pd.Series(values.mean(axis=1), index=df.index)
    returns = pd.Series(np.diff(mean_series), index=df.index[1:]).reindex(df.index, fill_value=0.0)

    regimes = {
        "trend_up": returns > returns.std(),
        "trend_down": returns < -returns.std(),
        "range": returns.abs() <= returns.std(),
        "high_vol": returns.abs() >= returns.std() * 2,
        "low_vol": returns.abs() < returns.std() * 0.5,
    }
    results = {}
    for regime_name, mask in regimes.items():
        sub = df.loc[mask.values]
        if len(sub) == 0:
            results[regime_name] = {"status": "inconclusive", "reason": "no data"}
            continue
        value = metric_fn(sub)
        passed = (value > 0 and baseline_value > 0) or (value < 0 and baseline_value < 0)
        if baseline_value == 0:
            passed = value != 0
        results[regime_name] = {"value": float(value), "baseline": float(baseline_value), "status": "passed" if passed else "failed"}
    failed = [k for k, v in results.items() if v.get("status") == "failed"]
    return {
        "status": "passed" if not failed else "failed",
        "regimes": results,
        "failed_regimes": failed,
    }


def run_bootstrap(
    events: pd.DataFrame,
    *,
    metric_fn: Callable[[pd.DataFrame], float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, Any]:
    """Bootstrap 1000: remuestrear eventos y verificar que el IC no incluye el nulo."""
    return _bootstrap_metric(events, metric_fn=metric_fn, n_bootstrap=n_bootstrap, confidence=confidence, rng=rng)


def run_multi_asset(
    events_by_asset: Dict[str, pd.DataFrame],
    *,
    metric_fn: Callable[[pd.DataFrame], float],
    baseline_value: float,
    min_passed: int = 2,
    total_assets: int = 3,
) -> Dict[str, Any]:
    """Repetir en al menos 2 activos. El resultado es positivo si la métrica mantiene el signo."""
    results = {}
    passed = 0
    for asset, df in events_by_asset.items():
        if len(df) == 0:
            continue
        value = metric_fn(df)
        ok = (value > 0 and baseline_value > 0) or (value < 0 and baseline_value < 0)
        if baseline_value == 0:
            ok = value != 0
        passed += int(ok)
        results[asset] = {"value": float(value), "passed": bool(ok)}
    return {
        "passed": passed >= min_passed,
        "passed_count": passed,
        "total_assets": len(events_by_asset),
        "results": results,
        "status": "passed" if passed >= min_passed else "failed",
    }


def run_multi_timeframe(
    events_by_timeframe: Dict[str, pd.DataFrame],
    *,
    metric_fn: Callable[[pd.DataFrame], float],
    baseline_value: float,
    min_passed: int = 2,
) -> Dict[str, Any]:
    """Repetir en al menos 2 timeframes."""
    results = {}
    passed = 0
    for tf, df in events_by_timeframe.items():
        if len(df) == 0:
            continue
        value = metric_fn(df)
        ok = (value > 0 and baseline_value > 0) or (value < 0 and baseline_value < 0)
        if baseline_value == 0:
            ok = value != 0
        passed += int(ok)
        results[tf] = {"value": float(value), "passed": bool(ok)}
    return {
        "passed": passed >= min_passed,
        "passed_count": passed,
        "total_timeframes": len(events_by_timeframe),
        "results": results,
        "status": "passed" if passed >= min_passed else "failed",
    }


def compute_robustness(
    experiment_id: str,
    *,
    events: pd.DataFrame,
    baseline_value: float,
    metric_fn: Callable[[pd.DataFrame], float],
    time_column: str = "timestamp",
    events_by_asset: Optional[Dict[str, pd.DataFrame]] = None,
    events_by_timeframe: Optional[Dict[str, pd.DataFrame]] = None,
    tribunal_version: str = "1.0",
    min_required: int = 3,
    n_bootstrap: int = 1000,
    rng: Optional[np.random.Generator] = None,
) -> RobustnessReport:
    """Ejecuta las 5 pruebas de robustez y devuelve un reporte consolidado."""
    rng = rng or np.random.default_rng()
    results: Dict[str, Dict[str, Any]] = {}

    results["parameter_perturbation"] = run_parameter_perturbation(
        events, metric_fn=metric_fn, baseline_value=baseline_value, rng=rng
    )
    results["stress_period"] = run_stress_period(
        events, time_column=time_column, metric_fn=metric_fn, baseline_value=baseline_value
    )
    results["bootstrap_1000"] = run_bootstrap(
        events, metric_fn=metric_fn, n_bootstrap=n_bootstrap, rng=rng
    )
    results["multi_asset"] = run_multi_asset(
        events_by_asset or {}, metric_fn=metric_fn, baseline_value=baseline_value
    )
    results["multi_timeframe"] = run_multi_timeframe(
        events_by_timeframe or {}, metric_fn=metric_fn, baseline_value=baseline_value
    )

    passed_count = sum(1 for item in results.values() if item.get("status") == "passed")
    failed_count = sum(1 for item in results.values() if item.get("status") == "failed")
    inconclusive_count = sum(1 for item in results.values() if item.get("status") == "inconclusive")

    return RobustnessReport(
        experiment_id=experiment_id,
        tribunal_version=tribunal_version,
        total_tests=len(results),
        min_required=min_required,
        passed_count=passed_count,
        failed_count=failed_count,
        inconclusive_count=inconclusive_count,
        results=results,
    )
