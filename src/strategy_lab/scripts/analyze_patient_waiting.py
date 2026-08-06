"""Analisis de hipotesis PACIENT WAITING para el Edificio.

Explora, para cada evento de cruce K/D registrado, cuantas velas adicionales de espera
son necesarias para alcanzar una separacion "real", y mide el trade-off tiempo vs winrate.

Restricciones:
- Solo numpy/pandas.
- Sin modificar src/edificio_contratacion.py ni src/edificio_executor.py.
- Sin look-ahead en features causales; este script es analisis offline de lab.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_SRC = Path(r"C:\Users\v_jac\Desktop\QUOTEX\src")
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from strategy_lab.compute_features import (
    PIP_FACTOR,
    SMC_ROOT,
    build_feature_frame,
    load_htf,
    load_m15,
)
from strategy_lab.scripts.backtest_edificio import DEFAULT_PAIRS, R

# Parametros de analisis
MAX_WAIT = 20  # velas max de espera post-cruce original
SEPARATION_THRESHOLDS = [2.0, 3.0, 4.0, 5.0, 6.0]
MAINTAIN_WINDOW = 5


def _find_entry_after_threshold(
    k: np.ndarray,
    d: np.ndarray,
    kd_dist: np.ndarray,
    hammer: np.ndarray,
    inv_hammer: np.ndarray,
    close: np.ndarray,
    direction: str,
    start_idx: int,
    threshold: float,
    maintain_window: int,
    n: int,
    pip: float,
) -> tuple[bool, int, int]:
    """Desde start_idx, buscar primera vela con separacion >= threshold y martillo confirmatorio.

    Devuelve (win, confirm_idx, entry_idx) o (False, -1, -1) si no se cumple.
    """
    if start_idx + 1 >= n:
        return False, -1, -1

    for jj in range(start_idx, min(start_idx + maintain_window, n - 1)):
        if not (np.isfinite(kd_dist[jj]) and np.isfinite(k[jj]) and np.isfinite(d[jj])):
            continue
        if kd_dist[jj] < threshold:
            continue
        # separacion ok, buscar martillo en ventana posterior
        for cc in range(jj + 1, min(jj + 1 + maintain_window, n - 1)):
            if not (np.isfinite(k[cc]) and np.isfinite(d[cc]) and np.isfinite(k[cc - 1]) and np.isfinite(d[cc - 1])):
                continue
            if kd_dist[cc] < threshold:
                # dejo de cumplir mantenimiento
                break
            valid = inv_hammer[cc] if direction == "CALL" else hammer[cc]
            if bool(valid):
                entry_idx = cc + 1
                if entry_idx + R >= n:
                    return False, cc, entry_idx
                seg = slice(entry_idx, entry_idx + R)
                sub_c = close[seg]
                win = False
                if direction == "CALL" and np.any(sub_c >= close[cc] + 5 * pip):
                    win = True
                elif direction == "PUT" and np.any(sub_c <= close[cc] - 5 * pip):
                    win = True
                return win, cc, entry_idx
    return False, -1, -1


def run_patient_waiting_analysis(
    pairs: list[str] = DEFAULT_PAIRS,
    max_wait: int = MAX_WAIT,
    thresholds: list[float] = SEPARATION_THRESHOLDS,
) -> pd.DataFrame:
    base_events = pd.read_csv(Path("src/strategy_lab/results/edificio_events.csv"))
    if base_events.empty:
        return pd.DataFrame()

    # Build feature frames per asset once
    frames: dict[str, pd.DataFrame] = {}
    for asset in pairs:
        try:
            frames[asset] = build_feature_frame(load_m15(asset, SMC_ROOT), load_htf(asset, SMC_ROOT))
        except Exception as exc:
            print(f"[warn] skip {asset}: {exc}")

    rows = []
    for _, ev in base_events.iterrows():
        asset = ev["asset"]
        if asset not in frames:
            continue
        df = frames[asset]
        brake_idx = int(ev["brake_idx"])
        cross_idx = int(ev["cross_idx"])
        direction = str(ev["direction"])
        original_win = int(ev["win"])
        sep_at_cross = float(ev["cross_separation"])

        c_close = np.asarray(df["close"].values, dtype=float)
        h = np.asarray(df["high"].values, dtype=float)
        l = np.asarray(df["low"].values, dtype=float)
        k = np.asarray(df["k"].values, dtype=float)
        d = np.asarray(df["d"].values, dtype=float)
        kd_dist = np.asarray(df["kd_dist"].values, dtype=float)
        hammer = np.asarray(df["hammer_15m"].values, dtype=bool)
        inv_hammer = np.asarray(df["hammer_inv_15m"].values, dtype=bool)

        pip = float(PIP_FACTOR.get(asset, 1e-4))
        n = len(c_close)

        # Separation trajectory from original cross forward
        sep_traj = []
        for w in range(0, max_wait + 1):
            idx = cross_idx + w
            if idx >= n or not np.isfinite(kd_dist[idx]):
                sep_traj.append(np.nan)
            else:
                sep_traj.append(float(kd_dist[idx]))
        sep_traj = np.array(sep_traj)

        # Max separation reached in full wait window
        max_sep_reached = float(np.nanmax(sep_traj[1:])) if len(sep_traj) > 1 else np.nan

        # Original outcome if no waiting
        original_entry_idx = int(ev["confirm_idx"]) + 1

        row = {
            "asset": asset,
            "brake_idx": brake_idx,
            "cross_idx": cross_idx,
            "direction": direction,
            "original_win": original_win,
            "original_separation": sep_at_cross,
            "max_separation_reachable": max_sep_reached,
        }

        # For each threshold, compute wait metrics
        for thr in thresholds:
            col_wait = f"wait_{int(thr)}"
            col_win = f"win_wait_{int(thr)}"
            col_reached = f"reached_{int(thr)}"

            first_idx = np.nan
            reached = False
            wait_win = False
            wait_confirm = -1
            wait_entry = -1

            if sep_at_cross >= thr:
                # Already enough separation; "wait 0"
                first_idx = 0
                reached = True
                win, cc, entry_idx = _find_entry_after_threshold(
                    k, d, kd_dist, hammer, inv_hammer, c_close, direction, cross_idx, thr, MAINTAIN_WINDOW, n, pip
                )
                wait_win = win
                wait_confirm = cc
                wait_entry = entry_idx
                actionable = bool(wait_confirm != -1)
                wait_win_val = float(wait_win) if actionable else np.nan
            else:
                for w in range(1, max_wait + 1):
                    idx = cross_idx + w
                    if idx >= n or not np.isfinite(kd_dist[idx]):
                        continue
                    if kd_dist[idx] >= thr:
                        first_idx = w
                        reached = True
                        win, cc, entry_idx = _find_entry_after_threshold(
                            k, d, kd_dist, hammer, inv_hammer, c_close, direction, idx, thr, MAINTAIN_WINDOW, n, pip
                        )
                        wait_win = win
                        wait_confirm = cc
                        wait_entry = entry_idx
                        break

            row[f"reached_{int(thr)}"] = int(reached)
            row[f"wait_cycles_{int(thr)}"] = int(first_idx) if reached else np.nan
            row[f"win_wait_{int(thr)}"] = int(wait_win) if reached else np.nan
            row[f"confirm_idx_wait_{int(thr)}"] = wait_confirm
            row[f"entry_idx_wait_{int(thr)}"] = wait_entry
            row[f"actionable_{int(thr)}"] = int(reached and wait_confirm != -1)
            row[f"winrate_actionable_{int(thr)}"] = float(wait_win) if (reached and wait_confirm != -1) else np.nan

        rows.append(row)

    out = pd.DataFrame(rows)
    return out


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    thr_cols = [c for c in df.columns if c.startswith("win_wait_")]
    summary_rows = []
    for thr_str in ["2", "3", "4", "5", "6"]:
        reached_col = f"reached_{thr_str}"
        wait_col = f"wait_cycles_{thr_str}"
        win_col = f"win_wait_{thr_str}"
        mask_reached = df[reached_col] == 1
        total_reached = int(mask_reached.sum())
        summary_rows.append({
            "threshold": float(thr_str),
            "events_reached": total_reached,
            "events_not_reached": int(len(df) - total_reached),
            "pct_reached": total_reached / len(df) if len(df) else 0.0,
            "winrate_if_waited": float(df.loc[mask_reached, win_col].mean()) if total_reached else np.nan,
            "avg_wait_cycles": float(df.loc[mask_reached, wait_col].mean()) if total_reached else np.nan,
            "median_wait_cycles": float(df.loc[mask_reached, wait_col].median()) if total_reached else np.nan,
        })
    return pd.DataFrame(summary_rows)


def tradeoff_by_separation_bucket(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["sep_bucket"] = pd.cut(
        df["original_separation"],
        bins=[-np.inf, 2, 3, 4, 5, np.inf],
        labels=["<=2", "2-3", "3-4", "4-5", ">5"],
    )
    rows = []
    for bucket, grp in df.groupby("sep_bucket", observed=True):
        if grp.empty:
            continue
        row = {
            "sep_bucket": str(bucket),
            "count": len(grp),
            "original_winrate": float(grp["original_win"].mean()),
        }
        for thr in ["2", "3", "4", "5", "6"]:
            mask = grp[f"reached_{thr}"] == 1
            row[f"reach_{thr}"] = int(mask.sum())
            row[f"winrate_wait_{thr}"] = float(grp.loc[mask, f"win_wait_{thr}"].mean()) if mask.any() else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out_dir = Path("src/strategy_lab/results")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[1/3] Ejecutando analisis de patient waiting...")
    analysis = run_patient_waiting_analysis()
    csv_path = out_dir / "patient_waiting_analysis.csv"
    analysis.to_csv(csv_path, index=False)
    print(f"CSV guardado en {csv_path}")

    print("[2/3] Generando resumenes...")
    summary = summarize(analysis)
    summary_csv = out_dir / "patient_waiting_summary.csv"
    summary.to_csv(summary_csv, index=False)

    tradeoff = tradeoff_by_separation_bucket(analysis)
    tradeoff_csv = out_dir / "patient_waiting_tradeoff.csv"
    tradeoff.to_csv(tradeoff_csv, index=False)

    print("[3/3] Generando reporte markdown...")
    low_sep = analysis[analysis["original_separation"] <= 3]
    high_sep = analysis[analysis["original_separation"] > 5]

    lines = [
        "# Pacient Waiting — Reporte de Analisis Edificio",
        "",
        "## Hipotesis",
        "En lugar de descartar cruces K/D con separacion baja, esperar N velas adicionales",
        "para ver si K/D desarrolla separacion real. Si alcanza umbral X, entrada con mejor calidad.",
        "",
        "## Dataset base",
        f"- Eventos analizados: {len(analysis)}",
        f"- Separacion <= 3: {len(low_sep)} ({len(low_sep)/len(analysis)*100:.1f}%)",
        f"- Separacion > 5: {len(high_sep)} ({len(high_sep)/len(analysis)*100:.1f}%)",
        "",
        "## Resumen por umbral",
    ]
    lines.append("")
    lines.append("| Umbral | Eventos que alcanzan | % del total | Winrate si espera | Wait promedio | Wait mediano |")
    lines.append("|--------|----------------------|-------------|-------------------|---------------|---------------|")
    for _, r in summary.iterrows():
        lines.append(
            f"| {r['threshold']:.1f} | {r['events_reached']} | {r['pct_reached']*100:.1f}% | "
            f"{r['winrate_if_waited']*100:.1f}% | {r['avg_wait_cycles']:.1f} | {r['median_wait_cycles']:.1f} |"
        )
    lines += [
        "",
        "## Trade-off por bucket de separacion original",
        "",
        "| Bucket | Count | Winrate original | reach_5 | winrate_wait_5 |",
        "|--------|-------|------------------|---------|----------------|",
    ]
    for _, r in tradeoff.iterrows():
        lines.append(
            f"| {r['sep_bucket']} | {r['count']} | {r['original_winrate']*100:.1f}% | "
            f"{r.get('reach_5', 0)} | {r.get('winrate_wait_5', 0)*100:.1f}% |"
        )

    lines += [
        "",
        "## Hallazgos clave",
        f"- De {len(low_sep)} eventos con separacion baja original (<=3), el porcentaje que alcanza separacion >=5 si espera es {low_sep['reached_5'].sum()/len(low_sep)*100:.1f}%.",
        f"- Winrate general con espera para umbral 5: {summary.loc[summary['threshold']==5, 'winrate_if_waited'].iloc[0]*100:.1f}%",
        f"- Trade-off: esperar mas velas aumenta separacion pero reduce cantidad de entradas ejecutables.",
        "",
        "## Propuesta ML: features para 'pacient waiting'",
        "- `sep_trend_3`: pendiente de separacion K/D en ultimas 3 velas pre-cruce (crece/decrece).",
        "- `sep_velocity`: cambio de separacion por vela en ventana pre-cruce.",
        "- `wait_cycles_needed`: velas hasta alcanzar threshold X; NaN si nunca alcanza.",
        "- `max_sep_in_wait`: separacion maxima alcanzada en ventana de espera.",
        "- `sep_at_entry`: separacion en la vela de entrada efectiva.",
        "- `patience_flag`: 1 si el sistema tuvo que esperar al menos 1 vela; 0 si entrada inmediata.",
        "- `time_to_threshold_binary`: 1 si alcanza threshold dentro de N velas; 0 si no.",
        "",
        "## Recomendacion operativa",
        "- No descartar automaticamente separacion <= 3. Esperar hasta 5 velas; si alcanza >=5, calidad sube.",
        "- Si en ventana de espera la separacion decrece o no despega, descartar (patience_flag=0 + sep_trend negativo).",
        "",
    ]

    report_path = out_dir / "patient_waiting_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Reporte guardado en {report_path}")
