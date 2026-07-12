"""Diag STRAT-F: mide el SCORE FINAL que usa el bot (score_candidate) con datos
reales, sin enviar ordenes.

Conecta a demo, baja 15m/5m/1m de los activos abiertos, corre evaluate_strat_f
y luego score_candidate (el mismo que usa el scanner del bot) para ver el score
real que decidiria la entrada. Asi calibro sin depender del host-kill del bot.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import MIN_PAYOUT, TF_5M, TF_15M, STRAT_F_MIN_SCORE  # type: ignore
from connection import connect_with_retry, fetch_candles_with_retry, get_open_assets  # type: ignore
from pyquotex.stable_api import Quotex  # type: ignore
from strat_fractal import evaluate_strat_f  # type: ignore
from models import CandidateEntry, SignalMode  # type: ignore
from entry_scorer import score_candidate  # type: ignore


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

    assets = await get_open_assets(client, min_payout=MIN_PAYOUT)
    print(f"Activos abiertos (payout>={MIN_PAYOUT}%): {len(assets)}")
    if not assets:
        await client.close()
        return

    passed = 0
    total_sig = 0
    print(f"\n{'ACTIVO':<14} {'DIR':<5} {'strength':>8} {'SCORE':>7} {'umbral':>6} {'RESULT':>8}  ctx/event")
    print("-" * 78)
    for sym, payout in assets:
        c15 = await fetch_candles_with_retry(client, sym, TF_15M, 30, timeout_sec=15)
        c5 = await fetch_candles_with_retry(client, sym, TF_5M, 20, timeout_sec=12)
        c1 = await fetch_candles_with_retry(client, sym, 60, 36, timeout_sec=12)
        if len(c15) < 6 or len(c5) < 5 or len(c1) < 3:
            continue
        ev = evaluate_strat_f(c15, c5, c1, payout=payout)
        if not (ev.has_signal and ev.direction and ev.zone):
            continue
        total_sig += 1
        f_amount = 1.0
        f_candidate = CandidateEntry(
            asset=sym,
            payout=payout,
            zone=ev.zone,
            direction=ev.direction,
            candles=c1,
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
        setattr(f_candidate, "_signal_ts_1m", c1[-1].ts if c1 else None)
        setattr(f_candidate, "_amount", f_amount)
        setattr(f_candidate, "_stage", "initial")
        score_candidate(f_candidate)
        res = "PASA" if f_candidate.score >= STRAT_F_MIN_SCORE else "NO"
        if res == "PASA":
            passed += 1
        print(f"{sym:<14} {ev.direction:<5} {ev.strength*100:>7.0f} "
              f"{f_candidate.score:>7.1f} {STRAT_F_MIN_SCORE:>6} {res:>8}  "
              f"{ev.m15_context}/{ev.m5_event}")

    print("-" * 78)
    print(f"Senales STRAT-F (evaluate_strat_f): {total_sig}")
    print(f"Pasan scorer umbral={STRAT_F_MIN_SCORE}: {passed}")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
