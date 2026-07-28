"""Estudio empírico v3: estocástico en zona OS/OB — barrido MULTI-ACTIVO.

Corrección empírica de Rubén: el empuje ocurre en la SALIDA de la zona, no
dentro. En binarias solo se mantiene 1 vela M15. Tu activo NO es OTC -> se
rige por estructura, no por horario de banco. Por eso barremos sin filtro de
hora, sobre TODOS los pares no-OTC prestados de SMC (read-only).

Variables del barrido:
  zona   : 20/80, 15/85, 10/90
  fwd    : 1, 2, 3 velas M15
  pips   : 1, 2, 3 pip mínimo de despegue
  sep    : 0 (sin exigir), 2, 5  (|K-D| mínimo en la salida)
  cruce  : False / True (exigir cruce %K/%D en la salida)

Mide win-rate de la operación binaria: alcista al salir de OS, bajista al
salir de OB. Reporta mejor combinación GLOBAL (unión de señales de todos los
pares) y WR por activo para cada combinación.

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
        df = df.iloc[-200_000:]          # cap por velocidad (aún ~14 años)
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
    print(f"[OK] pares cargados: {list(data)} "
          f"({sum(len(d) for d in data.values()):,} velas M15 total)")

    zonas = [(20.0, 80.0), (15.0, 85.0), (10.0, 90.0)]
    fwds = [1, 2, 3]
    pips = [1.0, 2.0, 3.0]
    seps = [0.0, 2.0, 5.0]
    cruz = [False, True]

    # precomputa estocastico + estadisticas por par
    pre = {}
    for p, df in data.items():
        kk, dd = fc.stochastic_full(
            df["high"].to_numpy(float), df["low"].to_numpy(float),
            df["close"].to_numpy(float), 14, 3, 3)
        pre[p] = (kk, dd, df["close"].to_numpy(float))

    rows = []
    for (os_, ob_), fwd, mp, sep, cx in product(zonas, fwds, pips, seps, cruz):
        cfg = base.as_dict()
        cfg["os"], cfg["ob"] = os_, ob_
        cfg["fwd"] = fwd
        cfg["rebote_min_pips"] = mp
        cfg["sep_min_barrido"] = sep
        # union global de senales
        all_sig_dir = []   # (direccion, move) por senal
        per_pair_wr = {}
        for p, (kk, dd, close) in pre.items():
            st = ez.binary_stats(kk, dd, close, cfg, cruce_en_salida=cx)
            per_pair_wr[p] = (st["n"], st["wr"])
            lab = ez.classify(kk, dd, close, cfg)
            n = len(close)
            idx = np.arange(n)
            sig = (lab.salida != 0) & (idx + fwd < n)
            if sep > 0:
                sig = sig & (np.abs(kk - dd) >= sep)
            if cx:
                sig = sig & (lab.cruce != 0)
            ix = np.where(sig)[0]
            if len(ix):
                move = close[ix + fwd] - close[ix]
                dirv = np.sign(lab.salida[ix])
                win = (np.sign(move) == dirv) & (np.abs(move) >= mp * 1e-4)
                all_sig_dir.append((len(ix), float(win.mean())))
        n_tot = sum(x[0] for x in all_sig_dir)
        wr_tot = (sum(x[0] * x[1] for x in all_sig_dir) / n_tot) if n_tot else 0.0
        rows.append({
            "os": os_, "ob": ob_, "fwd": fwd, "min_pips": mp, "sep": sep,
            "cruce": cx, "n": n_tot, "wr": wr_tot,
            **{f"wr_{p}": per_pair_wr[p][1] for p in data},
            **{f"n_{p}": per_pair_wr[p][0] for p in data},
        })

    res = pd.DataFrame(rows)
    res["score"] = res["wr"] * np.minimum(res["n"], 1000) / 1000.0
    top = res.sort_values("score", ascending=False).head(15)

    md = f"""# Estocástico en zona OS/OB — barrido MULTI-ACTIVO (no-OTC, sin filtro hora)

Pares: {", ".join(data)} — {sum(len(d) for d in data.values()):,} velas M15.
Filosofía: no-OTC se rige por estructura, no por sesión -> sin filtro de hora.

Mejores combinaciones por (WR × n>=1000 normalizado):

| os/ob | fwd | min_pip | sep | cruce | n | WR |
|-------|-----|---------|-----|-------|---|----|
"""
    for _, r in top.iterrows():
        md += (f"| {r['os']:.0f}/{r['ob']:.0f} | {r['fwd']} | {r['min_pips']:.0f} "
               f"| {r['sep']:.0f} | {r['cruce']} | {int(r['n']):,} | {100*r['wr']:.1f}% |\n")

    best = res.sort_values("wr", ascending=False).iloc[0]
    over = res[res["wr"] > 0.5]
    md += f"""
## Mejor WR puro: os/ob={best['os']:.0f}/{best['ob']:.0f} fwd={best['fwd']} "
        f"min_pip={best['min_pips']:.0f} sep={best['sep']:.0f} cruce={best['cruce']} "
        f"-> WR={100*best['wr']:.1f}% (n={int(best['n']):,})

## WR por activo en esa mejor combinación
"""
    for p in data:
        md += f"- {p}: WR={100*best[f'wr_{p}']:.1f}% (n={int(best[f'n_{p}']):,})\n"

    md += f"""
## Resumen
- Combinaciones: {len(res):,}
- WR > 50%: {len(over)} ({(100*len(over)/len(res)):.0f}% del total)

Si hay combinaciones WR>50% con n suficiente, tu teoría del "empujón al salir
de zona" se CONFIRMA con data grande multi-activo. Si no, el empuje es
simétrico (existe pero no predice dirección) y sirve como filtro, no señal.
"""
    rep = ROOT / "docs" / "ESTOCASTICO_ZONA_multisweep.md"
    rep.write_text(md, encoding="utf-8")
    res.to_csv(BORROWED / "estocastico_zona_multisweep.csv", index=False)
    print(f"[OK] combinaciones={len(res):,}  WR>50%: {len(over)}")
    print(f"[OK] mejor WR={100*best['wr']:.1f}% n={int(best['n']):,} "
          f"(os/ob={best['os']:.0f}/{best['ob']:.0f} fwd={best['fwd']} "
          f"min_pip={best['min_pips']:.0f} sep={best['sep']:.0f} cruce={best['cruce']})")
    print(f"[OK] reporte -> {rep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
