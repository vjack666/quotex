"""Pre-calibración del Edificio de Contratación (determinista, sin live).

Objetivo: verificar que el Edificio NO tiene gatillos sueltos antes de
soltarlo en EXP-039 (validación live). Dos reglas que pidió el humano:

  REGLA 1 — el PISO no es el activador: estar en un piso por sí solo
            no debe disparar un contrato.
  REGLA 2 — cada señal NO se activa individualmente como contrato de
            compra/venta: freno, extremo y cruce son condiciones de una
            puerta, no órdenes. Solo CONTRATADO envía orden, y exige la
            cadena completa + delay + SequenceEngine válido.

No requiere credenciales ni feed live: se alimenta evaluate() con
señales explícitas.
"""
from __future__ import annotations

import time

import pytest

from edificio_contratacion import (
    CONTRATADO,
    PISO_1,
    PISO_2,
    PISO_3,
    BuildingCard,
    EdificioContratacion,
)


def _new_edificio() -> EdificioContratacion:
    return EdificioContratacion()


def _hammer_candle(direction: str) -> dict:
    """Vela 5m que pasa el _5m_gate (body fuerte, body_pct explícito alto).

    El TEST D valida la CADENA de activación del Edificio, no el
    clasificador de velas; por eso usamos body_pct explícito y alto
    para que el gate P3 pase sin depender del detector de martillos.
    """
    return {"open": 1.0950, "high": 1.1005, "low": 1.0948,
            "close": 1.1000, "body": 0.0050, "total_range": 0.0057, "body_pct": 0.9}


# ── REGLA 2: señal suelta ≠ contrato ─────────────────────────────────

def test_A_freno_solo_no_contrata():
    """Solo el freno en P1 no debe disparar CONTRATADO (es alerta, no orden)."""
    e = _new_edificio()
    # Varios ciclos con solo brake_ok; nunca debe llegar a CONTRATADO.
    for _ in range(10):
        res = e.evaluate(
            asset="EURUSD", direction="CALL", payout=85,
            payout_ok=True, brake_ok=True,
        )
        card = e._cards["EURUSD"]
        assert card.piso != CONTRATADO, f"freno solo contrató (piso={card.piso})"
    # Debe quedar en P1 (esperando cierre de vela M15 para confirmar freno).
    assert e._cards["EURUSD"].piso in (PISO_1, PISO_2)


def test_B_cruce_solo_no_contrata():
    """Solo el cruce en P2 no debe disparar CONTRATADO."""
    e = _new_edificio()
    # Llevamos a P2 con freno confirmado, luego solo cruce (sin extremo).
    e.evaluate(asset="EURUSD", direction="CALL", payout=85,
               payout_ok=True, brake_ok=True)
    # forzamos freno confirmado para entrar a P2
    card = e._cards["EURUSD"]
    card.brake_verdict = "CONFIRMED"
    card.piso = PISO_2
    for _ in range(10):
        res = e.evaluate(
            asset="EURUSD", direction="CALL", payout=85,
            payout_ok=True, cross_ok=True, cross_sticky=False,
        )
        assert e._cards["EURUSD"].piso != CONTRATADO, "cruce solo contrató"
    # Se queda en P2 esperando extremo (Regla 2: cruce no es orden).
    assert e._cards["EURUSD"].piso == PISO_2


# ── REGLA 1: el piso no es el activador ──────────────────────────────

def test_C_piso_forzado_sin_senales_no_contrata():
    """Poner el activo manualmente en P3 sin señales NO debe contratar."""
    e = _new_edificio()
    e.evaluate(asset="EURUSD", direction="CALL", payout=85, payout_ok=True)
    card = e._cards["EURUSD"]
    card.piso = PISO_3  # forzamos el piso "alto" sin señales
    # Sin brake/extreme/cross: debe bajar de P3, jamás contratar.
    e.evaluate(asset="EURUSD", direction="CALL", payout=85, payout_ok=True)
    assert e._cards["EURUSD"].piso != CONTRATADO, "piso forzado contrató sin señales"
    assert e._cards["EURUSD"].piso < PISO_3, "el piso por sí solo retuvo P3"


# ── Cadena completa SÍ contrata (control positivo) ───────────────────

def test_D_cadena_completa_contrata(monkeypatch):
    """Solo la cadena completa (freno+extremo+cruce+vela5m+delay+seq) contrata."""
    e = _new_edificio()
    # Aislamos la lógica del Edificio del grafo del SequenceEngine (que tiene
    # su propio suite). El SequenceEngine solo certifica progresión legal;
    # aquí lo dejamos pasar para probar la cadena del Edificio.
    monkeypatch.setattr(e._sequence_engine, "is_contratado_valido", lambda card: True)
    base = dict(asset="EURUSD", direction="CALL", payout=85, payout_ok=True,
                brake_ok=True, extreme_ok=True, cross_ok=True,
                cross_sticky=False, close_candle_5m=_hammer_candle("CALL"))
    e.evaluate(**base)
    # Llevamos a P3 manualmente (ya con todas las señales) para aislar el gate final.
    # Nota: forzar el piso aquí es solo para acelerar; el SequenceEngine está
    # mockeado arriba, así que no bloquea por salto.
    card = e._cards["EURUSD"]
    card.piso = PISO_3
    card.brake_verdict = "CONFIRMED"
    # Primer evaluate en P3: marca entrada (entry_pending), arranca delay 5min.
    e.evaluate(**base)
    assert e._cards["EURUSD"].entry_pending is True
    assert e._cards["EURUSD"].piso == PISO_3
    # Avanzamos el reloj 301s (delay de 5min agotado).
    t0 = time.time()
    monkeypatch.setattr(time, "time", lambda: t0 + 301)
    e.evaluate(**base)
    assert e._cards["EURUSD"].piso == CONTRATADO, "cadena completa no contrató"
    assert len(e.pop_contratados()) >= 1
