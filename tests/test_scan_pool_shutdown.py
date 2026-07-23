"""Verifica que shutdown_scan_pool mata de verdad los workers del ProcessPool.

Sin esto, en Windows (spawn) los 10 workers de STRAT-F quedaban vivos en
call_queue.get(block=True) y se tragaban el Ctrl+C del padre (traceback
sucio + procesos huérfanos). El fix debe terminarlos.
"""
from __future__ import annotations

import time

from concurrent.futures import ProcessPoolExecutor

import loop_utils


def _burn(x: int) -> int:
    # Tarea que mantiene al worker ocupado/esperando (no importa el resultado)
    time.sleep(0.2)
    return x * 2


def test_shutdown_kills_workers(monkeypatch):
    pool = ProcessPoolExecutor(max_workers=4)
    # fuerza que haya trabajo encolado para que los workers esperen
    futs = [pool.submit(_burn, i) for i in range(8)]
    # Capturamos la referencia a los workers ANTES del shutdown (el stdlib
    # deja _processes en None tras shutdown()).
    procs = getattr(pool, "_processes", {}) or {}
    monkeypatch.setattr(loop_utils, "_SCAN_POOL", pool)

    loop_utils.shutdown_scan_pool()

    # Tras el shutdown, el global debe quedar None
    assert loop_utils.get_scan_pool() is None

    # Los workers deben morir en pocos segundos (no quedar colgados)
    deadline = time.time() + 5.0
    alive = True
    while time.time() < deadline:
        alive = any(p.is_alive() for p in procs.values())
        if not alive:
            break
        time.sleep(0.1)
    assert not alive, "los workers del scan pool quedaron vivos tras shutdown"


def test_shutdown_idempotent(monkeypatch):
    # Llamar con pool None no debe romper
    monkeypatch.setattr(loop_utils, "_SCAN_POOL", None)
    loop_utils.shutdown_scan_pool()
    assert loop_utils.get_scan_pool() is None
