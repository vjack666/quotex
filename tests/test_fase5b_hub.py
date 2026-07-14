"""Tests de Fase 5b — HUB: columna estocástico en panel + endpoint /api/blackbox.

No ejecuta el navegador (JS); verifica el contrato de datos Python:
- StratFRow/StratFReject aceptan stoch_m15 (lo que alimenta la columna).
- /api/blackbox devuelve el reporte (se prueba la coroutine del endpoint
  sin httpx, monkeypatcheando build_stats a una DB temporal).
"""
import asyncio
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hub.strat_f_state import StratFRow, StratFReject  # noqa: E402
import hub.server as srv  # noqa: E402


def test_stratf_row_accepts_stoch():
    r = StratFRow(
        asset="USDCOP_otc", direction="call", strength=60, payout=87,
        ctx="range", event="fractal_up",
        stoch_m15={"k": 12, "d": 14, "estado": "SOBREVENTA"},
    )
    assert r.stoch_m15.get("estado") == "SOBREVENTA"
    # sin stoch sigue funcionando (compatibilidad)
    r2 = StratFRow(asset="X", direction="put", strength=50, payout=80, ctx="", event="")
    assert r2.stoch_m15 is None


def test_stratf_reject_accepts_stoch():
    r = StratFReject(asset="EURUSD_otc", payout=85, skip_reason="payout", stoch_m15={"k": 80, "d": 78, "estado": "SOBRECOMPRA"})
    assert r.stoch_m15.get("estado") == "SOBRECOMPRA"


def test_api_blackbox_endpoint_returns_report():
    import black_box_recorder as bbr
    import stats as stats_mod

    tmp = tempfile.mkdtemp()
    db = str(Path(tmp) / "bb_hub.db")
    bbr.BLACK_BOX_DB = Path(db)
    rec = bbr.BlackBoxRecorder()
    sid = rec.record_scan_start("STRAT-F", 1)
    rec.record_candidate(sid, "STRAT-F", {
        "asset": "USDCOP_otc", "direction": "call", "score": 60.0, "payout": 87,
        "decision": "ACCEPTED", "candles_1m": [], "stoch_m15": {"k": 12, "d": 14, "estado": "SOBREVENTA"},
    })
    rec.resolve_candidate_for_asset("USDCOP_otc", "WIN", 8.0, stoch_m15={"k": 12, "d": 14, "estado": "SOBREVENTA"})

    def fake_build(db_path=None):
        return stats_mod.build_stats(db)

    orig = srv.build_stats
    srv.build_stats = fake_build
    try:
        data = asyncio.run(srv.api_blackbox())
    finally:
        srv.build_stats = orig

    assert data["total_resolved"] == 1
    assert data["win_rate"] == 100.0
    assert "by_asset" in data
    assert "loss_ranking" in data
    assert "stoch_ab" in data
