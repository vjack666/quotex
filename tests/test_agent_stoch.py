"""Tests para el loader comun (agent_common) y el agente estocastico."""

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import agent_common as ac  # noqa: E402
import agent_stoch as ast  # noqa: E402


# ── Helpers de datos sinteticos ──────────────────────────────────────────────
def _trade(target, direction="CALL", m15=None, m5=None, m1=None):
    m15 = m15 or {}
    m5 = m5 or {}
    m1 = m1 or {}
    return {
        "features": {},
        "stoch": {"m15": m15, "m5": m5, "m1": m1},
        "direction": direction,
        "target": target,
        "ts": 1.0,
        "source": "synth",
    }


def _trend_stoch(k, k_prev, estado="NEUTRO"):
    return {"k": k, "k_prev": k_prev, "estado": estado, "cruce": None}


def _synth():
    """Dataset que valida la hipotesis de Ruben con volumen."""
    rows = []
    # CALL + M15 bajando (k baja) -> pierde.
    for _ in range(15):
        rows.append(_trade(0, "CALL", _trend_stoch(40, 55)))
    # CALL + M15 subiendo (k sube) -> gana (sale de sobreventa hacia arriba).
    for _ in range(15):
        rows.append(_trade(1, "CALL", _trend_stoch(35, 18, "SOBREVENTA")))
    # PUT + M15 subiendo -> mezcla.
    for _ in range(8):
        rows.append(_trade(1, "PUT", _trend_stoch(60, 45)))
    for _ in range(7):
        rows.append(_trade(0, "PUT", _trend_stoch(60, 45)))
    return rows


# ── agent_common ─────────────────────────────────────────────────────────────
def test_wilson_zero_n():
    lo, c, hi = ac.wilson_interval(0, 0)
    assert (lo, c, hi) == (0.0, 0.0, 0.0)


def test_wilson_shrinks_small_n():
    # n=11 con 8 wins (72.7%) -> el lower bound debe ser mucho menor.
    lo, c, hi = ac.wilson_interval(8, 11)
    assert abs(c - 8 / 11) < 1e-9
    assert lo < 0.6   # shrinkage real: no llega a 60%


def test_stoch_trend_from_k():
    assert ac.stoch_trend(_trend_stoch(50, 30)) == "subiendo"
    assert ac.stoch_trend(_trend_stoch(30, 50)) == "bajando"
    assert ac.stoch_trend(_trend_stoch(40, 40)) == "plano"
    assert ac.stoch_trend({}) == "n/a"


def test_stoch_zone_label():
    assert ac.stoch_zone_label({"estado": "SOBREVENTA"}) == "sobreventa"
    assert ac.stoch_zone_label({"estado": "SOBRECOMPRA"}) == "sobrecompra"
    assert ac.stoch_zone_label({"k": 50}) == "neutro"
    assert ac.stoch_zone_label({}) == "n/a"


def test_load_resolved_trades_real_runs():
    rows = ac.load_resolved_trades()
    assert isinstance(rows, list)
    for t in rows[:5]:
        assert "stoch" in t and "m15" in t["stoch"]
        assert t["direction"] in ("CALL", "PUT", "")
        assert t["target"] in (0, 1)


# ── agent_stoch ──────────────────────────────────────────────────────────────
def test_analyze_stoch_hypothesis():
    rows = _synth()
    a = ast.analyze_stoch(rows)
    assert a["n"] == 45
    # Celda clave: CALL + M15 bajando debe tener winrate ~0.
    cell = a["direction_x_m15_trend"].get("CALL|M15:bajando")
    assert cell is not None
    assert cell["n"] == 15
    assert cell["wr"] == 0.0
    # CALL + M15 subiendo gana.
    cell_up = a["direction_x_m15_trend"].get("CALL|M15:subiendo")
    assert cell_up is not None
    assert cell_up["wr"] > 0.8


def test_analyze_stoch_includes_m1():
    rows = _synth()
    a = ast.analyze_stoch(rows)
    # M1 presente en el analisis aunque n=0 (sin datos M1 en synth).
    assert "m1_trend" in a
    assert "direction_x_m1_trend" in a
    # Inyectamos un trade con M1 para confirmar que se contabiliza.
    rows.append(_trade(1, "CALL", m1=_trend_stoch(20, 10, "SOBREVENTA")))
    a2 = ast.analyze_stoch(rows)
    assert a2["direction_x_m1_trend"].get("CALL|M1:subiendo", {}).get("n", 0) >= 1


def test_detect_rules_min_support_and_wilson():
    rows = _synth()
    a = ast.analyze_stoch(rows)
    rules = ast.detect_rules(a, min_support=10, good_wr=0.6, bad_wr=0.4)
    keys_bad = [e["key"] for e in rules["bad"]]
    keys_good = [e["key"] for e in rules["good"]]
    assert "CALL|M15:bajando" in keys_bad
    assert "CALL|M15:subiendo" in keys_good


def test_detect_rules_filters_low_support():
    # Poco volumen en CALL bajando -> no debe salir regla.
    rows = [_trade(0, "CALL", _trend_stoch(40, 55)) for _ in range(3)]
    a = ast.analyze_stoch(rows)
    rules = ast.detect_rules(a, min_support=10, good_wr=0.6, bad_wr=0.4)
    assert rules["bad"] == []


def test_compute_drift():
    prev = {"winrate": 0.5, "direction_x_m15_trend": {"CALL|M15:bajando": {"wr": 0.3}}}
    cur = {"winrate": 0.55, "direction_x_m15_trend": {"CALL|M15:bajando": {"wr": 0.4}}}
    d = ast.compute_drift(prev, cur)
    assert abs(d["winrate_delta"] - 0.05) < 1e-9
    assert abs(d["call_m15_down_wr_delta"] - 0.1) < 1e-9


def test_render_and_digest_no_crash():
    rows = _synth()
    a = ast.analyze_stoch(rows)
    rules = ast.detect_rules(a, min_support=10, good_wr=0.6, bad_wr=0.4)
    rep = ast.render_report(a, rules, {})
    assert "CALL|M15:bajando" in rep
    dig = ast.build_digest(a, rules, {}, "x.md")
    assert "HIPOTESIS" in dig
