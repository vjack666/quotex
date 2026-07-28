"""Tests del Bloque 3: el laboratorio descubre los numeros del freno y el
cerebro los adopta (en vez de semilla a mano).

Usa datos REALES de cajas negras. Si no hay DB, se skipean (no es fallo).
"""
import json
from pathlib import Path

import pytest

from strategy_lab.laws_freno import FrenoConfig, ley_stoch_extremo
from strategy_lab.law_engine import LawContext, LawResult
from strategy_lab import minar_leyes_freno as miner


DB = "data/db/black_box_strat_2026-07-17.db"


def _db_ok():
    return Path(DB).exists()


def test_miner_produce_json_con_datos_reales():
    if not _db_ok():
        pytest.skip("caja negra no disponible")
    out = miner.minar(DB)
    assert "meta" in out
    assert out["meta"]["eventos_total"] > 0
    # WR base del freno coherente con lo ya validado (~88-91%)
    assert 0.80 <= out["meta"]["wr_base_freno"] <= 0.99
    # Curvas presentes y con el barrido completo
    assert len(out["ley_5_separacion"]["curve"]) >= 8
    assert len(out["ley_6_salida_zona"]["curve"]) >= 6
    # Adoptados explicitos (eleccion honesta walk-forward 3.5): sep redundante
    # (WR base ya alta) -> 0.5 (no filtrar); salida_zona=30 (banda mas ancha).
    assert out["adoptados"]["sep_min"] == 0.5
    assert out["adoptados"]["salida_zona"] == 30.0


def test_freno_config_adopta_descubiertos():
    # El JSON existe en el repo (lo escribio el miner en este turno).
    cfg = FrenoConfig()  # __post_init__ carga el JSON
    assert cfg.sep_min == 0.5, f"esperado 0.5 adoptado, got {cfg.sep_min}"
    assert cfg.salida_zona == 30.0, f"esperado 30.0 adoptado, got {cfg.salida_zona}"


def test_ley_stoch_usa_salida_zona_descubierta():
    cfg = FrenoConfig()
    # CALL: k debe ser < 30 para pasar (antes era <20). k=25 pasa.
    ctx_pass = LawContext(stoch_m15={"k": 25.0}, direction_hint="CALL")
    r = ley_stoch_extremo(ctx_pass, cfg)
    assert isinstance(r, LawResult)
    assert r.ok is True
    # CALL: k=35 ya no pasa (>=30).
    ctx_fail = LawContext(stoch_m15={"k": 35.0}, direction_hint="CALL")
    r2 = ley_stoch_extremo(ctx_fail, cfg)
    assert r2.ok is False
    # PUT: k=65 pasa (>= 100-30=70? no, 65<70 => falla). k=72 pasa.
    ctx_put = LawContext(stoch_m15={"k": 72.0}, direction_hint="PUT")
    assert ley_stoch_extremo(ctx_put, cfg).ok is True
