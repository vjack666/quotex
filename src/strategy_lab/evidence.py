"""Motor estadístico del Laboratorio.

Responsabilidad única: cálculos de evidencia.
No aplica veredictos, no consulta el tribunal, no evalúa robustez.

Entrada principal: DataFrame de eventos con al menos:
  - split: 'train' | 'test'
  - win: 0/1
  - payout / profit / expected_value: opcional pero recomendado
Salida: EvidenceReport con métricas, intervalos, significancia y alertas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class EvidenceReport:
    experiment_id: str
    tribunal_version: str

    events_total: int
    events_train: int
    events_test: int

    win_rate: float
    win_rate_ci: Tuple[float, float]
    expected_value: float
    expected_value_ci: Tuple[float, float]
    profit_factor: Optional[float]
    profit_factor_ci: Optional[Tuple[float, float]]

    p_value_win_rate: float
    test_used: str

    train_test_divergence_pp: Optional[float]
    overfit_alarm: bool

    baseline_win_rate: Optional[float]
    baseline_expected_value: Optional[float]

    improvement_win_rate_pp: Optional[float]
    improvement_expected_value_percent: Optional[float]

    sample_ok: bool
    power_ok: bool
    evidence_level: str

    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


def _closest_pmf_binom(n: int, p: float) -> Optional[np.ndarray]:
    # Exact binomial test via SciPy.
    return stats.binom.pmf(np.arange(n + 1), n, p)


def _wilson_ci(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    phat = k / n
    denom = 1 + z**2 / n
    centre = (phat + z**2 / (2 * n)) / denom
    margin = (z * np.sqrt((phat * (1 - phat) + z**2 / (4 * n)) / n)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def _bootstrap_ci_expected_value(
    values: np.ndarray,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[float, float]:
    if len(values) == 0:
        return (0.0, 0.0)
    rng = rng or np.random.default_rng()
    boot = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        sample = rng.choice(values, size=len(values), replace=True)
        boot[i] = float(np.mean(sample))
    alpha = 1 - confidence
    return (float(np.percentile(boot, 100 * alpha / 2)), float(np.percentile(boot, 100 * (1 - alpha / 2))))


def _profit_factor(profits: np.ndarray) -> Optional[float]:
    pos = profits[profits > 0].sum()
    neg = -profits[profits < 0].sum()
    if neg <= 0:
        return None if pos == 0 else float("inf")
    return float(pos / neg)


def _power_analysis(effect_pp: float, baseline: float, n: int, alpha: float = 0.05) -> float:
    # Simplified power estimate for one-sample proportion.
    p0 = baseline
    p1 = baseline + effect_pp / 100
    if not (0 < p1 < 1) or n <= 0:
        return 0.0
    se = np.sqrt(p0 * (1 - p0) / n)
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = (p1 - p0 - z_alpha * se) / np.sqrt(p1 * (1 - p1) / n)
    return float(stats.norm.cdf(z_beta))


def compute_evidence(
    events: pd.DataFrame,
    *,
    experiment_id: str = "unknown",
    tribunal_version: str = "1.0",
    split_column: str = "split",
    win_column: str = "win",
    ev_column: Optional[str] = "expected_value",
    profit_column: Optional[str] = "profit",
    time_column: Optional[str] = "timestamp",
    baseline_win_rate: Optional[float] = None,
    baseline_expected_value: Optional[float] = None,
    effect_pp: float = 3.0,
    power_min: float = 0.80,
    divergence_alarm_pp: float = 10.0,
) -> EvidenceReport:
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    df = events.copy()
    if win_column not in df.columns:
        raise KeyError(f"Missing win column: {win_column}")

    win = pd.to_numeric(df[win_column], errors="coerce").fillna(0).astype(int).values
    n_total = int(win.size)

    if split_column in df.columns:
        train_mask = df[split_column].astype(str).str.lower().eq("train").values
        test_mask = df[split_column].astype(str).str.lower().eq("test").values
    else:
        train_mask = np.zeros(n_total, dtype=bool)
        test_mask = np.zeros(n_total, dtype=bool)

    if time_column and time_column in df.columns and not (train_mask | test_mask).any():
        ts = pd.to_datetime(df[time_column], errors="coerce")
        cutoff = ts.dropna().quantile(0.5)
        train_mask = (ts <= cutoff).fillna(False).astype(bool).values
        test_mask = (~train_mask)

    n_train = int(train_mask.sum())
    n_test = int(test_mask.sum())
    if n_total > 0 and not (train_mask | test_mask).any():
        warnings.append("No train/test labels found; using full sample for metrics.")
        train_mask = np.ones(n_total, dtype=bool)
        test_mask = np.ones(n_total, dtype=bool)
        n_train = n_total
        n_test = n_total

    win_rate = float(win.mean()) if n_total else 0.0
    win_rate_ci = _wilson_ci(int(win.sum()), n_total) if n_total else (0.0, 0.0)

    ev_values = None
    expected_value = None
    expected_value_ci = (None, None)
    if ev_column and ev_column in df.columns:
        ev_values = pd.to_numeric(df[ev_column], errors="coerce").fillna(0.0).values
        expected_value = float(np.nanmean(ev_values)) if n_total else 0.0
        if n_total > 1:
            expected_value_ci = _bootstrap_ci_expected_value(ev_values)

    profits = None
    profit_factor = None
    profit_factor_ci = None
    if profit_column and profit_column in df.columns:
        profits = pd.to_numeric(df[profit_column], errors="coerce").fillna(0.0).values
        profit_factor = _profit_factor(profits)

    train_wr = float(win[train_mask].mean()) if n_train else None
    test_wr = float(win[test_mask].mean()) if n_test else None
    divergence_pp = None
    overfit_alarm = False
    if train_wr is not None and test_wr is not None:
        divergence_pp = float((test_wr - train_wr) * 100)
        overfit_alarm = bool(abs(divergence_pp) >= divergence_alarm_pp)

    p_value = 1.0
    test_used = "none"
    if n_total > 0:
        try:
            # Exact binomial test against baseline or 0.5.
            p0 = baseline_win_rate if baseline_win_rate is not None else 0.5
            result = stats.binomtest(int(win.sum()), n_total, p0, alternative="two-sided")
            p_value = float(result.pvalue)
            test_used = "binomtest"
        except Exception as exc:  # pragma: no cover
            warnings.append(f"Significance test failed: {exc}")

    improvement_wr_pp = None
    improvement_ev_pct = None
    if baseline_win_rate is not None:
        improvement_wr_pp = float((win_rate - baseline_win_rate) * 100)
    if baseline_expected_value is not None and expected_value is not None and baseline_expected_value != 0:
        improvement_ev_pct = float((expected_value - baseline_expected_value) / abs(baseline_expected_value) * 100)

    power = _power_analysis(effect_pp, baseline_win_rate or 0.5, n_total) if baseline_win_rate is not None else 1.0
    sample_ok = n_total >= 60
    power_ok = bool(power >= power_min)

    if profit_factor is None:
        warnings.append("profit_factor unavailable: profits missing or all losses.")
    if expected_value is None:
        warnings.append("expected_value unavailable.")

    if overfit_alarm:
        warnings.append(f"Train/test divergence alarm: {divergence_pp:+.2f}pp")

    evidence_level = "Observacional"
    if sample_ok and p_value < 0.05:
        evidence_level = "Aislada"
    if n_test > 0 and evidence_level == "Aislada":
        evidence_level = "Reproducida"

    details.update(
        {
            "n_total": n_total,
            "n_train": n_train,
            "n_test": n_test,
            "train_wr": train_wr,
            "test_wr": test_wr,
            "p_value": p_value,
            "power": power,
            "win_sum": int(win.sum()),
        }
    )

    return EvidenceReport(
        experiment_id=experiment_id,
        tribunal_version=tribunal_version,
        events_total=n_total,
        events_train=n_train,
        events_test=n_test,
        win_rate=win_rate,
        win_rate_ci=win_rate_ci,
        expected_value=expected_value if expected_value is not None else 0.0,
        expected_value_ci=expected_value_ci if expected_value_ci[0] is not None else (0.0, 0.0),
        profit_factor=profit_factor,
        profit_factor_ci=profit_factor_ci,
        p_value_win_rate=p_value,
        test_used=test_used,
        train_test_divergence_pp=divergence_pp,
        overfit_alarm=overfit_alarm,
        baseline_win_rate=baseline_win_rate,
        baseline_expected_value=baseline_expected_value,
        improvement_win_rate_pp=improvement_wr_pp,
        improvement_expected_value_percent=improvement_ev_pct,
        sample_ok=sample_ok,
        power_ok=power_ok,
        evidence_level=evidence_level,
        warnings=warnings,
        details=details,
    )


def events_from_csv(path: str, **kwargs: Any) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "timestamp" in kwargs:
        ts_col = kwargs["timestamp"]
        if ts_col in df.columns:
            df[ts_col] = pd.to_datetime(df[ts_col], utc=True)
    return df
