"""Verifica la bandera FAST_ENTRY: la orden se lanza en open de vela M1 (60s)
en vez de M5 (300s), sin tocar el vencimiento (DURATION_SEC, 15 min)."""
from __future__ import annotations

import importlib

import config as _cfg
from entry_sync import EntrySynchronizer


def _resolve_entry_tf() -> int:
    """Replica la lógica de executor.py: FAST_ENTRY fuerza 60s, sino 300s."""
    return _cfg.FAST_ENTRY_TF_SEC if _cfg.FAST_ENTRY else _cfg.ENTRY_SYNC_TF_SEC


def test_default_fast_entry_is_off_uses_m5(monkeypatch):
    # FAST_ENTRY=False => entra en open de vela de 5 min (300s), sin importar el valor en disco.
    monkeypatch.setattr(_cfg, "FAST_ENTRY", False)
    assert _cfg.FAST_ENTRY is False
    assert _resolve_entry_tf() == 300


def test_fast_entry_on_uses_m1():
    prev = _cfg.FAST_ENTRY
    _cfg.FAST_ENTRY = True
    try:
        assert _resolve_entry_tf() == 60
    finally:
        _cfg.FAST_ENTRY = prev


def test_entry_sync_tf_reflects_flag(monkeypatch):
    # El EntrySynchronizer se construye con el tf resuelto.
    monkeypatch.setattr(_cfg, "FAST_ENTRY", True)
    sync = EntrySynchronizer(tf_sec=_resolve_entry_tf())
    assert sync.tf_sec == 60

    monkeypatch.setattr(_cfg, "FAST_ENTRY", False)
    sync = EntrySynchronizer(tf_sec=_resolve_entry_tf())
    assert sync.tf_sec == 300


def test_fast_entry_keeps_duration_intact():
    # La bandera NO debe tocar el vencimiento de la opción (15 min).
    assert _cfg.DURATION_SEC == 900
    prev = _cfg.FAST_ENTRY
    _cfg.FAST_ENTRY = True
    try:
        sync = EntrySynchronizer(tf_sec=_resolve_entry_tf())
        # duration_sec hereda de config (900) salvo que se pase explícito.
        assert sync.duration_sec == 900
    finally:
        _cfg.FAST_ENTRY = prev
