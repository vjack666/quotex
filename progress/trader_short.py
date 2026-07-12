"""Trader corto STRAT-F (sortea el host-kill del sandbox).

Hace UN ciclo compacto y SALE antes de que el host mate el WebSocket:
1. Reconcilia las PENDING de ciclos anteriores (client.get_result -> WIN/LOSS).
2. Evalua STRAT-F en ~10 activos (fetch en paralelo, concurrencia acotada).
3. Coloca 1 orden en PRACTICE con la mejor senal que pase STRAT_F_MIN_SCORE.
4. Registra PENDING con el order_id y SALE.

Al relanzarse (autopilot cada ~3 min) reconcilia la orden anterior. Asi el bot
acumula operaciones reales en la cuenta demo aunque el sandbox mate el proceso.

Reusa: connection.{connect_with_retry,fetch_candles_with_retry,get_open_assets,
place_order}, strat_fractal.evaluate_strat_f, entry_scorer.score_candidate,
massaniello_risk.MassanielloRiskManager, trade_journal, models.CandidateEntry.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import (  # type: ignore
    MIN_PAYOUT, TF_5M, TF_15M, STRAT_F_MIN_SCORE, STRAT_F_MIN_PAYOUT,
    DURATION_SEC, MASSANIELLO_OPERATIONS, MASSANIELLO_EXPECTED_WINS,
    SESSION_MAX_MIN,
)
from connection import (  # type: ignore
    connect_with_retry, fetch_candles_with_retry, get_open_assets, place_order,
)
from pyquotex.stable_api import Quotex  # type: ignore
from strat_fractal import evaluate_strat_f  # type: ignore
from models import CandidateEntry, SignalMode  # type: ignore
from entry_scorer import score_candidate  # type: ignore
from massaniello_risk import MassanielloRiskManager  # type: ignore
from massaniello_engine import calculate_stake  # type: ignore
from trade_journal import get_journal  # type: ignore
from config import BROKER_TZ  # type: ignore

N_ASSETS = 3
CONCURRENCY = 3


def _build_candidate(sym, payout, ev) -> CandidateEntry:
    f_candidate = CandidateEntry(
        asset=sym,
        payout=payout,
        zone=ev.zone,
        direction=ev.direction,
        candles=[],
        score=round(ev.strength * 100.0, 1),
        mode=SignalMode.REBOUND,
        score_breakdown={
            "compression": 0.0,
            "fractal": round(ev.strength * 35.0, 2),
            "context": round(ev.strength * 25.0, 2),
            "payout": round(min(20.0, (payout / 95.0) * 20.0), 2),
        },
    )
    setattr(f_candidate, "_strategy_origin", "STRAT-F")
    setattr(f_candidate, "_reversal_pattern", ev.pattern_name)
    setattr(f_candidate, "_reversal_strength", ev.strength)
    setattr(f_candidate, "_signal_ts_1m", None)
    setattr(f_candidate, "_amount", 1.0)
    setattr(f_candidate, "_stage", "initial")
    score_candidate(f_candidate)
    return f_candidate


async def _reconcile(client, journal) -> None:
    """Marca WIN/LOSS de las PENDING de hoy consultando get_result."""
    if journal._conn is None:
        return
    rows = journal._conn.execute(
        "SELECT id, order_id FROM candidates "
        "WHERE outcome='PENDING' AND decision='ACCEPTED'"
    ).fetchall()
    for rid, oid in rows:
        oid = str(oid or "").strip()
        if not oid or oid.startswith("DRY-") or oid in {"BROKER_NO_ID"}:
            continue
        try:
            status, payload = await client.get_result(oid)
            if status == "win":
                outcome = "WIN"
                profit = float((payload or {}).get("profitAmount", 0) or 0)
            elif status == "loss":
                outcome = "LOSS"
                profit = float((payload or {}).get("profitAmount", 0) or 0)
            else:
                continue
            journal._conn.execute(
                "UPDATE candidates SET outcome=?, profit=?, closed_at=? "
                "WHERE id=? AND outcome='PENDING'",
                (outcome, profit, datetime.now(tz=BROKER_TZ).isoformat(), rid),
            )
            print(f"[reconcile] #{rid} {oid} -> {outcome} (+{profit:.2f})")
        except Exception as ex:  # noqa: BLE001
            print(f"[reconcile] #{rid} {oid} error: {ex}")
    journal._conn.commit()


async def _eval_one(client, sym, payout, sem) -> tuple:
    async with sem:
        c15 = await fetch_candles_with_retry(client, sym, TF_15M, 20, timeout_sec=10)
        c5 = await fetch_candles_with_retry(client, sym, TF_5M, 16, timeout_sec=8)
        c1 = await fetch_candles_with_retry(client, sym, 60, 24, timeout_sec=8)
    if len(c15) < 6 or len(c5) < 5 or len(c1) < 3:
        return None
    ev = evaluate_strat_f(c15, c5, c1, payout=payout)
    if not (ev.has_signal and ev.direction and ev.zone):
        return None
    cand = _build_candidate(sym, payout, ev)
    if cand.score < STRAT_F_MIN_SCORE:
        return None
    return (cand, ev)


async def main() -> None:
    email = os.getenv("QUOTEX_EMAIL", "")
    password = os.getenv("QUOTEX_PASSWORD", "")
    if not email or not password:
        print("ERROR: faltan credenciales en .env")
        return

    client = Quotex(email=email, password=password)
    ok, reason = await connect_with_retry(client)
    if not ok:
        print(f"ERROR conexion: {reason}")
        return

    journal = get_journal()
    # 1) reconciliar PENDING previas
    await _reconcile(client, journal)

    # balance para Massaniello
    try:
        balance = float(await client.get_balance())
    except Exception:
        balance = 100.0

    # 2) evaluar activos
    assets = await get_open_assets(client, min_payout=MIN_PAYOUT)
    assets = [a for a in assets if a[1] >= STRAT_F_MIN_PAYOUT][:N_ASSETS]
    print(f"[trader] {len(assets)} activos evaluados (payout>={STRAT_F_MIN_PAYOUT}%)")
    sem = asyncio.Semaphore(CONCURRENCY)
    results = await asyncio.gather(*[_eval_one(client, s, p, sem) for s, p in assets])
    signals = [r for r in results if r is not None]
    if not signals:
        print("[trader] sin senales STRAT-F esta ronda")
        await client.close()
        return

    best = max(signals, key=lambda x: x[0].score)
    cand, ev = best
    print(f"[trader] MEJOR: {cand.asset} {cand.direction} score={cand.score:.1f} "
          f"strength={ev.strength*100:.0f} ctx={ev.m15_context}/{ev.m5_event}")

    # 3) monto Massaniello
    mr = MassanielloRiskManager(
        operations=MASSANIELLO_OPERATIONS,
        expected_wins=MASSANIELLO_EXPECTED_WINS,
        session_max_min=SESSION_MAX_MIN,
    )
    mr.set_balance(balance)
    if not mr.can_enter():
        print(f"[trader] Massaniello no permite entrada (wins={mr.wins} "
              f"losses={mr.losses} played={mr._played()})")
        await client.close()
        return
    try:
        from massaniello_engine import Settings as MS, effective_profit
        prof = effective_profit(float(cand.payout) / 100.0)
        settings = MS(
            initial_balance=max(balance, 1.0),
            operations=mr.operations,
            expected_itm=mr.expected_wins,
            profit=prof,
            mode="normal",
            system_mode="massaniello",
        )
        amount = calculate_stake(
            settings=settings,
            capital=max(balance, 1.0),
            wins=mr.wins,
            losses=mr.losses,
        )
        amount = float(amount) if amount is not None else 1.0
    except Exception as ex:  # noqa: BLE001
        print(f"[trader] stake fallback $1 ({ex})")
        amount = 1.0
    amount = max(amount, 1.0)
    print(f"[trader] monto Massaniello: ${amount:.2f}")

    # 4) colocar orden y SALIR (no esperar expiracion)
    # Reconexion fresca: el fetch paralelo satura el WebSocket; cerrar y
    # reconectar antes del buy para que responda rapido y quepa en el limite
    # del host (el sandbox mata WebSocket >~2.5 min).
    try:
        await client.close()
    except Exception:
        pass
    ok_c, reason_c = await connect_with_retry(client)
    if not ok_c:
        print(f"[trader] reconexion pre-buy fallo: {reason_c}")
        return
    ok_o, reason_o, open_price, order_id, rej = await place_order(
        client, cand.asset, cand.direction, amount,
        DURATION_SEC, False, "PRACTICE",
    )
    if ok_o:
        cid = journal.log_candidate(
            cand,
            decision="ACCEPTED",
            amount=amount,
            stage="initial",
            outcome="PENDING",
            order_id=str(order_id),
            strategy={"m15_context": ev.m15_context, "m5_event": ev.m5_event,
                      "strength": round(ev.strength * 100.0, 1)},
        )
        print(f"[trader] ORDEN COLOCADA {cand.asset} {cand.direction} "
              f"${amount:.2f} order_id={order_id} cid={cid}")
    else:
        print(f"[trader] FALLO colocar orden: {reason_o} / {rej}")
    # 5) salir ya (el host mataria el WebSocket de todos modos)
    await client.close()
    print(f"[trader] ciclo corto terminado {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
