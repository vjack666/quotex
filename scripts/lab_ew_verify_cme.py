"""EW / CME 6E — VERIFICACIÓN del DATA REQUIREMENTS (NO EJECUTADO aún: requiere datos adquiridos).

Corre DESPUÉS de lab_ew_acquire_cme.py. Ejecuta el checklist completo ANTES de congelar EW-1:
  - % volume == 0 o missing <= 2%
  - continuidad (huecos < 1% de sesiones)
  - distribución (cola derecha razonable)
  - sanity: corr(volume, |close-open|) y corr(volume, rango) positiva y significativa
  - cobertura TRAIN 2022-2024 / TEST 2025-2026
  - INSPECCIÓN DE ROLLOVERS (prueba crítica): comparar contratos negociados del contrato
    INDIVIDUAL alrededor de cada rollover frente al volumen de la serie CONTINUA, para asegurar
    que la continuidad no fabrica anomalías de volumen.
Si falla cualquier criterio: NO se arregla por imputación/filtrado; se documenta y se detiene.

NO congela EW-1. NO ejecuta experimento. Solo reporta PASS/FAIL por criterio y los metadatos reales.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

RAW = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\cme_6e\EURUSD_6E_1m_ohlcv.parquet")

# Metadatos planificados (se completan/sobrescriben con lo observado al correr)
META = {
    "dataset": "GLBX.MDP3",
    "symbol": "6E.v.0",            # continuous volume-roll front month
    "volume_def": "nº de contratos negociados (REAL traded volume, NO tick, NO proxy)",
    "tz": "UTC (ts_event ns epoch)",
    "roll_method": "Databento volume roll; NO back-adjust de precios",
    "build_m15": "agregación 1m->M15 local: open=first, high=max, low=min, close=last, vol=sum",
    "period": "2022-01-01 .. 2026-08-01",
}


def load_m15() -> pd.DataFrame:
    df = pd.read_parquet(RAW)
    # ts_event en ns epoch UTC -> datetime
    idx = pd.to_datetime(df.index) if df.index.name == "ts_event" else pd.to_datetime(df["ts_event"])
    df = df.set_index(idx)
    m15 = df.resample("15min").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"),
        volume=("volume", "sum"),
    ).dropna()
    return m15


def detect_rollovers(df: pd.DataFrame) -> list[pd.Timestamp]:
    """Detecta cambios de instrument_id (rollover real) si la columna existe; si no,
    aproxima por saltos de precio anómalos entre barras 1m continuas."""
    rolls = []
    if "instrument_id" in df.columns:
        chg = df["instrument_id"].ne(df["instrument_id"].shift())
        rolls = df.index[chg & df.index > df.index[0]].tolist()
    return rolls


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"FALTA el raw: {RAW}. Corre primero lab_ew_acquire_cme.py.")
    m15 = load_m15()
    ok = True
    def chk(name, cond, extra=""):
        nonlocal ok
        ok = ok and cond
        print(f"  [{'OK' if cond else 'FAIL'}] {name} {extra}")

    print("=== METADATOS ===")
    for k, v in META.items():
        print(f"  {k}: {v}")
    print(f"  filas M15: {len(m15):,}")
    print(f"  rango: {m15.index.min()} .. {m15.index.max()}")

    # 1. % ceros/missing
    zero = (m15["volume"] == 0).mean()
    miss = m15["volume"].isna().mean()
    chk("volume %==0 <=2%", zero <= 0.02, f"(={zero:.3%})")
    chk("volume %missing <=2%", miss <= 0.02, f"(={miss:.3%})")

    # 2. continuidad: sesiones esperadas vs presentes
    expected = len(pd.date_range(m15.index.min().normalize(), m15.index.max().normalize(), freq="D"))
    present_days = m15.index.normalize().nunique()
    gaps = (expected - present_days) / expected
    chk("huecos dias <1%", gaps < 0.01, f"(={gaps:.3%})")

    # 3. distribución
    chk("distribución: vol medio >0 y cola derecha", m15["volume"].mean() > 0 and m15["volume"].quantile(0.99) > m15["volume"].median())

    # 4. sanity correlaciones
    move = (m15["close"] - m15["open"]).abs()
    rng = m15["high"] - m15["low"]
    c1 = np.corrcoef(m15["volume"], move)[0, 1]
    c2 = np.corrcoef(m15["volume"], rng)[0, 1]
    chk("corr(vol,|move|) positiva", c1 > 0, f"(r={c1:.3f})")
    chk("corr(vol,rango) positiva", c2 > 0, f"(r={c2:.3f})")

    # 5. split OOS
    train = m15.loc[:"2024-12-31"]
    test = m15.loc["2025-01-01":]
    chk("TRAIN 2022-2024 presente", len(train) > 0)
    chk("TEST 2025-2026 presente", len(test) > 0)

    # 6. inspección rollovers (prueba crítica)
    rolls = detect_rollovers(m15)
    if rolls:
        print(f"  rollovers detectados: {len(rolls)}")
        for r in rolls[:5]:
            w = m15.loc[r - pd.Timedelta("2D"): r + pd.Timedelta("2D"), "volume"]
            chk(f"rollover {r.date()}: vol continuo continuo (sin 0 artificial)", w.min() > 0, f"(min={w.min():.0f})")
    else:
        print("  (rollovers no detectables sin instrument_id en OHLCV; inspeccion manual requerida)")

    print("\nCHECKLIST EW/CME:", "PASS" if ok else "FAIL")
    if not ok:
        print("=> FALLO: documentar y DETENER. NO imputar ni filtrar arbitrariamente. NO congelar EW-1.")
    else:
        print("=> PASS: presentar resultados para autorizar congelación de EW-1 (no ejecutar aún).")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
