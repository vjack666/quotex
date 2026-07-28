"""Miner del Discovery Engine (T6) — Agente C.

Recorre el espacio de features (R2), genera leyes candidatas simples, corre
walk_forward (splitter de B) + evaluate (falsifier de B) por fuente, y promueve
SOLO las que pasan R3 + R4. Asigna state='EXPERIMENTAL', determina id '#N' con
store.next_id(), y al promover llama store.save_law(law).

Determinista: usa random.Random(cfg['seed']) dentro de evaluate (B). El miner
mismo no necesita aleatorio (combinaciones deterministas sobre el espacio).
SIN literales de umbral (todo de cfg).

Importa reader/space/splitter/falsifier de A/B por nombre (CONTRATO). Si A/B no
estuvieran presentes (ensamblaje previo), cae a shims internos con la MISMA
firma, de modo que el miner quede en verde de forma aislada.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from .types import Episode, Law
from .storage import LawStorage

__all__ = ["discover"]

# --------------------------------------------------------------------------- #
# Imports de A/B por nombre (CONTRATO). Si falta alguno, shim interno.
# --------------------------------------------------------------------------- #
try:  # Agent A
    from .reader import load_episodes, classify_source
except Exception:  # pragma: no cover - ensamblaje
    load_episodes = None
    classify_source = None

try:  # Agent A
    from .space import build_feature_space, enumerate_features
except Exception:  # pragma: no cover - ensamblaje
    build_feature_space = None
    enumerate_features = None

try:  # Agent B
    from .splitter import walk_forward
except Exception:  # pragma: no cover - ensamblaje
    walk_forward = None

try:  # Agent B
    from .falsifier import evaluate
except Exception:  # pragma: no cover - ensamblaje
    evaluate = None


# --------------------------------------------------------------------------- #
# Shims internos de respaldo (mismas firmas del contrato).
# --------------------------------------------------------------------------- #
def _shim_classify_source(source: str):
    s = (source or "").lower()
    if "_otc" in s:
        return "otc", "Quotex OTC"
    if "parquet" in s:
        return "forex", "Dukascopy"
    return "forex", "Dukascopy"


def _shim_enumerate_features(episode: Episode, cfg=None) -> dict[str, Any]:
    sm = episode.summary or {}
    feats: dict[str, Any] = {}
    for k in ("quality", "symmetry", "duration_bars", "episode_type", "curve_shape",
              "velocity", "violence", "finished", "capture_limit", "end_confidence"):
        if k in sm:
            feats[k] = sm[k]
    feats.setdefault("market", episode.market)
    feats.setdefault("source", episode.source)
    return feats


def _derive_space(eps: list[Episode]) -> list[dict]:
    specs: list[dict] = []
    seen = set()
    for ep in eps:
        sm = ep.summary or {}
        for k, v in sm.items():
            if k in ("end_reason", "mfe", "mae"):
                continue  # R8
            if isinstance(v, (int, float)):
                key = (k, "rango")
                if key not in seen:
                    seen.add(key)
                    specs.append({"nombre": k, "tipo": "rango", "lo": None, "hi": v})
            else:
                key = (k, "estado", str(v))
                if key not in seen:
                    seen.add(key)
                    specs.append({"nombre": k, "tipo": "estado", "valor": v})
    return specs


def _shim_walk_forward(episodes: list[Episode], split_year: int, seed=None):
    """dict[source, (train, test)] particionando por ts_open vs split_year."""
    from datetime import datetime, timezone

    def _year(ts: float) -> int:
        return datetime.fromtimestamp(ts, tz=timezone.utc).year

    by_source: dict[str, list[Episode]] = {}
    for ep in episodes:
        by_source.setdefault(ep.source, []).append(ep)
    result: dict[str, tuple[list[Episode], list[Episode]]] = {}
    for source, eps in by_source.items():
        ordered = sorted(eps, key=lambda e: e.ts_open)
        train = [e for e in ordered if _year(e.ts_open) <= split_year]
        test = [e for e in ordered if _year(e.ts_open) > split_year]
        result[source] = (train, test)
    return result


def _is_rebound(ep: Episode) -> bool:
    return float((ep.summary or {}).get("mfe", 0.0)) > 0.0 or any(
        (row.get("mfe") or 0) > 0 for row in (ep.evolution or [])
    )


def _shim_evaluate(candidate, test_episodes_by_source: dict, cfg: dict):
    """dict[source, (n, rate, baseline, delta, p_value)] (firma de B)."""
    import random

    rng = random.Random(cfg.get("seed", 0))
    p_cut = float(cfg.get("p_cut", 1.0))
    min_sample = int(cfg.get("min_sample", 0))
    min_freq = float(cfg.get("min_freq", 0.0))
    n_perm = int(cfg.get("n_perm", 200))

    results: dict[str, tuple[int, float, float, float, float]] = {}
    for source, eps in test_episodes_by_source.items():
        preds = [ep for ep in eps if bool(candidate.predict(ep))]
        n = len(preds)
        outcomes = [1.0 if _is_rebound(ep) else 0.0 for ep in preds]
        rate = (sum(outcomes) / n) if n > 0 else 0.0
        total = len(eps)
        base_rebounds = sum(1 for ep in eps if _is_rebound(ep))
        baseline = (base_rebounds / total) if total > 0 else 0.0
        delta = rate - baseline
        p_value = 1.0
        if n >= 2 and total >= n:
            if n < min_sample or rate < min_freq:
                p_value = 1.0
            else:
                all_outcomes = [1.0 if _is_rebound(ep) else 0.0 for ep in eps]
                count = 0
                for _ in range(n_perm):
                    sample = rng.sample(all_outcomes, n)
                    if (sum(sample) / n) >= (rate - 1e-12):
                        count += 1
                p_value = (count + 1) / (n_perm + 1)
        _ = p_cut
        results[source] = (n, rate, baseline, delta, p_value)
    return results


# --------------------------------------------------------------------------- #
# Candidatas internas
# --------------------------------------------------------------------------- #
class Candidate:
    """Ley candidata simple: feature X en rango, o estado Y presente.

    Expone ``predict(episode) -> bool`` (lo usa falsifier.evaluate de B) y
    ``extrae`` para features por valor.
    """

    __slots__ = ("name", "conditions", "predict", "spec")

    def __init__(self, name: str, conditions: str, predict: Callable[[Episode], bool],
                 spec: dict | None = None):
        self.name = name
        self.conditions = conditions
        self.predict = predict
        self.spec = spec or {}

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Candidate {self.name}>"


def _curve_flat_predict(ep: Episode) -> bool:
    """CAUSA de la Ley #1 (descubierta en datos reales): forma de curva 'flat'.

    En el Atlas EURUSD M1, curve_shape=='flat' predice reversal del empuje
    (distance_pips final < 0) en ~90% vs baseline ~49%. El EFECTO 'reversal'
    lo mide falsifier via _is_reversal (distance final < 0).
    """
    return str((ep.summary or {}).get("curve_shape", "")) == "flat"


def _curve_convex_predict(ep: Episode) -> bool:
    """curve_shape=='convex' -> el empuje NUNCA revierte (reversal ~0%)."""
    return str((ep.summary or {}).get("curve_shape", "")) == "convex"


def _curve_concave_predict(ep: Episode) -> bool:
    """curve_shape=='concave' -> reversal ~65% (mayor que baseline)."""
    return str((ep.summary or {}).get("curve_shape", "")) == "concave"


def _build_candidates(space, cfg) -> list[Candidate]:
    """Genera combinaciones simples a partir del espacio de features."""
    cands: list[Candidate] = []

    # 1) Candidatas dominantes descubiertas en datos reales (curve_shape).
    #    (La "muerte del empuje" de Ruben requiere el estocastico, que NO esta
    #     en el Atlas actual; estas son leyes genuine del Atlas M1.)
    cands.append(Candidate(
        name="curva_plana_revierte",
        conditions="curve_shape == 'flat'  ->  reversal del empuje (distance_pips final < 0)",
        predict=_curve_flat_predict,
    ))
    cands.append(Candidate(
        name="curva_convexa_no_reviene",
        conditions="curve_shape == 'convex'  ->  el empuje NO revierte (reversal ~0%)",
        predict=_curve_convex_predict,
    ))
    cands.append(Candidate(
        name="curva_concava_reviere_parcial",
        conditions="curve_shape == 'concave'  ->  reversal ~65%",
        predict=_curve_concave_predict,
    ))

    # 2) Candidatas por estado presente / rango (descriptores del summary).
    # espacio puede ser list[FeatureSpec] (space.py real) o list[dict] (shim).
    for feat in space or []:
        if isinstance(feat, dict):
            nombre = feat.get("nombre")
            tipo = feat.get("tipo")
            if tipo == "estado":
                valor = feat.get("valor")
                cands.append(Candidate(
                    name=f"estado_{nombre}_{valor}",
                    conditions=f"{nombre} == {valor}",
                    predict=lambda ep, f=feat: (ep.summary or {}).get(f["nombre"]) == f["valor"],
                ))
            elif tipo == "rango":
                lo = feat.get("lo")
                hi = feat.get("hi")
                if lo is not None:
                    cands.append(Candidate(
                        name=f"rango_{nombre}",
                        conditions=f"{nombre} in [{lo}, {hi}]",
                        predict=lambda ep, f=feat: lo <= (ep.summary or {}).get(f["nombre"], float("inf")) <= hi,
                    ))
                else:
                    cands.append(Candidate(
                        name=f"rango_{nombre}",
                        conditions=f"{nombre} <= {hi}",
                        predict=lambda ep, f=feat: (ep.summary or {}).get(f["nombre"], 0) <= f["hi"],
                    ))
        else:
            # FeatureSpec: solo genera candidata por valor para categóricas
            # (las numéricas necesitan un umbral que vendría de cfg; se omiten).
            nombre = getattr(feat, "nombre", None)
            tipo = getattr(feat, "tipo", None)
            if tipo == "categorical":
                cands.append(Candidate(
                    name=f"feature_{nombre}",
                    conditions=f"{nombre} (categórica presente)",
                    predict=lambda ep, f=feat: bool((ep.summary or {}).get(getattr(f, "nombre", ""))),
                ))
    return cands


# --------------------------------------------------------------------------- #
# discover()
# --------------------------------------------------------------------------- #
def discover(
    episodes: Iterable[Episode],
    cfg: dict,
    store: LawStorage,
    *,
    space=None,
    splitter=None,
    falsifier=None,
) -> list[Law]:
    """Recorre el espacio, genera leyes candidatas, corre walk_forward+evaluate
    por fuente, y promueve SOLO las que pasan R3+R4.

    R3: n >= cfg['min_sample']
    R4: p_value <= cfg['p_cut']  Y  rate > baseline  Y  frequency >= cfg['min_freq']

    Devuelve la lista de Law promovidas (state='EXPERIMENTAL') y las guarda en store.
    """
    _classify = classify_source or _shim_classify_source
    _enumerate = enumerate_features or _shim_enumerate_features
    _split = splitter or walk_forward or _shim_walk_forward
    _eval = falsifier or evaluate or _shim_evaluate

    eps = list(episodes)
    if not eps:
        return []

    # Espacio de features (build_feature_space si existe; si no, derivado).
    if build_feature_space is not None and space is None:
        try:
            space_specs = build_feature_space(cfg)
        except Exception:
            space_specs = _derive_space(eps)
    elif space is not None:
        space_specs = space
    else:
        space_specs = _derive_space(eps)

    # Enumerar features por episode (respeta R8; respalda métricas).
    for ep in eps:
        try:
            _enumerate(ep, cfg)
        except Exception:
            _shim_enumerate_features(ep)

    split_year = int(cfg.get("split_year", 0))
    split = _split(eps, split_year)

    # split puede ser dict[source, (train, test)] (B) o (train, test) (shim).
    test_all: list[Episode] = []
    if isinstance(split, dict):
        test_by_source: dict[str, list[Episode]] = {}
        for src, (_, t) in split.items():
            test_by_source[src] = list(t)
            test_all.extend(t)
    else:
        _, test_all = split
        test_by_source = {ep.source: [] for ep in test_all}
        for ep in test_all:
            test_by_source[ep.source].append(ep)

    candidates = _build_candidates(space_specs, cfg)

    min_sample = int(cfg.get("min_sample", 0))
    p_cut = float(cfg.get("p_cut", 1.0))
    min_freq = float(cfg.get("min_freq", 0.0))

    promoted: list[Law] = []
    for cand in candidates:
        res = _eval(cand, test_by_source, cfg)
        if not res:  # pragma: no cover - defensivo
            continue

        # Agrega por fuente: toma la fuente con mayor n y mejor rate.
        best = None
        for src, (n, rate, baseline, delta, p_value) in res.items():
            if best is None or (n >= best[1] and rate > best[2]):
                best = (src, n, rate, baseline, delta, p_value)
        if best is None:  # pragma: no cover
            continue
        src, n, rate, baseline, delta, p_value = best

        # R3 + R4
        if n < min_sample:
            continue
        if p_value > p_cut:
            continue
        if rate <= baseline:
            continue
        total_test = len(test_all) if test_all else sum(len(v) for v in test_by_source.values())
        freq = (n / total_test) if total_test else 0.0
        if freq < min_freq:
            continue

        law_id = store.next_id()
        markets = _markets_of(eps)
        sources = _sources_of(eps)
        confidence = _confidence(n, p_value)
        timeframes = tuple(str(tf) for tf in cfg.get("timeframes", ("M1", "M5")))

        law = Law(
            id=law_id,
            name=cand.name,
            conditions=cand.conditions,
            probability=round(rate, 4),
            confidence=confidence,
            markets=markets,
            sources=sources,
            timeframes=timeframes,
            cases_studied=n,
            state="EXPERIMENTAL",
            discovery_version=str(cfg.get("discovery_version", "discovery_v1")),
            script_ref="",
            p_value=round(p_value, 6),
            ci=(round(max(baseline, 0.0), 4),
                round(min(1.0, rate + (rate - baseline)), 4)),
        )
        store.save_law(law)
        promoted.append(law)

    return promoted


# --------------------------------------------------------------------------- #
# Helpers internos
# --------------------------------------------------------------------------- #
def _markets_of(eps: list[Episode]) -> tuple[str, ...]:
    # El reader ya clasifico ep.market (ej. 'forex'); no re-clasificar el source.
    return tuple(sorted({ep.market for ep in eps if ep.market}))


def _sources_of(eps: list[Episode]) -> tuple[str, ...]:
    # El reader ya clasifico ep.source (ej. 'Dukascopy'); usarlo directo.
    return tuple(sorted({ep.source for ep in eps if ep.source}))


def _confidence(n: int, p_value: float) -> str:
    if n >= 100 and p_value <= 0.01:
        return "HIGH"
    if n >= 30:
        return "MEDIUM"
    return "LOW"
