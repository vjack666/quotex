"""T10 smoke E2E — Strategy Lab sobre EURUSD M15 prestado (14 años, read-only).

Carga el parquet M15 generado por scripts/build_m15_from_m1.py (datos SMC
prestados, NO se modifican), calcula features, corre el optimizer con la
estrategia propuesta de Rubén (muerte del empuje -> rebote) y emite el reporte.
No es un test frágil: solo verifica que el pipeline corre end-to-end y produce
una estrategia coherente. El edge real lo decides tú tras revisar el reporte.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Rutas relativas a este repo (QUOTEX). El M15 vive en data/smc_borrowed (gitignored).
ROOT = Path(__file__).resolve().parent.parent
M15 = ROOT / "data" / "smc_borrowed" / "EURUSD_M15.parquet"

sys.path.insert(0, str(ROOT / "src"))

from strategy_lab.config_loader import StrategyLabConfig, default_config_path  # noqa: E402
from strategy_lab import feature_calc as fc  # noqa: E402
from strategy_lab.optimizer import optimize  # noqa: E402
from strategy_lab.strategy_store import StrategyStore  # noqa: E402


def main() -> int:
    if not M15.exists():
        print(f"[SKIP] no existe {M15} — ejecuta scripts/build_m15_from_m1.py primero")
        return 0
    cfg = StrategyLabConfig.load(default_config_path())
    df = pd.read_parquet(M15)
    df = df.sort_values("time")
    # limita a una ventana representativa para el smoke (rapidez); el Lab completo usa todo
    df = df.iloc[-200_000:]
    t = np.array(df["time"].values)
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    feats = fc.compute_features(o, h, l, c, cfg.__dict__)
    print(f"[OK] features M15: {len(c):,} velas | "
          f"impulse_up={int((feats.impulse_net > 30e-4).sum())} "
          f"brake={int(feats.brake_mask.sum())} "
          f"stoch_ob={int((feats.stoch_k >= cfg.stochastic['overbought']).sum())}")

    proposed = {
        "name": "rebote_muerte_impulso",
        "steps": [
            {"name": "impulso_alcista", "primitive": "impulse_up"},
            {"name": "freno", "primitive": "brake"},
            {"name": "sobrecompra", "primitive": "stoch_overbought"},
            {"name": "respaldo_LAB001", "law_ref": "#1"},
        ],
    }
    res = optimize(proposed, feats, cfg.__dict__, t, known_law_ids={"#1"})
    opt = res.optimized
    print(f"[OK] optimizer: pasos_opt={opt.steps_ordered} direccion={opt.direction} "
          f"edge_train={opt.edge_train:.3f} edge_test={opt.edge_test:.3f} "
          f"descartados={res.dropped_steps}")

    # diagnóstico: edge bruto de cada paso aislado (para ver dónde falla la teoría)
    from strategy_lab.strategy_parser import parse_strategy
    from strategy_lab.backtester import score_variant
    from strategy_lab.variant_searcher import variant_from_included
    ps = parse_strategy(proposed, known_law_ids={"#1"})
    for idx, step in enumerate(ps.steps):
        vv = variant_from_included(ps, [idx])
        s = score_variant(vv, ps, feats, cfg.__dict__, t, cfg.split_year)
        print(f"   paso aislado {step.name:20s} edge_train={s.edge_train:.3f} n={s.n_train}")

    md = StrategyStore.to_markdown(opt)
    out = ROOT / "docs" / "STRATEGY_LAB_smoke_report.md"
    out.write_text(md, encoding="utf-8")
    print(f"[OK] reporte -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
