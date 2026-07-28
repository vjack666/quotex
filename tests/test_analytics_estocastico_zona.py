"""Tests del estudio estocástico-zona v2 (salida de zona + métrica binaria)."""
import numpy as np
import pytest

from analytics.config_loader import ZonaConfig, default_config_path
from analytics import estocastico_zona as ez

CFG = ZonaConfig.load(default_config_path())


def test_clasifica_zona_os_ob_fuera():
    k = np.array([10.0, 50.0, 90.0])
    d = np.array([8.0, 45.0, 88.0])
    c = np.zeros(3)
    lab = ez.classify(k, d, c, CFG.as_dict())
    assert list(lab.zona) == [1, 0, 2]


def test_estado_lineas_pegadas_separadas():
    k = np.array([10.0, 10.0, 90.0])
    d = np.array([10.0, 30.0, 80.0])
    c = np.zeros(3)
    lab = ez.classify(k, d, c, CFG.as_dict())
    assert list(lab.estado_lineas) == [0, 2, 2]


def test_salida_zona_deteccion():
    # %K en OS (15) luego sale (50): salida +1 en i=1
    k = np.array([15.0, 50.0])
    d = np.array([12.0, 45.0])
    c = np.zeros(2)
    lab = ez.classify(k, d, c, CFG.as_dict())
    assert lab.salida[1] == 1
    assert lab.salida[0] == 0


def test_binary_stats_senal_real():
    # 4 velas: OS en 0, sale en 1 (alcista), precio sube 5 pip a fwd=1
    k = np.array([15.0, 50.0, 50.0, 50.0])
    d = np.array([12.0, 45.0, 45.0, 45.0])
    c = np.array([1.0000, 1.0000, 1.0005, 1.0005])   # +5 pip en i=2 (tras salida i=1)
    cfg = CFG.as_dict()
    cfg["fwd"] = 1
    cfg["rebote_min_pips"] = 3.0
    st = ez.binary_stats(k, d, c, cfg)
    assert st["n"] == 1
    assert st["wr"] == 1.0
    assert st["wr_os"] == 1.0


def test_magnitude_stats_mayor_que_base():
    # salida de OS en i=1, precio salta 10 pip a fwd=1; base aleatoria plana
    k = np.array([15.0, 50.0, 50.0, 50.0])
    d = np.array([12.0, 45.0, 45.0, 45.0])
    c = np.array([1.0000, 1.0000, 1.0010, 1.0010])   # +10 pip en i=2
    cfg = CFG.as_dict()
    cfg["fwd"] = 1
    st = ez.magnitude_stats(k, d, c, cfg)
    assert st["n"] == 1
    assert st["mean_abs_salida"] == pytest.approx(10.0, abs=1e-6)
    assert st["ratio"] >= 1.0            # el salto se registra (no < ruido)
