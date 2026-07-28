"""Estudio empírico v2: estocástico en zona OS/OB — salida de zona + binaria 15 min.

Corrección empírica de Rubén: el empuje ocurre en la SALIDA de la zona, no
dentro. En binarias solo se mantiene 1 vela M15. Barremos múltiples variables
para encontrar la combinación que dé win-rate > 50%:

  zona      : 20/80, 15/85, 10/90
  fwd       : 1, 2, 3 velas M15  (horizonte de la operación binaria)
  min_pips  : 1, 2, 3 pip mínimo de despegue
  sep_bar   : 0 (sin exigir), 2, 5  (|K-D| mínimo en la salida)

Para cada combinación mide win-rate de la operación binaria (alcista al salir
de OS, bajista al salir de OB) sobre EURUSD M15 real (14 años, read-only).
Reporta las top combinaciones por win-rate y n de señales.

No toca el bot. No modifica datos SMC (solo lectura).
"""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
M15 = ROOT / "data" / "smc_borrowed" / "EURUSD_M15.parquet"
sys.path.insert(0, str(ROOT / "src"))

from analytics.config_loader import ZonaConfig, default_config_path  # noqa: E402
from analytics import estocastico_zona as ez  # noqa: E402
from strategy_lab import feature_calc as fc  # noqa: E402


def main() -> int:
    if not M15.exists():
        print(f"[SKIP] falta {M15}; corre scripts/build_m15_from_m1.py")
        return 0
    base = ZonaConfig.load(default_config_path())
    df = pd.read_parquet(M15).sort_values("time").iloc[-200_000:]
    kk, dd = fc.stochastic_full(
        df["high"].to_numpy(float), df["low"].to_numpy(float),
        df["close"].to_numpy(float), 14, 3, 3,
    )
    close = df["close"].to_numpy(float)

    zonas = [(20.0, 80.0), (15.0, 85.0), (10.0, 90.0)]
    fwds = [1, 2, 3]
    pips = [1.0, 2.0, 3.0]
    seps = [0.0, 2.0, 5.0]
    cruz = [False, True]   # exigir cruce %K/%D en la salida

    rows = []
    for (os_, ob_), fwd, mp, sep, cx in product(zonas, fwds, pips, seps, cruz):
        cfg = base.as_dict()
        cfg["os"], cfg["ob"] = os_, ob_
        cfg["fwd"] = fwd
        cfg["rebote_min_pips"] = mp
        cfg["sep_min_barrido"] = sep
        st = ez.binary_stats(kk, dd, close, cfg, cruce_en_salida=cx)
        rows.append({
            "os": os_, "ob": ob_, "fwd": fwd, "min_pips": mp, "sep": sep,
            "cruce": cx, "n": st["n"], "wr": st["wr"],
            "n_os": st["n_os"], "wr_os": st["wr_os"],
            "n_ob": st["n_ob"], "wr_ob": st["wr_ob"],
        })

    res = pd.DataFrame(rows)
    res["score"] = res["wr"] * np.minimum(res["n"], 500) / 500.0  # wr con peso por n
    top = res.sort_values("score", ascending=False).head(15)

    md = f"""# Estocástico en zona OS/OB — barrido binario 15 min (EURUSD M15, 14 años)

Corrección: el empuje se mide en la SALIDA de la zona, horizonte = fwd velas M15.
Señal: %K sale de OS (alcista) u OB (bajista); opcional |K-D|>=sep y/o cruce en
la salida. Win = precio se mueve >= min_pips en el sentido del empuje en fwd velas.

Total combinaciones: {len(res):,}. Mejores por (wr × n>=500 normalizado):

| os/ob | fwd | min_pip | sep | cruce | n | WR | WR_OS | WR_OB |
|-------|-----|---------|-----|-------|---|----|-------|-------|
"""
    for _, r in top.iterrows():
        md += (f"| {r['os']:.0f}/{r['ob']:.0f} | {r['fwd']} | {r['min_pips']:.0f} "
               f"| {r['sep']:.0f} | {r['cruce']} | {int(r['n']):,} | {100*r['wr']:.1f}% "
               f"| {100*r['wr_os']:.1f}% | {100*r['wr_ob']:.1f}% |\n")

    best = res.sort_values("wr", ascending=False).iloc[0]
    md += f"""
## Mejor WR puro: os/ob={best['os']:.0f}/{best['ob']:.0f} fwd={best['fwd']} "
        f"min_pip={best['min_pips']:.0f} sep={best['sep']:.0f} "
        f"-> WR={100*best['wr']:.1f}% (n={int(best['n']):,})

## Desglose por lado (todas las combinaciones)
- Media WR salida OS (alcista): {100*res['wr_os'].mean():.1f}%
- Media WR salida OB (bajista): {100*res['wr_ob'].mean():.1f}%
- WR > 50% en {int((res['wr']>0.5).sum())} de {len(res)} combinaciones.

Si alguna combinación da WR > 50% con n suficiente (>=200), tu teoría del
"empujón al salir de la zona" QUEDA REGISTRADA CON NÚMEROS para binarias de 15 min.
"""
    rep = ROOT / "docs" / "ESTOCASTICO_ZONA_sweep.md"
    rep.write_text(md, encoding="utf-8")
    res.to_csv(ROOT / "data" / "smc_borrowed" / "estocastico_zona_sweep.csv", index=False)

    print(f"[OK] combinaciones={len(res):,}  WR>50%: {int((res['wr']>0.5).sum())}")
    print(f"[OK] mejor: os/ob={best['os']:.0f}/{best['ob']:.0f} fwd={best['fwd']} "
          f"min_pip={best['min_pips']:.0f} sep={best['sep']:.0f} "
          f"WR={100*best['wr']:.1f}% n={int(best['n']):,}")
    print(f"[OK] reporte -> {rep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
