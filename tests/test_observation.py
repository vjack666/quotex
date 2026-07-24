"""Tests Feature 27 — Observación en vivo (build_entry_experience)."""
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from observation import build_entry_experience, build_experience_from_candidate_row
from experience_schema import MarketExperience
from models import Candle


def _mock_candidate():
    cand = mock.Mock()
    cand.asset = "EURUSD_otc"
    cand.direction = "CALL"
    cand.score = 72.0
    cand.payout = 85
    cand.candles_15m = [Candle(ts=1753300000, open=1.1, high=1.12, low=1.09, close=1.11)]
    return cand


def test_arc_cerrado_con_win():
    exp = build_entry_experience(
        candidate=_mock_candidate(),
        strategy_details={"ctx": "alcista", "event": "rebote", "pattern": "engulfing"},
        stoch_m15={"estado": "sobreventa", "k": 15, "d": 20},
        order_result="WIN",
        profit=8.5,
        entry_price=1.1100,
        exit_price=1.1110,
        loss_reason=None,
        improvement_hint=None,
        ts=1753300000,
        duration_sec=300,
    )
    assert isinstance(exp, MarketExperience)
    assert exp.is_closed()
    assert exp.resultado["decision"] == "WIN"
    assert exp.resultado["profit"] == 8.5
    assert exp.resultado["pips_netos"] == 10.0
    assert exp.evento["direccion"] == "CALL"
    assert exp.contexto_previo["stoch_m15"]["zone"] == "sobreventa"
    # El capturador NO etiqueta soporte/resistencia/FVG
    dump = str(exp.to_dict()).lower()
    assert "soporte" not in dump and "resistencia" not in dump and "fvg" not in dump


def test_sin_order_result_arco_sin_cerrar():
    exp = build_entry_experience(
        candidate=_mock_candidate(),
        order_result=None,
        ts=1753300000,
    )
    # Devuelve None o arco NO cerrado
    assert exp is None or not exp.is_closed()


def test_sin_datos_minimos_devuelve_none():
    assert build_entry_experience(candidate=None) is None
    assert build_experience_from_candidate_row({}) is None


def test_record_es_unico_write_path():
    """observation.py no debe leer la memoria (query_similar) ni escribirla directo."""
    src = (Path(__file__).resolve().parent.parent / "src" / "observation.py").read_text(
        encoding="utf-8"
    )
    assert "query_similar" not in src
    assert "ExperienceMemory(" not in src  # observation solo CONSTRUYE; graba el hook


def test_hook_usa_record():
    """El hook en black_box_recorder graba con ExperienceMemory().record()."""
    src = (Path(__file__).resolve().parent.parent / "src" / "black_box_recorder.py").read_text(
        encoding="utf-8"
    )
    assert "ExperienceMemory().record(" in src
    assert "OBSERVATION_ENABLED" in src
