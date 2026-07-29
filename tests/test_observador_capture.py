"""T5/T6 — CaptureMonitor (dimensiones configurables) y cierre natural/captura."""
from observador.evolution import (
    CAPTURE_LIMIT,
    CaptureMonitor,
    EpisodeEvolutionWriter,
)
from observador.store import EpisodeStore

# Fixture de cfg con umbrales LOCALES (no literales del SDD).
CFG_CAPTURE = {
    "dimensions": ["structural", "pressure", "energy", "direction",
                   "volatility"],
    "change_version": "capture_v1",
    "asset": {
        "silence_window_bars": 4,
        "pressure_delta_threshold_pips": 2.0,
        "energy_delta_threshold_pips": 2.0,
        "direction_delta_threshold_pips": 1.0,
        "volatility_range_threshold_pips": 3.0,
    },
}


def _bar(i, dist, state="QUIET"):
    return {"bar_index": i, "ts": float(i), "distance_pips": dist,
            "mfe": max(dist, 0.0), "mae": min(dist, 0.0), "state": state}


def test_monitor_vivo_si_una_dimension_cambia():
    m = CaptureMonitor(CFG_CAPTURE)
    # distancias saltando > umbral de presión: dimensión pressure viva
    bars = [_bar(i, 10.0 * i) for i in range(8)]
    assert m.should_stop(bars) is False
    # solo cambio estructural (distancias planas, estados distintos)
    bars = [_bar(i, 5.0, state="QUIET" if i % 2 else "EXPANSION")
            for i in range(8)]
    assert m.should_stop(bars) is False
    # solo dirección (deriva lenta acumulada > umbral direction)
    bars = [_bar(i, 0.5 * i) for i in range(8)]
    assert m.should_stop(bars) is False


def test_monitor_corta_cuando_todas_quietas():
    m = CaptureMonitor(CFG_CAPTURE)
    bars = [_bar(i, 5.0) for i in range(8)]  # plano total, mismo estado
    assert m.should_stop(bars) is True


def test_monitor_no_corta_sin_ventana_completa():
    m = CaptureMonitor(CFG_CAPTURE)
    bars = [_bar(i, 5.0) for i in range(3)]  # < silence_window_bars
    assert m.should_stop(bars) is False


def test_monitor_no_corta_por_conteo_fijo():
    # una serie larguísima pero SIEMPRE viva jamás corta (no hay tope de barras)
    m = CaptureMonitor(CFG_CAPTURE)
    bars = [_bar(i, 10.0 * i) for i in range(500)]
    assert m.should_stop(bars) is False


def _writer():
    w = EpisodeEvolutionWriter("EURUSD", origin_ts=0.0, origin_price=1.1,
                               vars_version="vars_v1")
    w.record(0, {"ts": 1.0, "close": 1.1010}, "EXPANSION")
    w.record(1, {"ts": 2.0, "close": 1.0995}, "PRESSURE")
    return w


def test_close_fin_natural():
    for reason in ("NEW_EXPANSION", "NEW_PRESSURE", "OPPOSITE_STRUCTURE",
                   "CHAOS"):
        closing = _writer().close(reason, 0.9)
        assert closing["finished"] == 1
        assert closing["end_reason"] == reason
        assert closing["end_confidence"] == 0.9
        assert closing["capture_limit"] == 0


def test_close_fin_de_captura():
    closing = _writer().close(CAPTURE_LIMIT, 0.8)
    assert closing["finished"] == 0
    assert closing["end_reason"] is None
    assert closing["end_confidence"] == 0.8
    assert closing["capture_limit"] == 1


def test_ambos_caminos_producen_fila_correcta(tmp_path):
    base = {"quality": 0.5, "velocity": "slow", "violence": "low",
            "curve_shape": "flat", "symmetry": 0.5, "episode_type": "REBOUND",
            "duration_bars": 2, "summary_version": "summary_v1",
            "vars_version": "vars_v1"}
    with EpisodeStore(str(tmp_path / "e.db")) as st:
        nat = dict(base, episode_id=1, **_writer().close("NEW_PRESSURE", 0.9))
        cap = dict(base, episode_id=2, **_writer().close(CAPTURE_LIMIT, 0.7))
        st.save_summary(nat)
        st.save_summary(cap)
        row_n = st.get_summary(1)
        row_c = st.get_summary(2)
    assert (row_n["finished"], row_n["end_reason"], row_n["capture_limit"]) \
        == (1, "NEW_PRESSURE", 0)
    assert (row_c["finished"], row_c["end_reason"], row_c["capture_limit"]) \
        == (0, None, 1)
