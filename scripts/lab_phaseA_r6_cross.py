"""PHASEA-R6 — Cruzar contexto (Phase_A_Score) x Edificio (R6).

Feature: edificio_wyckoff_phasea (R6). Caja negra intacta. Sin volumen.
Pregunta: cuando el Edificio dispara, ¿el contexto estructural (Phase_A_Score de la
ventana M15 previa, solo OHLC+tiempo) FILTRA la probabilidad de acierto?

Matriz:
  Fase A baja  -> win rate Edificio ?
  Fase A media -> win rate Edificio ?
  Fase A alta  -> win rate Edificio ?

Hipotesis a falsar: pendiente creciente (~52/56/63) en OOS.
El score se normaliza POR SPLIT (rank de las senales de ese split) para no contaminar OOS.
Sig. por diferencia de proporciones / chi2 entre terciles.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

M15_PATHS = [
    Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\cohorte_real_eurusd\EURUSD_M15.parquet"),
    Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\smc_borrowed\EURUSD_M15.parquet"),
]
EVENTS_PATH = Path(r"C:\Users\v_jac\Desktop\QUOTEX\src\strategy_lab\results\edificio_events.parquet")
REPORT_DIR = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\ew_reports\PHASEA-R6")
WINDOW = 20


def _load_m15() -> pd.DataFrame:
    for p in M15_PATHS:
        if p.exists():
            df = pd.read_parquet(p)
            df["ts"] = pd.to_datetime(df["time"])
            return df.sort_values("ts").set_index("ts")
    raise FileNotFoundError("No hay EURUSD_M15 en disco.")


def _componentes(o, h, l, c) -> dict:
    n = len(c)
    if n < 10:
        return {}
    half = max(5, n // 2)
    x = np.arange(n)
    sf = np.polyfit(x[:half], c[:half], 1)[0]
    ss = np.polyfit(x[half:], c[half:], 1)[0]
    rng = (h - l)
    net_first = abs(c[half - 1] - c[0]); net_second = abs(c[-1] - c[half - 1])
    agot = net_first - net_second
    comp = (rng[:half].mean() / rng[half:].mean()) if rng[half:].mean() > 0 else np.nan
    overlap = float(np.mean([min(h[i + 1], h[i]) - max(l[i + 1], l[i]) for i in range(n - 1)]))
    bf, ph, pl = 0, h[0], l[0]
    for i in range(1, n):
        touch = (h[i] >= ph) or (l[i] <= pl)
        inside = (c[i] <= ph) and (c[i] >= pl)
        if touch and inside:
            bf += 1
        ph, pl = max(ph, h[i]), min(pl, l[i])
    break_fail = bf / (n - 1) if n > 1 else 0.0
    safe = np.where(rng > 0, rng, np.nan)
    wick_vals = ((h - np.maximum(o, c)) + (np.minimum(o, c) - l)) / safe
    wick = float(np.nanmean(wick_vals)) if np.any(np.isfinite(wick_vals)) else 0.0
    chg = np.sign(np.diff(c))
    pf = float(np.mean(chg[: half - 1] != 0)) if half > 1 else 0.0
    ps = float(np.mean(chg[half - 1:] != 0)) if n - half > 1 else 0.0
    reduc = pf - ps
    cambio = abs(sf - ss)
    return {"agotamiento": float(agot), "compression": float(comp), "overlap": overlap,
            "break_fail": float(break_fail), "rechazo": wick, "reduc_cont": float(reduc),
            "cambio_reg": float(cambio)}


def _chi2_from_rates(wins, total):
    """chi2 de independencia tercil vs win/loss (2 grados). Devuelve chi2 y p-aprox."""
    import math
    obs = np.array([[w, t - w] for w, t in zip(wins, total)], dtype=float)
    if obs.shape[0] < 2 or obs.sum() == 0:
        return np.nan, np.nan
    row = obs.sum(axis=1, keepdims=True)
    col = obs.sum(axis=0, keepdims=True)
    exp = row @ col / obs.sum()
    if (exp <= 0).any():
        return np.nan, np.nan
    chi = float(((obs - exp) ** 2 / exp).sum())
    # p-value via chi2 survival con 2 gdl (aprox)
    p = math.exp(-chi / 2) * (1 + chi / 2)
    return chi, p


def main() -> int:
    m15 = _load_m15()
    events = pd.read_parquet(EVENTS_PATH)
    events["brake_time"] = pd.to_datetime(events["brake_time"], utc=True)
    events = events.sort_values("brake_time")

    comp_cols = ["agotamiento", "compression", "overlap", "break_fail", "rechazo", "reduc_cont", "cambio_reg"]
    rows = []
    for _, row in events.iterrows():
        bt = row["brake_time"]
        prev = m15.loc[:bt]
        if len(prev) < WINDOW + 1:
            continue
        win = prev.iloc[-(WINDOW + 1):-1]
        comp = _componentes(win["open"].values, win["high"].values, win["low"].values, win["close"].values)
        if not comp:
            continue
        comp.update({"win": int(row["win"]), "split": str(row.get("split", "unknown"))})
        rows.append(comp)
    df = pd.DataFrame(rows)
    if df.empty:
        print("[PHASEA-R6] sin senales"); return 1

    report = {"n_signals": int(len(df)), "window": WINDOW,
              "matriz_por_split": {}, "regla_oro": "sin volumen, Edificio caja negra"}
    for sp in ["test", "train"]:
        sub = df[df["split"] == sp] if sp in df["split"].values else df
        if len(sub) < 30:
            continue
        for col in comp_cols:
            sub = sub.assign(**{f"n_{col}": sub[col].rank(pct=True)})
        ncols = [f"n_{col}" for col in comp_cols]
        sub = sub.assign(phase_a_score=sub[ncols].sum(axis=1))
        sub = sub.assign(tercil=pd.cut(sub["phase_a_score"].rank(method="first"), bins=3, labels=["baja", "media", "alta"]))
        mat = {}
        wins, tot = [], []
        for t in ["baja", "media", "alta"]:
            g = sub[sub["tercil"] == t]
            w = int(g["win"].sum()); tt = int(len(g))
            mat[t] = {"n": tt, "win": w, "win_rate": float(w / tt) if tt else np.nan}
            wins.append(w); tot.append(tt)
        chi, p = _chi2_from_rates(wins, tot)
        report["matriz_por_split"][sp] = {"matriz": mat, "chi2": chi, "p_value_aprox": p,
                                          "pendiente_winrate": [mat[t]["win_rate"] for t in ["baja", "media", "alta"]]}

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    with open(REPORT_DIR / "summary.md", "w", encoding="utf-8") as f:
        f.write("# PHASEA-R6 — Contexto (Fase A) x Edificio (R6)\n\n")
        f.write(f"- Senales: {len(df)} (ventana M15 previa {WINDOW}). Score solo OHLC+tiempo, normalizado por split.\n")
        for sp, b in report["matriz_por_split"].items():
            f.write(f"\n## {sp.upper()}\n")
            for t in ["baja", "media", "alta"]:
                m = b["matriz"][t]
                f.write(f"- Fase A {t}: n={m['n']} win={m['win']} win_rate={m['win_rate']:.3f}\n")
            f.write(f"- chi2={b['chi2']:.3f} p_aprox={b['p_value_aprox']:.3f}\n")
            f.write(f"- pendiente winrate: {b['pendiente_winrate']}\n")
        f.write("\nHipotesis: si winrate crece baja<media<alta en TEST/OOS, el contexto FILTRA el timing.\n")
        f.write("Regla de oro: volumen NUNCA requisito. Edificio caja negra intacta. Charter: Sí\n")
    print(f"[PHASEA-R6] reporte: {REPORT_DIR} | senales={len(df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
