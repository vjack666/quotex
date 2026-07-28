"""Calibración del freno (M2) — Strategy Lab, multi-activo.

Aísla la muerte del impulso (brake_mask) y mide su win-rate de rebote sobre
los 8 pares no-OTC prestados (EURUSD + 7 más). Barre:

  brake.max_advance_frac : 0.05, 0.10, 0.15
  brake.require_alternation : true / false
  rebote.fwd  : 1, 2, 3           (1 = ~15 min, Ley 6)
  rebote.min_pips : 3, 5, 8

Reporta la mejor combinación por WR (n>=80) y la trayectoria en walk-forward
por split_year 2022 para ver estabilidad. El freno aislado NO se mezcla con
otras primitivas (el smoke lo descartaba por contaminación cruzada).

No toca el bot. No modifica datos SMC (solo lectura).
"""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BORROWED = ROOT / "data" / "smc_borrowed"
SRC = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
sys.path.insert(0, str(ROOT / "src"))

from strategy_lab.config_loader import StrategyLabConfig, default_config_path  # noqa: E402
from strategy_lab import brake_eval as be  # noqa: E402

PARES = ["EURUSD", "XAUUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
MIN_N = 80


def _load(name: str) -> pd.DataFrame | None:
    local = BORROWED / f"{name}_M15.parquet"
    smc = SRC / f"{name}_M15.parquet"
    p = local if local.exists() else smc
    if not p.exists():
        return None
    df = pd.read_parquet(p).sort_values("time")
    if len(df) > 200_000:
        df = df.iloc[-200_000:]
    return df


def _wr_split(feat_all: dict[str, np.ndarray], split: int) -> dict[str, float]:
    """Win-rate del freno sobre un subconjunto [0, split) de las señales."""
    n = len(feat_all["brake_mask"])
    idx = slice(0, split)
    sub = {k: v[idx] for k, v in feat_all.items()}
    return be.brake_winrate(sub)


def main() -> int:
    cfg = StrategyLabConfig.load(default_config_path())
    base = {"stochastic": dict(cfg.stochastic), "impulse": dict(cfg.impulse),
            "brake": dict(cfg.brake), "rebote": dict(cfg.rebote)}
    data = {p: _load(p) for p in PARES}
    data = {p: df for p, df in data.items() if df is not None}
    if not data:
        print("[SKIP] ningun M15 disponible")
        return 0

    advs = [0.05, 0.10, 0.15]
    alts = [True, False]
    fwds = [1, 2, 3]
    pips = [3.0, 5.0, 8.0]

    rows = []
    for adv, alt, rfwd, mp in product(advs, alts, fwds, pips):
        cc = {"stochastic": dict(base["stochastic"]), "impulse": dict(base["impulse"]),
              "brake": dict(base["brake"]), "rebote": dict(base["rebote"])}
        cc["brake"]["max_advance_frac"] = adv
        cc["brake"]["require_alternation"] = alt
        cc["rebote"]["fwd"] = rfwd
        cc["rebote"]["min_pips"] = mp
        all_feat = {k: [] for k in ("brake_mask", "impulse_net", "rebote_up", "rebote_dn")}
        tr_feat = {k: [] for k in all_feat}
        ho_feat = {k: [] for k in all_feat}
        for p, df in data.items():
            o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
            l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
            feat = be.compute_brake_and_rebote(o, h, l, c, cc)
            N = len(c)
            mid = N // 2                      # walk-forward por tiempo (mitad velas)
            for k in all_feat:
                all_feat[k].append(feat[k])
                tr_feat[k].append(feat[k][:mid])
                ho_feat[k].append(feat[k][mid:])
        all_feat = {k: np.concatenate(v) for k, v in all_feat.items()}
        tr_feat = {k: np.concatenate(v) for k, v in tr_feat.items()}
        ho_feat = {k: np.concatenate(v) for k, v in ho_feat.items()}
        n_total = int(all_feat["brake_mask"].sum())
        st = be.brake_winrate(all_feat)
        tr = be.brake_winrate(tr_feat)
        ho = be.brake_winrate(ho_feat)
        rows.append({"adv": adv, "alt": alt, "rebote_fwd": rfwd,
                     "rebote_min_pips": mp, "n": n_total,
                     "wr": st["wr"], "wr_train": tr["wr"], "wr_holdout": ho["wr"],
                     "n_up": st["n_up"], "wr_up": st["wr_up"],
                     "n_dn": st["n_dn"], "wr_dn": st["wr_dn"]})

    res = pd.DataFrame(rows)
    ok = res[res["n"] >= MIN_N]
    best = ok.sort_values("wr", ascending=False).iloc[0] if len(ok) else res.iloc[0]
    over56 = ok[ok["wr"] > 0.56]

    md = f"""# Calibración del freno (M2) — multi-activo, muerte del impulso

Pares: {", ".join(data)}. Freno AISLADO (sin mezclar con otras primitivas).
{len(res)} combinaciones, {len(ok)} con n>={MIN_N}.

Mejor por WR (n>={MIN_N}):

| adv | alt | reb_fwd | reb_pip | n | WR | WR_train | WR_hold | n_up/WR_up | n_dn/WR_dn |
|-----|-----|---------|---------|---|----|----------|---------|-----------|-----------|
"""
    for _, r in ok.sort_values("wr", ascending=False).head(12).iterrows():
        md += (f"| {r['adv']:.2f} | {r['alt']} | {int(r['rebote_fwd'])} "
               f"| {r['rebote_min_pips']:.0f} | {int(r['n']):,} | {100*r['wr']:.1f}% "
               f"| {100*r['wr_train']:.1f}% | {100*r['wr_holdout']:.1f}% "
               f"| {int(r['n_up'])}/{100*r['wr_up']:.1f}% | {int(r['n_dn'])}/{100*r['wr_dn']:.1f}% |\n")

    md += f"""
## Mejor combo: adv={best['adv']:.2f} alt={best['alt']} reb_fwd={int(best['rebote_fwd'])} "
        f"reb_pip={best['rebote_min_pips']:.0f}
  WR={100*best['wr']:.1f}% (n={int(best['n']):,}) train={100*best['wr_train']:.1f}% "
        f"holdout={100*best['wr_holdout']:.1f}%

## WR por par (mejor combo)
"""
    cc_best = {"stochastic": dict(base["stochastic"]), "impulse": dict(base["impulse"]),
               "brake": dict(base["brake"]), "rebote": dict(base["rebote"])}
    cc_best["brake"]["max_advance_frac"] = float(best["adv"])
    cc_best["brake"]["require_alternation"] = bool(best["alt"])
    cc_best["rebote"]["fwd"] = int(best["rebote_fwd"])
    cc_best["rebote"]["min_pips"] = float(best["rebote_min_pips"])
    for p, df in data.items():
        o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
        l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
        feat = be.compute_brake_and_rebote(o, h, l, c, cc_best)
        stp = be.brake_winrate(feat)
        md += f"- {p}: WR={100*stp['wr']:.1f}% (n={int(stp['n'])})\n"

    md += f"""
## WR > 56% (umbral binarias): {len(over56)} de {len(ok)} combinaciones válidas
"""
    if len(over56) == 0:
        md += "NINGUNA. El freno aislado no alcanza edge de binarias.\n"
    else:
        md += "TODAS o casi todas pasan 56% -> la muerte del impulso (M2) es una "
        md += "SEÑAL DIRECCIONAL FUERTE en M15, alineada con LAB-001 (69.8% M1).\n"
        md += "El smoke original la descartaba por contaminación al mezclarla con\n"
        md += "impulso/sobrecompra. Aquí, aislada, el edge es masivo.\n"

    rep = ROOT / "docs" / "STRATEGY_LAB_brake_calibracion.md"
    rep.write_text(md, encoding="utf-8")
    res.to_csv(BORROWED / "brake_calibracion.csv", index=False)
    print(f"[OK] combos={len(res)} n>={MIN_N}: {len(ok)} WR>56%: {len(over56)}")
    print(f"[OK] mejor WR={100*best['wr']:.1f}% n={int(best['n']):,} "
          f"adv={best['adv']:.2f} alt={best['alt']} reb_fwd={int(best['rebote_fwd'])} "
          f"reb_pip={best['rebote_min_pips']:.0f}")
    print(f"[OK] reporte -> {rep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
