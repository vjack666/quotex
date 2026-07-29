"""EpisodeSummary — snapshot final del episodio (D5, R8/R10).

Todas las fórmulas están versionadas por `summary_version` del cfg; ningún
umbral vive aquí: se leen del bloque `summary` de evolution_v1.yaml.
Sin reloj de pared: solo consume filas de evolución ya fechadas.
"""
from __future__ import annotations

# Buckets versionados (nombres de diseño; los cortes vienen del cfg).
VELOCITY_FAST = "fast"
VELOCITY_SLOW = "slow"
VIOLENCE_HIGH = "high"
VIOLENCE_LOW = "low"
CURVE_CONVEX = "convex"
CURVE_CONCAVE = "concave"
CURVE_FLAT = "flat"


class EpisodeSummary:
    """Computa el resumen para IA a partir de la traza de evolución."""

    def __init__(self, cfg_summary: dict):
        self._cfg = cfg_summary
        self.summary_version = cfg_summary["summary_version"]
        self._w_sym = float(cfg_summary["quality_symmetry_weight"])
        self._fast = float(cfg_summary["velocity_fast_pips_per_bar"])
        self._violent = float(cfg_summary["violence_high_pips_per_bar"])
        self._flat_mfe = float(cfg_summary["curve_flat_mfe_pips"])
        self._convex_ret = float(cfg_summary["curve_convex_retention"])

    def compute(self, rows_evolution: list[dict],
                resolution_type: str | None) -> dict:
        rows = sorted(rows_evolution, key=lambda r: r["bar_index"])
        if not rows:
            raise ValueError("compute() requiere al menos una fila")
        last = rows[-1]
        mfe = max(r["mfe"] for r in rows)
        mae = min(r["mae"] for r in rows)
        duration_bars = len(rows)
        net = last["distance_pips"]

        # symmetry v1: proporción del recorrido favorable retenido al cierre.
        excursion = mfe - mae
        symmetry = (net - mae) / excursion if excursion else 0.0
        symmetry = min(1.0, max(0.0, symmetry))

        # quality v1: mfe/(mfe+|mae|) ponderada por simetría (cfg weight).
        denom = mfe + abs(mae)
        base = mfe / denom if denom else 0.0
        quality = base * (1.0 - self._w_sym) + symmetry * self._w_sym

        # velocity / violence: buckets versionados (cortes del cfg).
        pips_per_bar = abs(net) / duration_bars
        velocity = VELOCITY_FAST if pips_per_bar >= self._fast else VELOCITY_SLOW
        max_step = max(
            (abs(rows[i]["distance_pips"] - rows[i - 1]["distance_pips"])
             for i in range(1, len(rows))), default=0.0)
        violence = VIOLENCE_HIGH if max_step >= self._violent else VIOLENCE_LOW

        # curve_shape: compara MFE vs recorrido neto.
        if mfe < self._flat_mfe:
            curve_shape = CURVE_FLAT
        elif mfe and net / mfe >= self._convex_ret:
            curve_shape = CURVE_CONVEX
        else:
            curve_shape = CURVE_CONCAVE

        return {
            "quality": quality,
            "velocity": velocity,
            "violence": violence,
            "curve_shape": curve_shape,
            "symmetry": symmetry,
            "episode_type": resolution_type,
            "duration_bars": duration_bars,
            "mfe": mfe,
            "mae": mae,
            "summary_version": self.summary_version,
        }
