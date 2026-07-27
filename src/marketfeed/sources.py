"""Fuentes de historia para el Market Replay Engine (T2/T3).

CsvSource      — CSV asset,timeframe,ts,open,high,low,close[,volume] (R2.3, R2.4, R6.3, R7.2)
BlackBoxSource — black_box_strat_*.db solo lectura, candles_1m/5m/15m (R6.1, R6.2, R7.1)

Ambas implementan el protocolo Source de base.py:
  iter_events() -> Iterator[Event] ordenado por ts
  quality_report() -> {'served','discarded_dup','discarded_contaminated','gaps'}
"""
from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import statistics
from typing import Dict, Iterator, List, Tuple

from marketfeed.base import Event, KIND_CANDLE_CLOSED, KIND_FEED_GAP

# ---------------------------------------------------------------------------

_CSV_REQUIRED = ("asset", "timeframe", "ts", "open", "high", "low", "close")
_TF_MAP = {"candles_1m": 60, "candles_5m": 300, "candles_15m": 900}
_CONTAMINATION_PCT = 0.30  # R6.2: cierre a >30% de la mediana del asset


def _empty_report() -> dict:
    return {"served": 0, "discarded_dup": 0, "discarded_contaminated": 0, "gaps": 0}


class _BaseSource:
    """Lógica común: dedup, orden, gaps, contadores."""

    def __init__(self) -> None:
        self._report = _empty_report()

    # candles: dict {(asset, tf, ts): (o, h, l, c, volume|None)}
    def _emit(self, candles: Dict[Tuple[str, int, float], tuple], source: str) -> Iterator[Event]:
        # orden total determinista por (ts, asset, timeframe)
        keys = sorted(candles.keys(), key=lambda k: (k[2], k[0], k[1]))
        last_ts: Dict[Tuple[str, int], float] = {}
        for asset, tf, ts in keys:
            prev = last_ts.get((asset, tf))
            if prev is not None and (ts - prev) > tf:
                self._report["gaps"] += 1
                yield Event(
                    kind=KIND_FEED_GAP,
                    asset=asset,
                    ts=ts,
                    payload={"ts_desde": prev, "ts_hasta": ts},
                    source=source,
                )
            last_ts[(asset, tf)] = ts
            o, h, l, c, vol = candles[(asset, tf, ts)]
            payload = {"timeframe": tf, "open": o, "high": h, "low": l, "close": c}
            if vol is not None:
                payload["volume"] = vol
            self._report["served"] += 1
            yield Event(kind=KIND_CANDLE_CLOSED, asset=asset, ts=ts, payload=payload, source=source)

    def quality_report(self) -> dict:
        return dict(self._report)


# ---------------------------------------------------------------------------


class CsvSource(_BaseSource):
    """T2 — CSV con columnas asset,timeframe,ts,open,high,low,close[,volume]."""

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path
        self.source = f"REPLAY:csv:{os.path.basename(path)}"

    def iter_events(self) -> Iterator[Event]:
        self._report = _empty_report()
        candles: Dict[Tuple[str, int, float], tuple] = {}
        with open(self._path, "r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            missing = [c for c in _CSV_REQUIRED if c not in fields]
            if missing:
                raise ValueError(
                    f"CSV {self._path!r} con esquema inválido: faltan columnas {missing}; "
                    f"requeridas: {list(_CSV_REQUIRED)} (R7.2)"
                )
            has_vol = "volume" in fields
            for row in reader:
                try:
                    key = (row["asset"], int(row["timeframe"]), float(row["ts"]))
                    vol = float(row["volume"]) if has_vol and row.get("volume") else None
                    val = (
                        float(row["open"]), float(row["high"]),
                        float(row["low"]), float(row["close"]), vol,
                    )
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"CSV {self._path!r}: fila inválida {row!r}: {exc}") from exc
                if key in candles:
                    self._report["discarded_dup"] += 1
                else:
                    candles[key] = val
        yield from self._emit(candles, self.source)


# ---------------------------------------------------------------------------


class BlackBoxSource(_BaseSource):
    """T3 — velas de scan_candidates en black_box_strat_YYYY-MM-DD.db (solo lectura)."""

    def __init__(self, db_path: str) -> None:
        super().__init__()
        self._db_path = db_path
        m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(db_path))
        fecha = m.group(1) if m else os.path.basename(db_path)
        self.source = f"REPLAY:blackbox:{fecha}"

    @staticmethod
    def _norm(candle: dict) -> tuple:
        """Acepta variantes de claves {ts,o,h,l,c} u {open,high,low,close}."""
        o = candle.get("o", candle.get("open"))
        h = candle.get("h", candle.get("high"))
        l = candle.get("l", candle.get("low"))
        c = candle.get("c", candle.get("close"))
        return float(candle["ts"]), float(o), float(h), float(l), float(c)

    def iter_events(self) -> Iterator[Event]:
        self._report = _empty_report()
        candles: Dict[Tuple[str, int, float], tuple] = {}
        uri = f"file:{self._db_path}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            rows = con.execute(
                "SELECT asset, candles_1m, candles_5m, candles_15m FROM scan_candidates"
            ).fetchall()
        finally:
            con.close()

        for asset, c1, c5, c15 in rows:
            for col, raw in (("candles_1m", c1), ("candles_5m", c5), ("candles_15m", c15)):
                if not raw:
                    continue
                try:
                    parsed = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                tf = _TF_MAP[col]
                for candle in parsed or []:
                    try:
                        ts, o, h, l, c = self._norm(candle)
                    except (KeyError, TypeError, ValueError):
                        continue
                    key = (asset, tf, ts)
                    if key in candles:
                        self._report["discarded_dup"] += 1
                    else:
                        candles[key] = (o, h, l, c, None)

        # Anticontaminación R6.2: mediana de cierres por asset
        closes_by_asset: Dict[str, List[float]] = {}
        for (asset, _tf, _ts), (_o, _h, _l, c, _v) in candles.items():
            closes_by_asset.setdefault(asset, []).append(c)
        medians = {a: statistics.median(v) for a, v in closes_by_asset.items()}
        clean: Dict[Tuple[str, int, float], tuple] = {}
        for key, val in candles.items():
            med = medians[key[0]]
            if med and abs(val[3] - med) > _CONTAMINATION_PCT * abs(med):
                self._report["discarded_contaminated"] += 1
            else:
                clean[key] = val

        yield from self._emit(clean, self.source)
