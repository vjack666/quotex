"""Tests del Agente A (T1 config, T2 reader, T3 space) — Discovery Engine.

Debe quedar en VERDE sin imports a bot/scanner/strat_fractal.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

from discovery.config_loader import load_config
from discovery.reader import classify_source, load_episodes
from discovery.space import (
    build_feature_space,
    enumerate_features,
    feature_count,
    fit_volatility_reference,
)
from discovery.types import Episode

# DB real del Atlas (CONTRATO: data/observador/episodes_eurusd_14y.db).
_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "observador",
    "episodes_eurusd_14y.db",
)

# Campos del summary que NO deben aparecer como feature del predictor (R8).
_NON_PREDICTOR = {"end_reason", "mfe", "mae"}


# --------------------------------------------------------------------------
# T1 — config_loader
# --------------------------------------------------------------------------

def test_config_loader_fields_and_values():
    cfg = load_config()
    # Campos obligatorios presentes.
    for key in (
        "min_sample",
        "p_cut",
        "min_freq",
        "max_depth",
        "seed",
        "split_year",
        "sources",
        "markets",
    ):
        assert key in cfg, f"falta campo {key}"
    # seed/p_cut se reflejan.
    assert cfg["seed"] == 20260727
    assert cfg["p_cut"] == 0.05
    assert isinstance(cfg["sources"], list)
    assert isinstance(cfg["markets"], list)
    assert "Dukascopy" in cfg["sources"]
    assert "forex" in cfg["markets"]


# --------------------------------------------------------------------------
# T2 — reader / classify_source
# --------------------------------------------------------------------------

def test_classify_source_forex():
    assert classify_source("REPLAY:parquet:EURUSD_M1.parquet") == (
        "forex",
        "Dukascopy",
    )


def test_classify_source_otc():
    assert classify_source("REPLAY:parquet:EURUSD_otc_M1.parquet") == (
        "otc",
        "Quotex OTC",
    )


def test_reader_loads_real_db_with_limit():
    if not os.path.exists(_DB_PATH):
        pytest.skip(f"DB no disponible: {_DB_PATH}")

    # Toma 50 ids explícitos (LIMIT 50) y luego carga esos episodios.
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    ids = [r["id"] for r in conn.execute("SELECT id FROM episodes LIMIT 50")]
    conn.close()
    assert len(ids) > 0

    eps = list(load_episodes(_DB_PATH))
    # Itera TODOS, pero verificamos que al menos los 50 ids están presentes.
    loaded_ids = {e.episode_id for e in eps}
    for i in ids:
        assert i in loaded_ids

    # Verifica structura de un episodio concreto (uno de los 50).
    sample = next(e for e in eps if e.episode_id == ids[0])
    assert isinstance(sample, Episode)
    assert sample.market == "forex"
    assert sample.source == "Dukascopy"
    assert len(sample.evolution) > 0
    assert isinstance(sample.summary, dict)
    # El summary completo conserva end_reason (para miner), pero NO como feature.
    assert "end_reason" in sample.summary


def test_reader_episode_has_no_end_reason_as_feature():
    if not os.path.exists(_DB_PATH):
        pytest.skip(f"DB no disponible: {_DB_PATH}")

    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    first_id = conn.execute("SELECT id FROM episodes LIMIT 1").fetchone()["id"]
    conn.close()

    ep = next(e for e in load_episodes(_DB_PATH) if e.episode_id == first_id)
    feats = enumerate_features(ep)
    # El PREDICTOR no usa end_reason/mfe/mae (R8).
    assert "end_reason" not in feats
    assert "mfe" not in feats
    assert "mae" not in feats


# --------------------------------------------------------------------------
# T3 — space
# --------------------------------------------------------------------------

def _fixture_episode() -> Episode:
    evolution = [
        {"bar_index": 0, "ts": 1.0, "price": 1.0, "distance_pips": 0.0,
         "mfe": 0.0, "mae": 0.0, "state": "EXPANSION", "vars_json": None,
         "vars_version": "v1"},
        {"bar_index": 1, "ts": 2.0, "price": 1.1, "distance_pips": 1.0,
         "mfe": 1.0, "mae": -0.5, "state": "PRESSURE", "vars_json": None,
         "vars_version": "v1"},
        {"bar_index": 2, "ts": 3.0, "price": 1.2, "distance_pips": 2.0,
         "mfe": 2.0, "mae": -1.0, "state": "PRESSURE", "vars_json": None,
         "vars_version": "v1"},
    ]
    summary = {
        "quality": 0.5,
        "velocity": "slow",
        "violence": "low",
        "curve_shape": "flat",
        "symmetry": 0.1,
        "episode_type": "CONTINUATION",
        "duration_bars": 3,
        "mfe": 2.0,
        "mae": -1.0,
        "end_reason": "DEAD_PUSH",  # debe quedar FUERA de features (R8)
        "end_confidence": 1.0,
        "finished": 1,
        "capture_limit": 0,
    }
    return Episode(
        episode_id=999,
        asset="EURUSD",
        market="forex",
        source="Dukascopy",
        ts_open=1.0,
        ts_close=4.0,
        state_final="RESOLUTION",
        evolution=evolution,
        summary=summary,
    )


def test_space_enumerate_expected_features():
    ep = _fixture_episode()
    feats = enumerate_features(ep)
    # Features esperadas derivadas de evolution.
    assert "distance_pips_mean" in feats
    assert "distance_speed" in feats
    assert "state_changes" in feats
    assert "volatility" in feats
    assert "volatility_pct" in feats
    assert "duration_bars" in feats
    # Descriptores del summary.
    assert feats["summary_velocity"] == "slow"
    assert feats["summary_violence"] == "low"
    assert feats["summary_curve_shape"] == "flat"
    # R8: end_reason/mfe/mae NO son features.
    assert "end_reason" not in feats
    assert "mfe" not in feats
    assert "mae" not in feats


def test_space_respects_max_depth():
    cfg = load_config()
    max_depth = int(cfg["max_depth"])
    space = build_feature_space(cfg)
    assert len(space) <= max_depth
    assert feature_count(cfg) == len(space)
    # Determinismo: misma config => mismo espacio (mismos nombres, mismo orden).
    space2 = build_feature_space(cfg)
    assert [s.nombre for s in space] == [s.nombre for s in space2]


def test_space_volatility_percentile_deterministic():
    # Sin referencia cargada, el percentil degrada a volatilidad cruda (determinista).
    ep = _fixture_episode()
    f1 = enumerate_features(ep)["volatility_pct"]
    f2 = enumerate_features(ep)["volatility_pct"]
    assert f1 == f2
    # Con referencia cargada (mismo elemento), el percentil es 1.0 (v<=v) y
    # sigue siendo determinista (igual en llamadas sucesivas).
    fit_volatility_reference([ep])
    p = enumerate_features(ep)["volatility_pct"]
    assert p == 1.0
    assert enumerate_features(ep)["volatility_pct"] == p
