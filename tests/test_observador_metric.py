"""Tests T1 — Metric (PTM v3: ningún número desnudo)."""
import dataclasses

import pytest

from observador.metric import Metric


def test_metric_valida_e_inmutable():
    m = Metric(2.5, 0.8, 0.9, "test_v1")
    assert m.raw == 2.5 and m.formula_version == "test_v1"
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.raw = 0


@pytest.mark.parametrize("kw", [
    dict(raw="x", normalized=0.5, confidence=0.5, formula_version="v"),
    dict(raw=1, normalized=2.0, confidence=0.5, formula_version="v"),
    dict(raw=1, normalized=0.5, confidence=1.5, formula_version="v"),
    dict(raw=1, normalized=0.5, confidence=-0.1, formula_version="v"),
    dict(raw=1, normalized=0.5, confidence=0.5, formula_version=""),
    dict(raw=True, normalized=0.5, confidence=0.5, formula_version="v"),
])
def test_metric_invalida(kw):
    with pytest.raises(ValueError):
        Metric(**kw)
