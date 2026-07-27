"""LAB-002: tamaño de la zona de freno (proxy POI) y probabilidad de rebote.

Reproducible: PYTHONPATH=src python scripts/lab_002_tamano_zona.py
Requiere data/observador/episodes_eurusd_14y.db + parquet SMC-SYSTEMS.
Informe canónico: docs/LAB_002_TAMANO_ZONA.md
"""
import random
import sqlite3
import statistics as st
from collections import defaultdict

import numpy as np
import pandas as pd

DB = "data/observador/episodes_eurusd_14y.db"
PARQUET = r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\EURUSD_M1.parquet"
PIP = 0.0001
SPLIT_2020 = 1577836800.0
SEED, N_SHUFFLES = 11, 1000

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
eps = c.execute("select id,resolution_type,ts_open from episodes "
                "where resolution_type in ('REBOUND','CONTINUATION','CHAOS')").fetchall()

data = []  # (resolution, ts_open, size_pips)
for eid, res, to in eps:
    sd = states.get(eid, {})
    a, b = sd.get("BRAKE"), sd.get("RESOLUTION")
    if a is None or b is None or b <= a:
        continue
    i0, i1 = np.searchsorted(ts, a), np.searchsorted(ts, b, side="right")
    if i1 - i0 < 2:
        continue
    data.append((res, to, (hi[i0:i1].max() - lo[i0:i1].min()) / PIP))

sizes_rb = [s for r, _, s in data if r == "REBOUND"]
print(f"n={len(data)} | zona en REBOUND: media {st.mean(sizes_rb):.1f} pips, "
      f"mediana {st.median(sizes_rb):.1f}, p25-p75 "
      f"{np.percentile(sizes_rb,25):.1f}-{np.percentile(sizes_rb,75):.1f}")

q1, q2 = np.percentile([s for _, _, s in data], [33, 66])
rb = lambda g: 100 * sum(1 for d in g if d[0] == "REBOUND") / len(g)
print(f"terciles: <{q1:.1f} / {q1:.1f}-{q2:.1f} / >{q2:.1f} pips")
for name, cond in [("CHICA", lambda s: s < q1), ("MEDIA", lambda s: q1 <= s <= q2),
                   ("GRANDE", lambda s: s > q2)]:
    g = [d for d in data if cond(d[2])]
    g1 = [d for d in g if d[1] < SPLIT_2020]
    g2 = [d for d in g if d[1] >= SPLIT_2020]
    print(f"  {name}: n={len(g)}, REBOUND {rb(g):.1f}% | eras {rb(g1):.1f}/{rb(g2):.1f}")

grande = [d for d in data if d[2] > q2]
resto = [d for d in data if d[2] <= q2]
diff = rb(grande) / 100 - rb(resto) / 100
labels = [d[0] for d in data]
random.seed(SEED)
n1, worse = len(grande), 0
for _ in range(N_SHUFFLES):
    random.shuffle(labels)
    dl = (sum(1 for x in labels[:n1] if x == "REBOUND") / n1
          - sum(1 for x in labels[n1:] if x == "REBOUND") / (len(labels) - n1))
    worse += abs(dl) >= abs(diff)
print(f"placebo GRANDE vs resto: diff {100*diff:+.1f} pts, p-valor {worse/N_SHUFFLES:.3f}")
