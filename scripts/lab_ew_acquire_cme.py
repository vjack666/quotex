"""EW / CME 6E — ADQUISICIÓN de datos desde Databento (NO EJECUTADO aún: requiere API key).

Orden del Trader-Humano (2026-08-07): adquirir SOLO lo necesario para validar el instrumento
EW (CME Euro FX Futures 6E), sin ejecutar EW-1. Mantener la adquisición pequeña: schema OHLCV
intradía (NO MBO gigante).

Metadatos conservados/documentados ANTES de integrar (ítems 1-7 de la orden):
  1. proveedor/dataset: databento / GLBX.MDP3
  2. símbolo/vencimiento: continuous 6E.v.0 (front-month por VOLUMEN, volume roll) -> mapea a
     contratos individuales 6Exxxx (ej. 6EU6) según la fecha
  3. definición de volume: nº de CONTRATOS negociados (real traded volume, NO tick, NO proxy)
  4. timestamps/timezone: ns epoch UTC (Databento entrega en UTC); ts_event
  5. construcción M15: agregación de barras 1m -> OHLC(first/open,max/high,min/low,last/close),
     sum(volume). Se hace LOCALMENTE (no usar resample de Databento) para controlar el rollover.
  6. rollover/continuous: Databento symbology continua `6E.v.0` usa VOLUME ROLL y NO back-adjusta
     precios (mantiene propiedades originales del contrato). El cambio de contrato ocurre cuando
     el volumen del mes siguiente supera al actual. El volumen es continuo; el precio puede tener
     un salto discreto en la fecha de roll (base). Eso es ESPERADO y se inspecciona en verify.
  7. período: 2022-01-01 .. 2026-08-01 (cubre TRAIN 2022-2024 / TEST 2025-2026).

Uso schema `ohlcv-1m` (1 minuto) en lugar de M15 directo: nos da granularidad para construir M15
localmente y para inspeccionar los rollovers barra a barra. Es OHLCV, NO MBO -> adquisición pequeña.

NO congela EW-1. NO ejecuta experimento. Solo descarga y guarda raw 1m (gitignored en data/).
"""
from __future__ import annotations
import os
from pathlib import Path
import databento as db

# --- Configuración (no secretos; la key viene de env DATABENTO_KEY) ---
DATASET = "GLBX.MDP3"
SYMBOL = "6E.v.0"          # continuous, volume roll, front month
STYPE_IN = "continuous"
SCHEMA = "ohlcv-1m"        # intradía OHLCV 1m (NO MBO)
START = "2022-01-01T00:00:00"   # UTC
END = "2026-08-01T00:00:00"     # UTC  (cubre TRAIN+TEST)
OUT_DIR = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\cme_6e")
OUT_FILE = OUT_DIR / "EURUSD_6E_1m_ohlcv.parquet"


def acquire() -> None:
    if not os.environ.get("DATABENTO_KEY"):
        raise SystemExit("FALTA DATABENTO_KEY: no se puede adquirir sin credencial. "
                         "Exporta la variable y vuelve a correr.")
    client = db.Historical(key=os.environ["DATABENTO_KEY"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[acquire] dataset={DATASET} symbol={SYMBOL} schema={SCHEMA}")
    print(f"[acquire] rango {START} .. {END} (UTC)")
    data = client.timeseries.get_range(
        dataset=DATASET,
        symbols=[SYMBOL],
        stype_in=STYPE_IN,
        schema=SCHEMA,
        start=START,
        end=END,
    )
    df = data.to_df()  # indice ts_event (UTC ns)
    df.to_parquet(OUT_FILE)
    print(f"[acquire] guardado {OUT_FILE}  filas={len(df):,}")


if __name__ == "__main__":
    acquire()
