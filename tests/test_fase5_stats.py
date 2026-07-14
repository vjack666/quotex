"""Tests de Fase 5 — stats.py lee la caja negra y calcula métricas.

Usa una DB temporal de la caja negra con candidatos STRAT-F resueltos.
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import black_box_recorder as bbr
import stats as stats_mod


def _seed(db_path: str):
    bbr.BLACK_BOX_DB = Path(db_path)
    rec = bbr.BlackBoxRecorder()
    sid = rec.record_scan_start("STRAT-F", 1)
    # 3 operaciones resueltas: 2 WIN, 1 LOSS (direccion_equivocada, stoch extremo)
    rec.record_candidate(sid, "STRAT-F", {
        "asset": "USDCOP_otc", "direction": "call", "score": 60.0, "payout": 87,
        "decision": "ACCEPTED", "candles_1m": [], "stoch_m15": {"k": 12, "d": 14, "estado": "SOBREVENTA"},
    })
    rec.resolve_candidate_for_asset("USDCOP_otc", "WIN", 8.0, stoch_m15={"k": 12, "d": 14, "estado": "SOBREVENTA"})
    rec.record_candidate(sid, "STRAT-F", {
        "asset": "EURUSD_otc", "direction": "put", "score": 65.0, "payout": 85,
        "decision": "ACCEPTED", "candles_1m": [], "stoch_m15": {"k": 80, "d": 78, "estado": "SOBRECOMPRA"},
    })
    rec.resolve_candidate_for_asset("EURUSD_otc", "WIN", 7.0, stoch_m15={"k": 80, "d": 78, "estado": "SOBRECOMPRA"})
    rec.record_candidate(sid, "STRAT-F", {
        "asset": "GBPUSD_otc", "direction": "call", "score": 55.0, "payout": 84,
        "decision": "ACCEPTED", "candles_1m": [], "stoch_m15": {"k": 75, "d": 72, "estado": "SOBRECOMPRA"},
    })
    rec.resolve_candidate_for_asset(
        "GBPUSD_otc", "LOSS", -10.0,
        stoch_m15={"k": 75, "d": 72, "estado": "SOBRECOMPRA"},
        loss_reason="direccion_equivocada",
        improvement_hint="revisar filtro M15",
    )
    return db_path


def test_build_stats_aggregates_correctly():
    tmp = tempfile.mkdtemp()
    db = str(Path(tmp) / "bb_stats.db")
    _seed(db)

    s = stats_mod.build_stats(db)
    assert s["total_resolved"] == 3
    assert s["wins"] == 2
    assert s["losses"] == 1
    assert abs(s["win_rate"] - 66.67) < 0.1
    # expectancy = (8 + 7 - 10) / 3 = 1.666...
    assert abs(s["expectancy"] - 1.6667) < 0.001
    # por asset
    assert "USDCOP_otc" in s["by_asset"]
    assert s["by_asset"]["USDCOP_otc"]["win_rate"] == 100.0
    # ranking de pérdidas
    assert s["loss_ranking"][0]["reason"] == "direccion_equivocada"
    assert s["loss_ranking"][0]["count"] == 1
    assert "revisar filtro M15" in s["loss_ranking"][0]["hint"]
    # A/B estocástico: 3 extremo, 0 neutro
    assert s["stoch_ab"]["extremo"]["n"] == 3
    assert "neutro" not in s["stoch_ab"]


def test_render_report_includes_sections():
    tmp = tempfile.mkdtemp()
    db = str(Path(tmp) / "bb_stats2.db")
    _seed(db)
    s = stats_mod.build_stats(db)
    text = stats_mod.render_report(s)
    assert "Caja Negra STRAT-F" in text
    assert "Win rate" in text
    assert "Ranking de pérdidas" in text
    assert "A/B estocástico" in text
    assert "direccion_equivocada" in text


def test_empty_db_returns_zeroed_stats():
    tmp = tempfile.mkdtemp()
    db = str(Path(tmp) / "bb_empty.db")
    bbr.BLACK_BOX_DB = Path(db)
    bbr.BlackBoxRecorder()  # crea el esquema
    s = stats_mod.build_stats(db)
    assert s["total_resolved"] == 0
    assert s["win_rate"] == 0.0
    assert s["loss_ranking"] == []
