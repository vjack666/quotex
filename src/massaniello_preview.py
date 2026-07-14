"""Massaniello bankroll preview for the hub dashboard.

Uses the same stake formula as the bot (`massaniello_engine.calculate_stake`).
Assigned capital (MASSANIELLO_VIRTUAL_CAPITAL) is the risk bankroll — not the
full broker account balance.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from massaniello_engine import Settings, calculate_stake, effective_profit


DEFAULT_PREVIEW_PAYOUT_PCT = 92


def _status_text(operations: int, expected_wins: int, wins: int, losses: int) -> str:
    played = wins + losses
    if wins >= expected_wins:
        return "Objetivo completado"
    max_losses = operations - expected_wins + 1
    if losses >= max_losses:
        return "Secuencia perdida"
    if played >= operations:
        return "Secuencia terminada"
    remaining_otm = operations - expected_wins - losses
    return f"Te quedan {remaining_otm} OTM"


def build_massaniello_preview(
    *,
    assigned_capital: float,
    operations: int,
    expected_wins: int,
    account_balance: Optional[float] = None,
    wins: int = 0,
    losses: int = 0,
    live_capital: Optional[float] = None,
    payout_pct: int = DEFAULT_PREVIEW_PAYOUT_PCT,
    source: str = "config",
) -> dict[str, Any]:
    """Build a serializable preview dict for the hub.

    Args:
        assigned_capital: Risk bankroll configured by the user (virtual capital).
        operations / expected_wins: Massaniello session shape.
        account_balance: Broker balance (informational only).
        wins / losses: Current sequence counters (0/0 when bot is stopped).
        live_capital: Manager current_balance when live; else assigned_capital.
        payout_pct: Assumed payout % for stake math (default 92).
        source: ``config`` | ``live``.
    """
    ops = max(1, int(operations))
    ew = max(1, min(int(expected_wins), ops))
    w = max(0, int(wins))
    l = max(0, int(losses))
    payout = max(1, int(payout_pct))
    profit_fraction = payout / 100.0  # 0.92 for 92%

    bankroll = float(live_capital) if live_capital is not None else float(assigned_capital or 0.0)
    if bankroll <= 0 and assigned_capital > 0:
        bankroll = float(assigned_capital)

    settings = Settings(
        initial_balance=max(bankroll, 0.01) if bankroll > 0 else 0.01,
        operations=ops,
        expected_itm=ew,
        profit=profit_fraction,
        system_mode="massaniello",
    )

    next_stake: Optional[float] = None
    if bankroll > 0:
        raw = calculate_stake(settings, bankroll, w, l)
        if raw is not None:
            next_stake = round(float(raw), 2)

    finished = next_stake is None
    can_enter = (not finished) and bankroll > 0 and (next_stake or 0) > 0

    warn_over_balance = (
        account_balance is not None
        and float(assigned_capital) > float(account_balance) > 0
    )

    return {
        "assigned_capital": round(float(assigned_capital or 0.0), 2),
        "account_balance": (
            round(float(account_balance), 2) if account_balance is not None else None
        ),
        "operations": ops,
        "expected_wins": ew,
        "wins": w,
        "losses": l,
        "payout_pct": payout,
        "next_stake": next_stake,
        "bankroll_used": round(bankroll, 2) if bankroll > 0 else 0.0,
        "status": _status_text(ops, ew, w, l),
        "can_enter": can_enter,
        "source": source,
        "warn_assigned_gt_balance": bool(warn_over_balance),
        "profit_multiplier": effective_profit(profit_fraction),
    }


def preview_from_runner(
    runner: Any,
    *,
    payout_pct: Optional[int] = None,
    assigned_capital: Optional[float] = None,
    operations: Optional[int] = None,
    expected_wins: Optional[int] = None,
    use_form_overrides: bool = False,
) -> dict[str, Any]:
    """Build preview from BotRunner config + optional live bot Massaniello.

    When ``use_form_overrides`` is True (hub live typing), ignore live session
    counters and compute a fresh-sequence stake from the form values so the
    user sees stake updates before pressing Guardar.
    """
    cfg: Mapping[str, Any] = runner.get_config() if hasattr(runner, "get_config") else {}
    assigned = float(
        assigned_capital
        if assigned_capital is not None
        else (cfg.get("massaniello_virtual_capital") or 0.0)
    )
    ops = int(operations if operations is not None else (cfg.get("massaniello_ops") or 5))
    ew = int(expected_wins if expected_wins is not None else (cfg.get("massaniello_wins") or 3))
    if payout_pct is None:
        payout_pct = int(cfg.get("min_payout") or DEFAULT_PREVIEW_PAYOUT_PCT)
    payout_pct = max(1, min(99, int(payout_pct)))

    bot = getattr(runner, "bot", None)
    account_balance = None
    if bot is not None and getattr(bot, "current_balance", None) is not None:
        # When virtual capital is active, bot.current_balance may be the bankroll.
        # Prefer broker-facing value if executor tracks it separately; else use config status.
        account_balance = float(bot.current_balance)

    status = runner.get_status() if hasattr(runner, "get_status") else {}
    if status.get("balance") is not None:
        # Runner status may expose broker-ish balance
        try:
            account_balance = float(status["balance"])
        except (TypeError, ValueError):
            pass

    mgr = getattr(bot, "massaniello", None) if bot is not None else None
    state = getattr(runner, "state", "stopped")
    live = state in ("running", "starting") and mgr is not None

    # Hub form typing: stake from form values immediately (before Guardar).
    if use_form_overrides:
        return build_massaniello_preview(
            assigned_capital=assigned,
            operations=ops,
            expected_wins=ew,
            account_balance=account_balance,
            wins=0,
            losses=0,
            live_capital=assigned if assigned > 0 else account_balance,
            payout_pct=payout_pct,
            source="form",
        )

    if live:
        st = mgr.session_status() if hasattr(mgr, "session_status") else {}
        stake_amt, stake_status = (0.0, "NO_BALANCE")
        if hasattr(mgr, "next_stake"):
            stake_amt, stake_status = mgr.next_stake(payout_pct)
        return {
            "assigned_capital": round(assigned, 2),
            "account_balance": (
                round(float(account_balance), 2) if account_balance is not None else None
            ),
            "operations": int(st.get("operations") or ops),
            "expected_wins": int(st.get("expected_wins") or ew),
            "wins": int(st.get("wins") or 0),
            "losses": int(st.get("losses") or 0),
            "payout_pct": int(payout_pct),
            "next_stake": round(float(stake_amt), 2) if stake_amt else None,
            "bankroll_used": round(float(st.get("balance") or assigned or 0), 2),
            "status": (
                "Objetivo completado"
                if st.get("complete")
                else "Secuencia perdida"
                if st.get("failed")
                else _status_text(
                    int(st.get("operations") or ops),
                    int(st.get("expected_wins") or ew),
                    int(st.get("wins") or 0),
                    int(st.get("losses") or 0),
                )
            ),
            "can_enter": bool(st.get("can_enter")) if "can_enter" in st else stake_status == "OK",
            "source": "live",
            "stake_status": stake_status,
            "warn_assigned_gt_balance": False,
            "profit_multiplier": effective_profit(payout_pct / 100.0),
        }

    return build_massaniello_preview(
        assigned_capital=assigned,
        operations=ops,
        expected_wins=ew,
        account_balance=account_balance,
        wins=0,
        losses=0,
        live_capital=assigned if assigned > 0 else account_balance,
        payout_pct=payout_pct,
        source="config",
    )
