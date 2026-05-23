from __future__ import annotations

from .models import RouterSnapshot


def render_control_center(snapshot: RouterSnapshot) -> str:
    ts = snapshot.generated_at.strftime("%H:%M:%S")
    top = "n/a"
    if snapshot.top_symbol and snapshot.top_strategy and snapshot.top_phase:
        top = (
            f"{snapshot.top_symbol} | {snapshot.top_strategy} | {snapshot.top_phase} "
            f"| conf={snapshot.top_confidence:.2f}"
        )

    return (
        "\n".join(
            [
                "[CONTROL-CENTER] Quant Signal Router",
                f"  UTC: {ts}",
                f"  Signals: total={snapshot.total_signals} routed={snapshot.routed_signals}",
                f"  Strategies: STRAT-B={snapshot.strat_b} BOB={snapshot.bob}",
                f"  Market phase: SETUP={snapshot.setup} RETEST={snapshot.retest} CONFIRMED={snapshot.confirmed}",
                f"  Top signal: {top}",
            ]
        )
    )


__all__ = ["render_control_center"]
