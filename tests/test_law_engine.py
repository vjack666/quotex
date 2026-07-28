"""Tests del motor de leyes (estratega). Verifican la arquitectura, no el bot.

Cubren:
- orden por prioridad (mayor primero)
- break si una ley evaluada falla
- skip si una dependencia no paso (no rompe el flujo)
- suma de pesos via weight_provider
- Ley #1 (freno) detecta muerte de impulso en M15 REAL de caja negra
"""
import numpy as np
import pytest

from strategy_lab.law_engine import (
    EngineResult, ExecutableLaw, LawContext, LawEngine, LawResult,
)
from strategy_lab.laws_freno import (
    FrenoConfig, build_freno_laws, ley_impulso_muerto,
)


def _weights(semilla=10.0):
    store = {
        "FRENO-IMPULSO-MUERTO": 40.0,
        "STOCH-EXTREMO": 20.0,
        "SEPARACION-KD": 15.0,
        "ZONA-HTF": 10.0,
        "RECHAZO-M1": 5.0,
    }
    return lambda lid, default: store.get(lid, default if default else semilla)


def test_orden_por_prioridad():
    order = []

    def mk(lid, prio):
        def _ev(c):
            order.append(lid)
            return LawResult(ok=True)
        return ExecutableLaw(id=lid, priority=prio, evaluar=_ev)

    laws = [mk("B", 50), mk("A", 100), mk("C", 75)]
    eng = LawEngine(laws, _weights())
    eng.evaluate(LawContext())
    assert order == ["A", "C", "B"]


def test_break_en_fallo():
    calls = []

    def mk(lid, ok, prio):
        def _ev(c):
            calls.append(lid)
            return LawResult(ok=ok, detail="x")
        return ExecutableLaw(id=lid, priority=prio, evaluar=_ev)

    laws = [mk("A", True, 100), mk("B", False, 90), mk("C", True, 80)]
    eng = LawEngine(laws, _weights())
    r = eng.evaluate(LawContext())
    assert r.ok is False
    assert r.failed_at == "B"
    assert calls == ["A", "B"]          # C no se evalua tras el break


def test_skip_por_dependencia_no_rompe():
    calls = []

    def mk(lid, prio, requires=()):
        def _ev(c):
            calls.append(lid)
            return LawResult(ok=True)
        return ExecutableLaw(id=lid, priority=prio, evaluar=_ev, requires=requires)

    # B requiere A, pero A falla -> B se salta (continue), no rompe
    laws = [mk("A", 100), mk("B", 90, requires=("A",)), mk("C", 80)]
    eng = LawEngine(laws, _weights())
    # forzamos A a fallar
    laws[0].evaluar = lambda c: LawResult(ok=False, detail="A falla")
    r = eng.evaluate(LawContext())
    assert r.ok is False
    assert r.failed_at == "A"
    assert "B" not in calls             # B se salto por dependencia


def _ctx_real_from_blackbox():
    """M15 REAL de una caja negra del bot (el freno ya marca 88% ahí).

    Reconstruye la serie M15 contigua de un activo juntando TODAS sus
    velas de todos los candidatos (dedup por ts). Si no hay DB o ningun
    activo con >=35 velas, el test se skipea.
    """
    import json
    import sqlite3
    from collections import defaultdict
    from pathlib import Path
    db = Path("data/db/black_box_strat_2026-07-17.db")
    if not db.exists():
        pytest.skip("caja negra no disponible")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT asset, candles_15m FROM scan_candidates "
            "WHERE candles_15m IS NOT NULL"
        ).fetchall()
    finally:
        con.close()
    by_asset: dict[str, dict[float, tuple]] = defaultdict(dict)
    for asset, raw in rows:
        try:
            arr = json.loads(raw)
        except (TypeError, ValueError):
            continue
        for c in arr or []:
            try:
                ts = float(c["ts"])
                o, h, l, cc = float(c["o"]), float(c["h"]), float(c["l"]), float(c["c"])
            except (KeyError, TypeError, ValueError):
                continue
            by_asset[asset][ts] = (ts, o, h, l, cc)
    for asset, d in by_asset.items():
        if len(d) < 35:
            continue
        series = [v for v in sorted(d.values())]
        o = np.array([s[1] for s in series], float)
        h = np.array([s[2] for s in series], float)
        l = np.array([s[3] for s in series], float)
        c = np.array([s[4] for s in series], float)
        return LawContext(o15=o, h15=h, l15=l, c15=c,
                          stoch_m15={"k": 15.0, "d": 12.0}, sym=asset)
    pytest.skip("sin activo con suficientes velas M15")


def test_suma_pesos_via_provider():
    # Aisla la suma de pesos con leyes mock (el freno real se prueba aparte)
    store = {"X": 40.0, "Y": 20.0, "Z": 15.0}

    def mk(lid, prio, w):
        def _ev(c):
            return LawResult(ok=True, weight=w)
        return ExecutableLaw(id=lid, priority=prio, evaluar=_ev)

    laws = [mk("Z", 70, 15.0), mk("X", 100, 40.0), mk("Y", 90, 20.0)]
    eng = LawEngine(laws, lambda lid, d: store.get(lid, d))
    r = eng.evaluate(LawContext())
    assert r.ok is True
    assert r.passed == ["X", "Y", "Z"]          # orden por prioridad
    assert abs(r.confianza - 75.0) < 1e-6        # 40+20+15


def test_ley_freno_muerte_impulso_dispara():
    ctx = _ctx_real_from_blackbox()
    r = ley_impulso_muerto(ctx, FrenoConfig())
    assert r.ok is True
    assert r.direction in ("CALL", "PUT")


def test_dependencia_stoch_falla_corta_flujo():
    laws = build_freno_laws(FrenoConfig(), _weights())
    ctx = _ctx_real_from_blackbox()
    # stoch en zona neutral (k=50) -> STOCH-EXTREMO falla
    ctx.stoch_m15 = {"k": 50.0, "d": 48.0}
    eng = LawEngine(laws, _weights())
    r = eng.evaluate(ctx)
    assert r.ok is False
    assert r.failed_at == "STOCH-EXTREMO"
