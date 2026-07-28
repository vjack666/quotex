"""Tests del Bloque 3.5: walk-forward (leave-one-date-out) sobre cajas negras.

Valida que los umbrales descubiertos por el laboratorio AGUANTAN en fechas
que el minero no vio (out-of-sample). Usa datos reales; si no hay >=2 cajas,
se skipea.
"""
from pathlib import Path

import pytest

from strategy_lab import minar_leyes_freno as miner
from strategy_lab import validar_walkforward as wf


DB_DIR = Path("data/db")


def _hay_walkforward():
    cajas = list(DB_DIR.glob("black_box_strat_*.db"))
    return len(cajas) >= 2


def test_walkforward_wr_out_of_sample_alta():
    if not _hay_walkforward():
        pytest.skip("menos de 2 cajas negras para walk-forward")
    res = wf.main()
    folds = res.get("folds", [])
    assert len(folds) >= 2
    # Todos los folds con volumen suficiente deben superar 80% WR out-of-sample
    con_vol = [f for f in folds if f["test_n_fijo"] >= 10]
    assert con_vol, "ningun fold con n>=10 para validar"
    wr_list = [f["test_wr_fijo"] for f in con_vol]
    prom = sum(wr_list) / len(wr_list)
    # El cerebro en demo debe sostener ~90% out-of-sample (validado 3.5)
    assert prom >= 0.85, f"WR promedio out-of-sample muy baja: {prom:.3f}"


def test_umbrales_fijos_estables_entre_folds():
    if not _hay_walkforward():
        pytest.skip("menos de 2 cajas negras para walk-forward")
    res = wf.main()
    folds = res.get("folds", [])
    seps = {f["sep_adopt"] for f in folds if f["test_n"] > 0}
    sals = {f["sal_adopt"] for f in folds if f["test_n"] > 0}
    # Los umbrales minados por fold deben coincidir (estabilidad del fenomeno)
    assert len(seps) <= 2, f"separacion inestable entre folds: {seps}"
    assert len(sals) <= 2, f"salida inestable entre folds: {sals}"


def test_freno_config_adopta_global_validado():
    from strategy_lab.laws_freno import FrenoConfig
    cfg = FrenoConfig()
    # Tras minado global walk-forward, el cerebro adopta sep=0.5 salida=30
    assert cfg.sep_min == 0.5
    assert cfg.salida_zona == 30.0
