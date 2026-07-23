"""Analyze black box trades: losses, wide wins, narrow wins."""
import sqlite3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from black_box_recorder import DB_DIR

# Find all black box DBs
dbs = sorted(DB_DIR.glob("black_box_strat_*.db"))
print(f"Found {len(dbs)} black box DB files")
for d in dbs:
    print(f"  {d.name} ({d.stat().st_size / 1024:.1f} KB)")

if not dbs:
    print("No black box DBs found.")
    sys.exit(0)

# Use the most recent one
db_path = dbs[-1]
print(f"\nAnalyzing: {db_path.name}")
con = sqlite3.connect(db_path)
con.row_factory = sqlite3.Row

# Get all resolved trades
trades = con.execute("""
    SELECT id, asset, direction, score, payout, order_result, profit,
           entry_price, exit_price, ts, created_at,
           candles_1m, candles_post, stoch_m15,
           loss_reason, improvement_hint, masaniello_snapshot,
           strategy_details
    FROM scan_candidates
    WHERE order_result IS NOT NULL
    ORDER BY id DESC
""").fetchall()

print(f"\nTotal resolved trades: {len(trades)}")

wins = [t for t in trades if t["order_result"] == "WIN"]
losses = [t for t in trades if t["order_result"] == "LOSS"]

print(f"  WIN: {len(wins)}")
print(f"  LOSS: {len(losses)}")
if len(trades) > 0:
    print(f"  Win Rate: {len(wins)/len(trades)*100:.1f}%")

# ── ANALYSIS OF LOSSES ──────────────────────────────────────────────────────
sep = "=" * 60
print(f"\n{sep}")
print(f"ANALYSIS OF LOSSES ({len(losses)})")
print(sep)

loss_reasons = {}
for t in losses:
    reason = t["loss_reason"] or "unknown"
    loss_reasons[reason] = loss_reasons.get(reason, 0) + 1

print("\nLoss reason ranking:")
for reason, count in sorted(loss_reasons.items(), key=lambda x: -x[1]):
    print(f"  {count}x — {reason}")

# Show improvement hints
hints = {}
for t in losses:
    hint = t["improvement_hint"] or "none"
    hints[hint] = hints.get(hint, 0) + 1

print("\nImprovement hints:")
for hint, count in sorted(hints.items(), key=lambda x: -x[1]):
    print(f"  {count}x — {hint}")

# Show score distribution of losses
loss_scores = [t["score"] for t in losses if t["score"] is not None]
if loss_scores:
    print(f"\nLoss score stats:")
    print(f"  Min: {min(loss_scores):.1f}")
    print(f"  Max: {max(loss_scores):.1f}")
    print(f"  Avg: {sum(loss_scores)/len(loss_scores):.1f}")

# Show detailed loss examples
print(f"\n--- Detailed loss examples (up to 5) ---")
for t in losses[:5]:
    details = json.loads(t["strategy_details"]) if t["strategy_details"] else {}
    candles_1m = json.loads(t["candles_1m"]) if t["candles_1m"] else []
    candles_post = json.loads(t["candles_post"]) if t["candles_post"] else []
    stoch = json.loads(t["stoch_m15"]) if t["stoch_m15"] else {}

    print(f"\n  Trade #{t['id']}")
    print(f"    Asset: {t['asset']} | Direction: {t['direction']}")
    print(f"    Score: {t['score']} | Payout: {t['payout']}%")
    print(f"    Profit: {t['profit']}")
    print(f"    Loss Reason: {t['loss_reason']}")
    print(f"    Improvement Hint: {t['improvement_hint']}")
    if stoch:
        print(f"    Stoch M15: K={stoch.get('k')} D={stoch.get('d')} Estado={stoch.get('estado')}")

    if candles_1m:
        print(f"    Candles 1m before entry (last 3):")
        for i, c in enumerate(candles_1m[-3:]):
            body = abs(c["c"] - c["o"])
            upper_wick = c["h"] - max(c["o"], c["c"])
            lower_wick = min(c["o"], c["c"]) - c["l"]
            total_range = c["h"] - c["l"] if c["h"] != c["l"] else 1
            body_pct = body / total_range * 100
            print(f"      Candle -{3-i}: O={c['o']:.5f} H={c['h']:.5f} L={c['l']:.5f} C={c['c']:.5f} body={body:.5f} ({body_pct:.0f}% of range) upper_wick={upper_wick:.5f} lower_wick={lower_wick:.5f}")

    if candles_post:
        print(f"    Candles 1m after entry (first 3):")
        for i, c in enumerate(candles_post[:3]):
            body = abs(c["c"] - c["o"])
            total_range = c["h"] - c["l"] if c["h"] != c["l"] else 1
            body_pct = body / total_range * 100
            print(f"      Candle +{i+1}: O={c['o']:.5f} H={c['h']:.5f} L={c['l']:.5f} C={c['c']:.5f} body={body:.5f} ({body_pct:.0f}% of range)")

# ── ANALYSIS OF WINS ────────────────────────────────────────────────────────
print(f"\n{sep}")
print(f"ANALYSIS OF WINS ({len(wins)})")
print(sep)

# Calculate margin for each win
win_margins = []
for t in wins:
    if t["entry_price"] and t["exit_price"] and t["entry_price"] > 0:
        margin = abs(t["exit_price"] - t["entry_price"]) / t["entry_price"] * 100
        win_margins.append((t, margin))

if win_margins:
    win_margins.sort(key=lambda x: x[1], reverse=True)

    # Wide wins (top 25%)
    wide_idx = max(1, len(win_margins) // 4)
    wide_threshold = win_margins[wide_idx - 1][1]
    # Narrow wins (bottom 25%)
    narrow_idx = max(0, len(win_margins) - len(win_margins) // 4)
    narrow_threshold = win_margins[narrow_idx][1]

    margins = [m for _, m in win_margins]
    print(f"\nWin margin stats:")
    print(f"  Min: {min(margins):.4f}%")
    print(f"  Max: {max(margins):.4f}%")
    print(f"  Avg: {sum(margins)/len(margins):.4f}%")
    sorted_m = sorted(margins)
    print(f"  Median: {sorted_m[len(sorted_m)//2]:.4f}%")
    print(f"  Wide win threshold (top 25%): >= {wide_threshold:.4f}%")
    print(f"  Narrow win threshold (bottom 25%): <= {narrow_threshold:.4f}%")

    # Wide wins
    wide_wins = [(t, m) for t, m in win_margins if m >= wide_threshold]
    narrow_wins = [(t, m) for t, m in win_margins if m <= narrow_threshold]

    print(f"\n--- Wide wins ({len(wide_wins)}) ---")
    for t, m in wide_wins[:5]:
        print(f"  #{t['id']} {t['asset']} {t['direction']} score={t['score']} margin={m:.4f}% profit={t['profit']}")
        candles_1m = json.loads(t["candles_1m"]) if t["candles_1m"] else []
        if candles_1m:
            for i, c in enumerate(candles_1m[-3:]):
                body = abs(c["c"] - c["o"])
                upper_wick = c["h"] - max(c["o"], c["c"])
                lower_wick = min(c["o"], c["c"]) - c["l"]
                total_range = c["h"] - c["l"] if c["h"] != c["l"] else 1
                body_pct = body / total_range * 100
                print(f"    Candle -{3-i}: O={c['o']:.5f} H={c['h']:.5f} L={c['l']:.5f} C={c['c']:.5f} body={body:.5f} ({body_pct:.0f}% of range) upper={upper_wick:.5f} lower={lower_wick:.5f}")

    print(f"\n--- Narrow wins ({len(narrow_wins)}) ---")
    for t, m in narrow_wins[:5]:
        print(f"  #{t['id']} {t['asset']} {t['direction']} score={t['score']} margin={m:.4f}% profit={t['profit']}")
        candles_1m = json.loads(t["candles_1m"]) if t["candles_1m"] else []
        if candles_1m:
            for i, c in enumerate(candles_1m[-3:]):
                body = abs(c["c"] - c["o"])
                upper_wick = c["h"] - max(c["o"], c["c"])
                lower_wick = min(c["o"], c["c"]) - c["l"]
                total_range = c["h"] - c["l"] if c["h"] != c["l"] else 1
                body_pct = body / total_range * 100
                print(f"    Candle -{3-i}: O={c['o']:.5f} H={c['h']:.5f} L={c['l']:.5f} C={c['c']:.5f} body={body:.5f} ({body_pct:.0f}% of range) upper={upper_wick:.5f} lower={lower_wick:.5f}")

    # Compare patterns between wide and narrow wins
    print(f"\n--- Pattern comparison: Wide vs Narrow wins ---")

    def avg_score(trades_with_margin):
        scores = [t["score"] for t, _ in trades_with_margin if t["score"] is not None]
        return sum(scores) / len(scores) if scores else 0

    def avg_payout(trades_with_margin):
        payouts = [t["payout"] for t, _ in trades_with_margin if t["payout"] is not None]
        return sum(payouts) / len(payouts) if payouts else 0

    def avg_body_before(trades_with_margin):
        bodies = []
        for t, _ in trades_with_margin:
            candles_1m = json.loads(t["candles_1m"]) if t["candles_1m"] else []
            if candles_1m:
                last = candles_1m[-1]
                body = abs(last["c"] - last["o"])
                total_range = last["h"] - last["l"] if last["h"] != last["l"] else 1
                bodies.append(body / total_range)
        return sum(bodies) / len(bodies) if bodies else 0

    def avg_upper_wick(trades_with_margin):
        wicks = []
        for t, _ in trades_with_margin:
            candles_1m = json.loads(t["candles_1m"]) if t["candles_1m"] else []
            if candles_1m:
                last = candles_1m[-1]
                upper_wick = last["h"] - max(last["o"], last["c"])
                total_range = last["h"] - last["l"] if last["h"] != last["l"] else 1
                wicks.append(upper_wick / total_range)
        return sum(wicks) / len(wicks) if wicks else 0

    def avg_lower_wick(trades_with_margin):
        wicks = []
        for t, _ in trades_with_margin:
            candles_1m = json.loads(t["candles_1m"]) if t["candles_1m"] else []
            if candles_1m:
                last = candles_1m[-1]
                lower_wick = min(last["o"], last["c"]) - last["l"]
                total_range = last["h"] - last["l"] if last["h"] != last["l"] else 1
                wicks.append(lower_wick / total_range)
        return sum(wicks) / len(wicks) if wicks else 0

    print(f"  Wide wins: avg_score={avg_score(wide_wins):.1f} avg_payout={avg_payout(wide_wins):.1f}% avg_body={avg_body_before(wide_wins):.2f} avg_upper_wick={avg_upper_wick(wide_wins):.2f} avg_lower_wick={avg_lower_wick(wide_wins):.2f}")
    print(f"  Narrow wins: avg_score={avg_score(narrow_wins):.1f} avg_payout={avg_payout(narrow_wins):.1f}% avg_body={avg_body_before(narrow_wins):.2f} avg_upper_wick={avg_upper_wick(narrow_wins):.2f} avg_lower_wick={avg_lower_wick(narrow_wins):.2f}")

con.close()
print(f"\n{sep}")
print("Analysis complete.")
