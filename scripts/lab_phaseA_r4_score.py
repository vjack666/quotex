"""PHASEA-R4 — Mapeo estructural explicito a Fase A de Wyckoff (R4).

Feature: edificio_wyckoff_phasea (R4, sobre R0-R3). NO modifica el Edificio.
Produce 3 entregables:
  1. Mapa evento Wyckoff -> evento OHLC puro (wyckoff_map.json).
  2. Phase_A_Score por senal (solo precio: agotamiento+compresion+solapamiento+
     fallos_ruptura+rechazo_extremos+reduccion_continuacion+cambio_regimen).
  3. Comparacion WIN vs LOSS del Edificio con ese score (effect size + razón).

Regla de oro (ADR-039): volumen NUNCA requisito. Solo OHLC+tiempo.
Normalizacion POR SPLIT (train/test) para no contaminar OOS.
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
REPORT_DIR = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\ew_reports\PHASEA-R4")
WINDOW = 20


def _load_m15() -> pd.DataFrame:
    for p in M15_PATHS:
        if p.exists():
            df = pd.read_parquet(p)
            df["ts"] = pd.to_datetime(df["time"])
            return df.sort_values("ts").set_index("ts")
    raise FileNotFoundError("No hay EURUSD_M15 en disco.")


def _componentes(win: pd.DataFrame) -> dict:
    o, h, l, c = win["open"].values, win["high"].values, win["low"].values, win["close"].values
    n = len(c)
    if n < 10:
        return {}
    half = max(5, n // 2)
    x = np.arange(n)
    slope_full = np.polyfit(x, c, 1)[0] if n > 1 else 0.0
    slope_first = np.polyfit(x[:half], c[:half], 1)[0]
    slope_second = np.polyfit(x[half:], c[half:], 1)[0]
    rng = (h - l)
    # Agotamiento: impulso inicial fuerte que decae
    net_first = abs(c[half - 1] - c[0])
    net_second = abs(c[-1] - c[half - 1])
    agotamiento = net_first - net_second  # positivo => decaimiento
    # Compresion: rango se achica
    first_rng = rng[:half].mean()
    last_rng = rng[half:].mean()
    compression = first_rng / last_rng if last_rng > 0 else np.nan  # >1 => se achica
    # Solapamiento entre velas adyacentes
    overlap = float(np.mean([min(h[i + 1], h[i]) - max(l[i + 1], l[i]) for i in range(n - 1)]))
    # Fallos de ruptura
    bf, ph, pl = 0, h[0], l[0]
    for i in range(1, n):
        touch = (h[i] >= ph) or (l[i] <= pl)
        inside = (c[i] <= ph) and (c[i] >= pl)
        if touch and inside:
            bf += 1
        ph, pl = max(ph, h[i]), min(pl, l[i])
    break_fail = bf / (n - 1) if n > 1 else 0.0
    # Rechazo de extremos (mechas)
    safe = np.where(rng > 0, rng, np.nan)
    wick = float(np.nanmean(((h - np.maximum(o, c)) + (np.minimum(o, c) - l)) / safe))
    # Reduccion de continuacion (segunda mitad cambia de direccion seguido)
    chg = np.sign(np.diff(c))
    persist_first = float(np.mean(chg[: half - 1] != 0)) if half > 1 else 0.0
    persist_second = float(np.mean(chg[half - 1:] != 0)) if n - half > 1 else 0.0
    reduc_cont = persist_first - persist_second  # positivo => mas cambios al final
    # Cambio de regimen (pendiente primera vs segunda)
    cambio = abs(slope_first - slope_second)
    return {
        "agotamiento": float(agotamiento),
        "compression": float(compression),
        "overlap": overlap,
        "break_fail": float(break_fail),
        "rechazo": wick,
        "reduc_cont": float(reduc_cont),
        "cambio_reg": float(cambio),
        "_slope_full": float(slope_full),
    }


def _cohen_d(a, b):
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return np.nan
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * a.std(ddof=1) ** 2 + (nb - 1) * b.std(ddof=1) ** 2) / (na + nb - 2))
    return float((a.mean() - b.mean()) / sp) if sp else np.nan


def main() -> int:
    m15 = _load_m15()
    events = pd.read_parquet(EVENTS_PATH)
    events["brake_time"] = pd.to_datetime(events["brake_time"], utc=True)
    events = events.sort_values("brake_time")

    rows = []
    for _, row in events.iterrows():
        bt = row["brake_time"]
        prev = m15.loc[:bt]
        if len(prev) < WINDOW + 1:
            continue
        win = prev.iloc[-(WINDOW + 1):-1]
        comp = _componentes(win)
        if not comp:
            continue
        comp.update({"win": int(row["win"]), "split": str(row.get("split", "unknown")),
                     "asset": str(row.get("asset", "")), "direction": str(row.get("direction", ""))})
        rows.append(comp)
    df = pd.DataFrame(rows)
    if df.empty:
        print("[PHASEA-R4] sin senales")
        return 1

    comp_cols = ["agotamiento", "compression", "overlap", "break_fail", "rechazo", "reduc_cont", "cambio_reg"]
    # Normalizar POR SPLIT con rank percentil (robusto a outliers, sin look-ahead)
    df["phase_a_score"] = 0.0
    report = {"n_signals": int(len(df)), "window": WINDOW,
              "mapa_wyckoff": _mapa(), "splits": {}}
    for sp in ["test", "train"]:
        sub = df[df["split"] == sp] if sp in df["split"].values else df
        for col in comp_cols:
            df.loc[sub.index, f"n_{col}"] = sub[col].rank(pct=True)
        ncols = [f"n_{c}" for c in comp_cols]
        score_sub = df.loc[sub.index, ncols].sum(axis=1)
        df.loc[sub.index, "phase_a_score"] = score_sub
        w = df.loc[sub.index][df.loc[sub.index]["win"] == 1]
        l = df.loc[sub.index][df.loc[sub.index]["win"] == 0]
        aw, al = w["phase_a_score"].values, l["phase_a_score"].values
        thr = 4.0  # score >4/7 ~ mitad alta
        pct_w = float((w["phase_a_score"] > thr).mean()) if len(w) else np.nan
        pct_l = float((l["phase_a_score"] > thr).mean()) if len(l) else np.nan
        comp_d = {c: _cohen_d(df.loc[w.index, f"n_{c}"].values, df.loc[l.index, f"n_{c}"].values) for c in comp_cols}
        report["splits"][sp] = {
            "n_win": int(len(w)), "n_loss": int(len(l)),
            "score_win_mean": float(np.nanmean(aw)), "score_loss_mean": float(np.nanmean(al)),
            "score_cohen_d": _cohen_d(aw, al),
            "pct_win_above_thr": pct_w, "pct_loss_above_thr": pct_l,
            "component_cohen_d": comp_d,
        }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (REPORT_DIR / "wyckoff_map.json").write_text(json.dumps(_mapa(), indent=2, ensure_ascii=False), encoding="utf-8")
    with open(REPORT_DIR / "summary.md", "w", encoding="utf-8") as f:
        f.write("# PHASEA-R4 — Mapeo estructural a Fase A de Wyckoff (R4)\n\n")
        f.write(f"- Senales: {len(df)} | ventana M15 previas: {WINDOW} | score 0..7 (rank/split)\n")
        for sp, b in report["splits"].items():
            f.write(f"\n## {sp.upper()} (WIN={b['n_win']}, LOSS={b['n_loss']})\n")
            f.write(f"- Phase_A_Score: WIN={b['score_win_mean']:.3f} LOSS={b['score_loss_mean']:.3f} d={b['score_cohen_d']:.3f}\n")
            f.write(f"- % score>4: WIN={b['pct_win_above_thr']:.2%} LOSS={b['pct_loss_above_thr']:.2%}\n")
            f.write("- Separacion por componente (|Cohen d|):\n")
            for c, d in sorted(b["component_cohen_d"].items(), key=lambda kv: abs(kv[1]) if not np.isnan(kv[1]) else -1, reverse=True):
                f.write(f"    - {c}: {d}\n")
        f.write("\n## Mapa evento Wyckoff -> OHLC puro\n")
        for k, v in _mapa().items():
            f.write(f"- **{k}** ({v['nombre']}): {v['ohlc']}\n")
        f.write("\nRegla de oro: volumen NUNCA requisito. Edificio caja negra. Charter: Sí\n")
    print(f"[PHASEA-R4] reporte: {REPORT_DIR} | senales={len(df)}")
    return 0


def _mapa() -> dict:
    return {
        "PS": {"nombre": "Agotamiento inicial del impulso", "ohlc": "movimiento fuerte + rango amplio + posterior perdida de continuacion direccional"},
        "SC": {"nombre": "Climax de venta/compra", "ohlc": "extremo + rango anormal + rechazo (mecha) + incapacidad de continuar"},
        "AR": {"nombre": "Rally automatico", "ohlc": "expansion en direccion contraria + ruptura del comportamiento previo"},
        "ST": {"nombre": "Test / retorno al area", "ohlc": "retorno al area + menor capacidad de continuar + nuevo rechazo"},
        "Spring": {"nombre": "Falsa ruptura bajista", "ohlc": "ruptura de minimo previo + fallo de ruptura (break_fail) + cierre adentro"},
        "UT": {"nombre": "Falsa ruptura alcista", "ohlc": "ruptura de maximo previo + fallo de ruptura + cierre adentro"},
        "FaseA_score": {"nombre": "Transicion tendencia->estructura", "ohlc": "agotamiento + compresion + solapamiento + fallos_ruptura + rechazo + reduc_continuacion + cambio_regimen"},
    }


if __name__ == "__main__":
    raise SystemExit(main())
