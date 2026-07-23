"""Deep analysis of all trades with margins."""
import sqlite3
import json
from pathlib import Path

db_path = Path("data/db/black_box_strat_2026-07-14.db")
con = sqlite3.connect(db_path)
con.row_factory = sqlite3.Row

trades = con.execute("""
    SELECT id, asset, direction, score, payout, order_result, profit,
           entry_price, exit_price, ts, created_at,
           candles_1m, candles_post, stoch_m15,
           loss_reason, improvement_hint, strategy_details
    FROM scan_candidates
    WHERE order_result IS NOT NULL
    ORDER BY id DESC
""").fetchall()

wins = [t for t in trades if t["order_result"] == "WIN"]
losses = [t for t in trades if t["order_result"] == "LOSS"]

print(f"Total: {len(trades)} trades ({len(wins)}W / {len(losses)}L)")
print()

# Check entry/exit prices
for t in trades:
    has_entry = t["entry_price"] is not None
    has_exit = t["exit_price"] is not None
    print(f"  #{t['id']} {t['asset']} {t['direction']} {t['order_result']} entry={t['entry_price']} exit={t['exit_price']} profit={t['profit']}")

# Calculate margins for trades that have prices
print("\n--- Margin analysis ---")
for t in trades:
    if t["entry_price"] and t["exit_price"] and t["entry_price"] > 0:
        margin = abs(t["exit_price"] - t["entry_price"]) / t["entry_price"] * 100
        direction_correct = (t["direction"] == "CALL" and t["exit_price"] > t["entry_price"]) or \
                           (t["direction"] == "PUT" and t["exit_price"] < t["entry_price"])
        print(f"  #{t['id']} {t['asset']} {t['direction']} {t['order_result']} margin={margin:.4f}% correct_dir={direction_correct}")

# Analyze candle patterns for wins vs losses
print("\n--- Candle pattern analysis ---")

def analyze_candles(trades_list, label):
    if not trades_list:
        return
    print(f"\n{label} ({len(trades_list)} trades):")

    # Last candle before entry analysis
    bodies = []
    upper_wicks = []
    lower_wicks = []
    body_ratios = []

    for t in trades_list:
        candles_1m = json.loads(t["candles_1m"]) if t["candles_1m"] else []
        if candles_1m:
            last = candles_1m[-1]
            body = abs(last["c"] - last["o"])
            total_range = last["h"] - last["l"] if last["h"] != last["l"] else 1
            upper_wick = last["h"] - max(last["o"], last["c"])
            lower_wick = min(last["o"], last["c"]) - last["l"]

            bodies.append(body)
            upper_wicks.append(upper_wick)
            lower_wicks.append(lower_wick)
            body_ratios.append(body / total_range)

            # Direction of last candle
            bullish = last["c"] > last["o"]
            print(f"  #{t['id']} {t['asset']} {t['direction']} last_candle={'bullish' if bullish else 'bearish'} body_ratio={body/total_range:.2f} upper_wick_ratio={upper_wick/total_range:.2f} lower_wick_ratio={lower_wick/total_range:.2f}")

    if bodies:
        avg_body = sum(bodies) / len(bodies)
        avg_upper = sum(upper_wicks) / len(upper_wicks)
        avg_lower = sum(lower_wicks) / len(lower_wicks)
        avg_body_ratio = sum(body_ratios) / len(body_ratios)
        print(f"  AVG: body={avg_body:.6f} upper_wick={avg_upper:.6f} lower_wick={avg_lower:.6f} body_ratio={avg_body_ratio:.2f}")

analyze_candles(wins, "WINS")
analyze_candles(losses, "LOSSES")

# Stochastic analysis
print("\n--- Stochastic M15 analysis ---")
for t in trades:
    stoch = json.loads(t["stoch_m15"]) if t["stoch_m15"] else {}
    if stoch:
        print(f"  #{t['id']} {t['asset']} {t['direction']} {t['order_result']} K={stoch.get('k')} D={stoch.get('d')} estado={stoch.get('estado')}")

con.close()
