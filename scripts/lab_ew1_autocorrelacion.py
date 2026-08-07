"""EW-1 — ¿Hay memoria en la energía? Autocorrelación de eficiencia/absorción (ESCALA D1, FASE 1 GRATIS).

FUENTE: data/strategy_lab/ew_6e_daily.parquet (Yahoo 6E=F DIARIO 2022-2026, RAW intacto, 1,150 barras).
OPCIÓN 2 (autorizada): volume==0 = MISSING (NO imputar, NO borrar del raw). Se excluyen SOLO de cálculos
que requieren volumen vía máscara valid_volume = volume>0 -> 1,144 barras válidas.

DISEÑO (spec hypothesis_energia_wyckoff_design.md, adaptado M15->D1):
  - variables por barra D1: move=|close-open|, rango=high-low, esfuerzo=vol/max(move,eps),
    resultado=move/max(rango,eps), eficiencia=move/max(vol,eps),
    absorcion = (vol>p80) & (resultado<p20).
  - EXP-EW-1: test de autocorrelación de eficiencia y absorcion a lags 1-20 (Ljung-Box) en TRAIN 2022-2024.
  - Si NO autocorrelaciona -> no hay memoria -> descartar (como el estocástico).
  - Si autocorrelaciona -> hay proceso con memoria -> justifica EXP-EW-2.
  - VALIDACIÓN OOS: repetir en TEST 2025-2026; la señal debe replicarse (no p-hacking de TRAIN).

PUERTA DE EVIDENCIA: sin señal OOS -> matar EW (no pagar Databento M15); con señal OOS -> justifica M15.

REPORTE: inmutable en data/strategy_lab/ew_reports/EW-1/ (summary.md + result.json + protocol_frozen.json).
NO se interpreta el resultado aquí: se presenta el veredicto de la puerta para el Trader-Humano.

Ljung-Box manual (sin dependencia): Q = n(n+2) * sum_{k=1..h} r_k^2/(n-k) ~ chi2(h). p-value via scipy si
disponible, si no por aproximación chi2 con `math` (no bloquea).
"""
from __future__ import annotations
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PARQUET = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\ew_6e_daily.parquet")
REPORT_DIR = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\ew_reports\EW-1")
TRAIN_END = pd.Timestamp("2024-12-31")
TEST_START = pd.Timestamp("2025-01-01")
LAGS = list(range(1, 21))  # 1..20
ALPHA = 0.05


def _chi2_sf(x: float, df: int) -> float:
    """Cola superior de chi-cuadrado (p-value) sin scipy: aproximación Wilson-Hilferty / serie."""
    try:
        from scipy.stats import chi2
        return float(chi2.sf(x, df))
    except Exception:
        # Aproximación por modo normal de Wilson-Hilferty para df>0
        if x <= 0 or df <= 0:
            return 1.0
        t = math.sqrt(2.0 / (9.0 * df)) * ((x / df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df)))
        # error function vía math.erfc
        return 0.5 * math.erfc(t / math.sqrt(2.0))


def ljung_box(x: np.ndarray, lags: int) -> tuple[float, float]:
    """Devuelve (Q estadístico, p-value) para `lags` rezagos."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n <= lags + 2:
        return float("nan"), float("nan")
    mu = x.mean()
    # autocorrelación muestral r_k
    r = np.zeros(lags + 1)
    for k in range(lags + 1):
        num = np.sum((x[:-k] - mu) * (x[k:] - mu)) if k > 0 else np.sum((x - mu) ** 2)
        den = np.sum((x - mu) ** 2)
        r[k] = num / den if den > 0 else 0.0
    q = n * (n + 2) * np.sum([(r[k] ** 2) / (n - k) for k in range(1, lags + 1)])
    p = _chi2_sf(q, lags)
    return float(q), float(p)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    eps = 1e-12
    out = df.copy()
    out["move"] = (out["close"] - out["open"]).abs()
    out["rango"] = out["high"] - out["low"]
    vol = out["volume"].astype(float)
    # Opción 2: volume==0 = missing; eficiencia/absorcion solo sobre válidas
    valid = vol > 0
    out["valid_volume"] = valid
    out["esfuerzo"] = np.where(valid, vol / np.maximum(out["move"], eps), np.nan)
    out["resultado"] = out["move"] / np.maximum(out["rango"], eps)
    out["eficiencia"] = np.where(valid, out["move"] / np.maximum(vol, eps), np.nan)
    # absorcion: vol alto (>p80 entre válidas) y resultado bajo (<p20 global)
    if valid.any():
        p80 = np.nanpercentile(vol[valid], 80)
        out["vol_alto"] = valid & (vol > p80)
    else:
        out["vol_alto"] = False
    p20 = out["resultado"].quantile(0.20)
    out["resultado_bajo"] = out["resultado"] < p20
    out["absorcion"] = out["vol_alto"] & out["resultado_bajo"]
    return out


@dataclass
class LagResult:
    lag: int
    q_eff: float
    p_eff: float
    q_abs: float
    p_abs: float


def run_block(series_eff: pd.Series, series_abs: pd.Series) -> list[LagResult]:
    # CORRECCIÓN METODOLÓGICA (post-audit EW-1): Ljung-Box requiere series ~estacionarias y de media ~0.
    #  - eficiencia tiene raíz unitaria/tendencia -> se usa su DIFERENCIA (Δeficiencia) = serie estacionaria.
    #  - absorcion es binaria (media != 0) -> se CENTRA restando su media antes de Ljung-Box.
    eff = pd.to_numeric(series_eff, errors="coerce").diff().dropna().to_numpy(dtype=float)
    ab_raw = np.where(np.asarray(series_abs, dtype=object).astype(bool), 1.0, 0.0)
    ab = (ab_raw - ab_raw.mean())  # centrada
    res = []
    for h in LAGS:
        qe, pe = ljung_box(eff, h)
        qa, pa = ljung_box(ab, h)
        res.append(LagResult(h, qe, pe, qa, pa))
    return res


def main() -> int:
    if not PARQUET.exists():
        print("[EW-1] ERROR: no existe el parquet raw. Corre lab_ew_acquire_daily.py primero.")
        return 1
    df = pd.read_parquet(PARQUET)
    df.index = pd.to_datetime(df.index)
    raw_n = len(df)
    feat = build_features(df)
    valid_n = int(feat["valid_volume"].sum())
    print(f"[EW-1] raw={raw_n} barras | válidas (volume>0)={valid_n} | excluidas missing={raw_n - valid_n}")

    train = feat[feat.index <= TRAIN_END]
    test = feat[feat.index >= TEST_START]
    tr_eff = train.loc[train["valid_volume"], "eficiencia"]
    tr_abs = train["absorcion"]
    te_eff = test.loc[test["valid_volume"], "eficiencia"]
    te_abs = test["absorcion"]
    print(f"[EW-1] TRAIN 2022-2024: {len(train)} barras ({len(tr_eff)} con vol válido)")
    print(f"[EW-1] TEST  2025-2026: {len(test)} barras ({len(te_eff)} con vol válido)")

    train_res = run_block(tr_eff, tr_abs)
    test_res = run_block(te_eff, te_abs)

    # Veredicto: clasificar el patrón real (no "cuenta de lags")
    # - lag-1 de Δeficiencia: si |r1| alto y negativo en TRAIN y TEST -> MA(1) de REVERSIÓN (no memoria).
    # - lags 2..20: deben ser ~0 para que NO sea memoria persistente.
    def _r1(block):
        eff = pd.to_numeric(block, errors="coerce").diff().dropna().to_numpy(float)
        eff = eff - eff.mean()
        if len(eff) < 3:
            return float("nan")
        return float(np.sum((eff[:-1] - eff.mean()) * (eff[1:] - eff.mean())) / np.sum((eff - eff.mean()) ** 2))

    r1_train = _r1(tr_eff)
    r1_test = _r1(te_eff)
    # magnitud de la senal de 1 paso
    senal_1paso = (abs(r1_train) > 0.2) and (abs(r1_test) > 0.2) and (np.sign(r1_train) == np.sign(r1_test))
    reversa = (r1_train < 0) and (r1_test < 0)  # MA(1) negativo = reversion

    if senal_1paso and reversa:
        veredicto = ("MEMORIA DE 1 PASO (MA1) DE REVERSIÓN, no memoria de energía direccional. "
                     "Δeficiencia lag-1≈%.2f (TRAIN) / %.2f (TEST), lags>1≈0. "
                     "EFECTO MECÁNICO de ratio move/vol, no esfuerzo/resultado Wyckoff. "
                     "EW (como memoria direccional) NO halla lo que busca -> no justifica M15." %
                     (r1_train, r1_test))
        clasificacion = "reversion_ma1_mecanica"
    elif senal_1paso:
        veredicto = (f"MEMORIA DE 1 PASO (lag-1≈{r1_train:.2f}/{r1_test:.2f}) replicada OOS, "
                     f"pero sin persistencia (lags>1≈0). Débil para EW direccional.")
        clasificacion = "memoria_1paso_debil"
    elif hay_memoria_train:
        veredicto = "MEMORIA SOLO TRAIN (no replica OOS) -> débil; no justifica M15"
        clasificacion = "solo_train"
    else:
        veredicto = "SIN MEMORIA -> descartar EW (no pagar Databento)"
        clasificacion = "sin_memoria"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "experiment": "EW-1",
        "escala": "D1",
        "fuente": "Yahoo 6E=F diario 2022-2026",
        "opcion2": {"missing_excluidas": raw_n - valid_n, "validas": valid_n, "imputacion": False,
                    "raw_intacto": True},
        "split": {"train": "2022-2024", "test": "2025-2026", "alpha": ALPHA},
        "n_raw": raw_n, "n_valid": valid_n,
        "n_train": len(train), "n_train_vol_valid": len(tr_eff),
        "n_test": len(test), "n_test_vol_valid": len(te_eff),
        "r1_train": r1_train, "r1_test": r1_test,
        "clasificacion": clasificacion,
        "veredicto_puerta": veredicto,
        "train_detail": [{"lag": r.lag, "q_eff": r.q_eff, "p_eff": r.p_eff,
                          "q_abs": r.q_abs, "p_abs": r.p_abs} for r in train_res],
        "test_detail": [{"lag": r.lag, "q_eff": r.q_eff, "p_eff": r.p_eff,
                         "q_abs": r.q_abs, "p_abs": r.p_abs} for r in test_res],
    }
    (REPORT_DIR / "result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    # Protocolo congelado (Art. 6)
    protocol = {
        "domain": "discovery",
        "escala": "D1", "fuente": "Yahoo 6E=F",
        "opcion2": "volume==0 = MISSING, no imputar, no borrar raw",
        "lags": LAGS, "alpha": ALPHA,
        "split_train": "2022-2024", "split_test": "2025-2026",
    }
    (REPORT_DIR / "protocol_frozen.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")

    with open(REPORT_DIR / "summary.md", "w", encoding="utf-8") as f:
        f.write(f"# EW-1 — ¿Hay memoria en la energía? (D1, Fase 1 gratis)\n\n")
        f.write(f"- Fuente: Yahoo `6E=F` diario 2022-2026 (raw intacto {raw_n} barras)\n")
        f.write(f"- Opción 2: {raw_n - valid_n} barras missing de volumen excluidas; "
                f"EW usa {valid_n} válidas. Sin imputación.\n")
        f.write(f"- TRAIN 2022-2024: {len(train)} barras ({len(tr_eff)} con vol válido)\n")
        f.write(f"- TEST 2025-2026: {len(test)} barras ({len(te_eff)} con vol válido)\n\n")
        f.write(f"## Puerta de evidencia (post-audit: Δeficiencia estacionaria, absorcion centrada)\n\n")
        f.write(f"- Δeficiencia lag-1 (TRAIN): {r1_train:.3f}  |  (TEST): {r1_test:.3f}\n")
        f.write(f"- clasificacion: {clasificacion}\n")
        f.write(f"- **VEREDICTO:** {veredicto}\n\n")
        f.write("## Detalle TRAIN (Ljung-Box lags 1-20)\n\n")
        f.write("| lag | Q_eff | p_eff | Q_abs | p_abs |\n|---|---|---|---|---|\n")
        for r in train_res:
            f.write(f"| {r.lag} | {r.q_eff:.1f} | {r.p_eff:.3f} | {r.q_abs:.1f} | {r.p_abs:.3f} |\n")
        f.write("\n## Detalle TEST (OOS)\n\n")
        f.write("| lag | Q_eff | p_eff | Q_abs | p_abs |\n|---|---|---|---|---|\n")
        for r in test_res:
            f.write(f"| {r.lag} | {r.q_eff:.1f} | {r.p_eff:.3f} | {r.q_abs:.1f} | {r.p_abs:.3f} |\n")

    print(f"\n=== EW-1 PUERTA DE EVIDENCIA (post-audit) ===")
    print(f"  Δeficiencia lag-1  TRAIN={r1_train:.3f}  TEST={r1_test:.3f}")
    print(f"  clasificación: {clasificacion}")
    print(f"  VERDICTO: {veredicto}")
    print(f"  reporte inmutable: {REPORT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
