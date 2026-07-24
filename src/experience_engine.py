"""Experience Engine — memoria única del mercado + distribución activa a IAs.

NO es una base de datos de detectores. Es la memoria viva del proyecto:

    Mercado -> Observación -> Experience Engine -> IAs (solo leen)

- La memoria es ÚNICA (append-only, sin silos por tipo de detector).
- Las IAs SOLO LEEN (query_similar). NUNCA escriben ni modifican la captura.
- El engine DISTRIBUYE experiencias similares a las IAs en modo activo.

Ver docs/experience_engine_concept.md y specs/experience_engine/.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from experience_schema import MarketExperience

# Root de la memoria única (append-only, particionado por mes)
MEMORY_DIR = Path("data/market_memory")


# ─────────────────────────────────────────────────────────────────────────────
#  MEMORIA ÚNICA (append-only, sin silos)
# ─────────────────────────────────────────────────────────────────────────────
class ExperienceMemory:
    """Almacén único de experiencias. Append-only, particionado por mes.

    Las IAs usan `query_similar` / `all_experiences` (solo lectura). El capturador
    (Observación) usa `record`. Ninguna IA debe llamar `record`.
    """

    def __init__(self, root: Path = MEMORY_DIR):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seen: set[str] = set()  # fingerprints en memoria (dedupe rápido)

    # ── escritura (SOLO capturador/Observación) ──
    def record(self, exp: MarketExperience) -> bool:
        """Adquiere un arco en la memoria. Devuelve True si se guardó (no dupe)."""
        fid = exp.fingerprint()
        with self._lock:
            if fid in self._seen:
                return False
            self._seen.add(fid)
            path = self._month_path(exp.ts)
            line = json.dumps(exp.to_dict(), default=str)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            return True

    # ── lectura (IAs) ──
    def query_similar(
        self,
        profile: Dict[str, Any],
        limit: int = 50,
    ) -> List[MarketExperience]:
        """Recupera experiencias por perfil grueso (SIN reglas de detección).

        El perfil típico: {"asset", "tf", "direction", "stoch_zone"}. El engine
        solo entrega candidatos por coincidencia de perfil; la similitud fina la
        afina cada IA después. No juzga si es soporte/resistencia/FVG.
        """
        out: List[MarketExperience] = []
        asset = profile.get("asset")
        tf = profile.get("tf")
        direction = profile.get("direction")
        for path in sorted(self.root.glob("*.jsonl")):
            for line in _read_lines(path):
                try:
                    exp = MarketExperience.from_dict(line)
                except Exception:
                    continue
                if asset and exp.asset != asset:
                    continue
                if tf and exp.tf != tf:
                    continue
                ev_dir = exp.evento.get("direction")
                if direction and ev_dir and ev_dir.upper() != direction.upper():
                    continue
                out.append(exp)
                if len(out) >= limit:
                    return out
        return out

    def all_experiences(self) -> List[MarketExperience]:
        out: List[MarketExperience] = []
        for path in sorted(self.root.glob("*.jsonl")):
            for line in _read_lines(path):
                try:
                    out.append(MarketExperience.from_dict(line))
                except Exception:
                    continue
        return out

    def count(self) -> int:
        n = 0
        for path in self.root.glob("*.jsonl"):
            n += sum(1 for _ in _read_lines(path))
        return n

    # ── helpers ──
    def _month_path(self, ts: int) -> Path:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return self.root / f"{dt.strftime('%Y-%m')}.jsonl"


def _read_lines(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                yield json.loads(ln)


# ─────────────────────────────────────────────────────────────────────────────
#  ENGINE (modo activo: distribuye a las IAs)
# ─────────────────────────────────────────────────────────────────────────────
IAHandler = Callable[[MarketExperience, List[MarketExperience]], Any]


class ExperienceEngine:
    """Adquiere experiencias y las DISTRIBUYE a las IAs conectadas (modo activo).

    Las IAs se registran con un handler; cuando se adquiere una experiencia, el
    engine busca arcos similares en la memoria y empuja (experiencia, similares)
    a cada IA. Las IAs responden con un Confidence Score / distribución. El engine
    NO decide; solo distribuye.
    """

    def __init__(self, memory: Optional[ExperienceMemory] = None):
        self.memory = memory or ExperienceMemory()
        self._handlers: List[IAHandler] = []
        self._lock = threading.Lock()

    def register_ia(self, handler: IAHandler) -> None:
        """Registra una IA (handler). La IA SOLO recibe; nunca escribe memoria."""
        with self._lock:
            self._handlers.append(handler)

    def acquire(self, exp: MarketExperience) -> Dict[str, Any]:
        """Adquiere un arco y lo DISTRIBUYE a las IAs conectadas (modo activo)."""
        self.memory.record(exp)
        profile = {
            "asset": exp.asset,
            "tf": exp.tf,
            "direction": exp.evento.get("direction"),
        }
        similars = self.memory.query_similar(profile, limit=50)
        responses: Dict[str, Any] = {}
        for i, handler in enumerate(self._handlers):
            try:
                responses[f"ia_{i}"] = handler(exp, similars)
            except Exception:
                responses[f"ia_{i}"] = None
        return responses
