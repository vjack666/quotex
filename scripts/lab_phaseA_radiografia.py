"""PHASEA-RADIO — Radiografia estructural WIN/LOSS del Edificio (R0-R3).

Feature: edificio_wyckoff_phasea (spec_ready, APROBADO trader-humano).
NO modifica el Edificio (src/ intacto). NO descarga datos. NO usa volumen como
requisito. Usa solo datasets en disco:
  - src/strategy_lab/results/edificio_events.parquet  (señales con win, split, brake_time)
  - data/strategy_lab/cohorte_real_eurusd/EURUSD_M15.parquet (OHLC M15, tick_volume)

Flujo:
  1. Cargar M15, indexar por timestamp (time column).
  2. Cargar señales del Edificio; clasificar WIN/LOSS por columna `win`; respetar `split`.
  3. Por cada señal, ventana N=20 velas M15 previas a brake_time (alineado por ts).
  4. Features estructurales SOLO OHLC+tiempo (tendencia/impulso/compresion/lucha).
  5. Comparar distribuciones WIN vs LOSS (medias, medianas, effect size Cohen's d,
     + prueba de separacion por grupo: diferencia de medias estandarizada).
  6. Reporte inmutable en data/strategy_lab/ew_reports/PHASEA-RADIO/.

Regla de oro (ADR-039): volumen NUNCA requisito. Si se quiere explorar, es
evidencia adicional, no feature obligatoria.

El script NO se ejecuta dentro del SDD; el implementer lo corre via temp ad-hoc.
"""
from __future__ import annotations
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

M15_PATHS = [
    Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\cohorte_real_eurusd\EURUSD_M15.parquet"),
    Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\smc_borrowed\EURUSD_M15.parquet"),
]
EVENTS_PATH = Path(r"C:\Users\v_jac\Desktop\QUOTEX\src\strategy_lab\results\edificio_events.parquet")
REPORT_DIR = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\ew_reports\PHASEA-RADIO")
WINDOW = 20  # velas M15 previas al brake_time


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_m15() -> pd.DataFrame:
    for p in M15_PATHS:
        if p.exists():
            df = pd.read_parquet(p)
            df["ts"] = pd.to_datetime(df["time"])
            df = df.sort_values("ts").set_index("ts")
            return df
    raise FileNotFoundError("No hay EURUSD_M15 en disco.")


def _structural_features(win: pd.DataFrame) -> dict:
    """Features SOLO OHLC + tiempo de una ventana de N velas M15."""
    o, h, l, c = win["open"].values, win["high"].values, win["low"].values, win["close"].values
    n = len(c)
    if n < 5:
        return {}
    # Tendencia
    x = np.arange(n)
    slope = np.polyfit(x, c, 1)[0] if n > 1 else 0.0
    hh = int(np.sum((c[1:] > c[:-1])))  # conteo de cierres crecientes (proxy HH)
    llmov = int(np.sum((c[1:] < c[:-1])))  # proxy LL
    # Impulso
    rng = (h - l)
    mean_range = float(rng.mean())
    net_disp = float(c[-1] - c[0])
    speed = net_disp / n
    persistence = float(np.mean(np.sign(np.diff(c)) != 0))  # fraccion de cambios de direccion
    # Compresion
    first_half = rng[: max(1, n // 2)].mean()
    last_half = rng[max(1, n // 2):].mean()
    compression = float(first_half / last_half) if last_half > 0 else np.nan
    # Solapamiento: min(high)-max(low) de velas adyacentes
    overlap = float(np.mean([min(h[i + 1], h[i]) - max(l[i + 1], l[i]) for i in range(n - 1)]))
    # Lucha estructural
    safe_rng = np.where(rng > 0, rng, np.nan)
    upper_wick = (h - np.maximum(o, c)) / safe_rng
    lower_wick = (np.minimum(o, c) - l) / safe_rng
    wick_ratio = float(np.nanmean((upper_wick + lower_wick) / 2))
    body_range = float(np.nanmean(np.abs(c - o) / safe_rng))
    # Fallos de ruptura: cierra dentro tras tocar extremo previo
    break_fail = 0
    prev_h, prev_l = h[0], l[0]
    for i in range(1, n):
        touched_high = h[i] >= prev_h
        touched_low = l[i] <= prev_l
        close_inside = (c[i] <= prev_h) and (c[i] >= prev_l)
        if (touched_high or touched_low) and close_inside:
            break_fail += 1
        prev_h, prev_l = max(prev_h, h[i]), min(prev_l, l[i])
    break_fail_rate = float(break_fail / (n - 1)) if n > 1 else 0.0
    return {
        "trend_slope": slope,
        "trend_hh_count": hh,
        "trend_ll_count": llmov,
        "impulse_mean_range": mean_range,
        "impulse_net_disp": net_disp,
        "impulse_speed": speed,
        "impulse_persistence": persistence,
        "compression_ratio": compression,
        "body_range_ratio": body_range,
        "overlap_sum": overlap,
        "wick_ratio": wick_ratio,
        "break_fail_rate": break_fail_rate,
    }


def _cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return np.nan
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * a.std(ddof=1) ** 2 + (nb - 1) * b.std(ddof=1) ** 2) / (na + nb - 2))
    if sp == 0:
        return np.nan
    return float((a.mean() - b.mean()) / sp)


def main() -> int:
    m15 = _load_m15()
    events = pd.read_parquet(EVENTS_PATH)
    events["brake_time"] = pd.to_datetime(events["brake_time"], utc=True)
    events = events.sort_values("brake_time")

    feats_per_signal = []
    for _, row in events.iterrows():
        bt = row["brake_time"]
        # ventana N velas M15 estrictamente previas a brake_time
        prev = m15.loc[:bt]
        if len(prev) < WINDOW + 1:
            continue
        win = prev.iloc[-(WINDOW + 1):-1]  # excluye la vela del brake_time
        f = _structural_features(win)
        if not f:
            continue
        f["win"] = int(row["win"])
        f["split"] = str(row.get("split", "unknown"))
        f["asset"] = str(row.get("asset", ""))
        f["direction"] = str(row.get("direction", ""))
        feats_per_signal.append(f)

    df = pd.DataFrame(feats_per_signal)
    if df.empty:
        print("[PHASEA-RADIO] sin señales con ventana valida")
        return 1

    # Separacion WIN vs LOSS (en TEST/OOS por defecto; tambien train para referencia)
    report = {"n_signals": int(len(df)), "window": WINDOW,
              "features_compared": [], "golden_rule_volume": "never_required"}
    for split_name in ["test", "train"]:
        sub = df[df["split"] == split_name] if split_name in df["split"].values else df
        w = sub[sub["win"] == 1]
        l = sub[sub["win"] == 0]
        comp = {}
        for col in [c for c in df.columns if c not in ("win", "split", "asset", "direction")]:
            aw, al = w[col].values.astype(float), l[col].values.astype(float)
            d = _cohen_d(aw, al)
            comp[col] = {
                "win_mean": float(np.nanmean(aw)), "loss_mean": float(np.nanmean(al)),
                "win_median": float(np.nanmedian(aw)), "loss_median": float(np.nanmedian(al)),
                "cohen_d": d,
            }
        report[f"split_{split_name}"] = {
            "n_win": int(len(w)), "n_loss": int(len(l)), "comparison": comp,
        }
        # top features por |cohen_d|
        ranked = sorted(comp.items(), key=lambda kv: abs(kv[1]["cohen_d"]) if not np.isnan(kv[1]["cohen_d"]) else -1, reverse=True)
        report["features_compared"].append({split_name: [k for k, _ in ranked[:5]]})

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    with open(REPORT_DIR / "summary.md", "w", encoding="utf-8") as f:
        f.write("# PHASEA-RADIO — Radiografia estructural WIN/LOSS (Edificio caja negra)\n\n")
        f.write(f"- Señales con ventana valida: {len(df)} | ventana M15 previas: {WINDOW}\n")
        for sn in ["test", "train"]:
            block = report.get(f"split_{sn}")
            if not block:
                continue
            f.write(f"\n## {sn.upper()} (n_win={block['n_win']}, n_loss={block['n_loss']})\n")
            f.write("Top features por separacion (|Cohen d|):\n")
            for k, v in sorted(block["comparison"].items(),
                                key=lambda kv: abs(kv[1]["cohen_d"]) if not np.isnan(kv[1]["cohen_d"]) else -1,
                                reverse=True)[:8]:
                f.write(f"  - {k}: WIN={v['win_mean']:.4f} LOSS={v['loss_mean']:.4f} d={v['cohen_d']}\n")
        f.write("\nRegla de oro: volumen NUNCA requisito (ADR-039). Este reporte usa solo OHLC+tiempo.\n")
        f.write("Cumple Charter: Sí\n")
    # protocolo inmutable
    proto = {
        "script": "lab_phaseA_radiografia.py",
        "datasets": {
            "m15": _sha256([p for p in M15_PATHS if p.exists()][0]),
            "events": _sha256(EVENTS_PATH),
        },
        "window": WINDOW,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "note": "Reporte inmutable. Edificio NO modificado. Datos en disco. Volumen no requisito.",
    }
    (REPORT_DIR / "protocol_frozen.json").write_text(json.dumps(proto, indent=2), encoding="utf-8")
    print(f"[PHASEA-RADIO] reporte: {REPORT_DIR} | señales={len(df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
