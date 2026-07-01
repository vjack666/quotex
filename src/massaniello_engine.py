from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Literal


Result = Literal["w", "l"]
Mode = Literal["normal", "progressive"]
SystemMode = Literal["massaniello", "calculator", "hybrid"]


@dataclass(frozen=True)
class Settings:
    initial_balance: float = 30.0
    operations: int = 7
    expected_itm: int = 4
    profit: float = 1.92
    mode: Mode = "normal"
    system_mode: SystemMode = "massaniello"
    reinvest_percent: float = 20.0
    objective_increment: int = 2
    manual_objective: float | None = None

    def validate(self) -> None:
        if self.initial_balance <= 0:
            raise ValueError("El saldo inicial debe ser mayor que 0.")
        if self.operations < 1:
            raise ValueError("El numero de operaciones debe ser al menos 1.")
        if not 1 <= self.expected_itm <= self.operations:
            raise ValueError("El numero de ITM debe estar entre 1 y el numero de operaciones.")
        if self.profit <= 0:
            raise ValueError("El profit debe ser mayor que 0. Usa 0.92 para 92% o 1.92 como multiplicador.")
        if self.mode not in ("normal", "progressive"):
            raise ValueError("El tipo de Masaniello debe ser normal o progressive.")
        if self.system_mode not in ("massaniello", "calculator", "hybrid"):
            raise ValueError("El sistema debe ser massaniello, calculator o hybrid.")
        if not 0 <= self.reinvest_percent <= 100:
            raise ValueError("El porcentaje de reinversion debe estar entre 0 y 100.")
        if self.objective_increment < 1:
            raise ValueError("El incremento objetivo debe ser al menos 1.")
        if self.manual_objective is not None and self.manual_objective <= 0:
            raise ValueError("El objetivo manual debe ser mayor que 0.")


@dataclass(frozen=True)
class BetRow:
    number: int
    result: Result | None
    stake: float
    massaniello_stake: float | None
    calculator_stake: float
    difference: float | None
    return_amount: float | None
    capital: float
    wins: int
    losses: int
    itm_percent: float | None
    withdrawal: float
    status: str


@dataclass(frozen=True)
class Simulation:
    settings: Settings
    rows: list[BetRow]
    current_capital: float
    next_stake: float | None
    next_massaniello_stake: float | None
    next_calculator_stake: float
    next_difference: float | None
    next_number: int | None
    wins: int
    losses: int
    withdrawals: float
    status: str
    finished: bool
    target_capital: float
    minimum_net_profit: float
    balance_objective: float
    objective_entry: float


def normalize_history(history: Iterable[str]) -> tuple[Result, ...]:
    cleaned: list[Result] = []
    for item in history:
        value = str(item).strip().lower()
        if not value:
            continue
        if value not in ("w", "l"):
            raise ValueError("El historial solo acepta W o L.")
        cleaned.append(value)  # type: ignore[arg-type]
    return tuple(cleaned)


def effective_profit(profit: float) -> float:
    return profit + 1 if profit < 1 else profit


@lru_cache(maxsize=512)
def _multiplier_table(operations: int, expected_itm: int, profit: float) -> tuple[tuple[float | None, ...], ...]:
    profit = effective_profit(profit)
    table: list[list[float | None]] = [
        [None for _ in range(expected_itm + 2)] for _ in range(operations + 1)
    ]

    for played in range(operations, -1, -1):
        for wins in range(expected_itm, -1, -1):
            if wins == expected_itm:
                table[played][wins] = 1.0
            elif expected_itm - wins == operations - played:
                table[played][wins] = profit ** (operations - played)
            elif played == operations:
                table[played][wins] = None
            else:
                after_loss = table[played + 1][wins]
                after_win = table[played + 1][wins + 1]
                if after_loss is None or after_win is None:
                    table[played][wins] = None
                else:
                    table[played][wins] = (
                        profit
                        * after_loss
                        * after_win
                        / (after_loss + (profit - 1) * after_win)
                    )

    return tuple(tuple(row) for row in table)


def calculate_stake(settings: Settings, capital: float, wins: int, losses: int) -> float | None:
    settings.validate()
    profit = effective_profit(settings.profit)
    played = wins + losses
    if _is_finished(settings, wins, losses, played):
        return None

    table = _multiplier_table(settings.operations, settings.expected_itm, profit)
    try:
        after_loss = table[played + 1][wins]
        after_win = table[played + 1][wins + 1]
    except IndexError:
        return None

    if after_loss is None or after_win is None:
        return capital

    denominator = after_loss + (profit - 1) * after_win
    if denominator == 0:
        return capital

    stake = (1 - profit * after_win / denominator) * capital
    return max(0.0, min(capital, stake))


def calculate_balance_objective(settings: Settings, capital: float) -> tuple[float, float]:
    settings.validate()
    profit = effective_profit(settings.profit)
    if settings.manual_objective is not None and settings.manual_objective > capital:
        objective = settings.manual_objective
    else:
        objective = float(int(capital // 1) + settings.objective_increment)

    payout = profit - 1
    utility_needed = max(0.0, objective - capital)
    entry = utility_needed / payout if payout > 0 else 0.0
    return objective, entry


def simulate(settings: Settings, history: Iterable[str]) -> Simulation:
    if settings.system_mode == "massaniello":
        return _simulate_massaniello(settings, history)
    return _simulate_objective_system(settings, history)


def _simulate_massaniello(settings: Settings, history: Iterable[str]) -> Simulation:
    settings.validate()
    results = normalize_history(history)

    capital = settings.initial_balance
    max_capital = settings.initial_balance
    wins = 0
    losses = 0
    withdrawals = 0.0
    rows: list[BetRow] = []

    for index, result in enumerate(results, start=1):
        played = wins + losses
        stake = calculate_stake(settings, capital, wins, losses)
        if stake is None:
            break
        _, calculator_stake = calculate_balance_objective(settings, capital)
        difference = stake - calculator_stake

        if result == "w":
            raw_return = stake * (settings.profit - 1)
            if settings.mode == "progressive":
                amount_to_previous_peak = max(0.0, max_capital - capital)
                excess = max(0.0, raw_return - amount_to_previous_peak)
                withdrawal = excess * (100 - settings.reinvest_percent) / 100
                new_capital = capital + raw_return - withdrawal
                new_max = max(max_capital, new_capital)
                if new_capital >= max_capital:
                    new_wins = 0
                    new_losses = 0
                else:
                    new_wins = wins + 1
                    new_losses = losses
            else:
                withdrawal = 0.0
                new_capital = capital + raw_return
                new_max = max(max_capital, new_capital)
                new_wins = wins + 1
                new_losses = losses
            return_amount = raw_return
        else:
            withdrawal = 0.0
            return_amount = -stake
            new_capital = capital - stake
            new_max = max_capital
            new_wins = wins
            new_losses = losses + 1

        wins_display = new_wins
        losses_display = new_losses
        status = _status(settings, new_wins, new_losses, new_wins + new_losses)
        itm_percent = (wins + (1 if result == "w" else 0)) / (played + 1)

        capital = new_capital
        max_capital = new_max
        wins = new_wins
        losses = new_losses
        withdrawals += withdrawal

        rows.append(
            BetRow(
                number=index,
                result=result,
                stake=stake,
                massaniello_stake=stake,
                calculator_stake=calculator_stake,
                difference=difference,
                return_amount=return_amount,
                capital=capital,
                wins=wins_display,
                losses=losses_display,
                itm_percent=itm_percent,
                withdrawal=withdrawal,
                status=status,
            )
        )

    played = wins + losses
    next_stake = calculate_stake(settings, capital, wins, losses)
    _, next_calculator_stake = calculate_balance_objective(settings, capital)
    next_difference = None if next_stake is None else next_stake - next_calculator_stake
    finished = next_stake is None
    status = _status(settings, wins, losses, played)
    target_multiplier = _multiplier_table(
        settings.operations, settings.expected_itm, settings.profit
    )[0][0]
    target_capital = settings.initial_balance * (target_multiplier or 1)
    balance_objective, objective_entry = calculate_balance_objective(settings, capital)

    return Simulation(
        settings=settings,
        rows=rows,
        current_capital=capital,
        next_stake=next_stake,
        next_massaniello_stake=next_stake,
        next_calculator_stake=next_calculator_stake,
        next_difference=next_difference,
        next_number=(len(rows) + 1 if not finished else None),
        wins=wins,
        losses=losses,
        withdrawals=withdrawals,
        status=status,
        finished=finished,
        target_capital=target_capital,
        minimum_net_profit=target_capital - settings.initial_balance,
        balance_objective=balance_objective,
        objective_entry=objective_entry,
    )


def _simulate_objective_system(settings: Settings, history: Iterable[str]) -> Simulation:
    settings.validate()
    results = normalize_history(history)

    capital = settings.initial_balance
    wins = 0
    losses = 0
    rows: list[BetRow] = []

    for index, result in enumerate(results, start=1):
        massaniello_stake = calculate_stake(settings, capital, wins, losses)
        _, calculator_stake = calculate_balance_objective(settings, capital)
        if settings.system_mode == "hybrid" and massaniello_stake is not None:
            stake = min(massaniello_stake, calculator_stake)
        else:
            stake = calculator_stake

        difference = None if massaniello_stake is None else massaniello_stake - calculator_stake
        if capital <= 0:
            break

        if result == "w":
            return_amount = stake * (settings.profit - 1)
            objective, _ = calculate_balance_objective(settings, capital)
            capital = objective
            wins += 1
            losses = 0
        else:
            return_amount = -stake
            capital = max(0.0, capital - stake)
            losses += 1

        status = "Ciclo objetivo"
        if result == "l":
            status = f"Gale {losses}"
        rows.append(
            BetRow(
                number=index,
                result=result,
                stake=stake,
                massaniello_stake=massaniello_stake,
                calculator_stake=calculator_stake,
                difference=difference,
                return_amount=return_amount,
                capital=capital,
                wins=wins,
                losses=losses,
                itm_percent=wins / index if index else None,
                withdrawal=0.0,
                status=status,
            )
        )

    massaniello_stake = calculate_stake(settings, capital, wins, losses)
    _, calculator_stake = calculate_balance_objective(settings, capital)
    if settings.system_mode == "hybrid" and massaniello_stake is not None:
        next_stake = min(massaniello_stake, calculator_stake)
    else:
        next_stake = calculator_stake
    next_difference = None if massaniello_stake is None else massaniello_stake - calculator_stake
    balance_objective, objective_entry = calculate_balance_objective(settings, capital)

    return Simulation(
        settings=settings,
        rows=rows,
        current_capital=capital,
        next_stake=next_stake,
        next_massaniello_stake=massaniello_stake,
        next_calculator_stake=calculator_stake,
        next_difference=next_difference,
        next_number=len(rows) + 1,
        wins=wins,
        losses=losses,
        withdrawals=0.0,
        status=_system_status(settings.system_mode, next_difference),
        finished=capital <= 0,
        target_capital=balance_objective,
        minimum_net_profit=max(0.0, balance_objective - capital),
        balance_objective=balance_objective,
        objective_entry=objective_entry,
    )


def _system_status(system_mode: SystemMode, difference: float | None) -> str:
    if system_mode == "calculator":
        return "Calculadora de Binarias"
    if system_mode == "hybrid":
        if difference is None:
            return "Modo hibrido"
        return "Hibrido: usa la menor entrada"
    return "Massaniello"


def _is_finished(settings: Settings, wins: int, losses: int, played: int) -> bool:
    return (
        played >= settings.operations
        or wins >= settings.expected_itm
        or losses >= settings.operations - settings.expected_itm + 1
    )


def _status(settings: Settings, wins: int, losses: int, played: int) -> str:
    if wins >= settings.expected_itm:
        return "Objetivo completado"
    if losses >= settings.operations - settings.expected_itm + 1:
        return "Secuencia perdida"
    if played >= settings.operations:
        return "Secuencia terminada"
    remaining_otm = settings.operations - settings.expected_itm - losses
    return f"Te quedan {remaining_otm} OTM"