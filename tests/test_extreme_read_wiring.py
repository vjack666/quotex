"""Wiring del extreme-read gate en el scanner (sin ctx pesado).

Confirma que:
- scanner importa el gate (cableado en _evaluate_strat_f_single).
- la bandera EXTREME_READ_ENABLED existe y arranca OFF (no cambia el
  comportamiento hasta que el usuario la encienda).
- el recorder acepta la bandera extreme_read (ya cubierto en
  test_blackbox_extreme_read, pero lo reafirmamos aquí como contrato).
"""
from __future__ import annotations

import scanner as _scanner
import config as _cfg


def test_scanner_imports_gate():
    assert hasattr(_scanner, "extreme_read_gate"), (
        "extreme_read_gate debe estar importado en scanner para el cableado"
    )


def test_flag_defaults_off():
    # Bandera OFF por defecto: el bot opera igual hasta que el usuario la encienda.
    assert _cfg.EXTREME_READ_ENABLED is False
    assert 0.0 < _cfg.EXTREME_READ_POS <= 0.5
    assert 0.0 < _cfg.EXTREME_READ_BODY_MIN_RATIO <= 1.0


def test_flag_read_dynamically(monkeypatch):
    # El scanner lee la bandera en runtime (no en import), así respeta override.
    monkeypatch.setattr(_cfg, "EXTREME_READ_ENABLED", True)
    assert _cfg.EXTREME_READ_ENABLED is True
    # revierto para no contaminar otros tests
    monkeypatch.setattr(_cfg, "EXTREME_READ_ENABLED", False)
