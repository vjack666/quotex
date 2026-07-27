"""Experimento LAB-002: tamaño de la zona de freno (proxy POI de reacción).

Reproducible: PYTHONPATH=src python scripts/lab_002_tamano_zona_freno.py
Requiere data/observador/episodes_eurusd_14y.db (scripts/corrida_14y.py)
y el parquet EURUSD_M1 de SMC-SYSTEMS (solo lectura).
Resultados canónicos: docs/LAB_002_TAMANO_ZONA_FRENO.md
"""
import sqlite3
import statistics as st
from collections import defaultdict

import numpy as np
import pandas as pd

PARQUET = r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\EURUSD_M1.parquet"
DB = "data/observador/episodes_eurusd_14y.db"
PIP = 0.0001

df = pd.read_parquet(PARQUET)
t = pd.to_datetime(df["time"], utc=True)
ts = (t - pd.Timestamp(0, tz="UTC")).dt.total_seconds().to_numpy()
hi, lo = df["high"].to_numpy(), df["low"].to_numpy()
order = np.argsort(ts)
ts, hi, lo = ts[order], hi[order], lo[order]

c = sqlite3.connect(DB)
states = defaultdict(dict)
for eid, s, te in c.execute("select episode_id,state,ts_enter from episode_states "
                            "where state in ('BRAKE','RESOLUTION')"):
    states[eid][s] = te

sizes, durs = defaultdict(list), defaultdict(list)
for eid, res in c.execute("select id,resolution_type from episodes "
                          "where resolution_type in ('REBOUND','CONTINUATION','CHAOS')"):
    sd = states.get(eid, {})
    a, b = sd.get("BRAKE"), sd.get("RESOLUTION")
    if a is None or b is None or b <= a:
        continue
    i0, i1 = np.searchsorted(ts, a), np.searchsorted(ts, b, side="right")
    if i1 - i0 < 2:
        continue
    sizes[res].append((hi[i0:i1].max() - lo[i0:i1].min()) / PIP)
    durs[res].append((b - a) / 60)

print("ZONA DE FRENO (BRAKE→RESOLUTION), EURUSD, pips:")
for res in ("REBOUND", "CONTINUATION", "CHAOS"):
    v = sizes[res]
    print(f"  {res}: n={len(v)}, media {st.mean(v):.1f}, mediana {st.median(v):.1f}, "
          f"p25-p75 {np.percentile(v, 25):.1f}-{np.percentile(v, 75):.1f}, "
          f"dur mediana {st.median(durs[res]):.0f} min")

allv = [(s, r) for r in sizes for s in sizes[r]]
q = np.percentile([s for s, _ in allv], [33, 66])
print(f"\nTerciles de tamaño (<{q[0]:.1f} / {q[0]:.1f}-{q[1]:.1f} / >{q[1]:.1f} pips):")
for name, cond in [("CHICA", lambda s: s < q[0]),
                   ("MEDIA", lambda s: q[0] <= s <= q[1]),
                   ("GRANDE", lambda s: s > q[1])]:
    grp = [(s, r) for s, r in allv if cond(s)]
    rb = sum(1 for _, r in grp if r == "REBOUND")
    print(f"  {name}: n={len(grp)}, REBOUND {100 * rb / len(grp):.1f}%")
