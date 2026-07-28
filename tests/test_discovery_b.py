"""Tests de Agente B: splitter, falsifier, law_store, law_relations, relation_miner.

Sin imports a bot. Sin time.now. Determinismo con semilla.
"""

import sqlite3

from discovery.splitter import walk_forward
from discovery.falsifier import evaluate
from discovery.law_store import SQLiteLawStore
from discovery.law_relations import (
    save_relation,
    get_relations,
    list_relations,
)
from discovery.relation_miner import propose_relations
from discovery.types import Episode, Law, LawRelation


# --- Fixtures ----------------------------------------------------------------

def _ep(episode_id, source, ts_open, mfe, state_final="x"):
    # Efecto medido por el falsifier = 'reversal' (distance_pips final < 0).
    # Si mfe>0 (rebote), el ultimo barra tiene distance_pips negativo.
    final_dist = -abs(mfe) if mfe > 0 else 1.0
    return Episode(
        episode_id=episode_id,
        asset="EURUSD",
        market="forex",
        source=source,
        ts_open=ts_open,
        ts_close=ts_open + 60,
        state_final=state_final,
        evolution=[{"bar_index": 0, "ts": ts_open, "price": 1.0,
                    "distance_pips": final_dist, "mfe": mfe, "mae": 0.0,
                    "state": "X", "vars_json": "{}", "vars_version": 1}],
        summary={"mfe": mfe, "end_reason": "DEAD_PUSH"},
    )


def _make_episodes():
    """2 fuentes, ts_open crecientes. Ano 2020 (train) y 2023 (test).

    Dukascopy test: 6 rebotes (mfe>0) + 10 no-rebote => baseline baja (~0.375)
    para que la ley real (predice solo rebotes) supere p_cut claramente.
    """
    t2020 = 1577836800.0
    t2023 = 1672531200.0
    eps = []
    # fuente A (Dukascopy): train 2020
    eps.append(_ep(1, "Dukascopy", t2020 + 1, 0.0))
    eps.append(_ep(2, "Dukascopy", t2020 + 2, 0.0))
    # fuente A test 2023: 6 rebotes
    for k in range(6):
        eps.append(_ep(3 + k, "Dukascopy", t2023 + 1 + k, 1.0))
    # fuente A test 2023: 10 no-rebote
    for k in range(10):
        eps.append(_ep(13 + k, "Dukascopy", t2023 + 10 + k, 0.0))
    # fuente B (Quotex OTC)
    eps.append(_ep(9, "Quotex OTC", t2020 + 3, 1.0))
    eps.append(_ep(10, "Quotex OTC", t2023 + 3, 0.0))
    return eps


class _RealLaw:
    """Ley 'real': predice reversal (distance_pips final < 0). Acierta siempre
    en el fixture de B (los episodios con mfe>0 tienen distance final < 0)."""

    name = "real"

    def predict(self, ep):
        ev = ep.evolution or []
        if not ev:
            return False
        return float(ev[-1].get("distance_pips", 0.0)) < 0.0


class _NoiseLaw:
    """Ley 'ruido': etiqueta al azar (no informativa)."""

    def __init__(self, rng):
        self._rng = rng

    def predict(self, ep):
        return self._rng.random() < 0.5


# --- Splitter ----------------------------------------------------------------

def test_splitter_by_source_and_year():
    eps = _make_episodes()
    res = walk_forward(eps, split_year=2021, seed=42)
    assert set(res.keys()) == {"Dukascopy", "Quotex OTC"}
    # train = 2020 (<=2021), test = 2023 (>2021)
    train_a, test_a = res["Dukascopy"]
    assert [e.episode_id for e in train_a] == [1, 2]
    assert [e.episode_id for e in test_a] == [3, 4, 5, 6, 7, 8] + list(range(13, 23))
    train_b, test_b = res["Quotex OTC"]
    assert [e.episode_id for e in train_b] == [9]
    assert [e.episode_id for e in test_b] == [10]


def test_splitter_deterministic_same_seed():
    eps = _make_episodes()
    r1 = walk_forward(eps, split_year=2021, seed=7)
    r2 = walk_forward(eps, split_year=2021, seed=7)
    assert r1 == r2


# --- Falsifier ---------------------------------------------------------------

def _test_by_source(eps):
    res = walk_forward(eps, split_year=2021, seed=0)
    # pasamos a falsifier como dict source -> test episodes
    test_by_source = {src: t for src, (_, t) in res.items()}
    return test_by_source


def test_falsifier_real_law_passes():
    eps = _make_episodes()
    test_by_source = _test_by_source(eps)
    cfg = {"seed": 1, "p_cut": 0.05, "min_sample": 2, "min_freq": 0.1, "n_perm": 200}
    res = evaluate(_RealLaw(), test_by_source, cfg)
    # fuente A: test = [3(mfe1),4(mfe0)] => todas las predichas (mfe>0) rebotan.
    n, rate, baseline, delta, p = res["Dukascopy"]
    assert n >= 2
    assert rate > 0
    assert p < cfg["p_cut"]  # ley real pasa


def test_falsifier_noise_law_discarded():
    import random
    eps = _make_episodes()
    test_by_source = _test_by_source(eps)
    cfg = {"seed": 123, "p_cut": 0.05, "min_sample": 2, "min_freq": 0.1, "n_perm": 200}
    rng = random.Random(123)
    res = evaluate(_NoiseLaw(rng), test_by_source, cfg)
    # La ley ruido no debe considerarse significativa: p>=p_cut o n bajo.
    discarded = True
    for src, (n, rate, baseline, delta, p) in res.items():
        if n >= cfg["min_sample"] and rate >= cfg["min_freq"]:
            if p < cfg["p_cut"]:
                discarded = False
    assert discarded is True


def test_falsifier_deterministic_with_seed():
    import random
    eps = _make_episodes()
    test_by_source = _test_by_source(eps)
    cfg = {"seed": 55, "p_cut": 0.05, "min_sample": 2, "min_freq": 0.1, "n_perm": 100}

    def run():
        rng = random.Random(55)
        return evaluate(_NoiseLaw(rng), test_by_source, cfg)

    r1 = run()
    r2 = run()
    assert r1 == r2


# --- Law store ---------------------------------------------------------------

def test_law_store_save_get_list():
    conn = sqlite3.connect(":memory:")
    store = SQLiteLawStore(conn)
    law = Law(
        id="#1",
        name="muerte empuje",
        conditions="mfe>0",
        probability=0.73,
        confidence="HIGH",
        markets=("forex",),
        sources=("Dukascopy",),
        timeframes=("M1",),
        cases_studied=100,
        state="EXPERIMENTAL",
        discovery_version="discovery_v1",
        script_ref="LAB_001.md",
    )
    store.save_law(law)
    got = store.get_law("#1")
    assert got is not None
    assert got.id == "#1"
    assert got.markets == ("forex",)
    assert got.sources == ("Dukascopy",)
    assert got.state == "EXPERIMENTAL"
    assert len(store.list_laws()) == 1


def test_law_store_next_id_sequential():
    conn = sqlite3.connect(":memory:")
    store = SQLiteLawStore(conn)
    assert store.next_id() == "#1"
    store.save_law(
        Law("#1", "a", "c", 0.5, "LOW", ("forex",), ("Dukascopy",), ("M1",), 10)
    )
    assert store.next_id() == "#2"
    store.save_law(
        Law("#2", "b", "c", 0.5, "LOW", ("forex",), ("Dukascopy",), ("M1",), 10)
    )
    assert store.next_id() == "#3"


def test_law_store_no_overwrite():
    conn = sqlite3.connect(":memory:")
    store = SQLiteLawStore(conn)
    l1 = Law("#1", "orig", "c", 0.5, "LOW", ("forex",), ("Dukascopy",), ("M1",), 10)
    l2 = Law("#1", "cambio", "c", 0.9, "HIGH", ("forex",), ("Dukascopy",), ("M1",), 99)
    store.save_law(l1)
    store.save_law(l2)
    got = store.get_law("#1")
    assert got.name == "orig"  # no sobrescribe
    assert got.cases_studied == 10


def test_law_store_default_state_experimental():
    conn = sqlite3.connect(":memory:")
    store = SQLiteLawStore(conn)
    store.save_law(
        Law("#1", "x", "c", 0.5, "LOW", ("forex",), ("Dukascopy",), ("M1",), 10)
    )
    assert store.get_law("#1").state == "EXPERIMENTAL"


# --- Law relations + relation_miner -----------------------------------------

def test_law_relations_save_get_list():
    conn = sqlite3.connect(":memory:")
    save_relation(
        conn,
        LawRelation("#1", "#2", "refuerza", 0.8, "discovery_v1"),
    )
    rels = get_relations(conn, "#1")
    assert len(rels) == 1
    assert rels[0].relation_type == "refuerza"
    assert rels[0].strength == 0.8
    # tambien se recupera por el nodo destino
    assert len(get_relations(conn, "#2")) == 1
    assert len(list_relations(conn)) == 1


def test_relation_miner_proposes_valid():
    laws = [
        Law("#1", "a", "c", 0.8, "HIGH", ("forex",), ("Dukascopy",), ("M1",), 50),
        Law("#2", "b", "c", 0.7, "HIGH", ("forex",), ("Dukascopy",), ("M1",), 50),
        Law("#3", "c", "c", 0.1, "LOW", ("forex",), ("Dukascopy",), ("M1",), 50),
    ]
    cfg = {"seed": 3, "discovery_version": "discovery_v1", "relation_prob_threshold": 0.5}
    rels = propose_relations(laws, cfg)
    assert len(rels) >= 1
    for r in rels:
        assert r.relation_type in LawRelation.VALID_TYPES
        assert r.from_law in ("#1", "#2")
        assert r.to_law in ("#1", "#2")
        # strength = min(prob) para refuerza entre misma fuente
    # #1 y #2 comparten market+source => 'refuerza'
    pair = {(r.from_law, r.to_law) for r in rels}
    assert ("#1", "#2") in pair or ("#2", "#1") in pair
    # ley #3 con prob baja no genera aristas
    involved = {r.from_law for r in rels} | {r.to_law for r in rels}
    assert "#3" not in involved


def test_relation_miner_deterministic():
    laws = [
        Law("#1", "a", "c", 0.8, "HIGH", ("forex",), ("Dukascopy",), ("M1",), 50),
        Law("#2", "b", "c", 0.7, "HIGH", ("forex",), ("Quotex OTC",), ("M1",), 50),
    ]
    cfg = {"seed": 9, "discovery_version": "discovery_v1", "relation_prob_threshold": 0.5}
    r1 = propose_relations(laws, cfg)
    r2 = propose_relations(laws, cfg)
    assert r1 == r2
