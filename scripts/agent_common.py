"""Utilidades compartidas por los agentes offline de analisis STRAT-F.

Centraliza la carga lightgbm-free de trades resueltos y los helpers
estadisticos (media, desviacion, intervalo de Wilson) para que cada
agente (review, stoch, ...) no duplique logica.

El loader enriquece cada trade con el estocastico de M15 y M5 tal como
esta persistido en los DBs (columnas ``stoch_m15`` / ``stoch_m5`` en
``scan_candidates`` y ``strategy_json`` en ``candidates``). M1 NO se
graba aun en el sistema: el agente stoch lo marca como no-disponible.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

# Path bootstrap
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SRC = os.path.join(_ROOT, "src")
for _p in (_SRC, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ml_features import FEATURE_NAMES  # noqa: E402

DB_GLOB_CANDIDATES = os.path.join(_ROOT, "data", "db", "trade_journal-*.db")
DB_GLOB_BLACKBOX = os.path.join(_ROOT, "data", "db", "black_box_strat*.db")
AGENT_DIR = os.path.join(_ROOT, "data", "agent")


# ── DB discovery ────────────────────────────────────────────────────────────
def discover_db_paths() -> list[str]:
    paths: list[str] = []
    seen = set()
    for pattern in (DB_GLOB_CANDIDATES, DB_GLOB_BLACKBOX):
        for p in sorted(glob.glob(pattern)):
            ap = os.path.abspath(p)
            if ap in seen:
                continue
            seen.add(ap)
            paths.append(p)
    return paths


def _to_epoch(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if value > 1e12:
            return float(value) / 1000.0
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _json_loads(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _parse_stoch(raw: Any) -> dict:
    """Normaliza un estocastico persistido a dict con k/d/estado/cruce."""
    s = _json_loads(raw)
    if not s:
        return {}
    return s


# ── Carga enriquecida ────────────────────────────────────────────────────────
def load_resolved_trades(db_paths: list[str] | None = None) -> list[dict]:
    """Devuelve [{features, stoch, target, direction, ts, source}, ...].

    ``stoch`` = {"m15": {...}, "m5": {...}} con la info del estocastico
    grabada en el momento de la decision. M1 ausente hasta que el scanner
    lo capture.
    """
    if db_paths is None:
        db_paths = discover_db_paths()
    rows: list[dict] = []
    for db in db_paths:
        try:
            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
        except sqlite3.Error:
            continue

        # Fuente 1: trade_journal (candidates)
        try:
            cur.execute(
                """
                SELECT outcome, strategy_origin, strategy_json, spring_margin,
                       direction, payout, scanned_at
                FROM candidates
                WHERE outcome IN ('WIN','LOSS') AND strategy_origin = 'STRAT-F'
                """
            )
            for r in cur.fetchall():
                r = dict(r)
                sj = _json_loads(r.get("strategy_json"))
                if not sj:
                    continue
                if r.get("spring_margin") is not None:
                    sj["spring_margin"] = r["spring_margin"]
                stoch = {
                    "m15": _parse_stoch(sj.get("stoch_m15")),
                    "m5": {},
                }
                rows.append({
                    "features": _features_from(sj),
                    "stoch": stoch,
                    "direction": str(r.get("direction") or "").upper(),
                    "target": 1 if str(r["outcome"]).upper() == "WIN" else 0,
                    "ts": _to_epoch(r.get("scanned_at")),
                    "source": os.path.basename(db),
                })
        except sqlite3.Error:
            pass

        # Fuente 2: black_box (scan_candidates) — lee stoch_m15 y stoch_m5
        try:
            cols = [d[1] for d in cur.execute("PRAGMA table_info(scan_candidates)")]
            has_m5 = "stoch_m5" in cols
            has_m1 = "stoch_m1" in cols
            sel = (
                "order_result, strategy, direction, payout, duration_sec, ts, "
                "stoch_m15" + (", stoch_m5" if has_m5 else "")
                + (", stoch_m1" if has_m1 else "")
            )
            cur.execute(
                f"""
                SELECT {sel}
                FROM scan_candidates
                WHERE order_result IN ('WIN','LOSS') AND strategy = 'STRAT-F'
                """
            )
            for r in cur.fetchall():
                r = dict(r)
                stoch = {
                    "m15": _parse_stoch(r.get("stoch_m15")),
                    "m5": _parse_stoch(r.get("stoch_m5")) if has_m5 else {},
                    "m1": _parse_stoch(r.get("stoch_m1")) if has_m1 else {},
                }
                sj = {
                    "direction": r.get("direction"),
                    "payout": r.get("payout"),
                    "duration_sec": r.get("duration_sec"),
                    "stoch_m15": stoch["m15"],
                }
                rows.append({
                    "features": _features_from(sj),
                    "stoch": stoch,
                    "direction": str(r.get("direction") or "").upper(),
                    "target": 1 if str(r["order_result"]).upper() == "WIN" else 0,
                    "ts": _to_epoch(r.get("ts")),
                    "source": os.path.basename(db),
                })
        except sqlite3.Error:
            pass

        conn.close()

    rows.sort(key=lambda x: (x["ts"] if x["ts"] is not None else float("inf"),))
    return rows


def _features_from(strategy_json: dict) -> dict:
    """Reusa extract_features de ml_features (import local para evitar ciclo)."""
    from ml_features import extract_features
    return extract_features(strategy_json)


# ── Helpers estadisticos ─────────────────────────────────────────────────────
def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def wilson_interval(wins: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Lower/upper bound + center del intervalo de Wilson para un winrate.

    Devuelve (lower, center, upper). Con n=0 devuelve (0,0,0). El lower
    bound es el que usamos para no vender como 'buen patron' uno con n=11.
    """
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5) / denom
    return (max(0.0, center - margin), p, min(1.0, center + margin))


def stoch_trend(stoch: dict) -> str:
    """Direccion del estocastico: 'subiendo' | 'bajando' | 'plano' | 'n/a'.

    Usa k vs k_prev cuando existen; si no, infiere por 'estado'/'cruce'.
    """
    if not stoch:
        return "n/a"
    k = stoch.get("k")
    kp = stoch.get("k_prev")
    if k is not None and kp is not None:
        if k > kp + 0.5:
            return "subiendo"
        if k < kp - 0.5:
            return "bajando"
        return "plano"
    cruce = str(stoch.get("cruce") or "")
    if cruce == "alcista":
        return "subiendo"
    if cruce == "bajista":
        return "bajando"
    return "n/a"


def stoch_zone_label(stoch: dict) -> str:
    """Etiqueta de zona del estocastico: 'sobreventa'|'sobrecompra'|'neutro'|'n/a'."""
    if not stoch:
        return "n/a"
    estado = str(stoch.get("estado") or "").upper()
    if estado == "SOBREVENTA":
        return "sobreventa"
    if estado == "SOBRECOMPRA":
        return "sobrecompra"
    k = stoch.get("k")
    if k is None:
        return "n/a"
    if k <= 20:
        return "sobreventa"
    if k >= 80:
        return "sobrecompra"
    return "neutro"
