"""T11 - Minero de relaciones (aristas del grafo) entre leyes.

Dada una lista de ``Law`` (sin datos), propone aristas simples y
deterministas:
  - dos leyes con probabilidad alta y MISMO market Y MISMA source => 'refuerza'
    con strength = min(probabilidad de ambas).
  - dos leyes con alta probabilidad pero DIFERENTE source del mismo market =>
    'requiere' con strength = min(prob).
  - dos leyes con probabilidad alta pero DIFERENTE market => 'contradice'
    (baja strength).

Acotado y determinista (semilla del cfg). No importa datos ni reader.
"""

from __future__ import annotations

import random

from .types import Law, LawRelation


def _overlap(a: tuple[str, ...], b: tuple[str, ...]) -> bool:
    return bool(set(a) & set(b))


def propose_relations(laws, cfg) -> list[LawRelation]:
    rng = random.Random(cfg.get("seed", 0))
    version = str(cfg.get("discovery_version", "discovery_v1"))
    prob_threshold = float(cfg.get("relation_prob_threshold", 0.5))
    laws = list(laws)
    relations: list[LawRelation] = []

    for i in range(len(laws)):
        for j in range(i + 1, len(laws)):
            a, b = laws[i], laws[j]
            if a.probability < prob_threshold or b.probability < prob_threshold:
                continue
            strength = min(a.probability, b.probability)
            if _overlap(a.markets, b.markets):
                if _overlap(a.sources, b.sources):
                    rtype = "refuerza"
                else:
                    rtype = "requiere"
            else:
                rtype = "contradice"
                strength = strength * 0.5
            relations.append(
                LawRelation(
                    from_law=a.id,
                    to_law=b.id,
                    relation_type=rtype,
                    strength=round(strength, 6),
                    discovery_version=version,
                )
            )
    # Determinismo: orden estable por (from_law, to_law).
    relations.sort(key=lambda r: (r.from_law, r.to_law))
    _ = rng  # semilla reservada para futuras variaciones deterministicas.
    return relations
