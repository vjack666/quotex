"""Experimento LAB-001: la muerte del empuje predice el rebote.

Reproducible: PYTHONPATH=src python scripts/lab_001_muerte_empuje.py
Requiere data/observador/episodes_eurusd_14y.db (generada por scripts/corrida_14y.py).
Resultados canónicos: docs/LAB_001_MUERTE_EMPUJE.md
"""
import random
import sqlite3
from collections import defaultdict

DB = "data/observador/episodes_eurusd_14y.db"
SPLIT_2020 = 1577836800.0  # 2020-01-01 UTC: frontera walk-forward
PCT_PEAK_DEAD = 0.10       # empuje muerto: <10% del pico
PCT_PEAK_ALIVE = 0.60      # empuje vivo: >60% del pico
SEED, N_SHUFFLES = 7, 1000

c = sqlite3.connect(DB)
rows = c.execute("select id,resolution_type,ts_open from episodes "
                 "where resolution_type in ('REBOUND','CONTINUATION','CHAOS')").fetchall()
by = defaultdict(list)
for eid, ts, raw, norm, cont in c.execute(
        "select episode_id,ts,net_advance_raw,net_advance_norm,continuity "
        "from pressure_points order by episode_id,ts"):
    by[eid].append((raw, norm, cont))

data = []
for eid, res, to in rows:
    cur = by.get(eid)
    if not cur or len(cur) < 8:
        continue
    tail = cur[-5:]
    adv_tail = sum(x[1] for x in tail) / 5
    cont_tail = sum(x[2] for x in tail) / 5
    peak = max(x[1] for x in cur) or 1e-9
    data.append((res, to, adv_tail, cont_tail, cur[-1][1] / peak))

advs = sorted(d[2] for d in data)
conts = sorted(d[3] for d in data)
ADV_LO, CONT_LO = advs[len(advs) // 3], conts[len(conts) // 3]
is_dead = lambda d: d[2] <= ADV_LO and d[4] < PCT_PEAK_DEAD and d[3] <= CONT_LO
rb = lambda g: 100 * sum(1 for d in g if d[0] == 'REBOUND') / len(g)

dead = [d for d in data if is_dead(d)]
rest = [d for d in data if not is_dead(d)]
alive = [d for d in data if d[4] > PCT_PEAK_ALIVE]
print(f"n={len(data)} | MUERTE TOTAL n={len(dead)}: REBOUND {rb(dead):.1f}% "
      f"(resto {rb(rest):.1f}%) | empuje vivo: {rb(alive):.1f}%")
for name, lo, hi in [("2012-2019", 0, SPLIT_2020), ("2020-2026", SPLIT_2020, 9e18)]:
    era = [d for d in dead if lo <= d[1] < hi]
    print(f"  walk-forward {name}: n={len(era)}, REBOUND {rb(era):.1f}%")

diff = rb(dead) / 100 - rb(rest) / 100
labels = [d[0] for d in data]
random.seed(SEED)
n1, worse = len(dead), 0
for _ in range(N_SHUFFLES):
    random.shuffle(labels)
    dl = (sum(1 for x in labels[:n1] if x == 'REBOUND') / n1
          - sum(1 for x in labels[n1:] if x == 'REBOUND') / (len(labels) - n1))
    worse += abs(dl) >= abs(diff)
print(f"placebo: diff real {100*diff:+.1f} pts, p-valor {worse/N_SHUFFLES:.3f}")
