"""Full analysis of all resolved STRAT-F trades across all black box DBs."""
import sys
import io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import sqlite3
import json
from pathlib import Path
from collections import defaultdict

db_dir = Path("data/db")
bb_dbs = sorted(db_dir.glob("black_box_strat_*.db"))

# Aggregate all resolved trades
trades = []
for db_path in bb_dbs:
    try:
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            SELECT id, asset, direction, score, payout, order_result, profit,
                   stoch_m15, stoch_contradicts, candles_15m, ts, created_at
            FROM scan_candidates
            WHERE strategy = 'STRAT-F' AND order_result IN ('WIN', 'LOSS')
            """
        ).fetchall()
        for row in rows:
            stoch = None
            if row["stoch_m15"]:
                try:
                    stoch = json.loads(row["stoch_m15"]) if isinstance(row["stoch_m15"], str) else row["stoch_m15"]
                except Exception:
                    pass
            trades.append({
                "id": row["id"],
                "asset": row["asset"],
                "direction": row["direction"],
                "score": row["score"],
                "payout": row["payout"],
                "result": row["order_result"],
                "profit": row["profit"] or 0.0,
                "stoch": stoch,
                "contradicts": row["stoch_contradicts"] or 0,
                "ts": row["ts"],
                "created_at": row["created_at"],
                "db": db_path.name,
            })
        con.close()
    except Exception:
        pass

total = len(trades)
wins = sum(1 for t in trades if t["result"] == "WIN")
losses = total - wins
baseline_wr = wins / max(1, total) * 100
total_profit = sum(t["profit"] for t in trades)
avg_profit_win = sum(t["profit"] for t in trades if t["result"] == "WIN") / max(1, wins)
avg_loss = sum(t["profit"] for t in trades if t["result"] == "LOSS") / max(1, losses)
expectancy = (baseline_wr/100 * avg_profit_win) + ((1 - baseline_wr/100) * avg_loss)

print("=" * 70)
print("  ANALISIS COMPLETO — STRAT-F BLACK BOX")
print("=" * 70)

print(f"\n[RESUMEN GENERAL]")
print(f"  Trades resueltos:  {total}")
print(f"  WIN:  {wins}  ({wins/max(1,total)*100:.1f}%)")
print(f"  LOSS: {losses}  ({losses/max(1,total)*100:.1f}%)")
print(f"  Baseline win rate:  {baseline_wr:.1f}%")
print(f"  Profit total:  ${total_profit:+.2f}")
print(f"  Avg WIN:  ${avg_profit_win:+.2f}")
print(f"  Avg LOSS: ${avg_loss:+.2f}")
print(f"  Expectancy:  ${expectancy:+.2f}/trade")
print(f"  Activos unicos:  {len(set(t['asset'] for t in trades))}")

# ── Win rate by estado ────────────────────────────────────────────────
print(f"\n[WIN RATE POR ESTADO]")
estado_stats = defaultdict(lambda: {"w": 0, "l": 0, "profit": 0.0})
for t in trades:
    if t["stoch"]:
        estado = t["stoch"].get("estado", "UNKNOWN")
    else:
        estado = "SIN_DATO"
    if t["result"] == "WIN":
        estado_stats[estado]["w"] += 1
    else:
        estado_stats[estado]["l"] += 1
    estado_stats[estado]["profit"] += t["profit"]

for estado, s in sorted(estado_stats.items(), key=lambda x: -(x[1]["w"] + x[1]["l"])):
    n = s["w"] + s["l"]
    wr = s["w"] / max(1, n) * 100
    print(f"  {estado:15s}: {s['w']:3d}/{n:3d} = {wr:5.1f}%  | profit=${s['profit']:+.2f}")

# ── Win rate by direction + estado ────────────────────────────────────
print(f"\n[WIN RATE POR DIRECCION + ESTADO]")
combo_stats = defaultdict(lambda: {"w": 0, "l": 0, "profit": 0.0})
for t in trades:
    if t["stoch"]:
        estado = t["stoch"].get("estado", "UNKNOWN")
    else:
        estado = "SIN_DATO"
    key = f"{t['direction']} + {estado}"
    if t["result"] == "WIN":
        combo_stats[key]["w"] += 1
    else:
        combo_stats[key]["l"] += 1
    combo_stats[key]["profit"] += t["profit"]

for combo, s in sorted(combo_stats.items(), key=lambda x: -(x[1]["w"] + x[1]["l"])):
    n = s["w"] + s["l"]
    wr = s["w"] / max(1, n) * 100
    flag = ">>>" if wr > baseline_wr + 10 else ("<<<" if wr < baseline_wr - 10 else "")
    print(f"  {combo:25s}: {s['w']:3d}/{n:3d} = {wr:5.1f}%  | profit=${s['profit']:+.2f}  {flag}")

# ── Win rate by cruce ─────────────────────────────────────────────────
print(f"\n[WIN RATE POR CRUCE]")
cruce_stats = defaultdict(lambda: {"w": 0, "l": 0, "profit": 0.0})
for t in trades:
    if t["stoch"]:
        cruce = str(t["stoch"].get("cruce") or "sin_cruce")
    else:
        cruce = "SIN_DATO"
    if t["result"] == "WIN":
        cruce_stats[cruce]["w"] += 1
    else:
        cruce_stats[cruce]["l"] += 1
    cruce_stats[cruce]["profit"] += t["profit"]

for cruce, s in sorted(cruce_stats.items(), key=lambda x: -(x[1]["w"] + x[1]["l"])):
    n = s["w"] + s["l"]
    wr = s["w"] / max(1, n) * 100
    print(f"  {cruce:15s}: {s['w']:3d}/{n:3d} = {wr:5.1f}%  | profit=${s['profit']:+.2f}")

# ── Win rate by divergencia ───────────────────────────────────────────
print(f"\n[WIN RATE POR DIVERGENCIA]")
div_stats = defaultdict(lambda: {"w": 0, "l": 0, "profit": 0.0})
for t in trades:
    if t["stoch"]:
        div = str(t["stoch"].get("divergencia") or "sin_div")
    else:
        div = "SIN_DATO"
    if t["result"] == "WIN":
        div_stats[div]["w"] += 1
    else:
        div_stats[div]["l"] += 1
    div_stats[div]["profit"] += t["profit"]

for div, s in sorted(div_stats.items(), key=lambda x: -(x[1]["w"] + x[1]["l"])):
    n = s["w"] + s["l"]
    wr = s["w"] / max(1, n) * 100
    print(f"  {div:15s}: {s['w']:3d}/{n:3d} = {wr:5.1f}%  | profit=${s['profit']:+.2f}")

# ── Contradicts ───────────────────────────────────────────────────────
print(f"\n[WIN RATE POR CONTRADICTS]")
for c in [0, 1]:
    subset = [t for t in trades if t["contradicts"] == c]
    n = len(subset)
    w = sum(1 for t in subset if t["result"] == "WIN")
    wr = w / max(1, n) * 100
    profit = sum(t["profit"] for t in subset)
    print(f"  contradicts={c}: {w:3d}/{n:3d} = {wr:5.1f}%  | profit=${profit:+.2f}")

# ── Win rate by payout range ──────────────────────────────────────────
print(f"\n[WIN RATE POR PAYOUT]")
payout_stats = defaultdict(lambda: {"w": 0, "l": 0, "profit": 0.0})
for t in trades:
    bucket = f"{t['payout'] // 5 * 5}-{t['payout'] // 5 * 5 + 4}%"
    if t["result"] == "WIN":
        payout_stats[bucket]["w"] += 1
    else:
        payout_stats[bucket]["l"] += 1
    payout_stats[bucket]["profit"] += t["profit"]

for bucket, s in sorted(payout_stats.items()):
    n = s["w"] + s["l"]
    wr = s["w"] / max(1, n) * 100
    print(f"  {bucket:10s}: {s['w']:3d}/{n:3d} = {wr:5.1f}%  | profit=${s['profit']:+.2f}")

# ── Win rate by asset (top 10) ────────────────────────────────────────
print(f"\n[WIN RATE POR ACTIVO (top 10 por volumen)]")
asset_stats = defaultdict(lambda: {"w": 0, "l": 0, "profit": 0.0})
for t in trades:
    if t["result"] == "WIN":
        asset_stats[t["asset"]]["w"] += 1
    else:
        asset_stats[t["asset"]]["l"] += 1
    asset_stats[t["asset"]]["profit"] += t["profit"]

top_assets = sorted(asset_stats.items(), key=lambda x: -(x[1]["w"] + x[1]["l"]))[:10]
for asset, s in top_assets:
    n = s["w"] + s["l"]
    wr = s["w"] / max(1, n) * 100
    print(f"  {asset:20s}: {s['w']:3d}/{n:3d} = {wr:5.1f}%  | profit=${s['profit']:+.2f}")

# ── Win rate by hour of day ───────────────────────────────────────────
print(f"\n[WIN RATE POR HORA DEL DIA (UTC-3)]")
hour_stats = defaultdict(lambda: {"w": 0, "l": 0})
for t in trades:
    if t["created_at"]:
        try:
            hour = int(t["created_at"][11:13])
            hour_utc3 = (hour - 3) % 24
        except Exception:
            continue
        if t["result"] == "WIN":
            hour_stats[hour_utc3]["w"] += 1
        else:
            hour_stats[hour_utc3]["l"] += 1

for hour in sorted(hour_stats.keys()):
    s = hour_stats[hour]
    n = s["w"] + s["l"]
    wr = s["w"] / max(1, n) * 100
    print(f"  {hour:02d}:00  : {s['w']:3d}/{n:3d} = {wr:5.1f}%")

# ── Key findings ──────────────────────────────────────────────────────
print(f"\n{'=' * 70}")
print("  HALLAZGOS CLAVE")
print("=" * 70)

# Find combos significantly above/below baseline
print(f"\n  Baseline win rate: {baseline_wr:.1f}%")
print(f"  Umbral 'bueno':    > {baseline_wr + 10:.1f}%")
print(f"  Umbral 'malo':     < {baseline_wr - 10:.1f}%")

print(f"\n  Combos que superan el baseline (+10pp):")
for combo, s in sorted(combo_stats.items(), key=lambda x: -(x[1]["w"] + x[1]["l"])):
    n = s["w"] + s["l"]
    if n >= 3:
        wr = s["w"] / max(1, n) * 100
        if wr > baseline_wr + 10:
            print(f"    >>> {combo}: {wr:.1f}% ({n} trades)")

print(f"\n  Combos por debajo del baseline (-10pp):")
for combo, s in sorted(combo_stats.items(), key=lambda x: -(x[1]["w"] + x[1]["l"])):
    n = s["w"] + s["l"]
    if n >= 3:
        wr = s["w"] / max(1, n) * 100
        if wr < baseline_wr - 10:
            print(f"    <<< {combo}: {wr:.1f}% ({n} trades)")

# Divergence analysis
div_with_trades = {k: v for k, v in div_stats.items() if k not in ("sin_div", "SIN_DATO", "None")}
if div_with_trades:
    print(f"\n  Divergencias detectadas:")
    for div, s in div_with_trades.items():
        n = s["w"] + s["l"]
        wr = s["w"] / max(1, n) * 100
        print(f"    {div}: {wr:.1f}% ({n} trades) vs baseline {baseline_wr:.1f}%")
else:
    print(f"\n  Divergencias: solo deteccion automatica del stoch (ventana 5 velas).")
    print(f"  Se necesita re-deteccion con algoritmo de swings (07_analisis, Fase C).")
