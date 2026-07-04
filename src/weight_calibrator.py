"""
weight_calibrator.py — Calibración dinámica de pesos del entry_scorer.
=========================================================================
Ajusta automáticamente los pesos de WEIGHTS_REBOUND y WEIGHTS_BREAKOUT
según condiciones de mercado (hora del día y volatilidad).

Uso offline::

    from weight_calibrator import WeightCalibrator
    cal = WeightCalibrator()
    n = cal.load_trades(days=90)
    print(f"Cargados {n} trades")
    weights = cal.calibrate()
    path = cal.export_weights()
    print(f"Exportado a {path}")

Carga en runtime::

    from weight_calibrator import WeightCalibrator
    w = WeightCalibrator.load_weights("data/exports/calibrated_weights.json")
    rebs, brks = WeightCalibrator.select_weights(w, hour=14, avg_range=0.002)
"""
from __future__ import annotations

import json
import logging
import sqlite3
import statistics
from datetime import datetime, timedelta, timezone
from itertools import product
from pathlib import Path
from typing import Any, Optional

from entry_scorer import WEIGHTS_BREAKOUT, WEIGHTS_REBOUND
from trade_journal import _DB_DIR, _now

log = logging.getLogger("consolidation_bot")

# ── Constantes ────────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS_PATH = (
    Path(__file__).resolve().parent.parent
    / "data" / "exports" / "calibrated_weights.json"
)

# Buckets horarios
HOUR_BUCKETS: dict[range, str] = {
    range(0, 6):   "night",
    range(6, 12):  "morning",
    range(12, 18): "afternoon",
    range(18, 24): "evening",
}

# Paso de búsqueda en grid
WEIGHT_STEP = 5
WEIGHT_MIN = 5
WEIGHT_MAX = 60
WEIGHT_TOTAL = 100

# Threshold base para filtrar trades aceptables
SCORE_THRESHOLD = 65

# Modos de estrategia → modo de scoring
REBOUND_ORIGINS = {"STRAT-REVERSAL-SWING", "STRAT-ORDER-BLOCK", "STRAT-A"}
BREAKOUT_ORIGINS = {"STRAT-MOMENTUM", "STRAT-B"}


# ─────────────────────────────────────────────────────────────────────────────
#  WeightCalibrator
# ─────────────────────────────────────────────────────────────────────────────


class WeightCalibrator:
    """Calibra pesos del entry_scorer usando datos históricos de trades.

    Proceso:
        1. Cargar trades desde la BD con outcome WIN/LOSS.
        2. Agrupar por bucket horario y régimen de volatilidad.
        3. Para cada grupo, buscar combinación de pesos que maximice
           Sharpe ratio sobre los trades filtrados por score.
        4. Exportar a JSON.
    """

    # ── Init ──────────────────────────────────────────────────────────────

    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path) if db_path else (
            _DB_DIR / f"trade_journal-{datetime.now().strftime('%Y-%m-%d')}.db"
        )
        self._conn: sqlite3.Connection | None = None
        self.trades: list[dict[str, Any]] = []

        # Copia de los pesos base para reconstruir ratios
        self._weights_rebound: dict[str, int] = dict(WEIGHTS_REBOUND)
        self._weights_breakout: dict[str, int] = dict(WEIGHTS_BREAKOUT)

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __del__(self) -> None:
        self.close()

    # ── Carga de trades  (R1) ────────────────────────────────────────────

    def load_trades(self, days: int = 90) -> int:
        """Carga trades históricos con outcome WIN/LOSS desde la BD.

        Retorna la cantidad de trades cargados.
        """
        since = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()

        rows = self.conn.execute(
            """SELECT scanned_at, asset, direction, payout,
                      outcome, profit,
                      score, score_compression, score_bounce,
                      score_trend, score_payout,
                      strategy_origin, candles_json
                 FROM candidates
                WHERE outcome IN ('WIN', 'LOSS')
                  AND decision = 'ACCEPTED'
                  AND scanned_at >= ?
                  AND candles_json IS NOT NULL
                ORDER BY scanned_at""",
            (since,),
        ).fetchall()

        self.trades = []
        for r in rows:
            trade = self._row_to_trade(r)
            if trade is not None:
                self.trades.append(trade)

        log.info(
            "[WeightCalibrator] Cargados %d trades (últimos %d días)",
            len(self.trades), days,
        )
        return len(self.trades)

    def _row_to_trade(self, row: sqlite3.Row) -> dict[str, Any] | None:
        """Convierte una fila de la BD a un dict interno para calibración."""
        try:
            candles = json.loads(row["candles_json"])
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

        if not candles:
            return None

        # Calcular avg_range (high-low) como proxy de volatilidad (R6)
        ranges = [float(c.get("high", 0)) - float(c.get("low", 0)) for c in candles]
        avg_range = statistics.mean(ranges) if ranges else 0.0

        # Extraer hora del scanned_at
        scanned = row["scanned_at"] or ""
        try:
            dt = datetime.fromisoformat(scanned)
            hour = dt.hour
        except (ValueError, TypeError):
            hour = 12  # fallback

        # Componentes de score
        s_comp = float(row["score_compression"] or 0.0)
        s_bounce = float(row["score_bounce"] or 0.0)
        s_trend = float(row["score_trend"] or 0.0)
        s_payout = float(row["score_payout"] or 0.0)
        total_score = float(row["score"] or 0.0)

        # Determinar modo según strategy_origin
        origin = str(row["strategy_origin"] or "STRAT-A")
        if origin in BREAKOUT_ORIGINS:
            mode = "breakout"
            base_w = self._weights_breakout
            # En BREAKOUT, score_bounce almacena el momentum
            comp_key = "momentum"
        else:
            mode = "rebound"
            base_w = self._weights_rebound
            comp_key = "bounce"

        # Reconstruir ratios: ratio = stored_component / base_weight
        ratios: dict[str, float] = {}
        for key, bw in base_w.items():
            if key == comp_key:
                ratios[key] = s_bounce / bw if bw > 0 else 0.0
            elif key == "compression":
                ratios[key] = s_comp / bw if bw > 0 else 0.0
            elif key == "trend":
                ratios[key] = s_trend / bw if bw > 0 else 0.0
            elif key == "payout":
                ratios[key] = s_payout / bw if bw > 0 else 0.0

        # Ajustes (age_adj + hist_adj + zone_memory_adj)
        base_sum = s_comp + s_bounce + s_trend + s_payout
        adjustments = total_score - base_sum

        return {
            "hour": hour,
            "avg_range": avg_range,
            "mode": mode,
            "origin": origin,
            "ratios": ratios,
            "adjustments": adjustments,
            "profit": float(row["profit"] or 0.0),
            "outcome": str(row["outcome"] or "LOSS"),
            "direction": str(row["direction"] or "call"),
        }

    # ── Agrupación ──────────────────────────────────────────────────────

    @staticmethod
    def _hour_bucket(hour: int) -> str:
        """Mapea hora (0-23) a bucket: night/morning/afternoon/evening."""
        for hr_range, name in HOUR_BUCKETS.items():
            if hour in hr_range:
                return name
        return "afternoon"  # fallback

    def _determine_vol_regimes(self) -> tuple[float, float]:
        """Calcula thresholds de volatilidad (percentiles 33 y 66)."""
        ranges = sorted(t["avg_range"] for t in self.trades)
        if len(ranges) < 3:
            return 0.0, 0.0
        n = len(ranges)
        low_th = ranges[n // 3]
        high_th = ranges[(2 * n) // 3]
        return low_th, high_th

    @staticmethod
    def _vol_regime(avg_range: float, low_th: float, high_th: float) -> str:
        if high_th == low_th:
            return "medium"
        if avg_range <= low_th:
            return "low"
        if avg_range > high_th:
            return "high"
        return "medium"

    # ── Re-score y Sharpe ───────────────────────────────────────────────

    @staticmethod
    def _recompute_score(trade: dict[str, Any], weights: dict[str, int]) -> float:
        """Recomputa el score total con nuevos pesos."""
        base = sum(trade["ratios"].get(k, 0.0) * w for k, w in weights.items())
        return base + trade["adjustments"]

    @staticmethod
    def _sharpe(profits: list[float]) -> float:
        """Calcula Sharpe ratio de una lista de profits.

        Retorna -999 si hay menos de 2 valores o desviación cero.
        """
        if len(profits) < 2:
            return -999.0
        mean_p = statistics.mean(profits)
        try:
            std_p = statistics.stdev(profits)
        except statistics.StatisticsError:
            return -999.0
        if std_p == 0.0:
            return -999.0
        return mean_p / std_p

    # ── Optimización ────────────────────────────────────────────────────

    def _optimize_weights(
        self,
        trades: list[dict[str, Any]],
        base_weights: dict[str, int],
    ) -> dict[str, int]:
        """Grid search sobre combinaciones de pesos.

        Varía cada componente en [-STEP, 0, +STEP] desde base_weights,
        respetando [WEIGHT_MIN, WEIGHT_MAX]. Evalúa cada combinación
        por Sharpe ratio de los trades que pasarían el threshold.

        Retorna la mejor combinación encontrada.
        """
        if len(trades) < 3:
            return dict(base_weights)

        best_sharpe = -999.0
        best_weights = dict(base_weights)

        # Generar valores candidatos por componente
        candidates: list[list[tuple[str, int]]] = []
        for key, base_val in base_weights.items():
            vals = []
            for delta in (-WEIGHT_STEP, 0, WEIGHT_STEP):
                v = base_val + delta
                if WEIGHT_MIN <= v <= WEIGHT_MAX:
                    vals.append((key, v))
            if not vals:
                vals = [(key, base_val)]
            candidates.append(vals)

        for combo in product(*candidates):
            candidate = dict(combo)
            total = sum(candidate.values())
            if total != WEIGHT_TOTAL:
                continue

            # Recalcular scores y filtrar por threshold
            scored_profits: list[float] = []
            for t in trades:
                new_score = self._recompute_score(t, candidate)
                if new_score >= SCORE_THRESHOLD:
                    scored_profits.append(t["profit"])

            if len(scored_profits) < 2:
                continue

            sharpe = self._sharpe(scored_profits)
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = candidate

        return best_weights

    # ── Calibración completa ────────────────────────────────────────────

    def calibrate(self) -> dict[str, Any]:
        """Ejecuta la calibración completa sobre self.trades.

        Agrupa por (hour_bucket, vol_regime, mode) y optimiza pesos
        para cada grupo con suficientes datos.

        Retorna dict con estructura para exportar a JSON.
        """
        if not self.trades:
            log.warning("[WeightCalibrator] No hay trades para calibrar")
            return self._empty_result()

        low_th, high_th = self._determine_vol_regimes()

        # Agrupar trades
        groups: dict[str, list[dict[str, Any]]] = {}
        for t in self.trades:
            hb = self._hour_bucket(t["hour"])
            vr = self._vol_regime(t["avg_range"], low_th, high_th)
            key = f"hour_{hb}_vol_{vr}_mode_{t['mode']}"
            groups.setdefault(key, []).append(t)

        # Optimizar por grupo
        by_group: dict[str, dict[str, Any]] = {}
        for key, grp_trades in groups.items():
            mode = "rebound" if "_mode_rebound" in key else "breakout"
            base = (
                self._weights_rebound if mode == "rebound"
                else self._weights_breakout
            )
            # Extraer sub-key limpia para el JSON
            parts = key.rsplit("_mode_", 1)
            group_label = parts[0]  # e.g. "hour_morning_vol_low"

            if group_label not in by_group:
                by_group[group_label] = {"rebound": {}, "breakout": {}}

            if len(grp_trades) >= 5:
                optimal = self._optimize_weights(grp_trades, base)
                by_group[group_label][mode] = optimal
            else:
                by_group[group_label][mode] = dict(base)

        # Asegurar que existe un default
        if not by_group:
            by_group = {"default": {
                "rebound": dict(self._weights_rebound),
                "breakout": dict(self._weights_breakout),
            }}

        # Calcular stats
        win_trades = [t for t in self.trades if t["outcome"] == "WIN"]
        loss_trades = [t for t in self.trades if t["outcome"] == "LOSS"]

        result: dict[str, Any] = {
            "calibrated_at": _now(),
            "total_trades_used": len(self.trades),
            "stats": {
                "wins": len(win_trades),
                "losses": len(loss_trades),
                "win_rate": (
                    round(len(win_trades) / len(self.trades), 4)
                    if self.trades else 0.0
                ),
            },
            "default": {
                "rebound": dict(self._weights_rebound),
                "breakout": dict(self._weights_breakout),
            },
            "by_group": by_group,
        }

        log.info(
            "[WeightCalibrator] Calibración completa: %d grupos, %d trades",
            len(by_group), len(self.trades),
        )
        return result

    def _empty_result(self) -> dict[str, Any]:
        return {
            "calibrated_at": _now(),
            "total_trades_used": 0,
            "stats": {"wins": 0, "losses": 0, "win_rate": 0.0},
            "default": {
                "rebound": dict(self._weights_rebound),
                "breakout": dict(self._weights_breakout),
            },
            "by_group": {},
        }

    # ── Exportación / Carga  (R3, R4) ───────────────────────────────────

    def export_weights(self, path: Path | None = None) -> Path:
        """Calibra y exporta pesos a un archivo JSON.

        Si no se especifica path, usa data/exports/calibrated_weights.json.
        Retorna el path del archivo escrito.
        """
        output = path or DEFAULT_WEIGHTS_PATH
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        data = self.calibrate()
        output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        log.info("[WeightCalibrator] Pesos exportados a %s (%d grupos)",
                 output, len(data.get("by_group", {})))
        return output

    @staticmethod
    def load_weights(path: Path | str = DEFAULT_WEIGHTS_PATH) -> dict[str, Any]:
        """Carga pesos calibrados desde un archivo JSON.

        Args:
            path: Ruta al archivo JSON.

        Returns:
            Dict con estructura de pesos o dict vacío si no existe.
        """
        p = Path(path)
        if not p.exists():
            log.warning("[WeightCalibrator] No se encontró %s — usando defaults", p)
            return {}
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            log.info("[WeightCalibrator] Pesos cargados desde %s", p)
            return data
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("[WeightCalibrator] Error cargando %s: %s", p, exc)
            return {}

    @staticmethod
    def select_weights(
        weights_data: dict[str, Any],
        hour: int,
        avg_range: float,
    ) -> tuple[dict[str, int], dict[str, int]]:
        """Selecciona los pesos correspondientes a un grupo (hora + vol).

        Args:
            weights_data: Dict cargado con load_weights().
            hour: Hora actual (0-23).
            avg_range: Rango promedio actual como proxy de volatilidad.

        Returns:
            (rebound_weights, breakout_weights) — cada uno es un dict
            con los pesos para ese modo. Si no se encuentra el grupo,
            retorna los pesos default.
        """
        if not weights_data:
            return dict(WEIGHTS_REBOUND), dict(WEIGHTS_BREAKOUT)

        hb = WeightCalibrator._hour_bucket(hour)

        # Determinar régimen de volatilidad desde los datos cargados
        # Si no tenemos referencia, usamos un valor fijo
        by_group = weights_data.get("by_group", {})

        # Intentar coincidencia exacta
        group_key = f"hour_{hb}_vol_{avg_range}"
        # No podemos saber el régimen exacto sin referencia — probamos low/medium/high
        for vol_regime in ("low", "medium", "high"):
            key = f"hour_{hb}_vol_{vol_regime}"
            if key in by_group:
                rebound_w = by_group[key].get("rebound")
                breakout_w = by_group[key].get("breakout")
                if rebound_w and breakout_w:
                    return dict(rebound_w), dict(breakout_w)

        # Fallback a default
        default = weights_data.get("default", {})
        return (
            dict(default.get("rebound", WEIGHTS_REBOUND)),
            dict(default.get("breakout", WEIGHTS_BREAKOUT)),
        )

    @staticmethod
    def apply_weights(
        rebound_weights: dict[str, int],
        breakout_weights: dict[str, int],
    ) -> None:
        """Sobrescribe los pesos globales en entry_scorer.

        Llámese al inicio del bot o cuando se quiera cambiar grupo.

        Args:
            rebound_weights: Pesos para modo REBOUND.
            breakout_weights: Pesos para modo BREAKOUT.
        """
        from entry_scorer import WEIGHTS_BREAKOUT as _WB, WEIGHTS_REBOUND as _WR
        _WR.clear()
        _WR.update(rebound_weights)
        _WB.clear()
        _WB.update(breakout_weights)
        log.info(
            "[WeightCalibrator] Pesos aplicados — REBOUND=%s BREAKOUT=%s",
            rebound_weights, breakout_weights,
        )
