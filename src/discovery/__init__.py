"""Paquete Discovery Engine (Capa 2.5). Minería de conocimiento del Atlas.

Lee episodios YA grabados (Fase B) y EMITE LEYES (#N) como conocimiento de la
Memoria del Mercado. NO opera, NO toca el feed, NO toca el bot.
Ver specs/discovery_engine/ y specs/discovery_engine/CONTRATO.md.
"""

from .types import Law, Episode, LawRelation

__all__ = ["Law", "Episode", "LawRelation"]
