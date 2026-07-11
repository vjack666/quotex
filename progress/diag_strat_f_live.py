"""Diagnóstico STRAT-F en vivo (solo lectura).

Conecta a demo, baja 15m/5m/1m de unos pocos pares y corre evaluate_strat_f,
imprimiendo señales reales (direccion, contexto M15, fuerza, Fase A). NO envia
ordenes. Punto de partida para ver STRAT-F contra datos reales.
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

from config import MIN_PAYOUT, TF_5M, TF_15M  # type: ignore
from connection import connect_with_retry, fetch_candles_with_retry, get_open_assets  # type: ignore
from pyquotex.stable_api import Quotex  # type: ignore
from strat_fractal import evaluate_strat_f  # type: ignore
from models import CandidateEntry, SignalMode  # type: ignore


def _feed_journal(sym, payout, ev) -> None:
    """Graba una decision STRAT-F en el diario (trade_journal.db)."""
    from trade_journal import get_journal

    decision = "ACCEPTED" if (ev.has_signal and ev.direction and ev.zone) else "REJECTED_STRAT_F"
    skip = ev.skip_reason or ""
    e = CandidateEntry(
        asset=sym,
        payout=payout,
        zone=ev.zone,
        direction=ev.direction or "call",
        candles=[],
        score=round(ev.strength * 100.0, 1),
        mode=SignalMode.REBOUND,
        score_breakdown={
            "fractal": ev.strength * 35.0,
            "context": ev.strength * 25.0,
            "payout": min(20.0, (payout / 95.0) * 20.0),
        },
    )
    setattr(e, "_strategy_origin", "STRAT-F")
    setattr(e, "_reversal_pattern", ev.pattern_name)
    setattr(e, "_reversal_strength", ev.strength)
    setattr(e, "_stage", "initial")
    get_journal().log_candidate(
        e,
        decision=decision,
        reject_reason=skip,
        strategy={
            "m15_context": ev.m15_context,
            "m5_event": ev.m5_event,
            "strength": round(ev.strength * 100.0, 1),
        },
    )


async def main(journal: bool = False) -> None:
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

    sample = assets[:14]
    signals = 0
    for sym, payout in sample:
        c15 = await fetch_candles_with_retry(client, sym, TF_15M, 30, timeout_sec=15)
        c5 = await fetch_candles_with_retry(client, sym, TF_5M, 20, timeout_sec=12)
        c1 = await fetch_candles_with_retry(client, sym, 60, 36, timeout_sec=12)
        if len(c15) < 6 or len(c5) < 5 or len(c1) < 3:
            print(f"  SHORT {sym}: 15m={len(c15)} 5m={len(c5)} 1m={len(c1)} payout={payout}%")
            continue
        ev = evaluate_strat_f(c15, c5, c1, payout=payout)
        if ev.has_signal and (ev.strength * 100) >= 60:
            signals += 1
            print(
                f"  SENAL {sym} {ev.direction} | ctx={ev.m15_context} "
                f"event={ev.m5_event} strength={ev.strength*100:.0f} "
                f"payout={payout}%"
            )
        else:
            print(
                f"  - {sym} ({payout}%) ctx={ev.m15_context} event={ev.m5_event} "
                f"skip={ev.skip_reason}"
            )
        if journal:
            try:
                _feed_journal(sym, payout, ev)
            except Exception as ex:  # noqa: BLE001
                print(f"  [JOURNAL] no grabado {sym}: {ex}")

    print(f"\nResumen ({len(sample)} activos): senales_filtradas={signals}")
    if journal:
        print("Diario STRAT-F actualizado. Ver: python -m trade_journal --strat-f")
    await client.close()


if __name__ == "__main__":
    import sys as _sys

    _journal = "--journal" in _sys.argv
    asyncio.run(main(journal=_journal))
