"""T11 - Almacen de relaciones entre leyes (grafo) en SQLite.

Crea la tabla ``law_relations`` si no existe y expone CRUD simple por
``conn`` (sin acoplarse a la clase store de leyes). ``relation_type`` en
('refuerza', 'contradice', 'requiere').
"""

from __future__ import annotations

from .types import LawRelation


VALID_TYPES = LawRelation.VALID_TYPES


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS law_relations (
            from_law TEXT,
            to_law TEXT,
            relation_type TEXT,
            strength REAL,
            discovery_version TEXT
        )
        """
    )
    conn.commit()


def save_relation(conn, rel: LawRelation) -> None:
    if rel.relation_type not in VALID_TYPES:
        raise ValueError(f"relation_type invalido: {rel.relation_type!r}")
    _ensure_table(conn)
    conn.execute(
        """
        INSERT INTO law_relations
        (from_law, to_law, relation_type, strength, discovery_version)
        VALUES (?,?,?,?,?)
        """,
        (
            rel.from_law,
            rel.to_law,
            rel.relation_type,
            float(rel.strength),
            rel.discovery_version,
        ),
    )
    conn.commit()


def get_relations(conn, law_id: str) -> list[LawRelation]:
    _ensure_table(conn)
    cur = conn.execute(
        """
        SELECT from_law, to_law, relation_type, strength, discovery_version
        FROM law_relations
        WHERE from_law = ? OR to_law = ?
        """,
        (law_id, law_id),
    )
    out = []
    for r in cur.fetchall():
        out.append(
            LawRelation(
                from_law=r[0],
                to_law=r[1],
                relation_type=r[2],
                strength=float(r[3]),
                discovery_version=r[4],
            )
        )
    return out


def list_relations(conn) -> list[LawRelation]:
    _ensure_table(conn)
    cur = conn.execute(
        """
        SELECT from_law, to_law, relation_type, strength, discovery_version
        FROM law_relations
        """
    )
    out = []
    for r in cur.fetchall():
        out.append(
            LawRelation(
                from_law=r[0],
                to_law=r[1],
                relation_type=r[2],
                strength=float(r[3]),
                discovery_version=r[4],
            )
        )
    return out
