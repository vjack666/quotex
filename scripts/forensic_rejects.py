"""Reconstrucción forense: ¿qué habría pasado si los rechazos hubieran entrado?

Fuente: caja negra black_box_strat_2026-07-27.db.
- Entrada hipotética: último close M1 guardado en el registro del candidato (precio al momento del scan).
- Salida: precio ~900s después, reconstruido desde las velas guardadas de TODOS los
  registros del mismo activo (M1 y M5). Sin inventar datos: si no hay vela cerca
  del ts de salida (tolerancia 120s), el caso se marca SIN_DATOS.
- Dirección: columna direction o inferida del evento (fractal_down=CALL, fractal_up=PUT).
"""
import sqlite3, json, sys
from collections import defaultdict
from datetime import datetime

DB = 'data/db/black_box_strat_2026-07-27.db'
DUR = 900
TOL = 120

c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
rows = c.execute("select * from scan_candidates").fetchall()

# 1) series de precios por activo desde velas guardadas (M1 preferente, M5 completa)
series = defaultdict(dict)  # asset -> {ts: close}
for r in rows:
    a = r['asset']
    for col, tf in (('candles_1m', 60), ('candles_5m', 300)):
        try:
            v = json.loads(r[col]) if r[col] else []
        except Exception:
            v = []
        for x in v:
            if isinstance(x, dict):
                ts = int(x.get('ts') or x.get('time') or 0)
                cl = x.get('close') if 'close' in x else x.get('c')
                if ts and cl:
                    series[a].setdefault(ts, float(cl))

def px_at(asset, ts):
    s = series.get(asset, {})
    best, bdiff = None, TOL + 1
    for t, p in s.items():
        d = abs(t - ts)
        if d < bdiff:
            best, bdiff = p, d
    return best

def direction_of(r):
    d = (r['direction'] or '').upper()
    if d in ('CALL', 'PUT'):
        return d
    try:
        ev = json.loads(r['strategy_details'] or '{}').get('event')
    except Exception:
        ev = None
    return {'fractal_down': 'CALL', 'fractal_up': 'PUT'}.get(ev)

def entry_px(r):
    try:
        v = json.loads(r['candles_1m'] or '[]')
        if v: return float(v[-1].get('close') or v[-1].get('c'))
    except Exception:
        pass
    return None

buckets = defaultdict(lambda: {'win': 0, 'loss': 0, 'flat': 0, 'nodata': 0, 'nodir': 0, 'ex': []})
for r in rows:
    if not str(r['decision']).startswith('REJECT'):
        continue
    reason = r['reject_reason'] or '?'
    key = ('LISTA_ESPERA (zona muy joven R3)' if reason.startswith('zona muy joven') else reason)
    b = buckets[key]
    d = direction_of(r)
    if not d:
        b['nodir'] += 1
        continue
    e = entry_px(r)
    x = px_at(r['asset'], int(r['ts']) + DUR)
    if e is None or x is None:
        b['nodata'] += 1
        continue
    if abs(x - e) < 1e-9:
        b['flat'] += 1; res = 'EMPATE'
    elif (x > e) == (d == 'CALL'):
        b['win'] += 1; res = 'GANA'
    else:
        b['loss'] += 1; res = 'PIERDE'
    if len(b['ex']) < 3:
        b['ex'].append((r['asset'], datetime.fromtimestamp(r['ts']).strftime('%H:%M'), d, e, x, res))

print(f"{'MOTIVO DE RECHAZO':46s} {'sim':>4s} {'gana':>5s} {'pierde':>6s} {'WR%':>6s} {'EV(u)':>7s} {'s/datos':>7s}")
tot_w = tot_l = 0
for k, b in sorted(buckets.items(), key=lambda kv: -(kv[1]['win'] + kv[1]['loss'])):
    n = b['win'] + b['loss']
    wr = 100 * b['win'] / n if n else 0
    ev = 0.9 * b['win'] - b['loss']  # payout medio 90%
    tot_w += b['win']; tot_l += b['loss']
    print(f"{k[:46]:46s} {n:4d} {b['win']:5d} {b['loss']:6d} {wr:6.1f} {ev:+7.1f} {b['nodata']+b['nodir']:7d}")
n = tot_w + tot_l
print('-' * 90)
print(f"{'TOTAL':46s} {n:4d} {tot_w:5d} {tot_l:6d} {100*tot_w/n if n else 0:6.1f} {0.9*tot_w-tot_l:+7.1f}")
print()
print('Breakeven con payout 90%: se necesita WR >= 52.6% para no perder plata.')
print()
for k, b in sorted(buckets.items(), key=lambda kv: -(kv[1]['win'] + kv[1]['loss'])):
    if b['ex']:
        print(f"[{k}] ejemplos:")
        for a, hh, d, e, x, res in b['ex']:
            print(f"   {a:14s} {hh} {d:4s} entry={e:<10g} exit={x:<10g} -> {res}")
