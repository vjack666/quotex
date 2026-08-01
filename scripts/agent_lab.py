"""Laboratorio OFFLINE de aprendizaje del estocastico por activo (STRAT-F).

Idea (Ruben 2026-07-24): a modo de laboratorio, descargar ~1 mes de velas
por activo, dejar que el agente MIRA los ciclos del estocastico y APRENDE
el patron, y tirar las velas (recyclable — no se guardan en disco). Sin
backtest: solo observacion estadistica del histórico.

El agente cuenta, por activo y por TF (M1/M5/M15):
  - ciclos 20->80 (salida de sobreventa -> sobrecompra) y 80->20 (inverso),
  - duracion de cada ciclo en velas,
  - que hace el PRECIO despues del ciclo (sube/baja en N velas post) -> patron
    predictivo, aun sin trade resuelto.

Lo aprendido se acumula en ``data/agent/lab_profiles.json`` (durable,
pequeno): por activo, conteo de ciclos y direccion post-ciclo. Las velas
NO se persisten — se reciclan en RAM.

Re-cycling: se puede correr N veces; cada corrida refina el conteo con
mas muestras / mas meses. Tope de 10 activos (LAB_MAX_ASSETS).

El fetcher es INYECTABLE: en tests se pasan velas sinteticas; en
produccion usa ``connection.fetch_candles_with_retry``. Asi la logica de
conteo se verifica sin tocar la API.

Uso:
  .venv/Scripts/python.exe scripts/agent_lab.py --assets EUR/USD,GBP/USD
  .venv/Scripts/python.exe scripts/agent_lab.py --max-assets 10 --rounds 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SRC = os.path.join(_ROOT, "src")
for _p in (_SRC, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from config import LAB_MONTH_COUNT_M1, LAB_MONTH_COUNT_M5, LAB_MONTH_COUNT_M15, LAB_MAX_ASSETS  # noqa: E402

PROFILES_PATH = os.path.join(_ROOT, "data", "agent", "lab_profiles.json")
TFS = {"M1": LAB_MONTH_COUNT_M1, "M5": LAB_MONTH_COUNT_M5, "M15": LAB_MONTH_COUNT_M15}
# Velas post-ciclo a mirar para ver la direccion del precio.
POST_LOOK = 5


# ── Conteo de ciclos del estocastico (logica pura, testeable) ────────────────
def detect_stoch_cycles(k_vals: list[float], lo: float = 20.0, hi: float = 80.0) -> list[dict]:
    """Devuelve ciclos completos del estocastico (recorrido low<->high).

    Cuenta cada transicion completa entre extremos:
      - ciclo 'up':   parte de <=lo y llega a >=hi  (20->80)
      - ciclo 'down': parte de >=hi y llega a <=lo  (80->20)
    Modelo ciclico: tras tocar un extremo, el siguiente ciclo es hacia el
    opuesto. Ignora el ruido dentro de la zona media.
    """
    cycles: list[dict] = []
    last_extreme = None  # 'low' | 'high'
    last_idx = 0
    for i, k in enumerate(k_vals):
        if last_extreme != "low" and k <= lo:
            if last_extreme == "high":
                cycles.append({"dir": "down", "start_idx": last_idx,
                               "end_idx": i, "duration": i - last_idx})
            last_extreme = "low"
            last_idx = i
        elif last_extreme != "high" and k >= hi:
            if last_extreme == "low":
                cycles.append({"dir": "up", "start_idx": last_idx,
                               "end_idx": i, "duration": i - last_idx})
            last_extreme = "high"
            last_idx = i
    return cycles


def post_cycle_direction(closes: list[float], end_idx: int, look: int = POST_LOOK) -> str:
    """Direccion del precio despues del ciclo: 'up' | 'down' | 'flat'."""
    if end_idx + 1 >= len(closes):
        return "flat"
    start_px = closes[min(end_idx, len(closes) - 1)]
    end_px = closes[min(end_idx + look, len(closes) - 1)]
    if end_px > start_px * 1.0001:
        return "up"
    if end_px < start_px * 0.9999:
        return "down"
    return "flat"


def learn_from_candles(candles: list[dict], tf: str) -> dict:
    """Aprende el patron de un set de velas de un TF.

    ``candles`` = [{"k": float, "close": float}, ...] (ya con %K calculado
    o crudo — aqui usamos "k" y "close"). Devuelve resumen acumulable.
    """
    k_vals = [float(c.get("k", 0.0)) for c in candles]
    closes = [float(c.get("close", 0.0)) for c in candles]
    cycles = detect_stoch_cycles(k_vals)
    n_up = n_down = 0
    post_up_after_up = post_down_after_up = 0
    post_up_after_down = post_down_after_down = 0
    for cyc in cycles:
        d = cyc["dir"]
        px_dir = post_cycle_direction(closes, cyc["end_idx"], POST_LOOK)
        if d == "up":
            n_up += 1
            if px_dir == "up":
                post_up_after_up += 1
            elif px_dir == "down":
                post_down_after_up += 1
        else:
            n_down += 1
            if px_dir == "up":
                post_up_after_down += 1
            elif px_dir == "down":
                post_down_after_down += 1
    total = n_up + n_down
    # Patron predictivo: dado un ciclo up, ¿el precio sube despues?
    up_predict_up = post_up_after_up / n_up if n_up else 0.0
    down_predict_down = post_down_after_down / n_down if n_down else 0.0
    return {
        "tf": tf,
        "n_cycles": total,
        "n_up": n_up,
        "n_down": n_down,
        "post_up_after_up": post_up_after_up,
        "post_down_after_up": post_down_after_up,
        "post_up_after_down": post_up_after_down,
        "post_down_after_down": post_down_after_down,
        # wr de direccion congruenta: ciclo up->precio up, ciclo down->precio down.
        "congruent_wr": round(
            (post_up_after_up + post_down_after_down) / total, 4
        ) if total else 0.0,
        "up_predict_up_wr": round(up_predict_up, 4),
        "down_predict_down_wr": round(down_predict_down, 4),
    }


# ── Perfil durable ──────────────────────────────────────────────────────────
def load_profiles() -> dict:
    if os.path.exists(PROFILES_PATH):
        try:
            with open(PROFILES_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _merge_profile(old: dict, new: dict) -> dict:
    """Acumula conteos (re-cycling): suma muestras, recalcula wr."""
    if not old:
        return new
    merged = dict(old)
    for key in ("n_cycles", "n_up", "n_down", "post_up_after_up",
                "post_down_after_up", "post_up_after_down", "post_down_after_down"):
        merged[key] = old.get(key, 0) + new.get(key, 0)
    total = merged["n_up"] + merged["n_down"]
    merged["congruent_wr"] = round(
        (merged["post_up_after_up"] + merged["post_down_after_down"]) / total, 4
    ) if total else 0.0
    merged["up_predict_up_wr"] = round(
        merged["post_up_after_up"] / merged["n_up"], 4
    ) if merged["n_up"] else 0.0
    merged["down_predict_down_wr"] = round(
        merged["post_down_after_down"] / merged["n_down"], 4
    ) if merged["n_down"] else 0.0
    merged["rounds"] = old.get("rounds", 0) + 1
    return merged


# ── Fetcher ──────────────────────────────────────────────────────────────────
async def _default_fetcher(client, asset: str, tf_sec: int, count: int) -> list[dict]:
    """Fetcher de produccion: usa connection.fetch_candles_with_retry.

    Devuelve velas como [{"k": %K, "close": close}] — pero el estocastico
    hay que calcularlo. Para el laboratorio calculamos %K aqui a partir de
    las velas crudas (usa stochastic_m15.compute_stoch por compatibilidad).
    """
    from connection import fetch_candles_with_retry
    from config import (CANDLE_FETCH_1M_TIMEOUT_SEC, CANDLE_FETCH_TIMEOUT_SEC, FETCH_RETRIES, TF_1M)
    from stochastic_m15 import compute_stoch
    raw = await fetch_candles_with_retry(
        client, asset, tf_sec, count,
        timeout_sec=CANDLE_FETCH_1M_TIMEOUT_SEC if tf_sec <= TF_1M else CANDLE_FETCH_TIMEOUT_SEC,
        retries=FETCH_RETRIES,
    )
    candles = [{"close": float(c.close), "ts": int(c.ts)} for c in raw]
    # compute_stoch necesita objetos Candle; recalculamos %K por ventana.
    st = compute_stoch(raw, d_period=3)
    candles[-1]["k"] = st.get("k", 0.0)
    # Para el laboratorio necesitamos %K por vela, no solo la ultima.
    # Reusamos la ventana deslizante manualmente:
    import numpy as _np  # type: ignore
    closes = [float(c.close) for c in raw]
    ks = _rolling_stoch_k(closes, 14)
    for i, c in enumerate(candles):
        c["k"] = ks[i]
    return candles


def _rolling_stoch_k(closes: list[float], period: int = 14) -> list[float]:
    ks: list[float] = []
    for i in range(len(closes)):
        if i < period - 1:
            ks.append(50.0)  # placeholder hasta tener ventana
            continue
        window = closes[i - period + 1: i + 1]
        ll = min(window)
        hh = max(window)
        rng = hh - ll
        ks.append(100.0 * (closes[i] - ll) / rng if rng > 0 else 50.0)
    return ks


# ── Orquestador ────────────────────────────────────────────────────────────
async def run_lab(
    assets: list[str],
    fetcher: Callable,
    client: Any = None,
    rounds: int = 1,
) -> dict:
    assets = assets[:LAB_MAX_ASSETS]
    profiles = load_profiles()
    for rnd in range(rounds):
        for asset in assets:
            prof = profiles.setdefault(asset, {})
            for tf, count in TFS.items():
                tf_sec = {"M1": 60, "M5": 300, "M15": 900}[tf]
                candles = await fetcher(client, asset, tf_sec, count)
                new = learn_from_candles(candles, tf)
                prof[tf] = _merge_profile(prof.get(tf, {}), new)
            prof["rounds"] = prof.get("rounds", 0) + 1
    os.makedirs(os.path.dirname(PROFILES_PATH), exist_ok=True)
    with open(PROFILES_PATH, "w", encoding="utf-8") as fh:
        json.dump(profiles, fh, indent=2)
    return profiles


def render_report(profiles: dict) -> str:
    L: list[str] = []
    L.append("# Laboratorio estocastico — perfiles por activo (STRAT-F)")
    L.append(f"\nGenerado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    L.append(f"Activos: {len(profiles)} (tope {LAB_MAX_ASSETS})")
    for asset, prof in sorted(profiles.items()):
        L.append(f"\n## {asset} (rondás={prof.get('rounds', 0)})")
        for tf in ("M1", "M5", "M15"):
            t = prof.get(tf)
            if not t:
                continue
            L.append(
                f"- {tf}: ciclos={t['n_cycles']} (up={t['n_up']}, down={t['n_down']}) "
                f"congruente={t['congruent_wr']*100:.1f}% "
                f"up->up={t['up_predict_up_wr']*100:.1f}% "
                f"down->down={t['down_predict_down_wr']*100:.1f}%"
            )
    L.append("\n---\nAgente scripts/agent_lab.py (laboratorio offline, deterministico).")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Laboratorio estocastico por activo.")
    ap.add_argument("--assets", type=str, default="", help="CSV de activos (max 10).")
    ap.add_argument("--max-assets", type=int, default=LAB_MAX_ASSETS)
    ap.add_argument("--rounds", type=int, default=1, help="Veces de reciclar velas.")
    ap.add_argument("--demo", action="store_true", help="Usa fetcher sintetico (tests).")
    args = ap.parse_args()

    assets = [a.strip() for a in args.assets.split(",") if a.strip()]
    if not assets:
        assets = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF",
                  "USD/CAD", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY"][:args.max_assets]

    if args.demo:
        # Fetcher sintetico: velas con %K en zig-zag para verificar conteo.
        async def _demo_fetcher(client, asset, tf_sec, count):
            candles = []
            for i in range(count):
                phase = i % 40
                k = 10 + 70 * abs(((phase % 20) / 20) - (0 if phase < 20 else 1)) * 2
                # zig-zag 20->80->20 cada 20 velas.
                kk = 20 + 60 * (1 - abs((phase % 20) / 10 - 1))
                candles.append({"k": kk, "close": 100.0 + i * 0.01})
            return candles
        fetcher = _demo_fetcher
        client = None
    else:
        async def _prod_fetcher(client, asset, tf_sec, count):
            return await _default_fetcher(client, asset, tf_sec, count)
        fetcher = _prod_fetcher
        client = getattr(_get_bot_client(), "client", None)

    import asyncio
    profiles = asyncio.run(run_lab(assets, fetcher, client, args.rounds))
    print(render_report(profiles))
    print(f"\n[LAB] perfiles -> {PROFILES_PATH}")
    return 0


def _get_bot_client():
    # Import perezoso del bot para no cargar todo en modo demo/tests.
    try:
        import consolidation_bot as cb
        return cb
    except Exception:
        return object()


if __name__ == "__main__":
    raise SystemExit(main())
