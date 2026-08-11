"""EXP-009 sobre OTC: EURUSD_otc real descargado de Quotex.
Resamplea M1 -> M5/M15 y corre el breaker como Motor de Secuencias.
Reporte embudo -> integridad -> winrate. Compara contra real (0.74).
"""
import sys, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(r"C:/Users/v_jac/Desktop/quotex/tools/quotex-historical-data")
SYS = pathlib.Path(r"C:/Users/v_jac/Desktop/backtest quotex")
sys.path.insert(0, str(SYS / "motor de quotex"))
sys.path.insert(0, str(SYS / "laboratorio experimental" / "EXP-009"))
import breaker_seq as bs

CSV = ROOT / "EURUSD_otc_60s_365days.csv"

def cargar_m1(path):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["datetime"])
    df = df.set_index("timestamp").sort_index()
    df = df[["open", "high", "low", "close"]].astype(float)
    df = df[~df.index.duplicated(keep="first")]
    return df

def resample(df, tf_min):
    agg = df.resample(f"{tf_min}min").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"))
    return agg.dropna()

def correr(df, nombre):
    print(f"\n=== {nombre} ({len(df)} velas, {df.index[0]} -> {df.index[-1]}) ===")
    ev, funnel = bs.breaker_sequence(df, mss_mode="implied")
    print("  EMBUDO:", {k: funnel[k] for k in
          ["ob_candidatos", "con_sweep", "con_cierre_mss", "zona_activa", "con_retest", "secuencia_completa"]})
    # backtest con las 4 configs
    res = {}
    for gate, exp, mss in [(True, "fixed4", "implied"),
                           (False, "fixed4", "implied"),
                           (True, "pullback", "implied"),
                           (True, "fixed4", "strict")]:
        _, _, r, _ = bs.run_breaker_backtest(df, bias_gate=gate, expiry_mode=exp, entry_mode="touch_edge")
        res[f"gate={gate} {exp} {mss}"] = r
        print(f"  {gate} {exp} {mss}: ops={r['ops']} WR={r['wr']:.3f}")
    return funnel, res

if __name__ == "__main__":
    m1 = cargar_m1(CSV)
    print(f"M1: {len(m1)} velas, {m1.index[0]} -> {m1.index[-1]}")
    for tf in [5, 15]:
        df = resample(m1, tf)
        correr(df, f"EURUSD_otc M{tf}")
