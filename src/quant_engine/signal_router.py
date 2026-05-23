from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List

from .models import RoutedSignal, RouterSnapshot, SignalPhase, StrategyName, StrategySignal


@dataclass
class RouterConfig:
    strategy_priority: Dict[StrategyName, float]
    phase_boost: Dict[SignalPhase, float]


def _default_config() -> RouterConfig:
    return RouterConfig(
        strategy_priority={
            StrategyName.BOB: 80.0,
            StrategyName.STRAT_B: 70.0,
        },
        phase_boost={
            SignalPhase.SETUP: 3.0,
            SignalPhase.RETEST: 7.0,
            SignalPhase.CONFIRMED: 15.0,
        },
    )


class SignalRouter:
    """Router de señales multi-estrategia con deduplicación por símbolo."""

    def __init__(self, config: RouterConfig | None = None) -> None:
        self.config = config or _default_config()

    def route(self, signals: Iterable[StrategySignal]) -> List[RoutedSignal]:
        scored: List[RoutedSignal] = []
        for s in signals:
            base = self.config.strategy_priority.get(s.strategy, 50.0)
            phase_boost = self.config.phase_boost.get(s.phase, 0.0)
            score = base + phase_boost + max(0.0, min(1.0, float(s.confidence))) * 20.0
            scored.append(
                RoutedSignal(
                    signal=s,
                    priority_score=score,
                    route_reason=(
                        f"strategy={s.strategy.value} base={base:.1f} phase={s.phase.value} "
                        f"boost={phase_boost:.1f} conf={s.confidence:.2f}"
                    ),
                )
            )

        # Deduplicación por símbolo: conservar la señal con mayor score.
        best_by_symbol: Dict[str, RoutedSignal] = {}
        for routed in sorted(scored, key=lambda item: item.priority_score, reverse=True):
            symbol = routed.signal.symbol.upper()
            if symbol not in best_by_symbol:
                best_by_symbol[symbol] = routed

        return sorted(best_by_symbol.values(), key=lambda item: item.priority_score, reverse=True)

    def snapshot(self, signals: Iterable[StrategySignal], routed: Iterable[RoutedSignal]) -> RouterSnapshot:
        signals_list = list(signals)
        routed_list = list(routed)

        strategy_counter = Counter(s.strategy for s in signals_list)
        phase_counter = Counter(s.phase for s in signals_list)

        top_symbol = None
        top_strategy = None
        top_phase = None
        top_conf = 0.0
        if routed_list:
            top = routed_list[0].signal
            top_symbol = top.symbol
            top_strategy = top.strategy.value
            top_phase = top.phase.value
            top_conf = float(top.confidence)

        return RouterSnapshot(
            generated_at=datetime.now(tz=timezone.utc),
            total_signals=len(signals_list),
            routed_signals=len(routed_list),
            strat_b=int(strategy_counter.get(StrategyName.STRAT_B, 0)),
            bob=int(strategy_counter.get(StrategyName.BOB, 0)),
            setup=int(phase_counter.get(SignalPhase.SETUP, 0)),
            retest=int(phase_counter.get(SignalPhase.RETEST, 0)),
            confirmed=int(phase_counter.get(SignalPhase.CONFIRMED, 0)),
            top_symbol=top_symbol,
            top_strategy=top_strategy,
            top_phase=top_phase,
            top_confidence=top_conf,
        )


__all__ = ["RouterConfig", "SignalRouter"]
