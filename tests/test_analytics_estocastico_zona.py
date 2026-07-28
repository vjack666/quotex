"""Tests del estudio estocástico-zona: clasificación con números."""
import numpy as np
import pytest

from analytics.config_loader import ZonaConfig, default_config_path
from analytics import estocastico_zona as ez

CFG = ZonaConfig.load(default_config_path())


def test_clasifica_zona_os_ob_fuera():
    k = np.array([10.0, 50.0, 90.0])   # OS, fuera, OB
    d = np.array([8.0, 45.0, 88.0])
    c = np.zeros(3)
    lab = ez.classify(k, d, c, CFG.as_dict())
    assert list(lab.zona) == [1, 0, 2]


def test_estado_lineas_pegadas_separadas():
    k = np.array([10.0, 10.0, 90.0])          # gap 0 / 0 / 0
    d = np.array([10.0, 30.0, 80.0])          # gap 0 / 20 / 10
    c = np.zeros(3)
    lab = ez.classify(k, d, c, CFG.as_dict())
    # gap 0 -> pegadas(0); gap 20 -> separadas(2); gap 10 -> separadas(2, sep_min=5)
    assert list(lab.estado_lineas) == [0, 2, 2]


def test_cruce_signo():
    k = np.array([10.0, 30.0, 5.0])           # K-D: +2 -> -25 -> -25
    d = np.array([8.0, 50.0, 6.0])            # diff: +2, -20, -1
    c = np.zeros(3)
    lab = ez.classify(k, d, c, CFG.as_dict())
    # i=1: diff pasa de + a - -> cruce -1
    assert lab.cruce[1] == -1
    assert lab.cruce[0] == 0


def test_en_zona_separadas_y_despegue():
    # construyo una secuencia: en OS, lineas separadas, cruce +, precio sube
    k = np.array([15.0, 8.0, 18.0, 18.0])
    d = np.array([13.0, 12.0, 10.0, 12.0])
    c = np.array([1.0000, 1.0000, 1.0005, 1.0030])   # sube 30 pip a fwd=1
    cfg = CFG.as_dict()
    cfg["fwd"] = 1
    lab = ez.classify(k, d, c, cfg)
    # velas 2 y 3: ambas en OS (<=20) y separadas (|K-D|>=5)
    assert lab.en_zona_sep[2]
    assert lab.en_zona_sep[3]
    # cruce + en i=2 (K pasa de bajo a alto vs D) -> despegue si precio sube
    assert lab.cruce[2] == 1
    assert lab.despegue[2]
