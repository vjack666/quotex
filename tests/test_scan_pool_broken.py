"""Verifica que _run_strat_f_parallel captura BrokenProcessPool (worker muerto)
y degrada a evaluacion serial sin tumbar el scan.

Reproduce el fallo real del usuario: el pool.submit lanza BrokenProcessPool
cuando un proceso hijo muere abruptamente. El fix debe loguear en espanol,
recrear el pool y evaluar en serial en vez de propagar la excepcion.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures.process import BrokenProcessPool

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import scanner as sc


def _ctx():
    return sc.StratFEvalContext(
        sym="TEST_otc", payout=90,
        candles_5m=[], candles_15m=[], candles_1m=[],
        strat_f_only_mode=False,
        flags={"STRAT_A_ONLY": False, "STRAT_F_ENABLED": False, "MIN_PAYOUT": 80,
               "STOCH_HELP_MODE": "hard", "MATURING_WATCHLIST_MODE": "live"},
    )


def _fake_pool_that_breaks():
    """Pool mock cuyo submit lanza BrokenProcessPool (worker muerto)."""
    p = MagicMock()
    p.submit.side_effect = BrokenProcessPool("A child process terminated abruptly")
    return p


@pytest.mark.asyncio
async def test_broken_process_pool_degrades_to_serial():
    ctxs = [_ctx()]
    bb = MagicMock()
    mw = MagicMock()
    log = MagicMock()
    candidates = []
    reject_counts = {}
    batch = [[], []]

    with patch.object(sc, "get_scan_pool", return_value=_fake_pool_that_breaks()), \
         patch.object(sc, "shutdown_scan_pool") as mock_shutdown, \
         patch.object(sc, "init_scan_pool") as mock_init:
        # No debe lanzar; debe degradar a serial y recrear el pool.
        accepts = await sc._run_strat_f_parallel(ctxs, bb, mw, log, candidates, reject_counts, batch)

    assert accepts == 0
    # El pool roto se cerro y se recreo para el proximo ciclo.
    mock_shutdown.assert_called_once()
    mock_init.assert_called_once()
    # El log de error en espanol se emitio.
    assert any("grupo de procesos se rompio" in str(c.args) for c in log.error.call_args_list)
