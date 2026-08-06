"""Ajuste de p-valores por comparaciones múltiples (FDR / Bonferroni).

Responsabilidad única: corregir la inferencia cuando se evalúan N hipótesis
a la vez (p.ej. 36 firmas de secuencia del LAB-SEC). Sin esto, por azar
algunas firmas caen "arriba" del umbral y el tribunal promovería basura.

Detectado por el revisor externo (ver PLAN_MANANA_FASE5_FDR.md, PASO 1).

Funciones puras, solo stdlib. No dependen de scipy/pandas.

Referencias:
  - Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery
    rate: a practical and powerful approach to multiple testing. JRSS B.
  - Bonferroni, C. E. (1936). Teoria statistica delle classi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class AdjustedResult:
    """Resultado del ajuste para una familia de hipótesis."""

    method: str
    n_tests: int
    alpha: float
    # p-valores crudos y ajustados en el mismo orden que la entrada
    raw_p: List[float]
    adj_p: List[float]
    # índices (en el orden de entrada) que pasan el umbral ajustado
    rejected_indices: List[int]
    # dict legible id -> (raw_p, adj_p, rechazada?)
    by_id: Dict[str, Tuple[float, float, bool]] = field(default_factory=dict)


def _validate_pvalues(pvalues: Sequence[float]) -> List[float]:
    out: List[float] = []
    for p in pvalues:
        try:
            pv = float(p)
        except (TypeError, ValueError):
            raise ValueError(f"p-value no numérico: {p!r}")
        if not (0.0 <= pv <= 1.0):
            # Un p-value fuera de rango es un error de cálculo, no ruido.
            raise ValueError(f"p-value fuera de [0,1]: {pv}")
        out.append(pv)
    return out


def bonferroni(pvalues: Sequence[float], alpha: float = 0.05) -> AdjustedResult:
    """Corrección de Bonferroni: p_adj = min(1, p * N).

    Controla la FWER (probabilidad de al menos un falso positivo).
    La más conservadora: mata señales reales con N grande, pero es el piso
    de honestidad cuando se promueve cualquier cosa.
    """
    raw = _validate_pvalues(pvalues)
    n = len(raw)
    adj = [min(1.0, p * n) for p in raw]
    rejected = [i for i, p in enumerate(adj) if p < alpha]
    return AdjustedResult(
        method="bonferroni",
        n_tests=n,
        alpha=alpha,
        raw_p=raw,
        adj_p=adj,
        rejected_indices=rejected,
    )


def benjamini_hochberg(pvalues: Sequence[float], alpha: float = 0.05) -> AdjustedResult:
    """Benjamini-Hochberg (FDR step-up).

    Ordena ascendente, encuentra el mayor k tal que
    p_(k) <= alpha * k / N, y rechaza las k primeras. Luego ajusta los
    p-values monotonicamente (p_adj(i) = min_{j>=i} (N/j) * p_(j)),
    respetando el límite en 1.0.
    """
    raw = _validate_pvalues(pvalues)
    n = len(raw)
    if n == 0:
        return AdjustedResult("fdr_bh", 0, alpha, [], [], [])

    order = sorted(range(n), key=lambda i: raw[i])
    adj_ordered = [0.0] * n

    # Paso 1: p_ajustado crudo = (N / rank) * p
    prev = float("inf")
    for rank, idx in enumerate(order, start=1):
        val = (n / rank) * raw[idx]
        prev = min(prev, val)
        adj_ordered[idx] = prev

    # Paso 2: cap a 1.0 y monotonicidad decreciente al retroceder
    capped = [min(1.0, v) for v in adj_ordered]
    for i in range(n - 2, -1, -1):
        capped[i] = min(capped[i], capped[i + 1])

    rejected = [i for i in range(n) if capped[i] < alpha]
    return AdjustedResult(
        method="fdr_bh",
        n_tests=n,
        alpha=alpha,
        raw_p=list(raw),
        adj_p=capped,
        rejected_indices=rejected,
    )


def adjust_pvalues(
    pvalues: Sequence[float],
    method: str = "fdr_bh",
    alpha: float = 0.05,
    ids: Optional[Sequence[str]] = None,
) -> AdjustedResult:
    """Dispatcher: aplica el método pedido y etiqueta por id si se pasan.

    `ids` debe tener la misma longitud que `pvalues` si se provee; crea
    `by_id` para consumo legible del tribunal.
    """
    if method == "bonferroni":
        res = bonferroni(pvalues, alpha)
    elif method in ("fdr_bh", "bh"):
        res = benjamini_hochberg(pvalues, alpha)
    else:
        raise ValueError(f"Método de comparaciones múltiples desconocido: {method!r}")

    if ids is not None:
        if len(ids) != len(res.raw_p):
            raise ValueError("ids y pvalues deben tener la misma longitud")
        by_id: Dict[str, Tuple[float, float, bool]] = {}
        for i, hid in enumerate(ids):
            by_id[hid] = (res.raw_p[i], res.adj_p[i], i in res.rejected_indices)
        object.__setattr__(res, "by_id", by_id)
    return res
