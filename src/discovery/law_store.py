"""T7 - Almacen de Leyes en SQLite (implementa LawStorage del CONTRATO).

Crea la tabla ``leyes`` si no existe. Acumula (NO sobrescribe): si el id ya
existe, lo ignora. ``state`` por defecto 'EXPERIMENTAL'. ``next_id`` devuelve
'#N' secuencial por max id existente.

Solo importa tipos del paquete. NO importa reader/space/miner.
"""

from __future__ import annotations

import json
from typing import Iterable

from .storage import LawStorage
from .types import Law


def _enc(seq: Iterable[str] | None) -> str:
    if seq is None:
        return ""
    seq = list(seq)
    if not seq:
        return ""
    return json.dumps(list(seq), ensure_ascii=False)


def _dec(text: str | None) -> tuple[str, ...]:
    if not text:
        return ()
    try:
        return tuple(json.loads(text))
    except (json.JSONDecodeError, TypeError):
        return tuple(s for s in (text or "").split(",") if s)


class SQLiteLawStore(LawStorage):
    def __init__(self, conn) -> None:
        self.conn = conn
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leyes (
                id TEXT PRIMARY KEY,
                name TEXT,
                conditions TEXT,
                probability REAL,
                confidence TEXT,
                markets TEXT,
                sources TEXT,
                timeframes TEXT,
                cases_studied INT,
                state TEXT,
                discovery_version TEXT,
                script_ref TEXT
            )
            """
        )
        self.conn.commit()

    def save_law(self, law: Law) -> None:
        # Acumula: NO sobrescribe si el id ya existe.
        cur = self.conn.execute("SELECT 1 FROM leyes WHERE id = ?", (law.id,))
        if cur.fetchone() is not None:
            return
        self.conn.execute(
            """
            INSERT INTO leyes
            (id, name, conditions, probability, confidence, markets, sources,
             timeframes, cases_studied, state, discovery_version, script_ref)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                law.id,
                law.name,
                law.conditions,
                law.probability,
                law.confidence,
                _enc(law.markets),
                _enc(law.sources),
                _enc(law.timeframes),
                int(law.cases_studied),
                law.state or "EXPERIMENTAL",
                law.discovery_version,
                law.script_ref,
            ),
        )
        self.conn.commit()

    def get_law(self, law_id: str) -> Law | None:
        cur = self.conn.execute("SELECT * FROM leyes WHERE id = ?", (law_id,))
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        d = dict(zip(cols, row))
        return Law(
            id=d["id"],
            name=d["name"],
            conditions=d["conditions"],
            probability=float(d["probability"]),
            confidence=d["confidence"],
            markets=_dec(d["markets"]),
            sources=_dec(d["sources"]),
            timeframes=_dec(d["timeframes"]),
            cases_studied=int(d["cases_studied"]),
            state=d["state"] or "EXPERIMENTAL",
            discovery_version=d["discovery_version"],
            script_ref=d["script_ref"],
        )

    def list_laws(self) -> list[Law]:
        cur = self.conn.execute("SELECT * FROM leyes ORDER BY id")
        cols = [d[0] for d in cur.description]
        out = []
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            out.append(
                Law(
                    id=d["id"],
                    name=d["name"],
                    conditions=d["conditions"],
                    probability=float(d["probability"]),
                    confidence=d["confidence"],
                    markets=_dec(d["markets"]),
                    sources=_dec(d["sources"]),
                    timeframes=_dec(d["timeframes"]),
                    cases_studied=int(d["cases_studied"]),
                    state=d["state"] or "EXPERIMENTAL",
                    discovery_version=d["discovery_version"],
                    script_ref=d["script_ref"],
                )
            )
        return out

    def next_id(self) -> str:
        cur = self.conn.execute("SELECT id FROM leyes")
        nums = [
            int(r[0].lstrip("#"))
            for r in cur.fetchall()
            if r[0] and r[0].startswith("#") and r[0].lstrip("#").isdigit()
        ]
        return f"#{max(nums) + 1 if nums else 1}"
