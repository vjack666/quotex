"""Almacenamiento de Leyes #N (CONTRATO compartido).

Define la interfaz `LawStorage` que implementa `law_store.SQLiteLawStore` (Agente B)
y que consume `reporter` (Agente C) sin acoplarse a la implementación concreta.
Incluye `InMemoryLawStore` para tests de C sin tocar SQLite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from .types import Law, LawRelation


class LawStorage(ABC):
    @abstractmethod
    def save_law(self, law: Law) -> None: ...

    @abstractmethod
    def get_law(self, law_id: str) -> Law | None: ...

    @abstractmethod
    def list_laws(self) -> list[Law]: ...

    @abstractmethod
    def next_id(self) -> str:
        """Devuelve el siguiente id '#N' (secuencial por max id existente)."""


class InMemoryLawStore(LawStorage):
    def __init__(self) -> None:
        self._laws: dict[str, Law] = {}

    def save_law(self, law: Law) -> None:
        # Acumula: no sobrescribe si ya existe (R5/R12).
        if law.id not in self._laws:
            self._laws[law.id] = law

    def replace_law(self, law: Law) -> None:
        # Reemplaza (para lifecycle T12: la ley OBSOLETA/VALIDADA NO se borra,
        # solo cambia de state). Usado por add_transition cuando se pasa un Law
        # actualizado que YA existe.
        self._laws[law.id] = law

    def get_law(self, law_id: str) -> Law | None:
        return self._laws.get(law_id)

    def list_laws(self) -> list[Law]:
        return sorted(self._laws.values(), key=lambda l: l.id)

    def next_id(self) -> str:
        nums = [int(l.id.lstrip("#")) for l in self._laws.values() if l.id.startswith("#")]
        return f"#{max(nums) + 1 if nums else 1}"
