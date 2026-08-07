"""PHASEA-R7 — Edificio como binaria: direccion + expiracion (R7).

Feature: edificio_wyckoff_phasea (R7). Caja negra intacta. OFFLINE. Sin volumen.
Sin filtro Wyckoff (R6 mostro filtro marginal y no robusto OOS).

Objetivo: con el Edificio tal cual, ¿cual es el win rate / EV real como binaria sobre
la cohorte historica, para distintos horizontes de expiracion H (M15)?

- Evento trae direccion (CALL/PUT) y brake_time.
- Solo EURUSD tiene datos M15 en disco (brecha de datos: no se cambia de instrumento).
- Se recalcula el win DESDE EL PRECIO con horizonte H fijo (no se reusa win del Edificio)
  para aislar el efecto del horizonte de expiracion.
- Compara con el win rate original del Edificio (campo win).
- EV asumiendo payout 80% (puede parametrizarse offline; NO es dinero real).

Limites honestos:
- Cobertura solo EURUSD (286 eventos; 205 train / 81 test).
- close(0)/close(H) usando la marca temporal mas cercana (intrabar); sin look-ahead
  porque brake_time es anterior a la expiracion.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

ASSET = "EURUSD"
M15_PATHS = [
    Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\cohorte_real_eurusd\EURUSD_M15.parquet"),
    Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\smc_borrowed\EURUSD_M15.parquet"),
]
EVENTS_PATH = Path(r"C:\Users\v_jac\Desktop\QUOTEX\src\strategy_lab\results\edificio_events.parquet")
REPORT_DIR = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\ew_reports\PHASEA-R7")
PAYOUT = 0.80
HORIZONTES = [1, 2, 3, 4, 5]  # en velas M15


def _load_m15() -> pd.DataFrame:
    for p in M15_PATHS:
        if p.exists():
            df = pd.read_parquet(p)
            df["ts"] = pd.to_datetime(df["time"])
            return df.sort_values("ts").set_index("ts")
    raise FileNotFoundError("No hay EURUSD_M15 en disco.")


def main() -> int:
    m15 = _load_m15()
    close_idx = m15["close"]
    events = pd.read_parquet(EVENTS_PATH)
    events["brake_time"] = pd.to_datetime(events["brake_time"], utc=True)
    ev = events[(events["asset"] == ASSET)].sort_values("brake_time").copy()
    if ev.empty:
        print(f"[PHASEA-R7] sin eventos {ASSET}")
        return 1

    recs = []
    for _, row in ev.iterrows():
        bt = row["brake_time"]
        try:
            close_brake = float(close_idx.asof(bt))
        except Exception:
            continue
        if not np.isfinite(close_brake):
            continue
        direction = str(row["direction"]).upper()
        rec = {"win_orig": int(row["win"]), "split": str(row["split"]),
               "direction": direction}
        for h in HORIZONTES:
            exp_t = bt + pd.Timedelta(minutes=15 * h)
            try:
                close_exp = float(close_idx.asof(exp_t))
            except Exception:
                close_exp = np.nan
            if not np.isfinite(close_exp):
                rec[f"win_h{h}"] = np.nan
                continue
            if direction == "CALL":
                rec[f"win_h{h}"] = 1 if close_exp > close_brake else 0
            elif direction == "PUT":
                rec[f"win_h{h}"] = 1 if close_exp < close_brake else 0
            else:
                rec[f"win_h{h}"] = np.nan
        recs.append(rec)
    df = pd.DataFrame(recs)
    df = df.dropna(subset=[f"win_h{h}" for h in HORIZONTES], how="all")
    if df.empty:
        print("[PHASEA-R7] sin coincidencias de precio")
        return 1

    report = {"asset": ASSET, "n_eval": int(len(df)), "payout_asumido": PAYOUT,
              "horizontes_M15": HORIZONTES,
              "nota_cobertura": "Solo EURUSD tiene M15 en disco (brecha de datos, no cambio de instrumento)",
              "regla_oro": "offline, caja negra intacta, sin volumen, sin filtro Wyckoff",
              "por_split": {}, "por_direccion": {}, "origen_win": {"train": {}, "test": {}}}

    for sp in ["train", "test"]:
        sub = df[df["split"] == sp] if sp in df["split"].values else df
        if len(sub) < 10:
            continue
        win_orig = float(sub["win_orig"].mean())
        hor = {}
        for h in HORIZONTES:
            col = f"win_h{h}"
            wr = float(sub[col].mean())
            evv = wr * PAYOUT - (1 - wr)
            hor[str(h)] = {"n": int(sub[col].notna().sum()), "win_rate": wr, "ev": evv}
        report["por_split"][sp] = {"win_edificio_original": {"win_rate": win_orig},
                                   "horizontes": hor}

    for d in ["CALL", "PUT"]:
        sub = df[df["direction"] == d]
        if len(sub) < 10:
            continue
        hor = {}
        for h in HORIZONTES:
            col = f"win_h{h}"
            wr = float(sub[col].mean())
            evv = wr * PAYOUT - (1 - wr)
            hor[str(h)] = {"n": int(sub[col].notna().sum()), "win_rate": wr, "ev": evv}
        report["por_direccion"][d] = {"n": int(len(sub)), "horizontes": hor}

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    with open(REPORT_DIR / "summary.md", "w", encoding="utf-8") as f:
        f.write(f"# PHASEA-R7 — Edificio como binaria ({ASSET})\n\n")
        f.write(f"- Evaluadas: {len(df)} senales (solo EURUSD; brecha de datos para otros assets).\n")
        f.write(f"- Payout asumido OFFLINE: {PAYOUT:.0%} (NO dinero real).\n")
        f.write(f"- Win recalculado desde precio con horizonte H fijo (M15). Sin filtro Wyckoff.\n\n")
        for sp, b in report["por_split"].items():
            f.write(f"## {sp.upper()} (n evaluadas={sum(b['horizontes'][str(h)]['n'] for h in HORIZONTES)})\n")
            f.write(f"- Win rate ORIGINAL del Edificio: {b['win_edificio_original']['win_rate']:.3f}\n")
            for h in HORIZONTES:
                hh = b["horizontes"][str(h)]
                f.write(f"  - H={h} M15: win_rate={hh['win_rate']:.3f} EV={hh['ev']:+.3f} (n={hh['n']})\n")
        f.write(f"\nRegla de oro: offline, Edificio caja negra intacta, sin volumen, sin filtro Wyckoff.\n")
    print(f"[PHASEA-R7] reporte: {REPORT_DIR} | evaluadas={len(df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
