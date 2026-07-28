"""Tests del Agente C — T6 (miner), T8 (reporter), T12 (lifecycle).

Aislado: usa InMemoryLawStore de storage.py como store. En ensamblaje los
módulos reales de A/B (reader/space/splitter/falsifier) toman precedencia.

Vocabulario REAL del Atlas (PTM v3): el efecto medido es 'reversal' = el
impulso revierte (distance_pips del ultimo barra < 0), NO mfe>0. La candidata
dominante descubierta en datos es curve_shape=='flat' -> reversal (~90%).
"""

from __future__ import annotations

import os
import tempfile

from discovery.types import Law, Episode
from discovery.storage import InMemoryLawStore
from discovery.miner import discover
from discovery.reporter import emit_lab_doc, record_law, add_transition, transition_log, slugify


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
def _mk_episode(ep_id, curve_shape, reverses, source="REPLAY:parquet:EURUSD_M1.parquet",
                market="forex", state_final="OK"):
    """Episode. Si `reverses`, el distance_pips del ultimo barra es < 0."""
    final_dist = -5.0 if reverses else 8.0
    evolution = [{
        "bar_index": 0, "ts": 0.0, "price": 1.0,
        "distance_pips": 10.0, "mfe": 5.0, "mae": -1.0,
        "state": "X", "vars_json": "{}", "vars_version": 1,
    }, {
        "bar_index": 1, "ts": 1.0, "price": 1.0,
        "distance_pips": final_dist, "mfe": 5.0, "mae": -1.0,
        "state": "Y", "vars_json": "{}", "vars_version": 1,
    }]
    summary = {
        "quality": "HIGH", "symmetry": 0.5, "duration_bars": 30,
        "episode_type": "REBOUND", "curve_shape": curve_shape, "velocity": "FAST",
        "violence": "LOW", "end_reason": "NEW_PRESSURE", "finished": 1,
        "capture_limit": 0, "end_confidence": 0.9, "mfe": 5.0,
    }
    return Episode(
        episode_id=ep_id, asset="EURUSD", market=market, source=source,
        ts_open=0.0, ts_close=1.0, state_final=state_final,
        evolution=evolution, summary=summary,
    )


def _make_episodes():
    eps = []
    # Subconjunto CLARO de 'curve_shape=flat -> reversal':
    # 60 episodes flat que revierten (distance final < 0).
    for i in range(60):
        eps.append(_mk_episode(i, "flat", reverses=True))
    # 60 episodes que NO son flat y NO revierten (distance final > 0).
    for i in range(60, 120):
        eps.append(_mk_episode(i, "convex", reverses=False))
    return eps


CFG = {
    "seed": 7,
    "min_sample": 10,
    "p_cut": 0.05,
    "min_freq": 0.0,
    "max_depth": 2,
    "split_year": 0,       # year(0)=1970 >= 0 -> todo en test
    "n_perm": 200,
    "timeframes": ("M1", "M5"),
    "discovery_version": "discovery_v1",
}


# --------------------------------------------------------------------------- #
# T6 — miner
# --------------------------------------------------------------------------- #
def test_miner_discovers_curve_flat_reversal():
    store = InMemoryLawStore()
    eps = _make_episodes()

    # baseline empírico del fixture: reversal global = 60/120 = 0.5
    baseline = sum(1 for ep in eps if (ep.evolution[-1].get("distance_pips") or 0) < 0) / len(eps)

    laws = discover(eps, CFG, store)

    assert len(laws) >= 1, "debe promover al menos 1 ley"
    strong = [l for l in laws if l.probability > baseline and l.state == "EXPERIMENTAL"]
    assert strong, "debe haber al menos 1 ley con prob>baseline y EXPERIMENTAL"

    # la ley 'curve_shape=flat -> reversal' debe ser reconocida
    names = {l.name for l in laws}
    assert "curva_plana_revierte" in names, "debe descubrir 'curve_shape=flat -> reversal'"

    # deterministicidad: misma entrada + cfg => mismo numero de leyes y mismos ids
    store2 = InMemoryLawStore()
    laws2 = discover(_make_episodes(), CFG, store2)
    assert [l.id for l in laws] == [l.id for l in laws2]
    assert len(laws) == len(laws2)


def test_miner_no_promote_below_min_sample():
    small_cfg = dict(CFG, min_sample=100)
    store = InMemoryLawStore()
    eps = [_mk_episode(i, "flat", reverses=True) for i in range(5)]
    laws = discover(eps, small_cfg, store)
    assert all(l.cases_studied >= 100 for l in laws)
    assert not any(l.name == "curva_plana_revierte" for l in laws)


# --------------------------------------------------------------------------- #
# T8 — reporter
# --------------------------------------------------------------------------- #
def test_reporter_emit_lab_doc_fields():
    law = Law(
        id="#1", name="curva_plana_revierte",
        conditions="curve_shape == 'flat' -> reversal (distance_pips final < 0)",
        probability=0.90, confidence="HIGH", markets=("forex",),
        sources=("Dukascopy",), timeframes=("M1", "M5"), cases_studied=10363,
        state="EXPERIMENTAL", discovery_version="discovery_v1",
        script_ref="LAB_001_curva_plana_revierte.md",
        p_value=0.01, ci=(0.72, 0.88),
    )
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "LAB_001_curva_plana_revierte.md")
    emit_lab_doc(law, path)

    assert os.path.isfile(path)
    with open(path, encoding="utf-8") as fh:
        doc = fh.read()

    for field_text in ("variables", "efecto", "IC", "walk-forward", "p",
                       "frecuencia", "markets", "sources", "state"):
        assert field_text in doc, f"falta campo R7: {field_text}"
    assert "forex" in doc
    assert "Dukascopy" in doc
    assert "EXPERIMENTAL" in doc
    assert "LAB_001_curva_plana_revierte.md" in doc


def test_reporter_record_law_no_overwrite():
    store = InMemoryLawStore()
    law = Law(id="#1", name="ley_a", conditions="x", probability=0.6,
              confidence="LOW", markets=("forex",), sources=("Dukascopy",),
              timeframes=("M1",), cases_studied=20, state="EXPERIMENTAL")
    record_law(law, store)
    other = Law(id="#1", name="ley_modificada", conditions="y", probability=0.99,
                confidence="HIGH", markets=("otc",), sources=("Quotex OTC",),
                timeframes=("M5",), cases_studied=99, state="VALIDADA")
    record_law(other, store)
    kept = store.get_law("#1")
    assert kept is not None
    assert kept.name == "ley_a", "record_law NO debe sobrescribir una ley existente"
    assert kept.state == "EXPERIMENTAL"


# --------------------------------------------------------------------------- #
# T12 — lifecycle
# --------------------------------------------------------------------------- #
def test_lifecycle_add_transition_validada():
    store = InMemoryLawStore()
    law = Law(id="#1", name="curva_plana_revierte", conditions="c",
              probability=0.90, confidence="HIGH", markets=("forex",),
              sources=("Dukascopy",), timeframes=("M1", "M5"), cases_studied=10363,
              state="EXPERIMENTAL", discovery_version="discovery_v1",
              script_ref="LAB_001_x.md")
    store.save_law(law)

    updated = add_transition(store, "#1", "VALIDADA", "v2", "walk-forward estable en hold-out")
    assert updated is not None
    assert updated.state == "VALIDADA"

    again = store.get_law("#1")
    assert again is not None, "la ley NO debe borrarse en lifecycle"
    assert again.state == "VALIDADA"
    assert len(store.list_laws()) == 1

    log = transition_log(store, "#1")
    assert any(t["state"] == "VALIDADA" and t["version"] == "v2" for t in log)


def test_lifecycle_obsoleta_no_borra():
    store = InMemoryLawStore()
    law = Law(id="#2", name="otra", conditions="c", probability=0.5,
              confidence="LOW", markets=("forex",), sources=("Dukascopy",),
              timeframes=("M1",), cases_studied=15, state="EXPERIMENTAL")
    store.save_law(law)
    add_transition(store, "#2", "OBSOLETA", "v3", "degradada en nuevo regimen")
    kept = store.get_law("#2")
    assert kept is not None
    assert kept.state == "OBSOLETA"
    assert len(store.list_laws()) == 1


def test_lifecycle_invalid_state_rejected():
    store = InMemoryLawStore()
    law = Law(id="#3", name="x", conditions="c", probability=0.5,
              confidence="LOW", markets=("forex",), sources=("Dukascopy",),
              timeframes=("M1",), cases_studied=15, state="EXPERIMENTAL")
    store.save_law(law)
    try:
        add_transition(store, "#3", "NO_EXISTE", "v4", "motivo")
    except ValueError:
        pass
    else:
        raise AssertionError("debio rechazar state invalido")
    assert store.get_law("#3").state == "EXPERIMENTAL"


def test_slugify_basics():
    assert slugify("curva plana revierte") == "curva-plana-revierte"
    assert slugify("Ley N") == "ley-n"
