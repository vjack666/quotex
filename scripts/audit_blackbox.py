"""Analyze black box data for STRAT-F + stochastic completeness."""
import sys
import io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import sqlite3
import json
from pathlib import Path

db_dir = Path("data/db")
bb_dbs = sorted(db_dir.glob("black_box_strat_*.db"))

print(f"Black box DBs found: {len(bb_dbs)}")
for db in bb_dbs:
    print(f"  {db.name} ({db.stat().st_size // 1024} KB)")

# Aggregate across all DBs
total_strat_f = 0
total_with_result = 0
stoch_complete = 0
stoch_null = 0
stoch_partial = 0
candles_15m_present = 0
candles_15m_enough = 0  # >= 15 candles for stoch computation
estado_dist = {}
contradicts_count = 0
divergencia_dist = {}
cruce_dist = {}
direction_dist = {}
win_count = 0
loss_count = 0
scores = []
assets = set()
issues = []

for db_path in bb_dbs:
    try:
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row

        rows = con.execute(
            """
            SELECT id, strategy, asset, direction, score, payout,
                   order_result, stoch_m15, stoch_contradicts,
                   candles_15m, candles_5m, candles_1m, ts
            FROM scan_candidates
            WHERE strategy = 'STRAT-F' AND order_result IN ('WIN', 'LOSS')
            """
        ).fetchall()

        for row in rows:
            total_strat_f += 1
            assets.add(row["asset"])
            scores.append(row["score"])
            direction_dist[row["direction"]] = direction_dist.get(row["direction"], 0) + 1

            if row["order_result"] == "WIN":
                win_count += 1
            else:
                loss_count += 1

            # stoch_m15 analysis
            stoch_raw = row["stoch_m15"]
            if stoch_raw is None:
                stoch_null += 1
            else:
                try:
                    stoch = json.loads(stoch_raw) if isinstance(stoch_raw, str) else stoch_raw
                    stoch_complete += 1

                    # Check completeness of stoch fields
                    has_k = stoch.get("k") is not None
                    has_d = stoch.get("d") is not None
                    has_estado = stoch.get("estado") is not None
                    has_cruce = stoch.get("cruce") is not None
                    has_div = stoch.get("divergencia") is not None

                    if not (has_k and has_d and has_estado):
                        stoch_partial += 1

                    # Estado distribution
                    estado = stoch.get("estado", "UNKNOWN")
                    estado_dist[estado] = estado_dist.get(estado, 0) + 1

                    # Cruce distribution
                    cruce = stoch.get("cruce")
                    if cruce:
                        cruce_dist[cruce] = cruce_dist.get(cruce, 0) + 1

                    # Divergencia distribution
                    div = stoch.get("divergencia")
                    if div:
                        divergencia_dist[div] = divergencia_dist.get(div, 0) + 1

                except (json.JSONDecodeError, TypeError):
                    stoch_partial += 1

            # stoch_contradicts
            if row["stoch_contradicts"]:
                contradicts_count += 1

            # candles_15m analysis
            c15_raw = row["candles_15m"]
            if c15_raw:
                candles_15m_present += 1
                try:
                    c15 = json.loads(c15_raw) if isinstance(c15_raw, str) else c15_raw
                    if isinstance(c15, list) and len(c15) >= 15:
                        candles_15m_enough += 1
                except (json.JSONDecodeError, TypeError):
                    pass

        con.close()
    except Exception as e:
        issues.append(f"Error reading {db_path.name}: {e}")

# ── Report ──────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  STRAT-F BLACK BOX DATA AUDIT")
print("=" * 70)

print(f"\n[VOLUME]")
print(f"  Total STRAT-F trades with result:  {total_strat_f}")
print(f"    WIN:  {win_count}  ({win_count/max(1,total_strat_f)*100:.1f}%)")
print(f"    LOSS: {loss_count}  ({loss_count/max(1,total_strat_f)*100:.1f}%)")
print(f"  Baseline win rate:  {win_count/max(1,total_strat_f)*100:.1f}%")
print(f"  Unique assets:  {len(assets)}")
print(f"  Score range:  {min(scores) if scores else 'N/A'} - {max(scores) if scores else 'N/A'}")
print(f"  Score avg:  {sum(scores)/max(1,len(scores)):.1f}")

print(f"\n[STOCHASTIC M15 COMPLETENESS]")
print(f"  Complete (valid JSON with k/d/estado):  {stoch_complete}  ({stoch_complete/max(1,total_strat_f)*100:.1f}%)")
print(f"  NULL / missing:  {stoch_null}  ({stoch_null/max(1,total_strat_f)*100:.1f}%)")
print(f"  Partial / malformed:  {stoch_partial}")

print(f"\n[STOCHASTIC ESTADO DISTRIBUTION]")
for estado, count in sorted(estado_dist.items(), key=lambda x: -x[1]):
    print(f"  {estado:15s}: {count:4d} trades")

print(f"\n[STOCHASTIC CRUCE DISTRIBUTION]")
for cruce, count in sorted(cruce_dist.items(), key=lambda x: -x[1]):
    print(f"  {cruce:15s}: {count:4d}")

print(f"\n[STOCHASTIC DIVERGENCIA DISTRIBUTION]")
for div, count in sorted(divergencia_dist.items(), key=lambda x: -x[1]):
    print(f"  {div:15s}: {count:4d}")

print(f"\n[CONTRADICTION]")
print(f"  stoch_contradicts=1:  {contradicts_count}  ({contradicts_count/max(1,total_strat_f)*100:.1f}%)")

print(f"\n[CANDLES_15m]")
print(f"  Present:  {candles_15m_present}  ({candles_15m_present/max(1,total_strat_f)*100:.1f}%)")
print(f"  Enough for divergence (>=15 candles):  {candles_15m_enough}  ({candles_15m_enough/max(1,total_strat_f)*100:.1f}%)")

print(f"\n[DIRECTION DISTRIBUTION]")
for d, count in sorted(direction_dist.items(), key=lambda x: -x[1]):
    print(f"  {d:15s}: {count:4d}")

if issues:
    print(f"\n[ISSUES]")
    for issue in issues:
        print(f"  - {issue}")

# -- Recommendation --
print(f"\n{'=' * 70}")
print("  RECOMMENDATION")
print("=" * 70)

if total_strat_f < 50:
    print(f"\n  INSUFFICIENT DATA: Only {total_strat_f} trades collected.")
    print(f"     Minimum recommended: 100 trades for meaningful analysis.")
    print(f"     Action: Keep running Continuous Mode.")
elif stoch_null > total_strat_f * 0.3:
    print(f"\n  STOCHASTIC DATA GAP: {stoch_null} trades ({stoch_null/max(1,total_strat_f)*100:.1f}%) have no stoch_m15.")
    print(f"     Action: Check if compute_stoch() is being called for all STRAT-F signals.")
elif candles_15m_enough < total_strat_f * 0.5:
    print(f"\n  CANDLE DATA GAP: Only {candles_15m_enough} trades have enough 15m candles for divergence detection.")
    print(f"     Action: Verify candles_15m is being populated in scanner.py.")
else:
    print(f"\n  DATA SUFFICIENT for initial divergence analysis.")
    print(f"     {total_strat_f} trades, {stoch_complete} with complete stoch, {candles_15m_enough} with enough candles.")
    print(f"     Next step: Run divergence re-detection (07_analisis_divergencias_blackbox.md, Fase C).")
