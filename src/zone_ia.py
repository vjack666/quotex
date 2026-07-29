"""IA de Zonas (Feature 28) — lectora de la memoria única del Experience Engine.

DESCUBRE zonas de reacción del mercado agrupando experiencias de la memoria por
PROXIMIDAD de nivel (clustering por distancia, sin umbral de "N toques", sin rol
hardcoded soporte/resistencia, sin _DECAY_TABLE). Emite `zone_confidence` ∈ [0,1]
que es el win rate observado en ese nivel. Reemplaza a zone_memory.py.

CONTRATO (RZ5): SOLO LEE la memoria (`ExperienceMemory.query_similar` /
`all_experiences`). NUNCA escribe. Publica zone_confidence hacia el scorer.

Bandera ZONE_IA_ENABLED en config.py controla si se aplica.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from config import ZONE_IA_ENABLED  # type: ignore
except Exception:
    ZONE_IA_ENABLED = True

# Banda de clustering: % del precio dentro de la cual dos niveles son la misma zona
ZONE_BAND_PCT = 0.0015          # 0.15% — igual que el prototipo validado
MIN_REACTIONS_FOR_CONF = 5      # muestra mínima para emitir confidence no-neutral
WALL_CONF_THRESHOLD = 0.30      # zone_confidence < esto => "muro" (veto)


def _level_band(level: float, pct: float = ZONE_BAND_PCT) -> float:
    """Redondea el nivel a la banda de clustering (para agrupar por proximidad)."""
    if not level:
        return 0.0
    return round(level / (level * pct), 0) * (level * pct)


def discover_zones(asset: str, mem, limit: int = 200) -> List[Dict[str, Any]]:
    """Agrupa experiencias cerradas del asset por proximidad de evento.nivel.

    Devuelve zonas descubiertas (sin etiqueta soporte/resistencia): cada una
    tiene nivel, n_reacciones, win_rate, confidence. SIN reglas de detección.
    """
    similars = mem.query_similar({"asset": str(asset)}, limit=limit)
    closed = [e for e in similars if e.is_closed()]

    groups: Dict[float, List[Any]] = {}
    for e in closed:
        lvl = e.evento.get("nivel")
        if not lvl:
            continue
        key = _level_band(lvl)
        groups.setdefault(key, []).append(e)

    zones: List[Dict[str, Any]] = []
    for key, exps in groups.items():
        if len(exps) < MIN_REACTIONS_FOR_CONF:
            continue
        wins = sum(1 for e in exps if e.resultado.get("decision") == "WIN")
        wr = wins / len(exps)
        # nivel representativo = media de los niveles del grupo
        lvl_mean = sum(e.evento.get("nivel", 0.0) for e in exps) / len(exps)
        zones.append({
            "nivel": lvl_mean,
            "n_reacciones": len(exps),
            "win_rate": round(wr, 3),
            "confidence": round(wr, 3),
        })
    zones.sort(key=lambda z: -z["n_reacciones"])
    return zones


def _zone_confidence_for_level(
    asset: str, direction: str, level: Optional[float], mem
) -> Optional[float]:
    """Win rate observado de experiencias cerradas en la zona de ese nivel.

    Mismo asset + misma direccion + nivel dentro de la banda. Si la muestra es
    insuficiente, devuelve None (el llamador lo trata como neutral 0.5).
    """
    if not level:
        return None
    similars = mem.query_similar({"asset": str(asset), "direction": direction}, limit=200)
    closed = [e for e in similars if e.is_closed()]
    band = level * ZONE_BAND_PCT
    in_zone = [
        e for e in closed
        if e.evento.get("nivel") is not None
        and abs(e.evento.get("nivel") - level) <= band
    ]
    if len(in_zone) < MIN_REACTIONS_FOR_CONF:
        return None
    wins = sum(1 for e in in_zone if e.resultado.get("decision") == "WIN")
    return wins / len(in_zone)


class ZoneIA:
    """Segunda IA lectora de la memoria única (Feature 27)."""

    _mem = None  # cache de ExperienceMemory (solo lectura)

    @classmethod
    def _memory(cls):
        if cls._mem is None:
            try:
                from experience_engine import ExperienceMemory  # type: ignore
                cls._mem = ExperienceMemory()
            except Exception:
                cls._mem = False
        return cls._mem or None

    @classmethod
    def score(cls, candidate: Any) -> Optional[float]:
        """Emite zone_confidence ∈ [0,1] para el candidato.

        None si la IA está desactivada o no hay muestra suficiente (neutral).
        """
        if not ZONE_IA_ENABLED:
            return None
        mem = cls._memory()
        if mem is None:
            return None
        asset = getattr(candidate, "asset", None)
        direction = (getattr(candidate, "direction", "") or "").upper()
        if not asset or direction not in ("CALL", "PUT"):
            return None
        # Nivel de la entrada: entry_price o close de la última vela
        level = getattr(candidate, "entry_price", None)
        if not level:
            candles = getattr(candidate, "candles", None) or []
            if candles:
                last = candles[-1]
                level = getattr(last, "close", None) or getattr(last, "c", None)
        # Feature 29 (RG4): consenso con geometría. Solo LECTURA de métricas
        # (level_role). No es regla: la confianza sigue siendo el WR de memoria;
        # la geometría solo se adjunta para trazabilidad/consenso en el scorer.
        geom = getattr(candidate, "geometry", None)
        if geom and level:
            try:
                from market_geometry_ctx import level_role
                role = level_role(geom, float(level))
                if role.get("is_support") or role.get("is_resistance"):
                    setattr(candidate, "zone_geom_role", role)
            except Exception:
                pass
        return _zone_confidence_for_level(asset, direction, level, mem)

    @classmethod
    def is_wall(cls, candidate: Any) -> bool:
        """True si la zona es un muro (zone_confidence bajo umbral)."""
        conf = cls.score(candidate)
        if conf is None:
            return False
        return conf < WALL_CONF_THRESHOLD
