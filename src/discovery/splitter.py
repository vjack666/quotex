"""T4 - Walk-forward splitter por fuente (R9b) y por ano.

Particiona episodios en train/test usando ``ts_open`` como criterio temporal.
Cuando hay >1 fuente distinta, particiona POR FUENTE y devuelve un dict
``{source: (train, test)}`` para que el falsifier evalue por fuente.

Determinismo: ordena por ``ts_open`` antes de cortar. Misma entrada => mismo
split. No usa wall-clock. No importa nada del bot.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .types import Episode


def _year(ts_open: float) -> int:
    # Convierte el timestamp de DATOS (no wall-clock) a ano UTC. Determinista.
    return datetime.fromtimestamp(ts_open, tz=timezone.utc).year


def walk_forward(
    episodes: Iterable[Episode],
    split_year: int,
    seed=None,
):
    """Particiona episodios walk-forward por ``ts_open`` y por ``source``.

    Devuelve ``dict[source, (train, test)]`` donde:
      - ``train``: episodios con ``year(ts_open) <= split_year``
      - ``test`` : episodios con ``year(ts_open)  > split_year``

    ``seed`` se acepta por compatibilidad de firma pero el corte es
    deterministico (orden por ``ts_open``), por lo que el mismo input produce
    el mismo output.
    """
    by_source: dict[str, list[Episode]] = {}
    for ep in episodes:
        by_source.setdefault(ep.source, []).append(ep)

    result: dict[str, tuple[list[Episode], list[Episode]]] = {}
    for source, eps in by_source.items():
        ordered = sorted(eps, key=lambda e: e.ts_open)
        train = [e for e in ordered if _year(e.ts_open) <= split_year]
        test = [e for e in ordered if _year(e.ts_open) > split_year]
        result[source] = (train, test)
    return result
