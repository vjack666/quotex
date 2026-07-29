"""Tests del laboratorio de aprendizaje por activo (agent_lab)."""

import asyncio
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import agent_lab as lab  # noqa: E402


def _zigzag(n=80):
    """Velas con %K en triangulo: 20->80 (up) luego 80->20 (down) por bloque de 40.

    En 80 velas: 2 ciclos up + 2 ciclos down = 4 ciclos. Precio sube
    monotono para que el patron post-ciclo sea 'up' congruente.
    """
    candles = []
    for i in range(n):
        block = i % 40
        if block < 20:
            k = 20.0 + (60.0 * block / 19.0)      # 20 -> 80 (up)
        else:
            k = 80.0 - (60.0 * (block - 20) / 19.0)  # 80 -> 20 (down)
        candles.append({"k": k, "close": 100.0 + i * 0.1})
    return candles


def test_detect_stoch_cycles_zigzag():
    # 80 velas -> 2 ciclos up (20->80) y 2 down (80->20).
    k_vals = [c["k"] for c in _zigzag(80)]
    cycles = lab.detect_stoch_cycles(k_vals)
    ups = [c for c in cycles if c["dir"] == "up"]
    downs = [c for c in cycles if c["dir"] == "down"]
    assert len(ups) == 2
    assert len(downs) == 2


def test_detect_stoch_cycles_flat_mid():
    # %K siempre en medio -> 0 ciclos.
    cycles = lab.detect_stoch_cycles([50.0] * 30)
    assert cycles == []


def test_post_cycle_direction():
    closes = [100.0] * 10 + [101.0, 102.0, 103.0, 104.0, 105.0]
    assert lab.post_cycle_direction(closes, 9, 5) == "up"
    closes2 = [100.0] * 10 + [99.0, 98.0, 97.0, 96.0, 95.0]
    assert lab.post_cycle_direction(closes2, 9, 5) == "down"
    closes3 = [100.0] * 16
    assert lab.post_cycle_direction(closes3, 9, 5) == "flat"


def test_learn_from_candles_counts():
    candles = _zigzag(80)
    # precio sube monotono SIEMPRE -> tanto ciclo up como down predicen 'up'.
    # up->up = 1.0; down->up = 1.0 (no down). congruent = (2+0)/4 = 0.5.
    res = lab.learn_from_candles(candles, "M5")
    assert res["n_cycles"] == 4
    assert res["n_up"] == 2 and res["n_down"] == 2
    assert res["up_predict_up_wr"] == 1.0
    assert res["congruent_wr"] == 0.5  # down no predice down porque el precio siempre sube


def test_learn_from_candles_down_predicts_down():
    # Precio congruente POR BLOQUE: en cada bloque de 40, sube en las
    # primeras 25 velas (cubre el ciclo up en block=19 + post 5) y baja en
    # las siguientes (cubre el ciclo down en block=39 + post 5).
    # Usamos 125 velas (3 bloques de 40 + 5 de cola) para que el ultimo
    # ciclo (down en i=119) tambien tenga post-velas.
    candles = []
    for i in range(125):
        block = i % 40
        local = i - (i // 40) * 40  # 0..39 dentro del bloque
        if block < 20:
            k = 20.0 + (60.0 * block / 19.0)   # 20 -> 80 (up, contado en block=19)
        else:
            k = 80.0 - (60.0 * (block - 20) / 19.0)  # 80 -> 20 (down, contado en block=39)
        if local <= 24:
            close = 100.0 + local * 0.1
        else:
            close = 100.0 + 24 * 0.1 - (local - 24) * 0.1
        candles.append({"k": k, "close": close})
    res = lab.learn_from_candles(candles, "M5")
    assert res["n_cycles"] == 6
    assert res["congruent_wr"] == 1.0


def test_merge_profile_accumulates():
    a = {"n_cycles": 4, "n_up": 2, "n_down": 2,
         "post_up_after_up": 2, "post_down_after_up": 0,
         "post_up_after_down": 0, "post_down_after_down": 2, "rounds": 1}
    b = {"n_cycles": 4, "n_up": 2, "n_down": 2,
         "post_up_after_up": 2, "post_down_after_up": 0,
         "post_up_after_down": 0, "post_down_after_down": 2}
    m = lab._merge_profile(a, b)
    assert m["n_cycles"] == 8
    assert m["rounds"] == 2
    assert m["congruent_wr"] == 1.0


def test_run_lab_demo_accumulates():
    async def fake_fetch(client, asset, tf_sec, count):
        return _zigzag(80)  # tamano fijo para controlar el conteo
    # Limpiar perfil previo para aislar el test.
    if os.path.exists(lab.PROFILES_PATH):
        os.remove(lab.PROFILES_PATH)
    assets = ["EUR/USD", "GBP/USD"]
    profiles = asyncio.run(lab.run_lab(assets, fake_fetch, None, rounds=2))
    assert "EUR/USD" in profiles
    # 2 rondas x (4 ciclos de 80 velas) = 8 ciclos por TF.
    assert profiles["EUR/USD"]["M5"]["n_cycles"] == 8
    # Se guardo el perfil durable.
    assert os.path.exists(lab.PROFILES_PATH)
    saved = lab.load_profiles()
    assert "EUR/USD" in saved


def test_run_lab_respects_max_assets():
    async def fake_fetch(client, asset, tf_sec, count):
        return _zigzag(count)
    if os.path.exists(lab.PROFILES_PATH):
        os.remove(lab.PROFILES_PATH)
    assets = [f"XXX/{i}" for i in range(15)]  # mas de 10
    profiles = asyncio.run(lab.run_lab(assets, fake_fetch, None, rounds=1))
    # Solo procesa los 10 primeros (los preexistentes no cuentan aqui).
    assert len([a for a in profiles if a.startswith("XXX/")]) == lab.LAB_MAX_ASSETS
