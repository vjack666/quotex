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
    FORCE_EXECUTE_STRONG_BREAKOUT,
    H1_CANDLES_LOOKBACK,
    H1_CONFIRM_ENABLED,
    H1_FETCH_TIMEOUT_SEC,
    H1_TF_SEC,
    MAX_CONCURRENT_TRADES,
    MAX_CONSOLIDATION_MIN,
    MIN_CONSOLIDATION_BARS,
    MIN_PAYOUT,
    ORDER_BLOCK_CANDLES,
    ORDER_BLOCK_TF_SEC,
    REBOUND_MIN_STRENGTH_CALL,
    REJECTION_CANDLE_MIN_BODY,
    SCAN_MAX_ASSETS_PER_CYCLE,
    SCAN_PROGRESS_EVERY,
    STRICT_PATTERN_CHECK,
    STRAT_B_CAN_TRADE,
    STRAT_B_DURATION_SEC,
    STRAT_B_LOG_TOP_N,
    STRAT_B_MIN_CONFIDENCE,
    STRAT_B_MIN_CONFIDENCE_EARLY,
    STRAT_B_PREVIEW_MIN_CONF,
    TF_5M,
    ZONE_AGE_BREAKOUT_MIN,
    ZONE_AGE_REBOUND_MIN,
    ZONE_MIN_AGE_MIN,
)
from connection import fetch_candles_with_retry, get_open_assets
from parallel_fetch import fetch_candles_parallel
from loop_utils import sleep_with_inline_countdown
from entry_scorer import CandidateEntry, explain_score, score_candidate, select_best
from models import Candle, ConsolidationZone, PendingReversal
from strat_a import (
    broke_above,
    broke_below,
    compute_dynamic_range,
    compute_ma_state,
    detect_consolidation,
    detect_order_blocks,
    infer_h1_trend,
    is_high_volume_break,
    is_put_pattern_blacklisted,
    price_at_ceiling,
    price_at_floor,
    required_rebound_strength,
    score_ma,
    score_order_blocks,
    validate_rejection_candle,
)
from strat_b import evaluate_strat_b, find_strong_support_2m
from trade_journal import get_journal

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


    def _compute_ma_state(self, asset: str, candles_5m: List[Candle]):
        prev = self.bot.ma_state_by_asset.get(asset)
        state = compute_ma_state(candles_5m, prev)
        if state is not None:
            self.bot.ma_state_by_asset[asset] = state
        return state

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

            req_strength = self._required_rebound_strength(pr.proposed_direction)
            candle_valid, candle_fail_reason = self._validate_rejection_candle(
                candles_1m,
                pr.proposed_direction,
                REJECTION_CANDLE_MIN_BODY,
            )

            if self._is_put_pattern_blacklisted(pr.proposed_direction, pattern_name):
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
                candidate._reversal_pattern = pattern_name  # type: ignore[attr-defined]
                candidate._reversal_strength = strength  # type: ignore[attr-defined]
                candidate._reversal_confirms = confirms  # type: ignore[attr-defined]
                candidate._entry_mode = pr.entry_mode  # type: ignore[attr-defined]
                candidate._signal_ts_1m = candles_1m[-1].ts if candles_1m else None  # type: ignore[attr-defined]
                amount, _ = self._compute_initial_amount(payout)
                candidate._amount = amount  # type: ignore[attr-defined]
                candidate._stage = "initial"  # type: ignore[attr-defined]
                candidate._from_pending = True  # type: ignore[attr-defined]
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
    async def scan_all(self) -> None:
        """
        Escanea todos los activos, puntúa cada candidato con el sensor
        matemático y opera SOLO el mejor (o los N mejores si MAX_ENTRIES_CYCLE > 1).
        Si ninguno supera el umbral dinámico de score, no opera ese ciclo.
        """
        if await self.executor.refresh_balance_and_risk():
            return

        assets = await get_open_assets(self.bot.client, MIN_PAYOUT)
        if not assets:
            log.warning("No se obtuvieron activos OTC disponibles.")
            return

        total_assets_available = len(assets)
        if SCAN_MAX_ASSETS_PER_CYCLE > 0 and len(assets) > SCAN_MAX_ASSETS_PER_CYCLE:
            assets = assets[:SCAN_MAX_ASSETS_PER_CYCLE]
            log.info(
                "⚡ Aceleración scan: %d/%d activos (top payout)",
                len(assets),
                total_assets_available,
            )

        self.bot.stats["scans"] += 1
        accepted_this_scan = 0
        self.executor._cleanup_asset_blacklist()
        log.info("═══ SCAN #%d | %d activos payout≥%d%% ═══",
                 self.bot.stats["scans"], len(assets), MIN_PAYOUT)

        # 1) Revisar martingalas de trades abiertos
        for sym in list(self.bot.trades.keys()):
            entered = await self.executor._check_martin(sym)
            if entered:
                await sleep_with_inline_countdown(COOLDOWN_BETWEEN_ENTRIES, "⏳ Cooldown post-orden")
            await asyncio.sleep(0.2)

        # Si hay operaciones abiertas: seguir escaneando para vigilar oportunidades.
        # El bloque de ejecución (paso 5) impedirá abrir nuevas entradas si se alcanzó
        # MAX_CONCURRENT_TRADES; los candidatos buenos se guardan en watched_candidates.
        if self.bot.trades:
            activos_abiertos = ', '.join(self.bot.trades.keys())
            log.info(
                "👁 Operación activa [%s] — escaneando igual para vigilar oportunidades.",
                activos_abiertos,
            )
        else:
            # Sin trades activos: limpiar vigilados viejos (> 5 min) para no ensuciar el log.
            if self.bot.watched_candidates:
                stale = [a for a, (_, ts) in self.bot.watched_candidates.items() if time.time() - ts > 300]
                for a in stale:
                    del self.bot.watched_candidates[a]

        # 2) Recolectar candidatos sin trade abierto
        candidates: list[CandidateEntry] = []
        cycle_ob_summary: dict[str, str] = {}
        cycle_ma_summary: dict[str, str] = {}
        strat_b_total = 0
        strat_b_insufficient = 0
        strat_b_timeout = 0  # fetches 1m que devolvieron 0 velas (timeout)
        strat_b_hits: list[tuple[str, int, float]] = []
        strat_b_nearmiss: list[tuple[str, int, float, str]] = []
        # Acumuladores para pending_reversals (populados durante el loop).
        candles_1m_collected: dict[str, list] = {}
        last_prices_collected: dict[str, float] = {}

        symbols = [sym for sym, _ in assets]
        fetch_t0 = time.monotonic()
        candles_5m_by_asset = await fetch_candles_parallel(
            self.bot.client,
            symbols,
            TF_5M,
            CANDLES_LOOKBACK,
            concurrency=CANDLE_FETCH_CONCURRENCY,
            timeout_sec=CANDLE_FETCH_TIMEOUT_SEC,
        )
        candles_1m_by_asset = await fetch_candles_parallel(
            self.bot.client,
            symbols,
            60,
            36,
            concurrency=CANDLE_FETCH_CONCURRENCY,
            timeout_sec=CANDLE_FETCH_1M_TIMEOUT_SEC,
        )
        scan_fetch_elapsed_ms = int((time.monotonic() - fetch_t0) * 1000)
        log.info(
            "⚡ Prefetch velas: scan_fetch_elapsed_ms=%d | activos=%d | concurrency=%d",
            scan_fetch_elapsed_ms,
            len(symbols),
            CANDLE_FETCH_CONCURRENCY,
        )

        # Decrementar contadores de activos en cooldown post-fallo.
        expired_failed = [a for a, n in self.bot.failed_assets.items() if n <= 1]
        for a in expired_failed:
            del self.bot.failed_assets[a]
        for a in self.bot.failed_assets:
            self.bot.failed_assets[a] -= 1

        for idx, (sym, payout) in enumerate(assets, start=1):
            if SCAN_PROGRESS_EVERY > 0 and (idx == 1 or idx % SCAN_PROGRESS_EVERY == 0 or idx == len(assets)):
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
                log.warning("⏭ %s: blacklist temporal activa (%.1f min restantes)", sym, remain_min)
                self.bot.stats["skipped"] += 1
                continue

            # Skip activos que fallaron recientemente en place_order().
            if sym in self.bot.failed_assets:
                log.info("⏭ %s skipped — falló en ciclo anterior (%d ciclos restantes)",
                         sym, self.bot.failed_assets[sym])
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
            strat_b_reason = str(strat_b_info.get("reason", f"{strat_b_signal_type or 'Señal'} detectado") or "Señal detectada")
            is_early_wyckoff = strat_b_signal_type.startswith("wyckoff_early")
            strat_b_required_conf = STRAT_B_MIN_CONFIDENCE_EARLY if is_early_wyckoff else STRAT_B_MIN_CONFIDENCE
            if strat_b_signal:
                self.bot.stats["strat_b_signals"] += 1
                strat_b_hits.append((sym, payout, strat_b_conf, strat_b_direction, strat_b_signal_type))
            else:
                if strat_b_conf >= STRAT_B_PREVIEW_MIN_CONF:
                    strat_b_nearmiss.append((sym, payout, strat_b_conf, strat_b_reason))

            # Modo opcional: STRAT-B puede abrir operación por sí sola.
            if (
                STRAT_B_CAN_TRADE
                and strat_b_signal
                and strat_b_conf >= strat_b_required_conf
                and len(self.bot.trades) < MAX_CONCURRENT_TRADES
            ):
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

                # Registrar STRAT-B en caja negra (journal) antes de enviar la orden.
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

            # STRAT-A requiere historial 5m mínimo para consolidación.
            if len(candles) < MIN_CONSOLIDATION_BARS + 2:
                continue

            dynamic_max_range, atr_pct, dynamic_touch_tolerance = compute_dynamic_range(candles)

            zone = detect_consolidation(candles, max_range_pct=dynamic_max_range)
            if zone is None:
                self.bot.zones.pop(sym, None)
                continue

            zone.asset = sym

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
                    continue
                zone.detected_at = existing.detected_at
            self.bot.zones[sym] = zone

            last = candles[-1]
            price = last.close

            # ── Guardia de precio contra contaminación cruzada de pyquotex ──
            # Capa 1: precio fuera del rango de zona ±15% → descarte.
            _zone_mid = (zone.ceiling + zone.floor) / 2.0
            if _zone_mid > 0 and not (zone.floor * 0.85 <= price <= zone.ceiling * 1.15):
                _last_valid = self.bot.last_known_price.get(sym)
                _last_txt = f" (último válido: {_last_valid:.5f})" if _last_valid else ""
                log.warning(
                    "⚠ %s: precio %.5f contaminado — fuera de zona [%.5f, %.5f]%s",
                    sym, price, zone.floor * 0.85, zone.ceiling * 1.15, _last_txt,
                )
                self.bot.stats["skipped"] += 1
                continue

            # Capa 2: variación > 5% respecto al último precio válido conocido → descarte.
            _last_valid = self.bot.last_known_price.get(sym)
            if _last_valid and _last_valid > 0:
                _delta_pct = abs(price - _last_valid) / _last_valid
                if _delta_pct > 0.05:
                    log.warning(
                        "⚠ %s: precio %.5f contaminado — cambio de %.1f%% vs último válido %.5f",
                        sym, price, _delta_pct * 100, _last_valid,
                    )
                    self.bot.stats["skipped"] += 1
                    continue

            # Precio válido — actualizar registro.
            self.bot.last_known_price[sym] = price
            last_prices_collected[sym] = price
            candles_ob = await fetch_candles_with_retry(
                self.bot.client,
                sym,
                ORDER_BLOCK_TF_SEC,
                ORDER_BLOCK_CANDLES,
                timeout_sec=CANDLE_FETCH_TIMEOUT_SEC,
                retries=1,
            )
            ob_tf_label = "3m"
            if len(candles_ob) < 6:
                candles_ob = candles
                ob_tf_label = "5m_fallback"
            blocks = detect_order_blocks(candles_ob)
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

            direction: Optional[str] = None
            amount, _ = self.executor._compute_initial_amount(payout)
            stage = "initial"
            entry_mode = "none"
            breakout_strength_ok = False

            if price_at_ceiling(price, zone.ceiling, dynamic_touch_tolerance):
                direction = "put"
                entry_mode = "rebound_ceiling"
            elif price_at_floor(price, zone.floor, dynamic_touch_tolerance):
                direction = "call"
                entry_mode = "rebound_floor"
            elif broke_above(last, zone.ceiling) and is_high_volume_break(last, candles):
                # Ruptura con fuerza hacia arriba: compra inmediata (momentum).
                direction = "call"
                stage = "breakout"
                entry_mode = "breakout_above"
                breakout_strength_ok = True
                log.info(
                    "🟢 %s: BROKEN_ABOVE techo=%.5f | cierre=%.5f cuerpo=%.5f → CALL inmediato",
                    sym, zone.ceiling, last.close, last.body,
                )
                expired_zone_id = get_journal().log_expired_zone(
                    asset=sym,
                    expiry_reason="BROKEN_ABOVE",
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
                    reason="BROKEN_ABOVE",
                    expired_zone_id=expired_zone_id,
                    zone=zone,
                    last=last,
                    candles_1m_used=candles_1m,
                    candles_5m_used=candles,
                )
                self._schedule_followup_capture(sym, capture_file)
                log.info("🧾 %s: snapshot BROKEN_ABOVE guardado -> %s", sym, capture_file.name)
                self.bot.broken_zones[sym] = time.time()
            elif broke_below(last, zone.floor) and is_high_volume_break(last, candles):
                # Ruptura con fuerza hacia abajo: venta inmediata (momentum).
                direction = "put"
                stage = "breakout"
                entry_mode = "breakout_below"
                breakout_strength_ok = True
                log.info(
                    "🔴 %s: BROKEN_BELOW piso=%.5f | cierre=%.5f cuerpo=%.5f → PUT inmediato",
                    sym, zone.floor, last.close, last.body,
                )
                expired_zone_id = get_journal().log_expired_zone(
                    asset=sym,
                    expiry_reason="BROKEN_BELOW",
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
                    reason="BROKEN_BELOW",
                    expired_zone_id=expired_zone_id,
                    zone=zone,
                    last=last,
                    candles_1m_used=candles_1m,
                    candles_5m_used=candles,
                )
                self._schedule_followup_capture(sym, capture_file)
                log.info("🧾 %s: snapshot BROKEN_BELOW guardado -> %s", sym, capture_file.name)
                self.bot.broken_zones[sym] = time.time()

            if direction is None:
                self.bot.stats["skipped"] += 1
                continue

            # Si la ruptura ya fue validada con fuerza (BROKEN_ABOVE/BELOW),
            # no bloquearla por antigüedad de zona para mantener el modo "inmediato".
            skip_zone_age_check = stage == "breakout" and breakout_strength_ok
            min_zone_age = ZONE_AGE_BREAKOUT_MIN if stage == "breakout" else ZONE_AGE_REBOUND_MIN
            if (not skip_zone_age_check) and zone.age_minutes < min_zone_age:
                log.info(
                    "⏭ %s: zona demasiado joven (%.1fmin < %dmin) — skip",
                    sym,
                    zone.age_minutes,
                    min_zone_age,
                )
                self.bot.stats["rejected_young_zone"] += 1
                self.bot.stats["skipped"] += 1
                continue

            # Confirmación de reversión para entradas por rebote en techo/piso.
            pattern_name = "none"
            strength = 0.0
            confirms = False
            if len(candles_1m) >= 3:
                signal_1m = detect_reversal_pattern(candles_1m, direction)
                pattern_name = signal_1m.pattern_name
                strength = signal_1m.strength
                confirms = signal_1m.confirms_direction

            if entry_mode.startswith("rebound"):
                side = "techo" if entry_mode == "rebound_ceiling" else "piso"
                
                # Validar forma de la vela 1m que tocó piso/techo
                candle_valid, candle_fail_reason = validate_rejection_candle(
                    candles_1m, direction, REJECTION_CANDLE_MIN_BODY
                )
                
                if not candle_valid:
                    # Vela no confirma rebote → espera activa
                    if sym not in self.bot.pending_reversals:
                        self.bot.pending_reversals[sym] = PendingReversal(
                            asset=sym,
                            zone=zone,
                            proposed_direction=direction,
                            conflicting_pattern=candle_fail_reason,
                            detected_at=datetime.now(tz=BROKER_TZ),
                            entry_mode=entry_mode,
                            payout=payout,
                        )
                        log.info(
                            "⏳ %s: vela 1m no confirma rebote en %s (%s) — esperando confirmación (1/%d)",
                            sym, side, candle_fail_reason,
                            self.bot.pending_reversals[sym].max_wait_scans,
                        )
                    else:
                        # Ya existe: actualizar razón de rechazo y zona
                        self.bot.pending_reversals[sym].conflicting_pattern = candle_fail_reason
                        self.bot.pending_reversals[sym].zone = zone
                    self.bot.stats["skipped"] += 1
                    continue
                
                # Vela confirma dirección — validar patrón de reversión como antes
                req_strength = required_rebound_strength(direction)
                if is_put_pattern_blacklisted(direction, pattern_name):
                    if sym not in self.bot.pending_reversals:
                        self.bot.pending_reversals[sym] = PendingReversal(
                            asset=sym,
                            zone=zone,
                            proposed_direction=direction,
                            conflicting_pattern=pattern_name,
                            detected_at=datetime.now(tz=BROKER_TZ),
                            entry_mode=entry_mode,
                            payout=payout,
                        )
                    else:
                        self.bot.pending_reversals[sym].conflicting_pattern = pattern_name
                        self.bot.pending_reversals[sym].zone = zone
                    log.info(
                        "↪ %s: patrón %s en lista negra para PUT — skip",
                        sym,
                        pattern_name,
                    )
                    self.bot.stats["skipped"] += 1
                    continue
                pattern_ok = confirms and strength >= req_strength

                if not pattern_ok:
                    if STRICT_PATTERN_CHECK and pattern_name != "none" and (not confirms) and strength >= 0.65:
                        log.info(
                            "⛔ %s: STRICT_PATTERN_CHECK activo — descarte antes de score por patrón contradictorio confirmado %s %.2f en %s",
                            sym,
                            pattern_name,
                            strength,
                            side,
                        )
                        self.bot.stats["skipped"] += 1
                        continue
                    if direction == "put":
                        if sym not in self.bot.pending_reversals:
                            self.bot.pending_reversals[sym] = PendingReversal(
                                asset=sym,
                                zone=zone,
                                proposed_direction=direction,
                                conflicting_pattern=f"{pattern_name}:{strength:.2f}",
                                detected_at=datetime.now(tz=BROKER_TZ),
                                entry_mode=entry_mode,
                                payout=payout,
                            )
                        if pattern_name == "none":
                            log.info(
                                "↪ %s: PUT requiere patrón ≥%.2f, detectado %s %.2f (%s)",
                                sym,
                                req_strength,
                                pattern_name,
                                strength,
                                explain_no_pattern_reason(candles_1m, direction),
                            )
                        else:
                            log.info(
                                "↪ %s: PUT requiere patrón ≥%.2f, detectado %s %.2f",
                                sym,
                                req_strength,
                                pattern_name,
                                strength,
                            )
                        self.bot.stats["skipped"] += 1
                        continue
                    if pattern_name != "none" and not confirms:
                        # Patrón contradictorio: registrar para espera activa.
                        if sym not in self.bot.pending_reversals:
                            self.bot.pending_reversals[sym] = PendingReversal(
                                asset=sym,
                                zone=zone,
                                proposed_direction=direction,
                                conflicting_pattern=pattern_name,
                                detected_at=datetime.now(tz=BROKER_TZ),
                                entry_mode=entry_mode,
                                payout=payout,
                            )
                            log.info(
                                "⏳ %s: patrón conflictivo (%s) en %s — "
                                "esperando reversión (intento 1/%d)",
                                sym, pattern_name, side,
                                self.bot.pending_reversals[sym].max_wait_scans,
                            )
                        else:
                            # Ya existe: actualizar patrón conflictivo y zona.
                            self.bot.pending_reversals[sym].conflicting_pattern = pattern_name
                            self.bot.pending_reversals[sym].zone = zone
                    else:
                        log.info(
                            "↪ %s: rebote en %s sin patrón suficiente (%s %.2f) — esperando confirmación.",
                            sym, side, pattern_name, strength,
                        )
                    self.bot.stats["skipped"] += 1
                    continue

            if H1_CONFIRM_ENABLED:
                h1_candles = await fetch_candles_with_retry(
                    self.bot.client,
                    sym,
                    H1_TF_SEC,
                    H1_CANDLES_LOOKBACK,
                    timeout_sec=H1_FETCH_TIMEOUT_SEC,
                )
                h1_trend = infer_h1_trend(h1_candles)
                if (direction == "put" and h1_trend == "bullish") or (
                    direction == "call" and h1_trend == "bearish"
                ):
                    self.bot.stats["filtered_sensor"] += 1
                    continue
            else:
                h1_candles = await fetch_candles_with_retry(
                    self.bot.client,
                    sym,
                    H1_TF_SEC,
                    H1_CANDLES_LOOKBACK,
                    timeout_sec=H1_FETCH_TIMEOUT_SEC,
                )

            candidate = CandidateEntry(
                asset=sym,
                payout=payout,
                zone=zone,
                direction=direction,
                candles=candles,
            )
            candidate.candles_h1 = h1_candles

            candidate._reversal_pattern = pattern_name  # type: ignore[attr-defined]
            candidate._reversal_strength = strength  # type: ignore[attr-defined]
            candidate._reversal_confirms = confirms  # type: ignore[attr-defined]
            candidate._entry_mode = entry_mode  # type: ignore[attr-defined]
            candidate._signal_ts_1m = candles_1m[-1].ts if candles_1m else None  # type: ignore[attr-defined]

            candidate._amount = amount  # type: ignore[attr-defined]
            candidate._stage = stage  # type: ignore[attr-defined]
            candidate._ma_state = ma_state  # type: ignore[attr-defined]
            candidate._order_blocks = blocks  # type: ignore[attr-defined]
            candidate._ob_tf = ob_tf_label  # type: ignore[attr-defined]
            candidate._force_execute = bool(
                FORCE_EXECUTE_STRONG_BREAKOUT and stage == "breakout" and breakout_strength_ok
            )  # type: ignore[attr-defined]

            score_candidate(candidate)

            # Calcular body_ratio para log
            body_ratio = 0.0
            if len(candles_1m) > 0:
                last_1m = candles_1m[-1]
                if last_1m.range > 0:
                    body_ratio = abs(last_1m.close - last_1m.open) / last_1m.range

            # Modificador por confirmación 1m.
            if confirms and strength >= 0.60:
                candidate.score = round(candidate.score + 8.0, 1)
                candidate.score_breakdown["reversal_bonus"] = 8.0
                log.debug(
                    "1m_pattern=%s strength=%.2f body_ratio=%.0f%% +8pts reversal_bonus",
                    pattern_name, strength, body_ratio * 100,
                )
            elif confirms and strength >= REBOUND_MIN_STRENGTH_CALL:
                candidate.score = round(candidate.score + 5.0, 1)
                candidate.score_breakdown["reversal_bonus"] = 5.0
                log.debug(
                    "1m_pattern=%s strength=%.2f body_ratio=%.0f%% +5pts reversal_bonus",
                    pattern_name, strength, body_ratio * 100,
                )
            elif (not confirms) and pattern_name != "none":
                candidate.score = round(candidate.score - 15.0, 1)
                candidate.score_breakdown["reversal_penalty"] = -15.0
                log.debug(
                    "1m_pattern=%s strength=%.2f body_ratio=%.0f%% -15pts reversal_penalty",
                    pattern_name, strength, body_ratio * 100,
                )
            elif pattern_name == "none":
                # Sin patrón detectado: vela confirma dirección (ya validada arriba)
                candidate.score = round(candidate.score - 10.0, 1)
                candidate.score_breakdown["weak_confirmation"] = -10.0
                log.debug(
                    "1m_pattern=%s strength=%.2f body_ratio=%.0f%% -10pts weak_confirmation",
                    pattern_name, strength, body_ratio * 100,
                )

            if stage == "breakout" and breakout_strength_ok:
                candidate.score = round(candidate.score + 6.0, 1)
                candidate.score_breakdown["breakout_bonus"] = 6.0

            ob_points, ob_info = score_order_blocks(
                direction=direction,
                price=price,
                blocks=blocks,
                avg_body=ma_state.avg_body if ma_state else 1e-9,
            )
            if ob_points != 0:
                candidate.score = round(candidate.score + ob_points, 1)
                candidate.score_breakdown["order_block"] = round(ob_points, 1)
            candidate._ob_info = f"tf={ob_tf_label} | {ob_info}"  # type: ignore[attr-defined]

            ma_points, ma_info = score_ma(direction, ma_state)
            if ma_points != 0:
                candidate.score = round(candidate.score + ma_points, 1)
                candidate.score_breakdown["ma_filter"] = round(ma_points, 1)
            candidate._ma_info = ma_info  # type: ignore[attr-defined]

            log.info(
                "[OB] %s tf=%s dir=%s ajuste=%+.1f | %s",
                sym,
                ob_tf_label,
                direction.upper(),
                ob_points,
                ob_info,
            )
            log.info(
                "[MA] %s dir=%s ajuste=%+.1f | %s",
                sym,
                direction.upper(),
                ma_points,
                ma_info,
            )

            candidates.append(candidate)
            await asyncio.sleep(0.30)  # breve pausa para separar respuestas WebSocket

        # Resumen STRAT-B por ciclo (evita spam por activo).
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

        # 3) Procesar reversiones pendientes (espera activa post-conflicto).
        if self.bot.pending_reversals:
            assets_payout_map = dict(assets)
            pending_confirmed = await self._process_pending_reversals(
                assets_payout_map,
                candles_1m_collected,
                last_prices_collected,
            )
            if pending_confirmed:
                log.info("⏳→✅ %d candidato(s) de pending_reversals agregados al ciclo.", len(pending_confirmed))
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

        # 3) Log de candidatos
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
            rng_pips = (c.zone.ceiling - c.zone.floor) * 10_000
            status = "✅" if c.score >= session_threshold else "❌"
            decision_tag = "ACEPTADO" if c.score >= session_threshold else "RECHAZADO"
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
                session_threshold,
                decision_tag,
            )
            log.info("      [OB] %s", getattr(c, "_ob_info", "sin datos"))
            log.info("      [MA] %s", getattr(c, "_ma_info", "sin datos"))

        # 4) Seleccionar mejores
        selected, rejected = select_best(candidates, threshold=session_threshold)

        forced_breakouts = [c for c in candidates if bool(getattr(c, "_force_execute", False))]
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

        # Registrar rechazados por score
        for c in rejected:
            journal.log_candidate(
                c,
                decision="REJECTED_SCORE",
                reject_reason=f"score={c.score:.1f} < umbral dinámico {session_threshold}",
                amount=getattr(c, "_amount", 0.0),
                stage=getattr(c, "_stage", "initial"),
                strategy=self.executor._strategy_snapshot(),
            )
            # Telemetría de antigüedad de zona
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

        log.info("[STRAT-A] 🏆 Mejor(es) seleccionado(s): %d de %d candidatos",
                 len(selected), len(candidates))

        # 5) Ejecutar seleccionados
        if len(self.bot.trades) >= MAX_CONCURRENT_TRADES:
            log.info(
                "🛑 Límite alcanzado (%d/%d). Se posponen nuevas entradas.",
                len(self.bot.trades), MAX_CONCURRENT_TRADES,
            )
            # Guardar el mejor candidato como "vigilado" para entrar cuando cierre el trade activo.
            best_watched = max(selected, key=lambda x: x.score)
            self.bot.watched_candidates[best_watched.asset] = (best_watched, time.time())
            rev_w = getattr(best_watched, "_reversal_pattern", "none")
            log.info(
                "👁  VIGILADO: %s %s score=%.1f/100 payout=%d%% 1m=%s — "
                "se intentará entrar en cuanto cierre la operación activa.",
                best_watched.direction.upper(), best_watched.asset,
                best_watched.score, best_watched.payout, rev_w,
            )
            # Registrar rechazados por límite
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
            log.info(explain_score(winner, threshold=session_threshold))
            amount = getattr(winner, "_amount", 0.0)
            stage = getattr(winner, "_stage", "initial")
            # Si hay compensación pendiente por LOSS anterior, escalar el monto
            if self.bot.compensation_pending and stage == "initial":
                amount, exp_profit = self.executor._compute_compensation_amount(winner.payout, self.bot.last_closed_amount)
                log.info(
                    "🔁 COMPENSACIÓN activa — monto dinámico $%.2f | payout=%d%% | recup=%.2f (est. neto=%.2f)",
                    amount,
                    winner.payout,
                    self.bot.last_closed_amount,
                    exp_profit,
                )
            # Pre-registrar como ACCEPTED (outcome se actualiza después)
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
                strategy_origin="STRAT-A",
                duration_sec=DURATION_SEC,
                payout=winner.payout,
                score_original=winner.score,
            )
            if entered:
                await sleep_with_inline_countdown(COOLDOWN_BETWEEN_ENTRIES, "⏳ Cooldown post-orden")

        self.bot.stats["skipped"] += len(rejected)
        self.executor._record_scan_acceptances(accepted_this_scan)
