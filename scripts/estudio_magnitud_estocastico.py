"""Estudio de MAGNITUD del empuje estocástico al salir de zona (no dirección).

Pregunta de Rubén: ¿el precio se MUEVE MÁS (en pip absolutos) tras salir de
la zona OS/OB que en una vela cualquiera? Si SÍ, el "empujón" es real como
explosión de volatilidad, útil para breakouts, aunque no prediga dirección.

Barrido: zona (20/80,15/85,10/90) x fwd (1,2,3) x sep (0,2,5) x cruce (False,True).
Para cada combinación mide, sobre los 8 pares no-OTC prestados:
  - mean_abs_salida : |movimiento| medio post-salida (pip)
  - mean_abs_base   : |movimiento| medio en índices aleatorios (pip)
  - ratio = salida / base  (>1 = hay empuje real de volatilidad)
  - p_value          : permutación, ¿la magnitud post-salida es azar?

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

from analytics.config_loader import ZonaConfig, default_config_path  # noqa: E402
from analytics import estocastico_zona as ez  # noqa: E402
from strategy_lab import feature_calc as fc  # noqa: E402


def load_pair(name: str) -> pd.DataFrame | None:
    local = BORROWED / f"{name}_M15.parquet"
    smc = SRC / f"{name}_M15.parquet"
    p = local if local.exists() else smc
    if not p.exists():
        return None
    df = pd.read_parquet(p).sort_values("time")
    if len(df) > 200_000:
        df = df.iloc[-200_000:]
    return df


def main() -> int:
    base = ZonaConfig.load(default_config_path())
    pairs = ["EURUSD", "XAUUSD", "GBPUSD", "AUDUSD", "NZDUSD",
             "USDCAD", "USDCHF", "USDJPY"]
    data = {p: load_pair(p) for p in pairs}
    data = {p: df for p, df in data.items() if df is not None}
    if not data:
        print("[SKIP] ningun M15 disponible")
        return 0

    pre = {}
    for p, df in data.items():
        kk, dd = fc.stochastic_full(
            df["high"].to_numpy(float), df["low"].to_numpy(float),
            df["close"].to_numpy(float), 14, 3, 3)
        pre[p] = (kk, dd, df["close"].to_numpy(float))

    zonas = [(20.0, 80.0), (15.0, 85.0), (10.0, 90.0)]
    fwds = [1, 2, 3]
    seps = [0.0, 2.0, 5.0]
    cruz = [False, True]
    rng = np.random.default_rng(20260728)

    rows = []
    for (os_, ob_), fwd, sep, cx in product(zonas, fwds, seps, cruz):
        cfg = base.as_dict()
        cfg["os"], cfg["ob"] = os_, ob_
        cfg["fwd"] = fwd
        cfg["sep_min_barrido"] = sep
        all_sal, all_base, all_n = [], [], []
        per = {}
        for p, (kk, dd, close) in pre.items():
            st = ez.magnitude_stats(kk, dd, close, cfg, rng=rng)
            per[p] = st
            all_n.append(st["n"])
            all_sal.append(st["mean_abs_salida"] * st["n"])
            all_base.append(st["mean_abs_base"] * st["n"])
        n_tot = sum(all_n)
        m_sal = sum(all_sal) / n_tot if n_tot else 0.0
        m_base = sum(all_base) / n_tot if n_tot else 0.0
        ratio = m_sal / m_base if m_base else 0.0
        # p global aproximado: usa el p de la combinacion ponderado por n
        p_w = sum(st["p_value"] * st["n"] for st in per.values()) / n_tot if n_tot else 1.0
        rows.append({"os": os_, "ob": ob_, "fwd": fwd, "sep": sep,
                     "cruce": cx, "n": n_tot, "mean_abs_salida": m_sal,
                     "mean_abs_base": m_base, "ratio": ratio, "p_value": p_w,
                     **{f"ratio_{p}": per[p]["ratio"] for p in data}})

    res = pd.DataFrame(rows).sort_values("ratio", ascending=False)
    best = res.iloc[0]
    sig = res[res["ratio"] > 1.1]

    md = f"""# Magnitud del empuje estocástico al salir de zona — 8 pares no-OTC

Pares: {", ".join(data)}. Sin filtro de hora (no-OTC = estructura).
ratio = |movimiento| post-salida / |movimiento| base aleatoria. ratio>1 = hay
empujón real de volatilidad; p_value<0.05 = no es azar.

Mejores por ratio (top 15):

| os/ob | fwd | sep | cruce | n | |salida| | |base| | ratio | p |
|-------|-----|-----|-------|---|--------|-------|-------|---|
"""
    for _, r in res.head(15).iterrows():
        md += (f"| {r['os']:.0f}/{r['ob']:.0f} | {r['fwd']} | {r['sep']:.0f} "
               f"| {r['cruce']} | {int(r['n']):,} | {r['mean_abs_salida']:.2f} "
               f"| {r['mean_abs_base']:.2f} | {r['ratio']:.3f} | {r['p_value']:.3f} |\n")

    md += f"""
## Mejor combo: os/ob={best['os']:.0f}/{best['ob']:.0f} fwd={best['fwd']} "
        f"sep={best['sep']:.0f} cruce={best['cruce']}
  |salida|={best['mean_abs_salida']:.2f} pip | |base|={best['mean_abs_base']:.2f} pip
  ratio={best['ratio']:.3f} p={best['p_value']:.3f}

## Lectura
- {len(sig)} de {len(res)} combinaciones tienen ratio>1.1 (empujón >10% sobre base).
- Si hay combos con ratio>1.1 Y p<0.05: tu "empujón al salir de zona" es REAL
  como explosión de volatilidad -> úsalo para breakouts, no como señal direccional.
- Si todos los ratio~1 y p~1: el movimiento post-salida es indistinguible del
  ruido -> el empuje que ves es efecto de tu selección (sesgo de confirmación).
"""
    rep = ROOT / "docs" / "ESTOCASTICO_ZONA_magnitud.md"
    rep.write_text(md, encoding="utf-8")
    res.to_csv(BORROWED / "estocastico_zona_magnitud.csv", index=False)
    print(f"[OK] combos={len(res)} ratio>1.1: {len(sig)}")
    print(f"[OK] mejor ratio={best['ratio']:.3f} p={best['p_value']:.3f} "
          f"|salida|={best['mean_abs_salida']:.2f} |base|={best['mean_abs_base']:.2f}")
    print(f"[OK] reporte -> {rep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
