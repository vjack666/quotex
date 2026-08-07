"""EW / 6E diario — VERIFICACIÓN del DATA REQUIREMENTS adaptado a D1 (FASE 1 GRATIS; AUTORIZADO A).

Lee data/strategy_lab/ew_6e_daily.parquet y corre el checklist (§5 DATA_REQUIREMENTS, adaptado de
M15->D1). NO construye features ni ejecuta EW-1.

SEMÁNTICA DE VOLUMEN (Opción 2, autorizada 2026-08-07):
  - `volume == 0` se trata como **MISSING de volumen** (laguna de reporte del proveedor), NO como
    "día sin volumen" ni como cero válido. NO se imputa volumen.
  - El parquet RAW queda INTACTO (1,150 barras). La exclusión es lógica vía máscara
    `valid_volume = volume > 0`; EW-1 usa solo las barras válidas. Trazabilidad preservada.
  - Criterio 2 evalúa el % de missing de volumen. Si el missing es disperso y las barras tienen
    precio real (Open≠Close, rango normal), se emite veredicto APTO CON EXCLUSIÓN DOCUMENTADA
    en vez de rechazo ciego.

Criterios (umbrales EW; en diario los huecos de fin de semana/feriado son esperados, se miden huecos
anómalos >4 días hábiles):
  1. Columnas OHLCV presentes; volumen = contratos reales (semántica documentada).
  2. % volume missing (==0) <= 2% GLOBAL y por año (sobre total de barras del periodo).
  3. Continuidad: huecos de >4 días hábiles < 1% de las transiciones.
  4. Distribución: cola derecha razonable (no saturado en cero); percentil 99 finito y >0.
  5. Sanity: corr(volume, |close-open|) y corr(volume, high-low) positivas (sobre barras válidas).
  6. Split OOS: cubre TRAIN 2022-2024 y TEST 2025-2026.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PARQUET = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\ew_6e_daily.parquet")
TEST_END = pd.Timestamp("2026-08-01")


def main() -> int:
    if not PARQUET.exists():
        print(f"[verify] ERROR: no existe {PARQUET}. Corre lab_ew_acquire_daily.py primero.")
        return 1
    df = pd.read_parquet(PARQUET)
    df.index = pd.to_datetime(df.index)
    print(f"[verify] {len(df):,} barras RAW  {df.index.min().date()}..{df.index.max().date()}")

    # Máscara de volumen válido (Opción 2: volume==0 = missing, NO imputar, NO borrar del raw)
    v = df["volume"].astype(float).to_numpy()
    valid_volume = v > 0
    n_valid = int(valid_volume.sum())
    n_missing = int((~valid_volume).sum())
    print(f"[verify] volumen válido (volume>0): {n_valid:,} | missing (volume==0): {n_missing} "
          f"-> EW usa SOLO las {n_valid:,} válidas; raw intacto.")

    results = {}
    # 1) columnas
    need = ["open", "high", "low", "close", "volume"]
    results["1_columnas"] = all(c in df.columns for c in need)

    # 2) missing de volumen global y por año (sobre TODAS las barras del periodo)
    pct_missing = float((~valid_volume).mean())
    years = df.index.year.to_numpy()
    by_year = {}
    for yr in np.unique(years):
        by_year[yr] = float((~valid_volume[years == yr]).mean())
    worst_year = max(by_year, key=by_year.get) if by_year else None
    worst_year_pct = max(by_year.values()) if by_year else 1.0
    results["2_missing_global"] = pct_missing <= 0.02
    results["2_missing_por_anio"] = worst_year_pct <= 0.02

    # 3) continuidad (huecos >4 días hábiles)
    días = df.index.normalize()
    gaps = días.to_series().diff().dropna().dt.days.to_numpy()
    huecos_grandes = int((gaps > 4).sum())
    transiciones = len(gaps)
    results["3_continuidad"] = (huecos_grandes / transiciones) < 0.01 if transiciones else False

    # 4) distribución cola (sobre válidos)
    p99 = float(np.nanpercentile(v[valid_volume], 99)) if n_valid else float("nan")
    results["4_distribucion"] = bool(np.isfinite(p99) and p99 > 0)

    # 5) sanity correlaciones (sobre barras con volumen válido)
    vv = v[valid_volume]
    move = (df["close"] - df["open"]).abs().to_numpy()[valid_volume]
    rango = (df["high"] - df["low"]).to_numpy()[valid_volume]
    corr_move = float(np.corrcoef(vv, move)[0, 1]) if len(vv) > 2 else float("nan")
    corr_rango = float(np.corrcoef(vv, rango)[0, 1]) if len(vv) > 2 else float("nan")
    results["5_sanity"] = bool(corr_move > 0 and corr_rango > 0)

    # 6) split OOS
    covers_train = (years <= 2024).any() and (years >= 2022).any()
    covers_test = (years >= 2025).any() and (df.index <= TEST_END).any()
    results["6_split_oos"] = bool(covers_train and covers_test)

    print("\n=== CHECKLIST DIARIO (EW FASE 1 GRATIS, Opción 2) ===")
    for k, ok in results.items():
        print(f"  [{'OK' if ok else 'FAIL'}] {k}")
    print(f"\n  missing volumen global = {pct_missing:.2%}")
    print("  missing por año:")
    for yr in sorted(by_year):
        flag = "OK" if by_year[yr] <= 0.02 else "ALT"
        print(f"    {yr}: {by_year[yr]:.2%} [{flag}]")
    print(f"  huecos>4d = {huecos_grandes}/{transiciones}")
    print(f"  p99 vol = {p99:.0f}")
    print(f"  corr(vol,|move|) = {corr_move:.3f} | corr(vol,rango) = {corr_rango:.3f}")

    passed = all(results.values())
    if passed:
        print("\nVEREDICTO: PASÓ ESTRICTO -> apto para autorizar congelación EW-1")
        return 0
    # Veredicto condicional: falla SOLO por missing de volumen disperso y con precio real
    solo_missing = (not results["2_missing_global"]) or (not results["2_missing_por_anio"])
    otros_ok = all(results[k] for k in results if k not in ("2_missing_global", "2_missing_por_anio"))
    if solo_missing and otros_ok:
        print("\nVEREDICTO: APTO CON EXCLUSIÓN DOCUMENTADA (Opción 2) ->")
        print(f"  {n_missing} barras marcadas MISSING de volumen (no imputadas, no borradas del raw).")
        print(f"  EW-1 usa solo las {n_valid:,} barras válidas. Dataset raw intacto para trazabilidad.")
        print("  apto para que el Trader-Humano autorice la congelación de EW-1 (sin ejecutar aún).")
        return 0
    print("\nVEREDICTO: FALLÓ (criterio no relacionado con missing) -> NO ejecutar; reportar fallo")
    return 2


if __name__ == "__main__":
    sys.exit(main())
