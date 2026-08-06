"""Runner del experimento de COMPORTAMIENTO del POI (fase de freno).

Mide cómo se comporta el precio frente a cada tipo de POI — swing,
volumen variante A y variante B — sobre M15 real (spot FX con tick_volume).
NO es un experimento de winrate: el winrate se mide al final de la cadena
de la estrategia. Acá se responden 4 hipótesis de calidad del nivel:

  H1  Sostiene el precio (tasa de rebote vs tasa de break)
  H2  Timing: velas entre el toque al POI y el primer freno real
      (detector estricto: impulso >= 5 pips que muere)
  H3  Aguante a caída estrepitosa (impulso fuerte previo vs calma)
  H4  Flip de rol: piso roto que pasa a techo y viceversa

Solo lectura sobre parquet de SMC-SYSTEMS. No toca el edificio.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from strategy_lab.brake_eval import compute_brake_and_rebote
from strategy_lab.poi_behavior import analyze_levels, swing_levels_causal, DEFAULT_CFG
from strategy_lab.volume_profile import build_volume_poi

try:
    import pandas as pd
except Exception:
    pd = None


SMC_ROOT = Path(r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw")
PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
PIP_SIZE = {p: (0.01 if p.endswith("JPY") else 1e-4) for p in PAIRS}

# Freno del laboratorio (laxo, igual que el experimento de WR)
BRAKE_CFG = {
    "impulse": {"window": 15, "min_pips": 0.5},
    "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
    "rebote": {"fwd": 2, "min_pips": 0.5},
}
# Freno REAL (estricto): impulso de >= 5 pips que muere — para el timing H2
BRAKE_STRICT_CFG = {
    "impulse": {"window": 15, "min_pips": 5.0},
    "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
    "rebote": {"fwd": 2, "min_pips": 0.5},
}

BEHAVIOR_CFG = dict(DEFAULT_CFG)

COLS = [
    "asset", "poi", "n_bands", "touches", "rebounds", "breaks", "neutros",
    "rate_rebound", "rate_break",
    "timing_n", "timing_median", "timing_pct_le1", "timing_pct_le3", "timing_pct_le5",
    "fuerte_n", "fuerte_rate", "debil_n", "debil_rate",
    "overshoot_fuerte", "overshoot_debil",
    "flip_breaks", "flip_retests", "flip_flips", "flip_rate",
]


def _load_m15(asset: str) -> dict[str, np.ndarray]:
    path = SMC_ROOT / f"{asset}_M15.parquet"
    if pd is None:
        raise RuntimeError("pandas requerido")
    df = pd.read_parquet(path)
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return {
        "o": df["open"].values.astype(float),
        "h": df["high"].values.astype(float),
        "l": df["low"].values.astype(float),
        "c": df["close"].values.astype(float),
        "ticks": df["tick_volume"].values.astype(float),
    }


def run_pair(asset: str) -> dict[str, object]:
    d = _load_m15(asset)
    o, h, l, c, ticks = d["o"], d["h"], d["l"], d["c"], d["ticks"]
    n = len(c)
    if n < 100:
        return {"asset": asset, "error": "short"}

    pip_size = PIP_SIZE[asset]
    # freno estricto (para H2) — usa el mismo pip_size (5 pips reales del par)
    strict_cfg = {
        "impulse": {"window": 15, "min_pips": 5.0},
        "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
        "rebote": {"fwd": 2, "min_pips": 0.5},
    }
    feat_strict = compute_brake_and_rebote(o, h, l, c, strict_cfg)
    brake_strict = feat_strict["brake_mask"].astype(bool)

    L = int(BEHAVIOR_CFG["imp_window"])
    impulse_prev = np.zeros(n)
    impulse_prev[L:] = c[L:] - c[:-L]
    strong_thr = float(np.nanpercentile(np.abs(impulse_prev), BEHAVIOR_CFG["strong_pct"]))

    def _metrics(floors, ceilings, act_from, act_to) -> dict[str, float]:
        return analyze_levels(l, h, c, floors, ceilings, act_from, act_to,
                              brake_strict, impulse_prev, strong_thr,
                              BEHAVIOR_CFG, pip_size=pip_size)

    # --- POI swing: niveles causales (activación tras 2º toque, 100 velas) ---
    fl_s, ce_s, af_s, at_s = swing_levels_causal(h, l, min_touches=2, tol_pips=5.0,
                                                 lookback=100, pip_size=pip_size)
    swing = _metrics(fl_s, ce_s, af_s, at_s)

    # --- POI volumen A y B (franja única, activa todo el dataset) ---
    vp = build_volume_poi(asset, h, l, ticks, band_pct=0.0015, threshold_a=0.60, coverage_b=0.70)
    ones_f = np.array([0], int)
    ones_t = np.array([n], int)
    vol_a = _metrics(np.array([min(vp.val_a, vp.vah_a)]), np.array([max(vp.val_a, vp.vah_a)]), ones_f, ones_t)
    vol_b = _metrics(np.array([min(vp.val_b, vp.vah_b)]), np.array([max(vp.val_b, vp.vah_b)]), ones_f, ones_t)

    rows = []
    for label, m in (("swing", swing), ("vol_a", vol_a), ("vol_b", vol_b)):
        if "error" in m:
            continue
        row = {"asset": asset, "poi": label}
        row.update({k: m.get(k, float("nan")) for k in COLS if k not in ("asset", "poi")})
        rows.append(row)
    return {"asset": asset, "rows": rows}


def _fmt(v: object) -> str:
    if isinstance(v, float):
        return f"{v:.3f}" if np.isfinite(v) else "nan"
    return str(v)


def main() -> int:
    all_rows: list[dict[str, object]] = []
    for asset in PAIRS:
        try:
            r = run_pair(asset)
            if "rows" in r:
                all_rows.extend(r["rows"])
        except Exception as e:  # noqa: BLE001 — el runner reporta y sigue
            print(f"{asset}: ERROR {e}", file=sys.stderr)

    print(",".join(COLS))
    for row in all_rows:
        print(",".join(_fmt(row.get(k, "")) for k in COLS))

    out = Path(__file__).resolve().parent.parent / "resultados_poi_comportamiento.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        f.write(",".join(COLS) + "\n")
        for row in all_rows:
            f.write(",".join(_fmt(row.get(k, "")) for k in COLS) + "\n")
    print(f"\nCSV guardado: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
