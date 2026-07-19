"""In-memory watchlist for STRAT-F zones rejected only as too young (R3)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any


VALID_MODES = frozenset({"off", "shadow", "live"})
_BAND_DECIMALS = 5


def normalize_mode(raw: str | None) -> str:
    """Return off|shadow|live; invalid values fail-safe to off."""
    m = (raw or "").strip().lower()
    if m not in VALID_MODES:
        return "off"
    return m


def is_r3_young_skip(reason: str | None) -> bool:
    """True when skip_reason is the R3 zone-too-young reject."""
    if not reason:
        return False
    r = reason.lower()
    return "zona muy joven" in r or "zone too young" in r


def direction_from_m5_event(m5_event: str | None) -> str | None:
    """Map fractal event to STRAT-F direction (CALL floor / PUT ceiling)."""
    if not m5_event:
        return None
    e = m5_event.lower()
    if e == "fractal_down":
        return "CALL"
    if e == "fractal_up":
        return "PUT"
    return None


def round_band(band: float) -> float:
    return round(float(band), _BAND_DECIMALS)


def parse_bars_age_from_skip(reason: str | None) -> int | None:
    """Best-effort bars_age snapshot from skip text (display only, not a gate)."""
    if not reason:
        return None
    # e.g. "zona muy joven (2 < 3 velas M5)"
    m = re.search(r"\((\d+)\s*<", reason)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def fractal_band_and_age(candles_5m: list[Any], m5_event: str | None = None) -> tuple[float | None, int, str]:
    """Locate latest Bill-Williams fractal band + age on M5 (no I/O).

    Mirrors strat_fractal fractal scan for capture metadata only; does not
    change the evaluator age gate.
    """
    if not candles_5m or len(candles_5m) < 5:
        return None, 0, m5_event or "none"

    last_idx = len(candles_5m) - 3
    want = (m5_event or "").lower()

    def _is_down(i: int) -> bool:
        lo = candles_5m[i].low
        return (
            lo < candles_5m[i - 1].low
            and lo < candles_5m[i - 2].low
            and lo < candles_5m[i + 1].low
            and lo < candles_5m[i + 2].low
        )

    def _is_up(i: int) -> bool:
        hi = candles_5m[i].high
        return (
            hi > candles_5m[i - 1].high
            and hi > candles_5m[i - 2].high
            and hi > candles_5m[i + 1].high
            and hi > candles_5m[i + 2].high
        )

    for i in range(last_idx, 1, -1):
        if want in ("", "none", "fractal_down") and _is_down(i):
            if want == "fractal_up":
                continue
            bars_age = (len(candles_5m) - 1) - i
            return float(candles_5m[i].low), bars_age, "fractal_down"
        if want in ("", "none", "fractal_up") and _is_up(i):
            if want == "fractal_down":
                continue
            bars_age = (len(candles_5m) - 1) - i
            return float(candles_5m[i].high), bars_age, "fractal_up"
    return None, 0, m5_event or "none"


def make_key(asset: str, direction: str, band: float) -> str:
    d = (direction or "").upper()
    return f"{asset}|{d}|{round_band(band):.{_BAND_DECIMALS}f}"


@dataclass
class MaturingEntry:
    asset: str
    direction: str
    band: float
    m15_context: str
    m5_event: str
    bars_age: int
    payout: int
    first_seen_ts: float
    last_seen_ts: float
    status: str = "maturing"  # maturing | promoted | dropped
    drop_reason: str = ""

    @property
    def key(self) -> str:
        return make_key(self.asset, self.direction, self.band)


@dataclass
class MaturingWatchlist:
    """Pure in-memory store: no broker I/O."""

    max_entries: int = 40
    max_age_bars: int = 12
    ttl_sec: float = 3600.0
    _entries: dict[str, MaturingEntry] = field(default_factory=dict)
    counters: dict[str, int] = field(
        default_factory=lambda: {
            "captured": 0,
            "promoted_live": 0,
            "promoted_shadow": 0,
            "dropped_expired": 0,
            "dropped_invalid": 0,
        }
    )

    def get(self, key: str) -> MaturingEntry | None:
        return self._entries.get(key)

    def find_active(self, asset: str, direction: str | None = None) -> list[MaturingEntry]:
        out: list[MaturingEntry] = []
        d = (direction or "").upper() if direction else None
        for e in self._entries.values():
            if e.status != "maturing":
                continue
            if e.asset != asset:
                continue
            if d and e.direction.upper() != d:
                continue
            out.append(e)
        return out

    def active(self) -> list[MaturingEntry]:
        return [e for e in self._entries.values() if e.status == "maturing"]

    def upsert_young(
        self,
        *,
        asset: str,
        direction: str,
        band: float,
        m15_context: str = "",
        m5_event: str = "",
        bars_age: int = 0,
        payout: int = 0,
        now: float | None = None,
    ) -> MaturingEntry:
        """Insert or refresh a maturing entry (idempotent by key)."""
        ts = float(now if now is not None else time.time())
        key = make_key(asset, direction, band)
        existing = self._entries.get(key)
        if existing is not None and existing.status == "maturing":
            existing.last_seen_ts = ts
            existing.bars_age = int(bars_age)
            existing.payout = int(payout)
            existing.m15_context = m15_context or existing.m15_context
            existing.m5_event = m5_event or existing.m5_event
            return existing

        entry = MaturingEntry(
            asset=asset,
            direction=(direction or "").upper(),
            band=round_band(band),
            m15_context=m15_context or "",
            m5_event=m5_event or "",
            bars_age=int(bars_age),
            payout=int(payout),
            first_seen_ts=ts,
            last_seen_ts=ts,
            status="maturing",
        )
        self._entries[key] = entry
        self.counters["captured"] = self.counters.get("captured", 0) + 1
        self._enforce_cap()
        return entry

    def mark_promoted(self, key: str, *, mode: str = "live") -> None:
        entry = self._entries.get(key)
        if entry is None:
            return
        entry.status = "promoted"
        entry.drop_reason = ""
        if normalize_mode(mode) == "shadow":
            self.counters["promoted_shadow"] = self.counters.get("promoted_shadow", 0) + 1
        else:
            self.counters["promoted_live"] = self.counters.get("promoted_live", 0) + 1
        del self._entries[key]

    def drop(self, key: str, reason: str) -> None:
        entry = self._entries.get(key)
        if entry is None:
            return
        entry.status = "dropped"
        entry.drop_reason = reason or "invalidated"
        if reason in ("expired", "ttl"):
            self.counters["dropped_expired"] = self.counters.get("dropped_expired", 0) + 1
        else:
            self.counters["dropped_invalid"] = self.counters.get("dropped_invalid", 0) + 1
        del self._entries[key]

    def expire_stale(
        self,
        now: float | None = None,
        *,
        bars_by_key: dict[str, int] | None = None,
    ) -> list[MaturingEntry]:
        """Drop entries past TTL or max age bars. Returns dropped copies."""
        ts = float(now if now is not None else time.time())
        bars_by_key = bars_by_key or {}
        dropped: list[MaturingEntry] = []
        for key, entry in list(self._entries.items()):
            if entry.status != "maturing":
                continue
            age_bars = bars_by_key.get(key, entry.bars_age)
            if age_bars > self.max_age_bars:
                entry.bars_age = int(age_bars)
                self.drop(key, "expired")
                dropped.append(entry)
                continue
            if (ts - entry.first_seen_ts) > float(self.ttl_sec):
                self.drop(key, "ttl")
                dropped.append(entry)
        return dropped

    def snapshot(self) -> dict[str, Any]:
        return {
            "entries": [
                {
                    "asset": e.asset,
                    "direction": e.direction,
                    "band": e.band,
                    "m15_context": e.m15_context,
                    "m5_event": e.m5_event,
                    "bars_age": e.bars_age,
                    "payout": e.payout,
                    "first_seen_ts": e.first_seen_ts,
                    "last_seen_ts": e.last_seen_ts,
                    "status": e.status,
                    "drop_reason": e.drop_reason,
                    "key": e.key,
                }
                for e in self.active()
            ],
            "counters": dict(self.counters),
            "count": len(self.active()),
        }

    def panel_rows(self) -> list[dict[str, Any]]:
        """Compact rows for hub STRAT-F panel."""
        return [
            {
                "asset": e.asset,
                "direction": e.direction,
                "bars_age": e.bars_age,
                "band": e.band,
                "status": e.status,
            }
            for e in self.active()
        ]

    def _enforce_cap(self) -> None:
        while len(self._entries) > int(self.max_entries):
            oldest_key = min(
                self._entries.keys(),
                key=lambda k: self._entries[k].last_seen_ts,
            )
            self.drop(oldest_key, "expired")
