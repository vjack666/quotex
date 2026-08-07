"""EW-BRAKE-LINK — ¿El freno del Edificio captura indirectamente la reversión de eficiencia de EW-1?

EXPERIMENTO DE DISEÑO (NO EJECUTADO aún; pendiente OK de ejecución del Trader-Humano).
No modifica el Edificio. No compra Databento. No es EW-2 todavía.

HIPÓTESIS (formulada por el TH, 2026-08-07):
  El Edificio detecta contracción de rango M15 (freno: range(nueva) < 0.7 * range(referencia)) y espera
  expansión. EW-1 halló que Δ(move/vol) en D1 revierte en 1 paso (≈-0.52, OOS). Como el freno opera sobre
  el eje `move` (rango≈move) y EW-1 sobre `move/vol`, la hipótesis es que EL FRENO DEL EDIFICIO ESTÁ
  PESCANDO INDIRECTAMENTE la misma compresión→reversión→expansión que EW-1 midió con dos ejes, pero ciego
  al volumen (proxy ruidoso).

PRUEBA POTENTE (criterio del TH):
  Cuando el Edificio activa su freno, ¿esas velas M15 presentan eficiencia move/vol anormalmente BAJA y, en
  la vela SIGUIENTE, esa eficiencia REVIERTE junto con EXPANSIÓN del precio — y esto ocurre también OOS?

DISEÑO DEL EXPERIMENTO (mínimo, con datos que YA tenemos en disco):
  1. Cargar EURUSD M15 histórico (data/strategy_lab/cohorte_real_eurusd/EURUSD_M15.parquet o
     data/smc_borrowed/EURUSD_M15.parquet). Sin red.
  2. Replicar el FRENO del Edificio sobre histórico M15 (SIN tocar el Edificio): para cada vela i,
     range_i = high-low; referencia = range de la vela de referencia del freno (en el Edificio es la vela
     M15 previa al candidato; aquí usamos range_{i-1} como referencia simple). freno_i = range_i < 0.7*range_{i-1}.
     NOTA: esto es una RÉPLICA de la definición del freno sobre histórico, NO los frenos reales del bot.
     Si en el futuro existe log de frenos reales, se sustituye esta lista. Se documenta como aproximación.
  3. En cada vela-freno: eficiencia_i = move_i / vol_i (move=|close-open|). ¿Está en cola BAJA (p.ej. < p20
     de la serie de eficiencia)?
  4. Vela SIGUIENTE (i+1): ¿la eficiencia SUBE respecto a i (reversión) Y el range SE EXPANDE
     (range_{i+1} > range_i)?
  5. CONTROL DE ARTEFACTO: ¿la reversión de Δeficiencia desaparece si uso move solo o vol solo? (aisla si es
     del ratio move/vol o propiedad mecánica del ratio construido). Esto evita repetir el error de EW-1.
  6. SPLIT OOS: umbral de "cola baja" (p20) se calcula en la PRIMERA mitad; la validación de
     reversión+expansión en la SEGUNDA mitad. Sin backtest de payout; solo coincidencia de regímenes.
  7. VEREDICTO:
       SÍ y OOS  -> CONEXIÓN PROBABLE: el freno captura indirectamente la reversión de eficiencia; útil para
                    mejorar el Edificio (filtro de calidad de freno / justificación mecánica).
       NO        -> SIN CONEXIÓN: el -0.52 es propiedad del ratio diario; no contaminar el Edificio.

SALIDA: reporte inmutable en data/strategy_lab/ew_reports/EW-BRAKE-LINK/ (summary.md + result.json).
No se interpreta el resultado aquí: se presenta el veredicto para el TH.

Ljung-Box / ACF: reusa la corrección de EW-1 (Δeficiencia estacionaria, absorción centrada) si se mide
autocorrelación intradía de Δeficiencia (paso opcional de caracterización, no del veredicto de freno).
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

# Datos M15 YA en disco (sin red). Preferir cohorte_real_eurusd si existe.
CANDIDATOS = [
    Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\cohorte_real_eurusd\EURUSD_M15.parquet"),
    Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\smc_borrowed\EURUSD_M15.parquet"),
]
BRAKE_RATIO = 0.7  # EDIFICIO_BRAKE_CONFIRM_RATIO (src/config.py:79)
LOW_PCTILE = 0.20   # cola baja de eficiencia
REPORT_DIR = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab\ew_reports\EW-BRAKE-LINK")


def _cargar_m15() -> pd.DataFrame:
    for p in CANDIDATOS:
        if p.exists():
            df = pd.read_parquet(p)
            df.index = pd.to_datetime(df.index)
            return df
    raise FileNotFoundError("No hay EURUSD_M15 en disco (cohorte_real_eurusd ni smc_borrowed). "
                            "Sin red: no se descarga.")


def main() -> int:
    print("[EW-BRAKE-LINK] modo DISEÑO (no ejecutado si se corre sin datos / sin OK).")
    df = _cargar_m15()
    print(f"[EW-BRAKE-LINK] M15 cargado: {len(df)} velas {df.index.min()}..{df.index.max()}")

    # features por vela M15
    df["move"] = (df["close"] - df["open"]).abs()
    df["range"] = df["high"] - df["low"]
    vol = df["volume"].astype(float)
    df["eficiencia"] = np.where(vol > 0, df["move"] / vol, np.nan)

    # 2) réplica del freno sobre histórico (range_i < 0.7 * range_{i-1})
    ref_range = df["range"].shift(1)
    df["is_freno"] = (df["range"] < BRAKE_RATIO * ref_range) & (ref_range > 0)
    n_frenos = int(df["is_freno"].sum())
    print(f"[EW-BRAKE-LINK] frenos replicados (range<0.7*ref): {n_frenos}")

    # 3) eficiencia en cola baja en velas-freno
    ef = df["eficiencia"]
    low_thr = ef.quantile(LOW_PCTILE)
    df["ef_low"] = ef < low_thr

    # 4) vela siguiente: eficiencia sube Y rango se expande
    ef_next = ef.shift(-1)
    range_next = df["range"].shift(-1)
    df["ef_revierte"] = ef_next > ef  # reversión de eficiencia
    df["rango_expande"] = range_next > df["range"]
    df["freno_exito"] = df["ef_revierte"] & df["rango_expande"]

    # split OOS: mitad 1 = entrenamiento de umbral, mitad 2 = validación
    mid = len(df) // 2
    train = df.iloc[:mid]
    test = df.iloc[mid:]
    low_thr_train = train["eficiencia"].quantile(LOW_PCTILE)

    def _tasa(sub: pd.DataFrame, thr: float) -> dict:
        fren = sub[sub["is_freno"]]
        n = len(fren)
        if n == 0:
            return {"n_frenos": 0, "pct_ef_low": None, "pct_exito": None}
        ef_low = float((fren["eficiencia"] < thr).mean())
        exito = float(fren["freno_exito"].mean())
        return {"n_frenos": n, "pct_ef_low": ef_low, "pct_exito": exito}

    res_train = _tasa(train, low_thr_train)
    res_test = _tasa(test, low_thr_train)  # umbral de train aplicado a test (OOS)

    # 5) control de artefacto: reversión de move solo y vol solo
    move_next_up = df["move"].shift(-1) > df["move"]
    vol_next_up = vol.shift(-1) > vol
    contr_move = float(df.loc[df["is_freno"], "move"].shift(-1).notna().mean())  # placeholder
    control = {
        "move_corr_lag1": float(df["move"].autocorr(1)) if hasattr(df["move"], "autocorr") else None,
        "vol_corr_lag1": float(vol.autocorr(1)) if hasattr(vol, "autocorr") else None,
        "eficiencia_corr_lag1": float(ef.autocorr(1)) if hasattr(ef, "autocorr") else None,
    }

    result = {
        "experimento": "EW-BRAKE-LINK",
        "hipotesis": "el freno del Edificio captura indirectamente la reversion de eficiencia de EW-1",
        "nota_metodo": "freno REPLICADO sobre M15 historico (no son los frenos reales del bot)",
        "brake_ratio": BRAKE_RATIO, "low_pctile": LOW_PCTILE,
        "n_total": len(df), "n_frenos_total": n_frenos,
        "train": res_train, "test_OOS": res_test,
        "control_artefacto": control,
        "veredic_to_pendiente_OK": "SÍ y OOS -> CONEXION PROBABLE; NO -> SIN CONEXION (no contaminar Edificio)",
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    with open(REPORT_DIR / "summary.md", "w", encoding="utf-8") as f:
        f.write("# EW-BRAKE-LINK (diseño, no interpretado)\n\n")
        f.write(f"- Freno replicado sobre M15: {n_frenos} velas (range < {BRAKE_RATIO}*ref)\n")
        f.write(f"- TRAIN: frenos={res_train['n_frenos']} | %ef_low={res_train['pct_ef_low']} "
                f"| %exito(rev+exp)={res_train['pct_exito']}\n")
        f.write(f"- TEST OOS: frenos={res_test['n_frenos']} | %ef_low={res_test['pct_ef_low']} "
                f"| %exito(rev+exp)={res_test['pct_exito']}\n")
        f.write(f"- Control artefacto (autocorr lag1): move={control['move_corr_lag1']} "
                f"vol={control['vol_corr_lag1']} eficiencia={control['eficiencia_corr_lag1']}\n")
        f.write("\nVEREDICTO: pendiente de OK de ejecución y lectura por el TH.\n")
    print(f"[EW-BRAKE-LINK] reporte: {REPORT_DIR}")
    print(f"[EW-BRAKE-LINK] TRAIN ef_low={res_train['pct_ef_low']} exito={res_train['pct_exito']} | "
          f"TEST ef_low={res_test['pct_ef_low']} exito={res_test['pct_exito']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
