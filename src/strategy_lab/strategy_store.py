"""strategy_store — emite la estrategia optimizada como objeto + doc (SL-R9,R12).

NO escribe leyes (solo lectura a la Memoria). La estrategia óptima es un
objeto estructurado: pasos ordenados, referencias a leyes, importancia por
paso, contribución por paso, edge walk-forward, p-valor, fuentes/mercados.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from strategy_lab.backtester import Score
from strategy_lab.strategy_parser import ParsedStrategy
from strategy_lab.variant_searcher import Variant


@dataclass(frozen=True)
class OptimizedStrategy:
    name: str
    steps_ordered: list[str]
    law_refs: list[str]
    importance: dict[str, float]      # step_name -> |delta| (ablation)
    contribution: dict[str, float]    # step_name -> edge_without
    edge_train: float
    edge_test: float
    p_values: dict[str, float]
    dropped: list[str]
    direction: str
    sources: list[str] = field(default_factory=lambda: ["EURUSD_M15_Dukascopy_prestado"])
    markets: list[str] = field(default_factory=lambda: ["forex"])


class StrategyStore:
    @staticmethod
    def build(name: str, parsed: ParsedStrategy, variant: Variant,
              score: Score, dropped: list[str], cfg: dict[str, Any]) -> OptimizedStrategy:
        steps_ordered = [parsed.steps[i].name for i in variant.order]
        law_refs = [parsed.steps[i].spec.get("law_ref", "")
                    for i in variant.order if parsed.steps[i].is_law()]
        return OptimizedStrategy(
            name=name,
            steps_ordered=steps_ordered,
            law_refs=[r for r in law_refs if r],
            importance={}, contribution={},
            edge_train=score.edge_train, edge_test=score.edge_test,
            p_values={}, dropped=dropped, direction=score.direction,
        )

    @staticmethod
    def to_markdown(opt: OptimizedStrategy) -> str:
        lines = [
            f"# Estrategia optimizada: {opt.name}",
            "",
            f"- Dirección de rebote: **{opt.direction}**",
            f"- Edge train: **{opt.edge_train:.3f}**  |  Edge hold-out: **{opt.edge_test:.3f}**",
            f"- Fuentes: {', '.join(opt.sources)}",
            f"- Mercados: {', '.join(opt.markets)}",
            "",
            "## Pasos en orden óptimo",
        ]
        for i, s in enumerate(opt.steps_ordered, 1):
            lines.append(f"{i}. {s}")
        if opt.law_refs:
            lines.append("")
            lines.append("## Leyes de la Memoria que respaldan")
            for r in opt.law_refs:
                lines.append(f"- {r}")
        if opt.dropped:
            lines.append("")
            lines.append("## Pasos eliminados (no aportan / no falsables)")
            for d in opt.dropped:
                lines.append(f"- {d}")
        return "\n".join(lines)
