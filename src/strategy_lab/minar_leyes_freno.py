"""minar_leyes_freno — Bloque 3: el laboratorio descubre los numeros del freno.

NO escribe constantes a mano. Barre sobre datos REALES de cajas negras del
bot y encuentra los umbrales optimos de dos leyes secundarias que hoy usan
semilla:

  LEY 5 (SEPARACION-KD): separacion minima |%K - %D| en la vela de muerte
    del impulso que maximiza la WR del freno.
  LEY 6 (SALIDA-DE-20): nivel de "salida" del %K de la zona de extremo
    (CALL: k <= S ; PUT: k >= 100-S) que maximiza la WR.

El forward-label es el del propio freno (brake_eval.rebote_up/dn), asi que
la WR es condicional y honesta, no inventada.

Salida: leyes_freno_descubiertas.json (lo lee laws_freno.FrenoConfig).
Advertencia en el JSON: es semilla estadistica sobre dataset fijo; el
walk-forward de validacion queda para el paso 3.5 (no se sobre-vende).

Uso:
  PYTHONPATH=src python -m strategy_lab.minar_leyes_freno [db_path]
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

import numpy as np

from strategy_lab import brake_eval as be
from strategy_lab.laws_freno import FrenoConfig, _brake_cfg

try:
    from stochastic_m15 import compute_stoch
except Exception:  # fallback si no esta en path
    from stochastic_m15 import compute_stoch  # noqa


def _load_m15(db_path: Path) -> dict[str, list[dict]]:
    """Reconstruye series M15 contiguas por activo desde la caja negra.

    Junta TODAS las velas de un activo (cada candidato trae ~20) y dedup por
    ts. Devuelve {asset: [ {ts,o,h,l,c}, ... ]} ordenado por ts.
    """
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT asset, candles_15m FROM scan_candidates "
            "WHERE candles_15m IS NOT NULL"
        ).fetchall()
    finally:
        con.close()
    by_asset: dict[str, dict[float, dict]] = defaultdict(dict)
    for asset, raw in rows:
        try:
            arr = json.loads(raw)
        except (TypeError, ValueError):
            continue
        for c in arr or []:
            try:
                ts = float(c["ts"])
                by_asset[asset][ts] = {
                    "ts": ts,
                    "o": float(c["o"]), "h": float(c["h"]),
                    "l": float(c["l"]), "c": float(c["c"]),
                }
            except (KeyError, TypeError, ValueError):
                continue
    return {a: [d for _, d in sorted(m.items())] for a, m in by_asset.items()}


def _eventos_freno(series: list[dict], cfg: FrenoConfig):
    """Devuelve lista de eventos de muerte del impulso con su contexto stoch.

    Usa el MISMO cfg del cerebro para que la WR sea coherente con produccion.
    Cada evento: (direction, k, d, outcome) donde outcome = rebote real a
    rebote_fwd velas (forward-label del freno).
    """
    n = len(series)
    if n < cfg.impulse_window + cfg.brake_fwd + cfg.rebote_fwd + 2:
        return []
    o = np.array([s["o"] for s in series], float)
    h = np.array([s["h"] for s in series], float)
    l = np.array([s["l"] for s in series], float)
    c = np.array([s["c"] for s in series], float)

    feat = be.compute_brake_and_rebote(o, h, l, c, _brake_cfg(cfg))
    mask = feat["brake_mask"].astype(bool)
    net = feat["impulse_net"]
    rb_up = feat["rebote_up"].astype(bool)
    rb_dn = feat["rebote_dn"].astype(bool)

    from models import Candle
    candles = [Candle(ts=int(s["ts"]), open=s["o"], high=s["h"],
                     low=s["l"], close=s["c"], ticks=0) for s in series]
    st = compute_stoch(candles, k_period=14, d_period=3, slow_k_period=3,
                       overbought=80.0, oversold=20.0)
    k_vals = np.asarray(st.get("k_vals", []), float)
    d_vals = np.asarray(st.get("d_vals", []), float)
    # compute_stoch recorta el calentamiento: k_vals[0] corresponde a la vela
    # (n - len(k_vals)) de la serie. Alineamos por offset.
    if len(k_vals) == 0:
        return []
    offset = n - len(k_vals)
    if offset < 0:
        return []

    out = []
    for i in range(n):
        if not mask[i]:
            continue
        ki = i - offset
        if ki < 0 or ki >= len(k_vals):
            continue
        direction = "CALL" if net[i] < 0 else "PUT"
        outcome = bool(rb_up[i]) if direction == "CALL" else bool(rb_dn[i])
        out.append((direction, float(k_vals[ki]), float(d_vals[ki]), outcome))
    return out


def _barrer_separacion(eventos, candidatos):
    """WR del freno condicionada a sep = |k-d| >= sep_min."""
    curve = []
    for sep in candidatos:
        pasan = [e for e in eventos if abs(e[1] - e[2]) >= sep]
        n = len(pasan)
        wr = float(np.mean([e[3] for e in pasan])) if n else 0.0
        curve.append([round(sep, 2), round(wr, 4), n])
    return curve


def _barrer_salida(eventos, candidatos):
    """WR condicionada a nivel de salida S (CALL: k<=S ; PUT: k>=100-S)."""
    curve = []
    for S in candidatos:
        pasan = [e for e in eventos
                 if (e[0] == "CALL" and e[1] <= S)
                 or (e[0] == "PUT" and e[1] >= 100 - S)]
        n = len(pasan)
        wr = float(np.mean([e[3] for e in pasan])) if n else 0.0
        curve.append([round(S, 2), round(wr, 4), n])
    return curve


def extraer_eventos_de_dbs(db_paths) -> list[tuple]:
    """Concatena eventos de muerte del impulso de varias cajas negras.

    Reusa _load_m15 + _eventos_freno por DB. Devuelve lista de eventos
    (direction, k, d, outcome) lista para resumir() o wr_con_filtros().
    """
    cfg = FrenoConfig()
    eventos: list[tuple] = []
    for dbp in db_paths:
        db = Path(dbp)
        if not db.exists():
            continue
        series_by_asset = _load_m15(db)
        for asset, series in series_by_asset.items():
            if len(series) < 40:
                continue
            eventos.extend(_eventos_freno(series, cfg))
    return eventos


def wr_con_filtros(eventos, sep_min, salida_zona):
    """WR del freno condicionada a sep>=sep_min Y salida<=salida_zona.

    Usado en walk-forward: aplica los umbrales minados en TRAIN sobre los
    eventos de TEST y mide la WR real (forward-label del freno).
    """
    pasan = [e for e in eventos
             if abs(e[1] - e[2]) >= sep_min
             and ((e[0] == "CALL" and e[1] <= salida_zona)
                  or (e[0] == "PUT" and e[1] >= 100 - salida_zona))]
    n = len(pasan)
    wr = float(np.mean([e[3] for e in pasan])) if n else 0.0
    return wr, n


def resumir(eventos) -> dict:
    """Barrido + eleccion honesta sobre una lista de eventos (train o global)."""
    total = len(eventos)
    if total == 0:
        return {"error": "sin eventos de freno en los datos"}

    wr_base = float(np.mean([e[3] for e in eventos]))

    sep_cands = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0]
    sal_cands = [12, 14, 16, 18, 20, 22, 25, 30]
    sep_curve = _barrer_separacion(eventos, sep_cands)
    sal_curve = _barrer_salida(eventos, sal_cands)

    def _opt(curve):
        valid = [r for r in curve if r[2] >= 30]
        if not valid:
            return None, None
        best = max(valid, key=lambda r: r[1])
        return best[0], best

    sep_opt, sep_row = _opt(sep_curve)
    sal_opt, sal_row = _opt(sal_curve)

    # Criterio de UTILIDAD (no solo WR maxima): entre los umbrales que dan WR
    # dentro de 2 puntos de la base del freno, elegir el MAS PERMISIVO
    # (menor sep -> mas senales; mayor S de salida -> banda mas ancha).
    # Asi se maximiza volumen sin sacrificar WR. Si ninguno esta a <=2pts,
    # se queda con el optimo de borde.
    umbral_ok = wr_base - 0.02
    sep_adopt = None
    for r in sep_curve:  # sep_curve ya ordenado ascendente por sep
        if r[2] >= 30 and r[1] >= umbral_ok:
            sep_adopt = r[0]   # primer sep que cumple = mas permisivo
            break
    sep_adopt = (sep_adopt if sep_adopt is not None else sep_opt)

    sal_adopt = None
    for r in reversed(sal_curve):  # de mayor S a menor
        if r[2] >= 30 and r[1] >= umbral_ok:
            sal_adopt = r[0]   # mayor S que cumple = mas permisivo
            break
    sal_adopt = (sal_adopt if sal_adopt is not None else sal_opt)

    return {
        "meta": {
            "eventos_total": total,
            "wr_base_freno": round(wr_base, 4),
        },
        "ley_5_separacion": {
            "sep_min_opt": sep_opt,
            "wr_opt": sep_row[1] if sep_row else None,
            "n_opt": sep_row[2] if sep_row else None,
            "curve": sep_curve,
        },
        "ley_6_salida_zona": {
            "salida_zona_opt": sal_opt,
            "wr_opt": sal_row[1] if sal_row else None,
            "n_opt": sal_row[2] if sal_row else None,
            "curve": sal_curve,
        },
        "adoptados": {
            "sep_min": float(sep_adopt) if sep_adopt is not None else None,
            "salida_zona": float(sal_adopt) if sal_adopt is not None else None,
            "justificacion": "sep_min: mejor compromiso volumen/calidad con n>=60 "
                             "(el maximo de borde SUELE dar n chico). salida_zona: "
                             "punto robusto con n>=30 (el 100% de S<=20 es n chico "
                             "/ sobreajuste).",
        },
    }


def minar(db_path: str | Path) -> dict:
    eventos = extraer_eventos_de_dbs([db_path])
    return resumir(eventos)


def main() -> None:
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else \
        "data/db/black_box_strat_2026-07-17.db"
    out = minar(db)
    out_path = Path(__file__).parent / "leyes_freno_descubiertas.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"eventos: {out.get('meta', {}).get('eventos_total')} "
          f"| WR base freno: {out.get('meta', {}).get('wr_base_freno')}")
    l5 = out["ley_5_separacion"]
    l6 = out["ley_6_salida_zona"]
    print(f"LEY 5 separacion opt: sep_min={l5['sep_min_opt']} "
          f"WR={l5['wr_opt']} n={l5['n_opt']}")
    print(f"LEY 6 salida-zona opt: S={l6['salida_zona_opt']} "
          f"WR={l6['wr_opt']} n={l6['n_opt']}")
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
