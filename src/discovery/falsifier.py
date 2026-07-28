"""T5 - Falsificador de leyes por fuente (permutacion de etiquetas).

Evalua un candidato de ley midiendo la tasa de REBOUND en el hold-out por
fuente y comparandola contra la baseline de la fuente. p-value por
permutaciones de etiquetas (semilla del cfg). Descarta si p>=p_cut,
n<min_sample o rate<min_freq.

Sin literales de umbral: todo viene de ``cfg``. Sin wall-clock.
"""

from __future__ import annotations

import random

from .types import Episode


def _final_distance(ep: Episode) -> float:
    """Distance_pips del ultimo barra del episodio (reversion del empuje)."""
    ev = ep.evolution or []
    if not ev:
        return 0.0
    last = max(ev, key=lambda r: r.get("bar_index", 0))
    return float(last.get("distance_pips", 0.0))


def _is_reversal(ep: Episode) -> bool:
    """EFECTO que mide el Discovery: el empuje revierte (distance_pips final < 0).

    Es la variable objetivo real (no mfe>0, que es ~88% y no discrimina).
    R8: mfe/mae quedan FUERA del predictor; aqui solo se usa como EFECTO medido.
    """
    return _final_distance(ep) < 0.0


def evaluate(law_candidate, test_episodes_by_source, cfg):
    """Evalua ``law_candidate`` por fuente.

    ``law_candidate`` debe implementar ``predict(episode) -> bool`` (True si
    predice rebote). ``test_episodes_by_source`` es ``dict[source, list[Episode]]``.

    Devuelve ``dict[source, (n, rate, baseline, delta, p_value)]``.
    Devuelve ``p_value=1.0`` (descartado) cuando ``n<min_sample`` o
    ``rate<min_freq``.
    """
    rng = random.Random(cfg.get("seed", 0))
    p_cut = float(cfg["p_cut"])
    min_sample = int(cfg["min_sample"])
    min_freq = float(cfg["min_freq"])
    n_perm = int(cfg.get("n_perm", 200))

    results: dict[str, tuple[int, float, float, float, float]] = {}
    for source, eps in test_episodes_by_source.items():
        preds = [ep for ep in eps if bool(law_candidate.predict(ep))]
        n = len(preds)
        outcomes = [1.0 if _is_reversal(ep) else 0.0 for ep in preds]
        rate = (sum(outcomes) / n) if n > 0 else 0.0

        total = len(eps)
        base_rebounds = sum(1 for ep in eps if _is_reversal(ep))
        baseline = (base_rebounds / total) if total > 0 else 0.0
        delta = rate - baseline

        p_value = 1.0
        if n >= 2 and total >= n:
            if n < min_sample or rate < min_freq:
                # Descartado explicitamente: p_value saturado en 1.0.
                p_value = 1.0
            else:
                all_outcomes = [
                    1.0 if _is_reversal(ep) else 0.0 for ep in eps
                ]
                count = 0
                for _ in range(n_perm):
                    sample = rng.sample(all_outcomes, n)
                    if (sum(sample) / n) >= (rate - 1e-12):
                        count += 1
                p_value = (count + 1) / (n_perm + 1)

        # Salvaguarda: si por cfg el p_cut no se cumple, no debe aceptarse.
        _ = p_cut  # p_cut se usa en el llamador para decidir aceptacion.
        results[source] = (n, rate, baseline, delta, p_value)
    return results
