"""Tests de la fabrica de herramientas del Edificio (feature 40, Fase F/T13).

Cubre las reglas del contrato R1-R10 verificables en codigo:
  R2  Evidence sin campo de orden
  R1  Registro y catalogo de herramientas
  R4  Ensamblador produce BUY/SELL/NO_TRADE
  R5  Inspector frena conflicto
  R6  Gobernador veta por DD
  R8  Trazabilidad a experimento
  R9  Candado de dominio REAL->OTC
  R10 Candado de n minimo

Ejecutar: pytest tests/test_edificio_tools.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from edificio_tools import (
    Evidence, Tool, load_catalog, get_tool, active_tools,
    inspect, assemble, assemble_from_tools, Decision,
    Governor, audit_decision, check_promotion,
)

SRC = os.path.join(os.path.dirname(__file__), "..", "src")


def test_r2_evidence_sin_orden():
    ev = Evidence(direction="LONG", strength=0.7, confidence=0.6,
                  stage="P3", tool="valvula_kd")
    assert "BUY" not in ev.__dict__ and "SELL" not in ev.__dict__
    assert ev.direction == "LONG"


def test_r2_evidence_rechaza_direction_invalida():
    import pytest
    with pytest.raises(ValueError):
        Evidence(direction="UP", strength=0.5, confidence=0.5,
                 stage="P3", tool="x")


def test_r2_evidence_rechaza_rango():
    import pytest
    with pytest.raises(ValueError):
        Evidence(direction="LONG", strength=1.5, confidence=0.5,
                 stage="P3", tool="x")


def test_r1_catalogo_carga():
    tools = load_catalog()
    assert len(tools) >= 4
    names = [t.name for t in tools]
    assert "arcoiris_7ema" in names
    assert "valvula_kd" in names


def test_r1_cruce_limpio_inactiva():
    t = get_tool("cruce_limpio")
    assert t is not None and t.active is False


def test_r1_activas_3():
    act = active_tools()
    assert len(act) == 3


def test_r4_call_a_buy():
    d = assemble_from_tools("call")
    assert d.action == "BUY" and d.direction == "LONG"


def test_r4_put_a_sell():
    d = assemble_from_tools("put")
    assert d.action == "SELL" and d.direction == "SHORT"


def test_r4_none_a_no_trade():
    d = assemble_from_tools(None)
    assert d.action == "NO_TRADE"


def test_r5_inspector_conflicto():
    evs = [
        Evidence("LONG", 0.8, 0.7, "P3", "arcoiris_7ema"),
        Evidence("SHORT", 0.8, 0.7, "P3", "valvula_kd"),
    ]
    conflict, reason = inspect(evs)
    assert conflict
    d = assemble(evs)
    assert d.action == "NO_TRADE" and d.conflict


def test_r5_sin_conflicto_baja_confianza():
    evs = [
        Evidence("LONG", 0.5, 0.3, "P3", "a"),
        Evidence("SHORT", 0.5, 0.3, "P3", "b"),
    ]
    conflict, _ = inspect(evs)
    assert not conflict


def test_r6_gobernador_permite():
    g = Governor(bankroll=1000.0, dd_limit=0.20, payout=0.85)
    s = g.size(wr=0.605, n=200)
    assert s.allowed and s.lot_fraction > 0


def test_r6_gobernador_veta_dd():
    g = Governor(bankroll=1000.0, dd_limit=0.03, payout=0.85)
    s = g.size(wr=0.52, n=50)
    assert not s.allowed and s.projected_dd > 0.03


def test_r8_auditoria_trazable():
    d = assemble_from_tools("call")
    rec = audit_decision(d)
    assert rec.action == "BUY"
    assert any(t.get("exp_ref") for t in rec.tools)
    assert rec.wr_combined is not None and rec.n_combined is not None


def test_r9_candado_dominio():
    # arcoiris solo tiene evidencia REAL -> no promover a OTC
    tools = [get_tool("arcoiris_7ema")]
    v = check_promotion(tools, target_domain="OTC")
    assert not v.allowed
    v_real = check_promotion(tools, target_domain="REAL")
    assert v_real.allowed


def test_r10_candado_n_minimo():
    tools = [Tool(name="mala", exp_ref="EXP-X", wr_pooled=55.0, n=10,
                  charter_verdict="CANDIDATA", domain="REAL", stage="P2")]
    v = check_promotion(tools, target_domain="REAL", min_n=100)
    assert not v.allowed


def test_gate_enchufado_al_edificio_importa():
    # El edificio debe importar sin error con la fabrica enchufada (feature 40).
    import importlib
    import edificio_contratacion  # noqa: F401  (debe cargar con la capa fabrica)
    importlib.reload(edificio_contratacion)
    # La capa fabrica esta presente en el codigo fuente del edificio.
    import inspect
    src = inspect.getsource(edificio_contratacion)
    assert "CAPA FABRICA DE HERRAMIENTAS" in src
    assert "_fab.assemble_from_tools" in src
    assert "_fab.Governor" in src
    assert "_fab.audit_decision" in src


def test_gate_logica_contratado_permite_call():
    # Logica que el gate ejecuta cuando el edificio llega a CONTRATADO con CALL.
    d = assemble_from_tools("call")
    assert d.action == "BUY"
    # Gobernador con WR combinado de herramientas activas debe permitir (R6).
    tools = active_tools()
    wr_comb = sum(t.wr_pooled for t in tools) / max(1, len(tools))
    g = Governor(bankroll=1000.0, dd_limit=0.20, payout=0.85)
    s = g.size(wr=wr_comb / 100.0, n=200)
    assert s.allowed
