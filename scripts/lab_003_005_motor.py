"""LAB-003/004/005: geografía del giro, tiempo en la pelea, y el MOTOR (apilado).

Reproducible: PYTHONPATH=src python scripts/lab_003_005_motor.py
Requiere data/observador/episodes_eurusd_14y.db + parquet SMC-SYSTEMS.
Informe canónico: docs/LAB_003_005_MOTOR.md
"""
import sqlite3
import statistics as st
from collections import defaultdict

import numpy as np
import pandas as pd

DB = "data/observador/episodes_eurusd_14y.db"
PARQUET = r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\EURUSD_M1.parquet"
PIP, SPLIT_2020 = 0.0001, 1577836800.0

df = pd.read_parquet(PARQUET)
t = pd.to_datetime(df["time"], utc=True)
ts = (t - pd.Timestamp(0, tz="UTC")).dt.total_seconds().to_numpy()
hi, lo = df["high"].to_numpy(), df["low"].to_numpy()
o = np.argsort(ts)
ts, hi, lo = ts[o], hi[o], lo[o]

c = sqlite3.connect(DB)
states = defaultdict(dict)
for eid, s, te in c.execute("select episode_id,state,ts_enter from episode_states "
                            "where state in ('BRAKE','RESOLUTION')"):
    states[eid][s] = te
dirs = dict(c.execute("select episode_id, direction from pressure_points group by episode_id"))
pp = defaultdict(list)
for eid, norm, cont in c.execute("select episode_id,net_advance_norm,continuity "
                                 "from pressure_points order by episode_id,ts"):
    pp[eid].append((norm, cont))
eps = c.execute("select id,resolution_type,ts_open from episodes "
                "where resolution_type in ('REBOUND','CONTINUATION','CHAOS')").fetchall()

rows = []
for eid, res, to in eps:
    sd, d, cur = states.get(eid, {}), dirs.get(eid), pp.get(eid)
    a, b = sd.get("BRAKE"), sd.get("RESOLUTION")
    if a is None or b is None or b <= a or d is None or not cur or len(cur) < 8:
        continue
    ia, i1 = np.searchsorted(ts, a), np.searchsorted(ts, b, side="right")
    if ia < 5 or i1 - ia < 2:
        continue
    zh, zl = hi[ia - 5:ia].max(), lo[ia - 5:ia].min()
    size = zh - zl
    if size <= 0:
        continue
    pen = ((hi[ia:i1].max() - zh) if d > 0 else (zl - lo[ia:i1].min())) / size
    tail = cur[-5:]
    peak = max(x[0] for x in cur) or 1e-9
    rows.append(dict(res=res, to=to, pen=pen, dwell=(b - a) / 60.0,
                     adv=sum(x[0] for x in tail) / 5, cont=sum(x[1] for x in tail) / 5,
                     frac=cur[-1][0] / peak,
                     zona=(hi[ia:i1].max() - lo[ia:i1].min()) / PIP))

rb = lambda g: 100 * sum(1 for r in g if r["res"] == "REBOUND") / len(g) if g else 0.0
eras = lambda g: (rb([r for r in g if r["to"] < SPLIT_2020]),
                  rb([r for r in g if r["to"] >= SPLIT_2020]))
print(f"n analizable: {len(rows)}")

# LAB-003: penetración más allá de la caja del freno (5 velas pre-BRAKE)
p33, p66 = np.percentile([r["pen"] for r in rows], [33, 66])
print(f"\nLAB-003 PENETRACION (terciles {100*p33:.0f}%/{100*p66:.0f}%):")
for name, cond in [("POCA", lambda p: p < p33), ("MEDIA", lambda p: p33 <= p <= p66),
                   ("MUCHA", lambda p: p > p66)]:
    g = [r for r in rows if cond(r["pen"])]
    e1, e2 = eras(g)
    print(f"  {name}: n={len(g)}, REBOUND {rb(g):.1f}% | eras {e1:.1f}/{e2:.1f}")

# LAB-005: el motor — apilado de condiciones
ADV = np.percentile([r["adv"] for r in rows], 33.33)
CONT = np.percentile([r["cont"] for r in rows], 33.33)
Z66 = np.percentile([r["zona"] for r in rows], 66)
D66 = np.percentile([r["dwell"] for r in rows], 66)
muerte = lambda r: r["adv"] <= ADV and r["frac"] < 0.10 and r["cont"] <= CONT
print("\nLAB-005 MOTOR:")
for name, cond in [
        ("base", lambda r: True),
        ("A muerte empuje (LAB-001)", muerte),
        ("B A+zona grande", lambda r: muerte(r) and r["zona"] > Z66),
        ("C A+poca penetracion", lambda r: muerte(r) and r["pen"] < p33),
        ("D B+poca penetracion", lambda r: muerte(r) and r["zona"] > Z66 and r["pen"] < p33),
        ("E D+pelea larga", lambda r: muerte(r) and r["zona"] > Z66 and r["pen"] < p33
                                      and r["dwell"] > D66)]:
    g = [r for r in rows if cond(r)]
    if not g:
        continue
    e1, e2 = eras(g)
    print(f"  {name}: n={len(g)}, REBOUND {rb(g):.1f}% | eras {e1:.1f}/{e2:.1f} "
          f"| ~{len(g)/14/250:.1f}/dia")
