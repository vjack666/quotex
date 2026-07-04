"""Descarga de velas y recolección de candidatos por activo."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

from candle_patterns import detect_reversal_pattern, explain_no_pattern_reason
import config as _runtime_config
from config import (
    ADAPTIVE_THRESHOLD_HIGH,
    ADAPTIVE_THRESHOLD_LOW,
    ADAPTIVE_THRESHOLD_WINDOW_SCANS,
    BROKEN_FOLLOWUP_1M_COUNT,
    BROKEN_FOLLOWUP_DELAY_SEC,
    BROKER_TZ,
    CANDLE_FETCH_1M_TIMEOUT_SEC,
    CANDLE_FETCH_TIMEOUT_SEC,
    CANDLES_LOOKBACK,
    CANDLE_FETCH_CONCURRENCY,
    COOLDOWN_BETWEEN_ENTRIES,
    DRY_RUN_VERBOSE,
    DURATION_SEC,
    H1_CANDLES_LOOKBACK,
    H1_FETCH_TIMEOUT_SEC,
    H1_TF_SEC,
    MAX_CONCURRENT_TRADES,
    MAX_CONSOLIDATION_MIN,
    MIN_CONSOLIDATION_BARS,
    MIN_PAYOUT,

    REBOUND_MIN_STRENGTH_CALL,
    REBOUND_MIN_STRENGTH_PUT,
    REJECTION_CANDLE_MIN_BODY,
    SCAN_MAX_ASSETS_PER_CYCLE,
    SCAN_PHASE_LOG,
    SCAN_PROGRESS_EVERY,

    STRAT_A_MIN_PAYOUT,
    STRAT_A_MIN_SCORE,
    STRAT_A_RADAR_ENABLED,
    STRAT_A_RADAR_MIN_READINESS,
    STRAT_A_ZONE_MIN_AGE_REBOUND,
    STRAT_B_CAN_TRADE,
    STRAT_B_DURATION_SEC,
    STRAT_MOMENTUM_ENABLED,
    STRAT_ORDER_BLOCK_ENABLED,
    STRAT_ORDER_BLOCK_MIN_STRENGTH,
    STRAT_B_LOG_TOP_N,
    STRAT_B_MIN_CONFIDENCE,
    STRAT_B_MIN_CONFIDENCE_EARLY,
    STRAT_B_PREVIEW_MIN_CONF,
    TF_1M,
    TF_5M,
    ZONE_AGE_BREAKOUT_MIN,
    ZONE_AGE_REBOUND_MIN,
    ZONE_MIN_AGE_MIN,
)
from connection import fetch_candles_with_retry, get_open_assets
from entry_decision_engine import (
    _check_htf_available_and_aligned,
    _check_zone_memory_no_wall,
)
from scan_prefetch import (
    ScanCycleData,
    decrement_failed_assets,
    prefetch_primary_candles,
    prefetch_strat_a_secondary,
    symbols_needing_strat_a_prefetch,
)
from loop_utils import sleep_with_inline_countdown
from diversification_enforcer import DiversificationEnforcer
from entry_scorer import CandidateEntry, explain_score, score_candidate, select_best
from models import Candle, ConsolidationZone, PendingReversal
from strat_a import (
    compute_dynamic_range,
    compute_ma_state,
    detect_consolidation,
    evaluate_strat_a,
    infer_h1_trend,
    is_put_pattern_blacklisted,
    PendingReversalHint,
    price_at_ceiling,
    price_at_floor,
    required_rebound_strength,
    StratAEvaluation,
    validate_rejection_candle,
)
from strat_a_radar import (
    RadarWatchEntry,
    compute_readiness,
    rank_and_trim,
    should_watch,
)
from strat_b import evaluate_strat_b, find_strong_support_2m
from strat_momentum import detect_momentum_1m
from strat_order_block import detect_order_block_entry
from strat_reversal_swing import detect_reversal_swing
from trade_journal import get_journal
from zone_memory import query_nearby_zones, score_zone_memory

if TYPE_CHECKING:
    from executor import TradeExecutor

log = logging.getLogger("scanner")


@dataclass
class ScanResult:
    candidates: list[CandidateEntry] = field(default_factory=list)
    stats_delta: dict[str, int] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)


class AssetScanner:
    def __init__(self, bot: Any, executor: "TradeExecutor"):
        self.bot = bot
        self.executor = executor

    @staticmethod
    def _phase_log(phase: str, detail: str) -> None:
        if SCAN_PHASE_LOG:
            log.info("[FASE %s] %s", phase, detail)

    @staticmethod
    def _radar_enabled() -> bool:
        return bool(_runtime_config.STRAT_A_ONLY or STRAT_A_RADAR_ENABLED)

    @staticmethod
    def _is_strat_a_candidate(candidate: CandidateEntry) -> bool:
        return getattr(candidate, "_strategy_origin", "STRAT-A") == "STRAT-A"

    @staticmethod
    def _score_threshold_for_candidate(
        candidate: CandidateEntry,
        session_threshold: int,
    ) -> int:
        if getattr(candidate, "_strategy_origin", "STRAT-A") == "STRAT-A":
            return STRAT_A_MIN_SCORE
        return session_threshold

    @staticmethod
    def _log_strat_a_pattern_veto(sym: str, ev: StratAEvaluation) -> None:
        side = "techo" if ev.entry_mode == "rebound_ceiling" else "piso"
        if ev.skip_reason == "pattern_missing":
            log.info(
                "⛔ [STRAT-A] %s: rebote %s — sin patrón 1m confirmado",
                sym,
                side,
            )
        elif ev.skip_reason == "pattern_insufficient":
            log.info(
                "⛔ [STRAT-A] %s: rebote %s — patrón 1m insuficiente (%s %.2f)",
                sym,
                side,
                ev.pattern_name,
                ev.strength,
            )
        elif ev.skip_reason == "strict_pattern_veto":
            log.info(
                "⛔ [STRAT-A] %s: rebote %s — patrón contradictorio confirmado %s %.2f",
                sym,
                side,
                ev.pattern_name,
                ev.strength,
            )

    def _radar_entry_from_evaluation(
        self,
        sym: str,
        payout: int,
        zone: ConsolidationZone,
        price: float,
        ev: StratAEvaluation,
        dynamic_touch_tolerance: float,
    ) -> RadarWatchEntry | None:
        if not self._radar_enabled():
            return None
        if ev.direction is None or ev.has_signal:
            return None
        if payout < STRAT_A_MIN_PAYOUT:
            return None
        if not should_watch(zone, price, ev.entry_mode, ev.stage, dynamic_touch_tolerance):
            return None
        in_pending = sym in self.bot.pending_reversals
        readiness = compute_readiness(
            zone,
            price,
            payout,
            ev.entry_mode,
            ev.stage,
            in_pending=in_pending,
            dynamic_touch_tolerance=dynamic_touch_tolerance,
        )
        return RadarWatchEntry(
            asset=sym,
            payout=payout,
            zone=zone,
            direction=ev.direction,
            entry_mode=ev.entry_mode,
            stage=ev.stage,
            readiness_score=readiness,
            side_label="techo" if ev.entry_mode == "rebound_ceiling" else (
                "piso" if ev.entry_mode == "rebound_floor" else "ruptura"
            ),
        )

    def _update_radar_watchlist(self, entries_from_cycle: list[RadarWatchEntry]) -> None:
        if not self._radar_enabled():
            return
        merged: dict[str, RadarWatchEntry] = dict(self.bot.radar_watchlist)
        for entry in entries_from_cycle:
            merged[entry.asset] = entry
        trimmed = rank_and_trim(list(merged.values()))
        self.bot.radar_watchlist = {e.asset: e for e in trimmed}
        if trimmed:
            parts = [
                f"{e.asset} {e.direction.upper()} {e.side_label} readiness={e.readiness_score:.0f}"
                for e in trimmed
            ]
            log.info("[RADAR] Watchlist (%d): %s", len(trimmed), " | ".join(parts))
        elif merged:
            log.info("[RADAR] Watchlist vacía tras filtro readiness (min=%.0f)", STRAT_A_RADAR_MIN_READINESS)

    def _compute_ma_state(self, asset: str, candles_5m: List[Candle]):
        prev = self.bot.ma_state_by_asset.get(asset)
        state = compute_ma_state(candles_5m, prev)
        if state is not None:
            self.bot.ma_state_by_asset[asset] = state
        return state

    def _merge_zone_state(
        self,
        sym: str,
        zone: ConsolidationZone,
        candles: List[Candle],
        payout: int,
    ) -> ConsolidationZone | None:
        if sym in self.bot.zones:
            existing = self.bot.zones[sym]
            if MAX_CONSOLIDATION_MIN > 0 and existing.age_minutes > MAX_CONSOLIDATION_MIN:
                log.info(
                    "⏱  %s: zona expirada por TIME_LIMIT (%.0fmin) | "
                    "techo=%.5f piso=%.5f rango=%.3f%% barras=%d | precio_actual=%.5f",
                    sym,
                    existing.age_minutes,
                    existing.ceiling,
                    existing.floor,
                    existing.range_pct * 100,
                    existing.bars_inside,
                    candles[-1].close if candles else 0.0,
                )
                get_journal().log_expired_zone(
                    asset=sym,
                    expiry_reason="TIME_LIMIT",
                    ceiling=existing.ceiling,
                    floor=existing.floor,
                    range_pct=existing.range_pct,
                    bars_inside=existing.bars_inside,
                    age_min=existing.age_minutes,
                    last_close=candles[-1].close if candles else 0.0,
                    payout=payout,
                )
                del self.bot.zones[sym]
                self.bot.stats["expired_zones"] += 1
                return None
            zone.detected_at = existing.detected_at
        self.bot.zones[sym] = zone
        return zone

    def _price_sanity_ok(self, sym: str, zone: ConsolidationZone, price: float) -> bool:
        _zone_mid = (zone.ceiling + zone.floor) / 2.0
        if _zone_mid > 0 and not (zone.floor * 0.85 <= price <= zone.ceiling * 1.15):
            _last_valid = self.bot.last_known_price.get(sym)
            _last_txt = f" (último válido: {_last_valid:.5f})" if _last_valid else ""
            log.warning(
                "⚠ %s: precio %.5f contaminado — fuera de zona [%.5f, %.5f]%s",
                sym, price, zone.floor * 0.85, zone.ceiling * 1.15, _last_txt,
            )
            self.bot.stats["skipped"] += 1
            return False

        _last_valid = self.bot.last_known_price.get(sym)
        if _last_valid and _last_valid > 0:
            _delta_pct = abs(price - _last_valid) / _last_valid
            if _delta_pct > 0.05:
                log.warning(
                    "⚠ %s: precio %.5f contaminado — cambio de %.1f%% vs último válido %.5f",
                    sym, price, _delta_pct * 100, _last_valid,
                )
                self.bot.stats["skipped"] += 1
                return False
        return True

    def _apply_pending_reversal_hint(
        self,
        sym: str,
        zone: ConsolidationZone,
        payout: int,
        hint: PendingReversalHint,
        skip_reason: str,
        candles_1m: List[Candle],
    ) -> None:
        side = "techo" if hint.entry_mode == "rebound_ceiling" else "piso"
        if sym not in self.bot.pending_reversals:
            self.bot.pending_reversals[sym] = PendingReversal(
                asset=sym,
                zone=zone,
                proposed_direction=hint.proposed_direction,
                conflicting_pattern=hint.conflicting_pattern,
                detected_at=datetime.now(tz=BROKER_TZ),
                entry_mode=hint.entry_mode,
                payout=payout,
            )
            if skip_reason == "rejection_candle_fail":
                log.info(
                    "⏳ %s: vela 1m no confirma rebote en %s (%s) — esperando confirmación (1/%d)",
                    sym, side, hint.conflicting_pattern,
                    self.bot.pending_reversals[sym].max_wait_scans,
                )
            elif skip_reason in ("pattern_missing", "pattern_insufficient") and hint.proposed_direction == "put":
                if hint.conflicting_pattern == "none":
                    log.info(
                        "↪ %s: PUT requiere patrón ≥%.2f, detectado %s (%s)",
                        sym,
                        REBOUND_MIN_STRENGTH_PUT,
                        hint.conflicting_pattern,
                        explain_no_pattern_reason(candles_1m, hint.proposed_direction),
                    )
                else:
                    parts = hint.conflicting_pattern.split(":")
                    pat = parts[0]
                    stren = parts[1] if len(parts) > 1 else "0.00"
                    log.info(
                        "↪ %s: PUT requiere patrón ≥%.2f, detectado %s %s",
                        sym,
                        REBOUND_MIN_STRENGTH_PUT,
                        pat,
                        stren,
                    )
            elif skip_reason in ("pattern_missing", "pattern_insufficient"):
                log.info(
                    "⏳ %s: patrón conflictivo (%s) en %s — esperando reversión (intento 1/%d)",
                    sym, hint.conflicting_pattern, side,
                    self.bot.pending_reversals[sym].max_wait_scans,
                )
        elif hint.update_existing:
            self.bot.pending_reversals[sym].conflicting_pattern = hint.conflicting_pattern
            self.bot.pending_reversals[sym].zone = zone

        if skip_reason == "put_pattern_blacklisted":
            log.info(
                "↪ %s: patrón %s en lista negra para PUT — skip",
                sym,
                hint.conflicting_pattern,
            )

    def _bump_strat_a_skip_stats(self, skip_reason: str | None) -> None:
        if skip_reason == "zone_too_young":
            self.bot.stats["rejected_young_zone"] += 1
        if skip_reason == "h1_conflict":
            self.bot.stats["filtered_sensor"] += 1
        elif skip_reason in ("htf_reject", "zone_memory_wall"):
            self.bot.stats["skipped"] += 1
        elif skip_reason is not None:
            self.bot.stats["skipped"] += 1

    def _apply_strat_a_htf_zone_gates(
        self,
        sym: str,
        direction: str,
        price: float,
    ) -> tuple[bool, list, list, str | None]:
        """
        Veto HTF 15m y muro zone_memory antes de crear candidato STRAT-A.

        Retorna (passed, candles_15m, zones, skip_reason).
        """
        candles_15m = self.bot.htf_scanner.get_candles_15m(sym)
        veto, _htf_trend = _check_htf_available_and_aligned(
            candles_15m, direction, infer_h1_trend,
        )
        if not veto.passed:
            log.info("⛔ [STRAT-A] %s: %s", sym, veto.reason)
            self._bump_strat_a_skip_stats("htf_reject")
            try:
                from instrumentation_layer import metrics
                metrics.gate_htf_reject += 1
            except Exception:
                pass
            return False, candles_15m, [], "htf_reject"

        journal = get_journal()
        zones = query_nearby_zones(journal.db_path, sym, price)
        zone_adj = score_zone_memory(zones, direction, price) if zones else 0.0
        wall = _check_zone_memory_no_wall(zone_adj, -10.0)
        if not wall.passed:
            log.info("⛔ [STRAT-A] %s: zone_memory wall (adj=%.1f)", sym, zone_adj)
            self._bump_strat_a_skip_stats("zone_memory_wall")
            return False, candles_15m, zones, "zone_memory_wall"

        return True, candles_15m, zones, None

    async def _handle_breakout_side_effects(
        self,
        sym: str,
        zone: ConsolidationZone,
        candles: List[Candle],
        candles_1m: List[Candle],
        payout: int,
        ev: StratAEvaluation,
    ) -> None:
        last = candles[-1]
        if ev.entry_mode == "breakout_above":
            log.info(
                "🟢 %s: BROKEN_ABOVE techo=%.5f | cierre=%.5f cuerpo=%.5f → CALL inmediato",
                sym, zone.ceiling, last.close, last.body,
            )
            reason = "BROKEN_ABOVE"
        else:
            log.info(
                "🔴 %s: BROKEN_BELOW piso=%.5f | cierre=%.5f cuerpo=%.5f → PUT inmediato",
                sym, zone.floor, last.close, last.body,
            )
            reason = "BROKEN_BELOW"

        expired_zone_id = get_journal().log_expired_zone(
            asset=sym,
            expiry_reason=reason,
            ceiling=zone.ceiling,
            floor=zone.floor,
            range_pct=zone.range_pct,
            bars_inside=zone.bars_inside,
            age_min=zone.age_minutes,
            last_close=last.close,
            break_body=last.body,
            payout=payout,
        )
        capture_file = self._record_broken_zone_snapshot(
            asset=sym,
            payout=payout,
            reason=reason,
            expired_zone_id=expired_zone_id,
            zone=zone,
            last=last,
            candles_1m_used=candles_1m,
            candles_5m_used=candles,
        )
        self._schedule_followup_capture(sym, capture_file)
        log.info("🧾 %s: snapshot %s guardado -> %s", sym, reason, capture_file.name)
        self.bot.broken_zones[sym] = time.time()

    def _candidate_from_strat_a_evaluation(
        self,
        sym: str,
        payout: int,
        candles: List[Candle],
        h1_candles: List[Candle],
        ev: StratAEvaluation,
        amount: float,
        ma_state: Any,
        blocks: dict[str, list],
        ob_tf_label: str,
        candles_1m: List[Candle],
    ) -> CandidateEntry:
        candidate = CandidateEntry(
            asset=sym,
            payout=payout,
            zone=ev.zone,
            direction=ev.direction,
            candles=candles,
        )
        candidate.candles_h1 = h1_candles
        candidate._reversal_pattern = ev.pattern_name  # type: ignore[attr-defined]
        candidate._reversal_strength = ev.strength  # type: ignore[attr-defined]
        candidate._reversal_confirms = ev.confirms  # type: ignore[attr-defined]
        candidate._entry_mode = ev.entry_mode  # type: ignore[attr-defined]
        candidate._signal_ts_1m = candles_1m[-1].ts if candles_1m else None  # type: ignore[attr-defined]
        candidate._amount = amount  # type: ignore[attr-defined]
        candidate._stage = ev.stage  # type: ignore[attr-defined]
        candidate._ma_state = ma_state  # type: ignore[attr-defined]
        candidate._order_blocks = blocks  # type: ignore[attr-defined]
        candidate._ob_tf = ob_tf_label  # type: ignore[attr-defined]
        candidate._force_execute = ev.force_execute  # type: ignore[attr-defined]
        candidate._strategy_origin = "STRAT-A"  # type: ignore[attr-defined]
        return candidate

    def _apply_score_adjustments(
        self,
        candidate: CandidateEntry,
        ev: StratAEvaluation,
        ob_tf_label: str,
        sym: str,
    ) -> None:
        adj = ev.score_adjustments
        if adj.reversal_bonus:
            candidate.score = round(candidate.score + adj.reversal_bonus, 1)
            candidate.score_breakdown["reversal_bonus"] = adj.reversal_bonus
        elif adj.reversal_penalty:
            candidate.score = round(candidate.score + adj.reversal_penalty, 1)
            candidate.score_breakdown["reversal_penalty"] = adj.reversal_penalty
        elif adj.weak_confirmation:
            candidate.score = round(candidate.score + adj.weak_confirmation, 1)
            candidate.score_breakdown["weak_confirmation"] = adj.weak_confirmation

        if adj.breakout_bonus:
            candidate.score = round(candidate.score + adj.breakout_bonus, 1)
            candidate.score_breakdown["breakout_bonus"] = adj.breakout_bonus

        if adj.order_block:
            candidate.score = round(candidate.score + adj.order_block, 1)
            candidate.score_breakdown["order_block"] = adj.order_block
        candidate._ob_info = f"tf={ob_tf_label} | {ev.ob_info}"  # type: ignore[attr-defined]

        if adj.ma_filter:
            candidate.score = round(candidate.score + adj.ma_filter, 1)
            candidate.score_breakdown["ma_filter"] = adj.ma_filter
        candidate._ma_info = ev.ma_info  # type: ignore[attr-defined]

        log.info(
            "[OB] %s tf=%s dir=%s ajuste=%+.1f | %s",
            sym,
            ob_tf_label,
            ev.direction.upper() if ev.direction else "",
            adj.order_block,
            ev.ob_info,
        )
        log.info(
            "[MA] %s dir=%s ajuste=%+.1f | %s",
            sym,
            ev.direction.upper() if ev.direction else "",
            adj.ma_filter,
            ev.ma_info,
        )

    def _serialize_candles(candles: List[Candle]) -> list[dict[str, float | int]]:
        return [
            {
                "ts": int(c.ts),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "body": float(c.body),
                "range": float(c.range),
            }
            for c in candles
        ]
    def _broken_capture_file(self, asset: str, reason: str, expired_zone_id: int) -> Path:
        ts = datetime.now(tz=BROKER_TZ).strftime("%Y%m%d_%H%M%S")
        safe_asset = "".join(ch if (ch.isalnum() or ch in ("_", "-")) else "_" for ch in asset)
        return self.bot.capture_dir / f"{ts}_{safe_asset}_{reason}_{expired_zone_id}.json"
    def _write_capture_payload(self, file_path: Path, payload: dict[str, Any]) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    def _record_broken_zone_snapshot(
        self,
        *,
        asset: str,
        payout: int,
        reason: str,
        expired_zone_id: int,
        zone: ConsolidationZone,
        last: Candle,
        candles_1m_used: List[Candle],
        candles_5m_used: List[Candle],
    ) -> Path:
        capture_file = self._broken_capture_file(asset, reason, expired_zone_id)
        trigger_ts = int(last.ts)
        pre_40_1m = [c for c in candles_1m_used if int(c.ts) < trigger_ts][-40:]
        post_40_1m_initial = [c for c in candles_1m_used if int(c.ts) > trigger_ts][:40]
        payload = {
            "event_type": "BROKEN_ZONE",
            "saved_at": datetime.now(tz=BROKER_TZ).isoformat(),
            "asset": asset,
            "reason": reason,
            "expired_zone_id": int(expired_zone_id),
            "payout": int(payout),
            "zone": {
                "ceiling": float(zone.ceiling),
                "floor": float(zone.floor),
                "range_pct": float(zone.range_pct),
                "bars_inside": int(zone.bars_inside),
                "age_min": float(zone.age_minutes),
            },
            "trigger_candle_5m": {
                "ts": int(last.ts),
                "open": float(last.open),
                "high": float(last.high),
                "low": float(last.low),
                "close": float(last.close),
                "body": float(last.body),
            },
            "analysis_1m": {
                "target_window": {
                    "pre": 40,
                    "post": 40,
                },
                "pre_40": self._serialize_candles(pre_40_1m),
                "post_40_initial": self._serialize_candles(post_40_1m_initial),
            },
            "candles_1m_used": self._serialize_candles(candles_1m_used[-60:]),
            "candles_5m_zone_context": self._serialize_candles(candles_5m_used[-24:]),
            "followup": {
                "delay_sec": BROKEN_FOLLOWUP_DELAY_SEC,
                "requested_candles_1m": BROKEN_FOLLOWUP_1M_COUNT,
                "status": "pending",
                "saved_at": None,
                "candles_1m": [],
                "error": None,
            },
        }
        self._write_capture_payload(capture_file, payload)
        return capture_file
    async def _capture_followup_after_delay(self, asset: str, capture_file: Path) -> None:
        try:
            await asyncio.sleep(BROKEN_FOLLOWUP_DELAY_SEC)
            followup_1m = await fetch_candles_with_retry(
                self.bot.client,
                asset,
                60,
                BROKEN_FOLLOWUP_1M_COUNT,
                timeout_sec=CANDLE_FETCH_1M_TIMEOUT_SEC,
            )
            payload = json.loads(capture_file.read_text(encoding="utf-8"))
            payload.setdefault("followup", {})
            payload["followup"]["status"] = "saved"
            payload["followup"]["saved_at"] = datetime.now(tz=BROKER_TZ).isoformat()
            payload["followup"]["candles_1m"] = self._serialize_candles(followup_1m)
            payload["followup"]["error"] = None
            self._write_capture_payload(capture_file, payload)
            log.info("🧾 %s: follow-up 1m guardado (%d velas) -> %s", asset, len(followup_1m), capture_file.name)
        except Exception as exc:
            try:
                payload = json.loads(capture_file.read_text(encoding="utf-8"))
                payload.setdefault("followup", {})
                payload["followup"]["status"] = "error"
                payload["followup"]["saved_at"] = datetime.now(tz=BROKER_TZ).isoformat()
                payload["followup"]["error"] = str(exc)
                self._write_capture_payload(capture_file, payload)
            except Exception:
                pass
            log.warning("⚠ %s: no se pudo guardar follow-up 1m (%s)", asset, exc)
    def _schedule_followup_capture(self, asset: str, capture_file: Path) -> None:
        task = asyncio.create_task(
            self._capture_followup_after_delay(asset, capture_file),
            name=f"followup_1m:{asset}",
        )
        self.bot._followup_capture_tasks.add(task)
        task.add_done_callback(self._on_background_task_done)
    @staticmethod
    def _threshold_label(threshold: int) -> str:
        if threshold == ADAPTIVE_THRESHOLD_LOW:
            return "bajo"
        if threshold == ADAPTIVE_THRESHOLD_HIGH:
            return "alto"
        return "base"

    @staticmethod
    def _threshold_change_reason(accepted_last_window: int) -> str:
        if accepted_last_window == 0:
            return "sin señales en últimos 10 scans"
        if accepted_last_window > 2:
            return "2+ señales en últimos 10 scans"
        return "señales mixtas en últimos 10 scans"
    def _build_blacklist_summary_line(self) -> str:
        if not self.bot.asset_blacklist_until:
            return "ninguna"
        now_ts = time.time()
        chunks: list[str] = []
        for asset, until_ts in sorted(self.bot.asset_blacklist_until.items()):
            if until_ts <= now_ts:
                continue
            until_txt = datetime.fromtimestamp(until_ts, tz=BROKER_TZ).strftime("%H:%M")
            chunks.append(f"{asset} (hasta {until_txt})")
        return ", ".join(chunks) if chunks else "ninguna"

    @staticmethod
    def _build_ob_summary_line(cycle_ob_summary: dict[str, str]) -> str:
        if not cycle_ob_summary:
            return "ninguno"
        return " | ".join(f"{asset} → {desc}" for asset, desc in sorted(cycle_ob_summary.items()))

    @staticmethod
    def _build_ma_summary_line(cycle_ma_summary: dict[str, str]) -> str:
        if not cycle_ma_summary:
            return "ninguno"
        return " | ".join(f"{asset} {desc}" for asset, desc in sorted(cycle_ma_summary.items()))
    def _log_dry_run_verbose_cycle_summary(
        self,
        *,
        cycle_num: int,
        threshold: int,
        accepted_last_window: int,
        cycle_ob_summary: dict[str, str],
        cycle_ma_summary: dict[str, str],
    ) -> None:
        if not (DRY_RUN_VERBOSE and self.bot.dry_run):
            return
        threshold_tag = self._threshold_label(threshold)
        log.info("══════════════════════════════════════")
        log.info(
            "[CICLO #%d] UMBRAL ACTIVO: %d (%s) | ventana: %d/%d scans con señal",
            cycle_num,
            threshold,
            threshold_tag,
            accepted_last_window,
            ADAPTIVE_THRESHOLD_WINDOW_SCANS,
        )
        log.info("[CICLO #%d] BLACKLIST: %s", cycle_num, self._build_blacklist_summary_line())
        log.info("[CICLO #%d] OB detectados: %s", cycle_num, self._build_ob_summary_line(cycle_ob_summary))
        log.info("[CICLO #%d] MA state: %s", cycle_num, self._build_ma_summary_line(cycle_ma_summary))
        log.info("══════════════════════════════════════")
    async def _process_pending_reversals(
        self,
        assets_payout: dict[str, int],
        candles_1m_by_asset: dict[str, list],
        current_prices: dict[str, float],
    ) -> list[CandidateEntry]:
        """
        Re-evalúa activos en pending_reversals.
        Devuelve candidatos listos para entrar; limpia expirados/inválidos.
        """
        ready_candidates: list[CandidateEntry] = []
        to_remove: list[str] = []

        for sym, pr in list(self.bot.pending_reversals.items()):
            side = "techo" if pr.entry_mode == "rebound_ceiling" else "piso"

            # Verificar que el activo sigue disponible este ciclo
            if sym not in assets_payout:
                to_remove.append(sym)
                log.info("↩ %s: no disponible este ciclo, cancelando espera", sym)
                continue

            # Verificar que el precio sigue cerca del extremo de la zona
            price = current_prices.get(sym)
            if price is None:
                to_remove.append(sym)
                continue

            if pr.proposed_direction == "call":
                still_at_extreme = price_at_floor(price, pr.zone.floor)
            else:
                still_at_extreme = price_at_ceiling(price, pr.zone.ceiling)

            if not still_at_extreme:
                log.info(
                    "↩ %s: precio %.5f abandonó el %s (%.5f), cancelando espera",
                    sym, price, side,
                    pr.zone.floor if pr.proposed_direction == "call" else pr.zone.ceiling,
                )
                to_remove.append(sym)
                continue

            # Re-evaluar patrón 1m
            candles_1m = candles_1m_by_asset.get(sym, [])
            pattern_name = "none"
            strength = 0.0
            confirms = False
            if len(candles_1m) >= 3:
                signal_1m = detect_reversal_pattern(candles_1m, pr.proposed_direction)
                pattern_name = signal_1m.pattern_name
                strength = signal_1m.strength
                confirms = signal_1m.confirms_direction

            pr.scans_waited += 1

            log.info(
                "⏳ %s: reintento %d/%d — patrón actual: %s (%.2f) %s",
                sym, pr.scans_waited, pr.max_wait_scans,
                pattern_name, strength,
                "✓" if confirms else "✗",
            )

            req_strength = required_rebound_strength(pr.proposed_direction)
            candle_valid, candle_fail_reason = validate_rejection_candle(
                candles_1m,
                pr.proposed_direction,
                REJECTION_CANDLE_MIN_BODY,
            )

            if is_put_pattern_blacklisted(pr.proposed_direction, pattern_name):
                log.info(
                    "↪ %s: patrón %s en lista negra para PUT — skip",
                    sym,
                    pattern_name,
                )
                if pr.scans_waited >= pr.max_wait_scans:
                    to_remove.append(sym)
                continue

            # Tanto CALL como PUT requieren patrón confirmado con fuerza suficiente.
            can_enter = candle_valid and confirms and strength >= req_strength

            if can_enter:
                passed, candles_15m, zones, _skip = self._apply_strat_a_htf_zone_gates(
                    sym, pr.proposed_direction, price,
                )
                if not passed:
                    if pr.scans_waited >= pr.max_wait_scans:
                        to_remove.append(sym)
                    continue

                log.info(
                    "✅ %s: reversión confirmada tras %d scan(s) — entrando %s",
                    sym, pr.scans_waited, pr.proposed_direction.upper(),
                )
                payout = assets_payout[sym]
                # Necesitamos velas 5m para construir el CandidateEntry — solo tenemos 1m aquí,
                # así que usamos una lista vacía: el score se basará en zona/payout/trend de 1m.
                candles_5m: list = []
                # Fetch H1 para niveles históricos
                h1_hist: List[Candle] = await fetch_candles_with_retry(
                    self.bot.client,
                    sym,
                    H1_TF_SEC,
                    H1_CANDLES_LOOKBACK,
                    timeout_sec=H1_FETCH_TIMEOUT_SEC,
                )
                candidate = CandidateEntry(
                    asset=sym,
                    payout=payout,
                    zone=pr.zone,
                    direction=pr.proposed_direction,
                    candles=candles_5m,
                )
                candidate.candles_h1 = h1_hist
                candidate.zone_memory = zones
                candidate.candles_15m = candles_15m
                candidate._reversal_pattern = pattern_name  # type: ignore[attr-defined]
                candidate._reversal_strength = strength  # type: ignore[attr-defined]
                candidate._reversal_confirms = confirms  # type: ignore[attr-defined]
                candidate._entry_mode = pr.entry_mode  # type: ignore[attr-defined]
                candidate._signal_ts_1m = candles_1m[-1].ts if candles_1m else None  # type: ignore[attr-defined]
                amount, _ = self.executor._compute_initial_amount(payout)
                candidate._amount = amount  # type: ignore[attr-defined]
                candidate._stage = "initial"  # type: ignore[attr-defined]
                candidate._from_pending = True  # type: ignore[attr-defined]
                candidate._strategy_origin = "STRAT-A"  # type: ignore[attr-defined]
                score_candidate(candidate)
                if confirms and strength >= 0.60:
                    candidate.score = round(candidate.score + 8.0, 1)
                    candidate.score_breakdown["reversal_bonus"] = 8.0
                elif confirms and strength >= REBOUND_MIN_STRENGTH_CALL:
                    candidate.score = round(candidate.score + 5.0, 1)
                    candidate.score_breakdown["reversal_bonus"] = 5.0
                elif pattern_name == "none":
                    candidate.score = round(candidate.score - 10.0, 1)
                    candidate.score_breakdown["weak_confirmation"] = -10.0
                ready_candidates.append(candidate)
                to_remove.append(sym)

            elif pr.scans_waited >= pr.max_wait_scans:
                log.info(
                    "⏰ %s: expiró espera sin confirmación (%d scans)",
                    sym, pr.scans_waited,
                )
                to_remove.append(sym)
            elif not confirms or strength < req_strength:
                if pattern_name == "none":
                    log.info(
                        "↪ %s: %s requiere patrón ≥%.2f, detectado %s %.2f (%s)",
                        sym,
                        pr.proposed_direction.upper(),
                        req_strength,
                        pattern_name,
                        strength,
                        explain_no_pattern_reason(candles_1m, pr.proposed_direction),
                    )
                else:
                    log.info(
                        "↪ %s: %s requiere patrón ≥%.2f, detectado %s %.2f",
                        sym,
                        pr.proposed_direction.upper(),
                        req_strength,
                        pattern_name,
                        strength,
                    )
            elif not candle_valid:
                log.info(
                    "↪ %s: vela 1m no confirma rebote en %s (%s)",
                    sym,
                    side,
                    candle_fail_reason,
                )

        for sym in to_remove:
            self.bot.pending_reversals.pop(sym, None)

        return ready_candidates

    async def _scan_phase_prepare(self) -> list[tuple[str, int]] | None:
        """FASE 1/5 — martin, assets, filtros iniciales."""
        self._phase_log("1/5", "Preparación — martin, assets, filtros")

        assets = await get_open_assets(self.bot.client, MIN_PAYOUT)
        if not assets:
            log.warning("No se obtuvieron activos OTC disponibles.")
            return None

        total_assets_available = len(assets)
        if SCAN_MAX_ASSETS_PER_CYCLE > 0 and len(assets) > SCAN_MAX_ASSETS_PER_CYCLE:
            assets = assets[:SCAN_MAX_ASSETS_PER_CYCLE]
            log.info(
                "⚡ Aceleración scan: %d/%d activos (top payout)",
                len(assets),
                total_assets_available,
            )

        self.bot.stats["scans"] += 1
        self.executor._cleanup_asset_blacklist()
        log.info(
            "═══ SCAN #%d | %d activos payout≥%d%% ═══",
            self.bot.stats["scans"],
            len(assets),
            MIN_PAYOUT,
        )

        for sym in list(self.bot.trades.keys()):
            entered = await self.executor._check_martin(sym)
            if entered:
                await sleep_with_inline_countdown(COOLDOWN_BETWEEN_ENTRIES, "⏳ Cooldown post-orden")
            await asyncio.sleep(0.2)

        if self.bot.trades:
            activos_abiertos = ", ".join(self.bot.trades.keys())
            log.info(
                "👁 Operación activa [%s] — escaneando igual para vigilar oportunidades.",
                activos_abiertos,
            )
        else:
            if self.bot.watched_candidates:
                stale = [
                    a for a, (_, ts) in self.bot.watched_candidates.items()
                    if time.time() - ts > 300
                ]
                for a in stale:
                    del self.bot.watched_candidates[a]

        decrement_failed_assets(self.bot)
        return assets

    async def _scan_phase_prefetch(self, assets: list[tuple[str, int]]) -> ScanCycleData:
        """FASE 2/5 y 3b — prefetch primario (5m+1m) y secundario (OB+H1)."""
        symbols = [sym for sym, _ in assets]
        candle_cache = getattr(self.bot, "candle_cache", None)

        self._phase_log("2/5", "Prefetch primario — 5m+1m paralelo")
        fetch_t0 = time.monotonic()
        candles_5m, candles_1m = await prefetch_primary_candles(
            self.bot.client,
            symbols,
            candle_cache,
            CANDLE_FETCH_CONCURRENCY,
        )
        scan_fetch_elapsed_ms = int((time.monotonic() - fetch_t0) * 1000)
        log.info(
            "⚡ Prefetch velas: scan_fetch_elapsed_ms=%d | activos=%d | concurrency=%d",
            scan_fetch_elapsed_ms,
            len(symbols),
            CANDLE_FETCH_CONCURRENCY,
        )

        strat_a_symbols = symbols_needing_strat_a_prefetch(
            assets,
            self.bot,
            candles_5m,
            is_blacklisted=self.executor._is_asset_blacklisted,
        )
        self._phase_log(
            "3b/5",
            f"Prefetch secundario OB+H1 — {len(strat_a_symbols)} símbolos",
        )
        candles_ob, candles_h1, ob_tf_labels, blocks_by_symbol = await prefetch_strat_a_secondary(
            self.bot.client,
            strat_a_symbols,
            candles_5m,
            candle_cache,
            CANDLE_FETCH_CONCURRENCY,
        )
        log.info(
            "⚡ Prefetch OB: blocks_precalc=%d | símbolos=%d",
            len(blocks_by_symbol),
            len(strat_a_symbols),
        )

        return ScanCycleData(
            symbols=symbols,
            assets=assets,
            candles_5m=candles_5m,
            candles_1m=candles_1m,
            candles_ob=candles_ob,
            candles_h1=candles_h1,
            ob_tf_labels=ob_tf_labels,
            blocks_by_symbol=blocks_by_symbol,
        )

    async def _scan_phase_evaluate_assets(
        self,
        cycle: ScanCycleData,
    ) -> dict[str, Any]:
        """FASE 3/5 — STRAT-B, MOMENTUM y STRAT-A sin I/O de red."""
        self._phase_log("3/5", "Evaluación — STRAT-B/MOMENTUM/STRAT-A")
        if _runtime_config.STRAT_A_ONLY:
            log.info("[STRAT-A-ONLY] Modo activo — solo candidatos consolidación")

        candidates: list[CandidateEntry] = []
        cycle_ob_summary: dict[str, str] = {}
        cycle_ma_summary: dict[str, str] = {}
        strat_b_total = 0
        strat_b_insufficient = 0
        strat_b_timeout = 0
        strat_b_hits: list[tuple[str, int, float]] = []
        strat_b_nearmiss: list[tuple[str, int, float, str]] = []
        candles_1m_collected: dict[str, list] = {}
        last_prices_collected: dict[str, float] = {}
        radar_entries_from_cycle: list[RadarWatchEntry] = []

        candles_5m_by_asset = cycle.candles_5m
        candles_1m_by_asset = cycle.candles_1m
        assets = cycle.assets

        for idx, (sym, payout) in enumerate(assets, start=1):
            if SCAN_PROGRESS_EVERY > 0 and (
                idx == 1 or idx % SCAN_PROGRESS_EVERY == 0 or idx == len(assets)
            ):
                log.info("⏱ Progreso scan: %d/%d activos", idx, len(assets))

            if sym in self.bot.trades:
                continue

            if sym in self.bot.greylist_assets:
                log.info("⏭ %s: en lista gris — skip", sym)
                self.bot.stats["skipped"] += 1
                continue

            if self.executor._is_asset_blacklisted(sym):
                until_ts = self.bot.asset_blacklist_until.get(sym, time.time())
                remain_min = max(0.0, (until_ts - time.time()) / 60.0)
                log.warning(
                    "⏭ %s: blacklist temporal activa (%.1f min restantes)", sym, remain_min,
                )
                self.bot.stats["skipped"] += 1
                continue

            if sym in self.bot.failed_assets:
                log.info(
                    "⏭ %s skipped — falló en ciclo anterior (%d ciclos restantes)",
                    sym,
                    self.bot.failed_assets[sym],
                )
                continue

            candles = candles_5m_by_asset.get(sym, [])
            strat_b_total += 1
            candles_1m = candles_1m_by_asset.get(sym, [])
            if len(candles_1m) < 20:
                log.debug(
                    "STRAT-B DEBUG: %s devolvió %d velas 1m (mínimo=20, timeout=%.0fs)",
                    sym, len(candles_1m), CANDLE_FETCH_1M_TIMEOUT_SEC,
                )
            candles_1m_collected[sym] = candles_1m
            strat_b_signal = False
            strat_b_info = {
                "confidence": 0.0,
                "reason": "Datos 1m insuficientes",
                "signal_type": None,
                "direction": None,
            }
            if len(candles_1m) >= 20:
                strat_b_eval = evaluate_strat_b(candles_1m)
                strat_b_signal = bool(strat_b_eval and strat_b_eval.get("signal"))
                strat_b_info = strat_b_eval or {
                    "confidence": 0.0,
                    "reason": "Datos 1m insuficientes",
                    "signal_type": None,
                    "direction": None,
                }
            elif len(candles_1m) == 0:
                strat_b_timeout += 1
            else:
                strat_b_insufficient += 1

            strat_b_conf = float(strat_b_info.get("confidence", 0.0) or 0.0)
            strat_b_signal_type = str(strat_b_info.get("signal_type") or "")
            strat_b_direction = str(strat_b_info.get("direction") or "call")
            strat_b_reason = str(
                strat_b_info.get("reason", f"{strat_b_signal_type or 'Señal'} detectado")
                or "Señal detectada"
            )
            is_early_wyckoff = strat_b_signal_type.startswith("wyckoff_early")
            strat_b_required_conf = (
                STRAT_B_MIN_CONFIDENCE_EARLY if is_early_wyckoff else STRAT_B_MIN_CONFIDENCE
            )
            if strat_b_signal:
                self.bot.stats["strat_b_signals"] += 1
                strat_b_hits.append((sym, payout, strat_b_conf, strat_b_direction, strat_b_signal_type))
            else:
                if strat_b_conf >= STRAT_B_PREVIEW_MIN_CONF:
                    strat_b_nearmiss.append((sym, payout, strat_b_conf, strat_b_reason))

            if (
                not _runtime_config.STRAT_A_ONLY
                and STRAT_B_CAN_TRADE
                and strat_b_signal
                and strat_b_conf >= strat_b_required_conf
                and len(self.bot.trades) < MAX_CONCURRENT_TRADES
            ):
                # ── Diversification guard ─────────────────────────────
                d_enforcer: DiversificationEnforcer | None = getattr(
                    self.bot, "diversification_enforcer", None,
                )
                if d_enforcer is not None:
                    d_ok, d_reason = d_enforcer.check(self.bot.trades, sym)
                    if not d_ok:
                        log.info(
                            "⛔ [STRAT-B] %s: diversificación — %s", sym, d_reason,
                        )
                        self.bot.stats["rejected_diversification"] = (
                            self.bot.stats.get("rejected_diversification", 0) + 1
                        )
                        continue

                b_amount, _ = self.executor._compute_initial_amount(payout)
                pseudo_zone = ConsolidationZone(
                    asset=sym,
                    ceiling=float(candles_1m[-1].high),
                    floor=float(candles_1m[-1].low),
                    bars_inside=0,
                    detected_at=time.time(),
                    range_pct=0.0,
                )
                if strat_b_signal_type == "upthrust":
                    pattern_label = "Upthrust"
                elif strat_b_signal_type == "spring":
                    pattern_label = "Spring Sweep"
                elif strat_b_signal_type == "wyckoff_early_upthrust":
                    pattern_label = "Wyckoff Early M1+M2 (Upthrust)"
                elif strat_b_signal_type == "wyckoff_early_spring":
                    pattern_label = "Wyckoff Early M1+M2 (Spring)"
                else:
                    pattern_label = "Wyckoff"
    
                b_candidate = CandidateEntry(
                    asset=sym,
                    payout=payout,
                    zone=pseudo_zone,
                    direction=strat_b_direction,
                    candles=candles_1m,
                    score=round(strat_b_conf * 100.0, 1),
                    score_breakdown={
                        "compression": 0.0,
                        "bounce": round(strat_b_conf * 35.0, 2),
                        "trend": round(strat_b_conf * 25.0, 2),
                        "payout": round(min(20.0, (payout / 95.0) * 20.0), 2),
                    },
                )
                setattr(b_candidate, "_reversal_pattern", strat_b_signal_type or "none")
                setattr(b_candidate, "_reversal_strength", strat_b_conf)
    
                b_strategy = self.executor._strategy_snapshot()
                b_strategy.update(
                    {
                        "strategy_origin": "STRAT-B",
                        "strat_b_signal_type": strat_b_signal_type,
                        "strat_b_confidence": strat_b_conf,
                        "strat_b_required_conf": strat_b_required_conf,
                        "strat_b_reason": strat_b_reason,
                    }
                )
    
                b_outcome = "DRY_RUN" if self.bot.dry_run else "PENDING"
                b_cid = get_journal().log_candidate(
                    b_candidate,
                    decision="ACCEPTED",
                    amount=b_amount,
                    stage="initial",
                    outcome=b_outcome,
                    strategy=b_strategy,
                )
    
                await self.executor.enter_trade(
                    sym,
                    strat_b_direction,
                    b_amount,
                    pseudo_zone,
                    f"{pattern_label} conf={strat_b_conf*100:.1f}% req={strat_b_required_conf*100:.1f}%",
                    "initial",
                    journal_cid=b_cid,
                    signal_ts=candles_1m[-1].ts if candles_1m else None,
                    strategy_origin="STRAT-B",
                    duration_sec=STRAT_B_DURATION_SEC,
                    payout=payout,
                    score_original=round(strat_b_conf * 100.0, 1),
                )
                await sleep_with_inline_countdown(COOLDOWN_BETWEEN_ENTRIES, "⏳ Cooldown post-orden")

            momentum_hit = (
                detect_momentum_1m(candles_1m)
                if not _runtime_config.STRAT_A_ONLY and _runtime_config.STRAT_MOMENTUM_ENABLED
                else None
            )
            if momentum_hit and sym not in self.bot.trades:
                mom_dir, mom_strength = momentum_hit
                mom_zone = ConsolidationZone(
                    asset=sym,
                    ceiling=float(candles_1m[-1].high),
                    floor=float(candles_1m[-1].low),
                    bars_inside=0,
                    detected_at=time.time(),
                    range_pct=0.0,
                )
                mom_amount, _ = self.executor._compute_initial_amount(payout)
                mom_candidate = CandidateEntry(
                    asset=sym,
                    payout=payout,
                    zone=mom_zone,
                    direction=mom_dir,
                    candles=candles_1m,
                    score=round(mom_strength * 100.0, 1),
                    score_breakdown={
                        "compression": 0.0,
                        "momentum": round(mom_strength * 35.0, 2),
                        "trend": round(mom_strength * 25.0, 2),
                        "payout": round(min(20.0, (payout / 95.0) * 20.0), 2),
                    },
                )
                setattr(mom_candidate, "_strategy_origin", "STRAT-MOMENTUM")
                setattr(mom_candidate, "_reversal_pattern", "momentum_1m")
                setattr(mom_candidate, "_reversal_strength", mom_strength)
                setattr(mom_candidate, "_signal_ts_1m", candles_1m[-1].ts if candles_1m else None)
                setattr(mom_candidate, "_amount", mom_amount)
                setattr(mom_candidate, "_stage", "initial")
                candidates.append(mom_candidate)
                self.bot.stats.setdefault("strat_momentum_signals", 0)
                self.bot.stats["strat_momentum_signals"] += 1
                log.info(
                    "[STRAT-MOMENTUM] %s %s strength=%.2f score=%.1f",
                    sym,
                    mom_dir.upper(),
                    mom_strength,
                    mom_candidate.score,
                )

            # ── Reversal Swing ──
            swing_hit = (
                detect_reversal_swing(candles_1m)
                if not _runtime_config.STRAT_A_ONLY and _runtime_config.STRAT_REVERSAL_SWING_ENABLED
                else None
            )
            if swing_hit and sym not in self.bot.trades:
                swing_dir, swing_strength = swing_hit
                swing_zone = ConsolidationZone(
                    asset=sym,
                    ceiling=float(candles_1m[-1].high),
                    floor=float(candles_1m[-1].low),
                    bars_inside=0,
                    detected_at=time.time(),
                    range_pct=0.0,
                )
                swing_amount, _ = self.executor._compute_initial_amount(payout)
                swing_candidate = CandidateEntry(
                    asset=sym,
                    payout=payout,
                    zone=swing_zone,
                    direction=swing_dir,
                    candles=candles_1m,
                    score=0.0,
                    score_breakdown={},
                    reversal_pattern="swing_rejection",
                    reversal_strength=swing_strength,
                    reversal_confirms=True,
                )
                setattr(swing_candidate, "_strategy_origin", "STRAT-REVERSAL-SWING")
                setattr(swing_candidate, "_signal_ts_1m", candles_1m[-1].ts if candles_1m else None)
                setattr(swing_candidate, "_amount", swing_amount)
                setattr(swing_candidate, "_stage", "initial")
                score_candidate(swing_candidate)
                candidates.append(swing_candidate)
                self.bot.stats.setdefault("strat_reversal_swing_signals", 0)
                self.bot.stats["strat_reversal_swing_signals"] += 1
                log.info(
                    "[STRAT-MOMENTUM] %s %s strength=%.2f score=%.1f",
                    sym,
                    mom_dir.upper(),
                    mom_strength,
                    mom_candidate.score,
                )

            # ── Order Block (post-momentum, pre-STRAT-A) ──
            ob_hit = (
                detect_order_block_entry(candles_1m)
                if not _runtime_config.STRAT_A_ONLY and STRAT_ORDER_BLOCK_ENABLED
                else None
            )
            if ob_hit and sym not in self.bot.trades:
                ob_dir, ob_strength, ob_low, ob_high = ob_hit
                ob_zone = ConsolidationZone(
                    asset=sym,
                    ceiling=ob_high,
                    floor=ob_low,
                    bars_inside=0,
                    detected_at=time.time(),
                    range_pct=0.0,
                )
                ob_candidate = CandidateEntry(
                    asset=sym,
                    payout=payout,
                    zone=ob_zone,
                    direction=ob_dir,
                    candles=candles_1m,
                    score=round(ob_strength * 100.0, 1),
                    mode=SignalMode.REBOUND,
                    score_breakdown={
                        "compression": 0.0,
                        "bounce": round(ob_strength * 35.0, 2),
                        "trend": round(ob_strength * 25.0, 2),
                        "payout": round(min(20.0, (payout / 95.0) * 20.0), 2),
                    },
                )
                setattr(ob_candidate, "_strategy_origin", "STRAT-ORDER-BLOCK")
                setattr(ob_candidate, "_reversal_pattern", "order_block")
                setattr(ob_candidate, "_reversal_strength", ob_strength)
                setattr(ob_candidate, "_signal_ts_1m", candles_1m[-1].ts if candles_1m else None)
                score_candidate(ob_candidate)
                candidates.append(ob_candidate)
                self.bot.stats.setdefault("strat_order_block_signals", 0)
                self.bot.stats["strat_order_block_signals"] += 1
                log.info(
                    "[STRAT-ORDER-BLOCK] %s %s strength=%.2f score=%.1f ob_range=[%.5f, %.5f]",
                    sym,
                    ob_dir.upper(),
                    ob_strength,
                    ob_candidate.score,
                    ob_low,
                    ob_high,
                )

            if payout < STRAT_A_MIN_PAYOUT:
                log.info(
                    "⛔ [STRAT-A] %s: payout=%d%% < %d%% — excluido del scan",
                    sym,
                    payout,
                    STRAT_A_MIN_PAYOUT,
                )
                self.bot.stats["skipped"] = self.bot.stats.get("skipped", 0) + 1
                continue

            if len(candles) < MIN_CONSOLIDATION_BARS + 2:
                continue

            dynamic_max_range, atr_pct, dynamic_touch_tolerance = compute_dynamic_range(candles)

            zone = detect_consolidation(candles, max_range_pct=dynamic_max_range)
            if zone is None:
                self.bot.zones.pop(sym, None)
                continue

            zone.asset = sym
            zone = self._merge_zone_state(sym, zone, candles, payout)
            if zone is None:
                continue

            price = candles[-1].close
            if not self._price_sanity_ok(sym, zone, price):
                continue

            self.bot.last_known_price[sym] = price
            last_prices_collected[sym] = price

            blocks = cycle.blocks_by_symbol.get(sym, {"bull": [], "bear": []})
            ob_tf_label = cycle.ob_tf_labels.get(sym, "5m_fallback")
            self.bot.order_blocks_by_asset[sym] = blocks
            ma_state = self._compute_ma_state(sym, candles)
            if blocks.get("bull"):
                b = blocks["bull"][0]
                cycle_ob_summary[sym] = f"bull@{b.high:.4f}-{b.low:.4f} ({ob_tf_label})"
            elif blocks.get("bear"):
                b = blocks["bear"][0]
                cycle_ob_summary[sym] = f"bear@{b.high:.4f}-{b.low:.4f} ({ob_tf_label})"
            if ma_state is None:
                cycle_ma_summary[sym] = "SIN_DATOS"
            elif ma_state.trend == "FLAT":
                cycle_ma_summary[sym] = "FLAT"
            else:
                comparator = ">" if ma_state.ma35 >= ma_state.ma50 else "<"
                cycle_ma_summary[sym] = (
                    f"{ma_state.trend} (MA35={ma_state.ma35:.4f} {comparator} MA50={ma_state.ma50:.4f})"
                )

            h1_candles = cycle.candles_h1.get(sym, [])
            h1_trend = infer_h1_trend(h1_candles)

            ev = evaluate_strat_a(
                candles_5m=candles,
                candles_1m=candles_1m,
                zone=zone,
                blocks=blocks,
                ma_state=ma_state,
                dynamic_touch_tolerance=dynamic_touch_tolerance,
                h1_trend=h1_trend,
                zone_age_rebound_min=STRAT_A_ZONE_MIN_AGE_REBOUND,
            )

            if ev.entry_mode.startswith("breakout"):
                await self._handle_breakout_side_effects(
                    sym, zone, candles, candles_1m, payout, ev,
                )

            if ev.pending_reversal_hint:
                self._apply_pending_reversal_hint(
                    sym, zone, payout, ev.pending_reversal_hint, ev.skip_reason or "", candles_1m,
                )

            radar_entry = self._radar_entry_from_evaluation(
                sym, payout, zone, price, ev, dynamic_touch_tolerance,
            )
            if radar_entry is not None:
                radar_entries_from_cycle.append(radar_entry)

            if not ev.has_signal:
                if ev.skip_reason == "zone_too_young":
                    min_zone_age = (
                        ZONE_AGE_BREAKOUT_MIN if ev.stage == "breakout" else STRAT_A_ZONE_MIN_AGE_REBOUND
                    )
                    log.info(
                        "⏭ %s: zona demasiado joven (%.1fmin < %dmin) — skip",
                        sym,
                        zone.age_minutes,
                        min_zone_age,
                    )
                elif (
                    ev.entry_mode.startswith("rebound")
                    and ev.skip_reason in ("pattern_missing", "pattern_insufficient", "strict_pattern_veto")
                ):
                    self._log_strat_a_pattern_veto(sym, ev)
                self._bump_strat_a_skip_stats(ev.skip_reason)
                continue

            passed, candles_15m, zones, _skip = self._apply_strat_a_htf_zone_gates(
                sym, ev.direction, price,
            )
            if not passed:
                continue

            amount, _ = self.executor._compute_initial_amount(payout)
            candidate = self._candidate_from_strat_a_evaluation(
                sym, payout, candles, h1_candles, ev, amount, ma_state, blocks, ob_tf_label, candles_1m,
            )
            candidate.zone_memory = zones
            candidate.candles_15m = candles_15m
            score_candidate(candidate)
            self._apply_score_adjustments(candidate, ev, ob_tf_label, sym)
            candidates.append(candidate)

        log.info(
            "[STRAT-B] Resumen ciclo: %d evaluados | señales=%d | "
            "timeout_fetch=%d | datos_insuficientes=%d | sin_patrón=%d",
            strat_b_total,
            len(strat_b_hits),
            strat_b_timeout,
            strat_b_insufficient,
            strat_b_total - len(strat_b_hits) - strat_b_timeout - strat_b_insufficient,
        )
        if strat_b_hits:
            for sym, payout, conf, b_dir, b_type in sorted(strat_b_hits, key=lambda x: -x[2])[:STRAT_B_LOG_TOP_N]:
                if b_type == "upthrust":
                    pattern_label = "Upthrust"
                elif b_type == "spring":
                    pattern_label = "Spring Sweep"
                elif b_type == "wyckoff_early_upthrust":
                    pattern_label = "Wyckoff Early M1+M2 (Upthrust)"
                elif b_type == "wyckoff_early_spring":
                    pattern_label = "Wyckoff Early M1+M2 (Spring)"
                else:
                    pattern_label = "Wyckoff"
                log.info(
                    "[STRAT-B] ✅ %s [%d%%] %s | conf=%.1f | %s ✓",
                    sym,
                    payout,
                    b_dir.upper(),
                    conf * 100,
                    pattern_label,
                )
                candles_2m = await fetch_candles_with_retry(
                    self.bot.client,
                    sym,
                    120,
                    90,
                    timeout_sec=CANDLE_FETCH_TIMEOUT_SEC,
                )
                support_2m, touches = find_strong_support_2m(candles_2m)
                if support_2m is not None:
                    log.info(
                        "[STRAT-B] 📍 %s soporte fuerte 2m=%.5f (toques=%d)",
                        sym,
                        support_2m,
                        touches,
                    )
                else:
                    log.info("[STRAT-B] 📍 %s sin soporte fuerte 2m detectable", sym)
        elif strat_b_nearmiss:
            for sym, payout, conf, reason in sorted(strat_b_nearmiss, key=lambda x: -x[2])[:STRAT_B_LOG_TOP_N]:
                log.info(
                    "[STRAT-B] ~ %s [%d%%] conf=%.1f | %s",
                    sym,
                    payout,
                    conf * 100,
                    reason,
                )

        if radar_entries_from_cycle:
            self._update_radar_watchlist(radar_entries_from_cycle)

        return {
            "candidates": candidates,
            "cycle_ob_summary": cycle_ob_summary,
            "cycle_ma_summary": cycle_ma_summary,
            "candles_1m_collected": candles_1m_collected,
            "last_prices_collected": last_prices_collected,
        }

    async def radar_watch_tick(self) -> bool:
        """Tick 1m sobre pares en watchlist. Devuelve True si se intentó entrada."""
        watchlist = (
            self.bot.radar_watchlist
            if isinstance(getattr(self.bot, "radar_watchlist", None), dict)
            else {}
        )
        if not self._radar_enabled() or not watchlist:
            return False

        if await self.executor.refresh_balance_and_risk():
            return False

        entries_before = self.bot.stats.get("entries", 0)
        watch_items = list(watchlist.items())
        candidates: list[CandidateEntry] = []
        candles_1m_collected: dict[str, list] = {}
        last_prices_collected: dict[str, float] = {}
        stale_assets: list[str] = []
        radar_1m_count = 36

        for sym, watch in watch_items:
            try:
                candles_1m = await self.bot.candle_cache.get_or_update(
                    self.bot.client,
                    sym,
                    TF_1M,
                    radar_1m_count,
                )
            except Exception as exc:
                log.warning("[RADAR] %s: fetch 1m falló (%s)", sym, exc)
                continue

            if len(candles_1m) < 3:
                continue

            price = float(candles_1m[-1].close)
            candles_1m_collected[sym] = candles_1m
            last_prices_collected[sym] = price

            zone = self.bot.zones.get(sym, watch.zone)
            if zone is None:
                stale_assets.append(sym)
                continue

            candles_5m = await self.bot.candle_cache.get_or_update(
                self.bot.client, sym, TF_5M, CANDLES_LOOKBACK,
            )
            if len(candles_5m) < MIN_CONSOLIDATION_BARS + 2:
                continue

            _, _, dynamic_touch_tolerance = compute_dynamic_range(candles_5m)

            if not should_watch(zone, price, watch.entry_mode, watch.stage, dynamic_touch_tolerance):
                log.info(
                    "[RADAR] %s: precio %.5f salió del extremo (%s) — removido",
                    sym, price, watch.side_label,
                )
                stale_assets.append(sym)
                continue

            blocks = self.bot.order_blocks_by_asset.get(sym, {"bull": [], "bear": []})
            ma_state = self.bot.ma_state_by_asset.get(sym)
            h1_candles = await self.bot.candle_cache.get_or_update(
                self.bot.client, sym, H1_TF_SEC, H1_CANDLES_LOOKBACK,
            )
            h1_trend = infer_h1_trend(h1_candles)

            ev = evaluate_strat_a(
                candles_5m=candles_5m,
                candles_1m=candles_1m,
                zone=zone,
                blocks=blocks,
                ma_state=ma_state,
                price=price,
                dynamic_touch_tolerance=dynamic_touch_tolerance,
                h1_trend=h1_trend,
                zone_age_rebound_min=STRAT_A_ZONE_MIN_AGE_REBOUND,
            )

            if ev.pending_reversal_hint:
                self._apply_pending_reversal_hint(
                    sym, zone, watch.payout, ev.pending_reversal_hint, ev.skip_reason or "", candles_1m,
                )

            if not ev.has_signal:
                if (
                    ev.entry_mode.startswith("rebound")
                    and ev.skip_reason in ("pattern_missing", "pattern_insufficient", "strict_pattern_veto")
                ):
                    self._log_strat_a_pattern_veto(sym, ev)
                continue

            passed, candles_15m, zones, _skip = self._apply_strat_a_htf_zone_gates(
                sym, ev.direction, price,
            )
            if not passed:
                continue

            amount, _ = self.executor._compute_initial_amount(watch.payout)
            candidate = self._candidate_from_strat_a_evaluation(
                sym,
                watch.payout,
                candles_5m,
                h1_candles,
                ev,
                amount,
                ma_state,
                blocks,
                "radar_cache",
                candles_1m,
            )
            candidate.zone_memory = zones
            candidate.candles_15m = candles_15m
            score_candidate(candidate)
            self._apply_score_adjustments(candidate, ev, "radar", sym)
            setattr(candidate, "_from_radar", True)
            candidates.append(candidate)
            log.info(
                "[RADAR] %s: señal lista en tick — %s %s readiness=%.0f",
                sym, ev.direction.upper(), watch.side_label, watch.readiness_score,
            )

        for sym in stale_assets:
            self.bot.radar_watchlist.pop(sym, None)

        assets_map: dict[str, int] = {sym: w.payout for sym, w in self.bot.radar_watchlist.items()}
        for sym, pr in self.bot.pending_reversals.items():
            assets_map.setdefault(sym, pr.payout)

        if not candidates and not self.bot.pending_reversals:
            return False

        eval_result = {
            "candidates": candidates,
            "cycle_ob_summary": {},
            "cycle_ma_summary": {},
            "candles_1m_collected": candles_1m_collected,
            "last_prices_collected": last_prices_collected,
        }
        await self._scan_phase_select_execute(eval_result, list(assets_map.items()))
        return self.bot.stats.get("entries", 0) > entries_before

    async def _scan_phase_select_execute(
        self,
        eval_result: dict[str, Any],
        assets: list[tuple[str, int]],
    ) -> None:
        """FASE 4/5 y 5/5 — pending reversals, selección y ejecución."""
        self._phase_log("4/5", "Pending reversals + selección")

        candidates: list[CandidateEntry] = eval_result["candidates"]
        cycle_ob_summary = eval_result["cycle_ob_summary"]
        cycle_ma_summary = eval_result["cycle_ma_summary"]
        candles_1m_collected = eval_result["candles_1m_collected"]
        last_prices_collected = eval_result["last_prices_collected"]
        accepted_this_scan = 0

        if self.bot.pending_reversals:
            assets_payout_map = dict(assets)
            pending_confirmed = await self._process_pending_reversals(
                assets_payout_map,
                candles_1m_collected,
                last_prices_collected,
            )
            if pending_confirmed:
                log.info(
                    "⏳→✅ %d candidato(s) de pending_reversals agregados al ciclo.",
                    len(pending_confirmed),
                )
                candidates.extend(pending_confirmed)

        candidates, pending_martin_entered = await self.executor._process_pending_martin(candidates)
        if pending_martin_entered:
            await sleep_with_inline_countdown(COOLDOWN_BETWEEN_ENTRIES, "⏳ Cooldown post-martin diferido")
            return

        prev_threshold = self.bot.current_score_threshold
        session_threshold = self.executor._update_dynamic_threshold()
        window_accepts = sum(self.bot.accepted_scans_window)
        if prev_threshold != session_threshold:
            reason = self._threshold_change_reason(window_accepts)
            log.warning(
                "⚠ UMBRAL cambiado: %d → %d (%s)",
                prev_threshold,
                session_threshold,
                reason,
            )
        self._log_dry_run_verbose_cycle_summary(
            cycle_num=self.bot.stats["scans"],
            threshold=session_threshold,
            accepted_last_window=window_accepts,
            cycle_ob_summary=cycle_ob_summary,
            cycle_ma_summary=cycle_ma_summary,
        )

        if not candidates:
            log.info("  Sin señales este ciclo.")
            self.executor._record_scan_acceptances(0)
            return

        log.info(
            "[SCORE] Umbral dinámico sesión=%d (ventana=%d scans, accepted=%d)",
            session_threshold,
            ADAPTIVE_THRESHOLD_WINDOW_SCANS,
            window_accepts,
        )

        journal = get_journal()
        log.info("── %d candidatos evaluados ──", len(candidates))
        for c in sorted(candidates, key=lambda x: -x.score):
            eff_threshold = self._score_threshold_for_candidate(c, session_threshold)
            if (
                self._is_strat_a_candidate(c)
                and c.score < STRAT_A_MIN_SCORE
                and c.score >= session_threshold
            ):
                log.info(
                    "⛔ [STRAT-A] %s: score=%.1f < %d — veto calidad (umbral STRAT-A fijo)",
                    c.asset,
                    c.score,
                    STRAT_A_MIN_SCORE,
                )
            rng_pips = (c.zone.ceiling - c.zone.floor) * 10_000
            status = "✅" if c.score >= eff_threshold else "❌"
            decision_tag = "ACEPTADO" if c.score >= eff_threshold else "RECHAZADO"
            rev_pattern = getattr(c, "_reversal_pattern", "none")
            rev_strength = float(getattr(c, "_reversal_strength", 0.0) or 0.0)
            rev_confirms = bool(getattr(c, "_reversal_confirms", False))
            ob_adj = int(round(c.score_breakdown.get("order_block", 0.0)))
            ma_adj = int(round(c.score_breakdown.get("ma_filter", 0.0)))
            zone_age_min = c.zone.age_minutes
            if rev_pattern == "none":
                rev_txt = "~ sin patrón 1m"
            elif rev_confirms:
                rev_txt = "✓ confirmado"
            else:
                rev_txt = "✗ contradice (-15pts)"
            log.info(
                "  %s %s [%d%%] %s  score=%.1f/100  "
                "[comp=%.1f  rebote=%.1f  trend=%.1f  payout=%.1f]  "
                "rng=%.1fpips  zona=%.0fmin  1m_pattern=%s strength=%.2f %s "
                "[OB%+d][MA%+d][umbral=%d] → %s",
                status, c.asset, c.payout, c.direction.upper(), c.score,
                c.score_breakdown.get("compression", 0),
                c.score_breakdown.get("bounce", 0),
                c.score_breakdown.get("trend", 0),
                c.score_breakdown.get("payout", 0),
                rng_pips,
                zone_age_min,
                rev_pattern,
                rev_strength,
                rev_txt,
                ob_adj,
                ma_adj,
                eff_threshold,
                decision_tag,
            )
            log.info("      [OB] %s", getattr(c, "_ob_info", "sin datos"))
            log.info("      [MA] %s", getattr(c, "_ma_info", "sin datos"))

        selected, rejected = select_best(
            candidates,
            threshold=session_threshold,
            threshold_for=lambda c: self._score_threshold_for_candidate(c, session_threshold),
        )

        forced_breakouts = [
            c for c in candidates
            if bool(getattr(c, "_force_execute", False))
            and c.score >= self._score_threshold_for_candidate(c, session_threshold)
        ]
        if forced_breakouts:
            existing = {id(c) for c in selected}
            for c in forced_breakouts:
                if id(c) not in existing:
                    selected.append(c)
                    existing.add(id(c))
            rejected = [c for c in rejected if id(c) not in {id(x) for x in forced_breakouts}]
            log.warning(
                "⚠ Modo FORCE_BREAKOUT: %d ruptura(s) fuerte(s) enviadas aun con score bajo umbral.",
                len(forced_breakouts),
            )

        for c in rejected:
            journal.log_candidate(
                c,
                decision="REJECTED_SCORE",
                reject_reason=f"score={c.score:.1f} < umbral dinámico {session_threshold}",
                amount=getattr(c, "_amount", 0.0),
                stage=getattr(c, "_stage", "initial"),
                strategy=self.executor._strategy_snapshot(),
            )
            age_penalty = abs(c.score_breakdown.get("age_penalty", 0.0))
            if age_penalty > 0 and c.zone.age_minutes > 120:
                self.bot.stats["score_rejected_age"] += 1
            else:
                self.bot.stats["score_rejected_score"] += 1

        if not selected:
            best = max(candidates, key=lambda x: x.score)
            log.info(
                "[STRAT-A] ⛔ Ningún candidato supera el umbral %d/100. "
                "Mejor disponible: %s score=%.1f — NO se opera este ciclo.",
                session_threshold, best.asset, best.score,
            )
            self.bot.stats["skipped"] += len(candidates)
            self.executor._record_scan_acceptances(0)
            return

        log.info(
            "[STRAT-A] 🏆 Mejor(es) seleccionado(s): %d de %d candidatos",
            len(selected),
            len(candidates),
        )

        self._phase_log("5/5", "Ejecución")

        if len(self.bot.trades) >= MAX_CONCURRENT_TRADES:
            log.info(
                "🛑 Límite alcanzado (%d/%d). Se posponen nuevas entradas.",
                len(self.bot.trades), MAX_CONCURRENT_TRADES,
            )
            best_watched = max(selected, key=lambda x: x.score)
            self.bot.watched_candidates[best_watched.asset] = (best_watched, time.time())
            rev_w = getattr(best_watched, "_reversal_pattern", "none")
            log.info(
                "👁  VIGILADO: %s %s score=%.1f/100 payout=%d%% 1m=%s — "
                "se intentará entrar en cuanto cierre la operación activa.",
                best_watched.direction.upper(), best_watched.asset,
                best_watched.score, best_watched.payout, rev_w,
            )
            for c in selected:
                journal.log_candidate(
                    c,
                    decision="REJECTED_LIMIT",
                    reject_reason=f"trades abiertos={len(self.bot.trades)}/{MAX_CONCURRENT_TRADES} — vigilado",
                    amount=getattr(c, "_amount", 0.0),
                    stage=getattr(c, "_stage", "initial"),
                    strategy=self.executor._strategy_snapshot(),
                )
            self.bot.stats["skipped"] += len(selected)
            self.executor._record_scan_acceptances(0)
            return

        for winner in selected:
            if len(self.bot.trades) >= MAX_CONCURRENT_TRADES:
                journal.log_candidate(
                    winner,
                    decision="REJECTED_LIMIT",
                    reject_reason=f"trades abiertos={len(self.bot.trades)}/{MAX_CONCURRENT_TRADES}",
                    amount=getattr(winner, "_amount", 0.0),
                    stage=getattr(winner, "_stage", "initial"),
                    strategy=self.executor._strategy_snapshot(),
                )
                break

            # ── Diversification guard ─────────────────────────────────────
            d_enforcer: DiversificationEnforcer | None = getattr(
                self.bot, "diversification_enforcer", None,
            )
            if d_enforcer is not None:
                stage = getattr(winner, "_stage", "initial")
                d_ok, d_reason = d_enforcer.check(
                    self.bot.trades, winner.asset, stage=stage,
                )
                if not d_ok:
                    log.info("⛔ %s: diversificación — %s", winner.asset, d_reason)
                    journal.log_candidate(
                        winner,
                        decision="REJECTED_DIVERSIFICATION",
                        reject_reason=d_reason,
                        amount=getattr(winner, "_amount", 0.0),
                        stage=stage,
                        strategy=self.executor._strategy_snapshot(),
                    )
                    self.bot.stats["rejected_diversification"] = (
                        self.bot.stats.get("rejected_diversification", 0) + 1
                    )
                    continue

            log.info(explain_score(winner, threshold=session_threshold))
            amount = getattr(winner, "_amount", 0.0)
            stage = getattr(winner, "_stage", "initial")
            if self.bot.compensation_pending and stage == "initial":
                amount, exp_profit = self.executor._compute_compensation_amount(
                    winner.payout, self.bot.last_closed_amount,
                )
                log.info(
                    "🔁 COMPENSACIÓN activa — monto dinámico $%.2f | payout=%d%% | recup=%.2f (est. neto=%.2f)",
                    amount,
                    winner.payout,
                    self.bot.last_closed_amount,
                    exp_profit,
                )
            outcome = "DRY_RUN" if self.bot.dry_run else "PENDING"
            cid = journal.log_candidate(
                winner,
                decision="ACCEPTED",
                amount=amount,
                stage=stage,
                outcome=outcome,
                strategy=self.executor._strategy_snapshot(),
            )
            accepted_this_scan += 1
            winner._journal_cid = cid  # type: ignore[attr-defined]
            entered = await self.executor.enter_trade(
                winner.asset, winner.direction, amount,
                winner.zone,
                f"SCORE={winner.score:.1f}/100 | {winner.direction.upper()} "
                f"en {winner.asset} payout={winner.payout}%",
                stage,
                journal_cid=cid,
                signal_ts=getattr(winner, "_signal_ts_1m", winner.candles[-1].ts if winner.candles else None),
                strategy_origin=getattr(winner, "_strategy_origin", "STRAT-A"),
                duration_sec=DURATION_SEC,
                payout=winner.payout,
                score_original=winner.score,
            )
            if entered:
                await sleep_with_inline_countdown(COOLDOWN_BETWEEN_ENTRIES, "⏳ Cooldown post-orden")

        self.bot.stats["skipped"] += len(rejected)
        self.executor._record_scan_acceptances(accepted_this_scan)

    async def scan_all(self) -> None:
        """
        Escanea todos los activos, puntúa cada candidato con el sensor
        matemático y opera SOLO el mejor (o los N mejores si MAX_ENTRIES_CYCLE > 1).
        Si ninguno supera el umbral dinámico de score, no opera ese ciclo.
        """
        if await self.executor.refresh_balance_and_risk():
            return

        assets = await self._scan_phase_prepare()
        if not assets:
            return

        cycle = await self._scan_phase_prefetch(assets)
        eval_result = await self._scan_phase_evaluate_assets(cycle)
        self.bot.last_scan_candidates = eval_result.get("candidates", [])
        await self._scan_phase_select_execute(eval_result, assets)

