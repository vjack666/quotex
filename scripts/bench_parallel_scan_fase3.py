"""Benchmark empírico (T8): serial vs ProcessPool para STRAT-F.

Mide el speedup real del dispatch paralelo. Usa un evaluate_strat_f simulado
que duerme 10ms por activo para representar el costo CPU de la detección real.
El objetivo es confirmar que el ProcessPool (10 workers) paraleliza N activos.

No es un benchmark de la detección fractal real (eso depende de las velas en
vivo); aquí se valida la ARQUITECTURA de paralelización del dispatch.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import patch

from loop_utils import init_scan_pool, shutdown_scan_pool
from scanner import _run_strat_f_parallel
from tests.test_parallel_scan_fase3 import _make_ctx


def _slow_eval(*args, **kw):
    # Simula ~10ms de trabajo CPU por activo (equivale a la detección real).
    time.sleep(0.01)
    from strat_fractal import StratFEvaluation
    from models import ConsolidationZone
    if "zone" not in kw:
        kw["zone"] = ConsolidationZone(asset="x", ceiling=1.0, floor=0.9,
                                        bars_inside=5, detected_at=0.0, range_pct=0.1)
    return StratFEvaluation(has_signal=kw.get("has_signal", False),
                            direction=kw.get("direction"),
                            zone=kw["zone"], skip_reason=kw.get("skip_reason"))


N = 40  # SCAN_MAX_ASSETS_PER_CYCLE


async def _run(mode: str) -> float:
    ctxs = [_make_ctx() for _ in range(N)]
    if mode == "serial":
        shutdown_scan_pool()
    else:
        init_scan_pool()
    from unittest.mock import MagicMock
    _bb = MagicMock()
    maturing_wl = MagicMock()
    log = MagicMock()
    candidates, reject_counts, batch = [], {}, [[], []]
    t0 = time.perf_counter()
    with patch("strat_fractal.evaluate_strat_f", side_effect=_slow_eval):
        await _run_strat_f_parallel(ctxs, _bb, maturing_wl, log,
                                    candidates, reject_counts, batch)
    return time.perf_counter() - t0


async def main() -> None:
    print(f"Benchmark STRAT-F dispatch: N={N} ctxs, 10 workers esperados")
    t_serial = await _run("serial")
    t_pool = await _run("pool")
    speedup = t_serial / t_pool if t_pool > 0 else float("inf")
    print(f"  serial : {t_serial:.3f}s")
    print(f"  pool   : {t_pool:.3f}s")
    print(f"  speedup: {speedup:.2f}x")
    ok = speedup >= 1.5
    print(f"  DoD R7 (speedup>=1.5x): {'PASS' if ok else 'FAIL'}")
    shutdown_scan_pool()


if __name__ == "__main__":
    asyncio.run(main())
