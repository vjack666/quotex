"""Estudio empírico: estocástico en zona OS/OB sobre EURUSD M15 (14 años, read-only).

Registra CON NÚMEROS la secuencia de tu teoría:
  - en qué momento %K y %D están dentro de la zona (OS/OB)
  - cuándo las líneas están PEGADAS vs SEPARADAS de verdad (|K-D|)
  - el cruce de líneas (+1 arriba, -1 abajo)
  - cuándo, estando en zona y separadas, el precio se DESPEGA en fwd velas M15

Salida:
  data/smc_borrowed/events_estocastico_zona.csv  (una fila por vela con los números)
  docs/ESTOCASTICO_ZONA_reporte.md               (tasas de la teoría)

No toca el bot. No modifica datos SMC (solo lectura).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
M15 = ROOT / "data" / "smc_borrowed" / "EURUSD_M15.parquet"
sys.path.insert(0, str(ROOT / "src"))

from analytics.config_loader import ZonaConfig, default_config_path  # noqa: E402
from analytics import estocastico_zona as ez  # noqa: E402
from strategy_lab import feature_calc as fc  # noqa: E402


def main() -> int:
    if not M15.exists():
        print(f"[SKIP] falta {M15}; corre scripts/build_m15_from_m1.py")
        return 0
    cfg = ZonaConfig.load(default_config_path())
    df = pd.read_parquet(M15).sort_values("time")
    df = df.iloc[-200_000:]                      # ventana representativa (rapidez)
    kk, dd = fc.stochastic_full(
        df["high"].to_numpy(float), df["low"].to_numpy(float),
        df["close"].to_numpy(float), 14, 3, 3,
    )
    close = df["close"].to_numpy(float)
    lab = ez.classify(kk, dd, close, cfg.as_dict())

    # --- CSV por vela con todos los números ---
    out_df = pd.DataFrame({
        "time": df["time"].values,
        "K": np.round(kk, 2),
        "D": np.round(dd, 2),
        "gap": np.round(np.abs(kk - dd), 2),
        "zona": np.where(lab.zona == 0, "fuera", np.where(lab.zona == 1, "OS", "OB")),
        "estado_lineas": np.where(lab.estado_lineas == 0, "pegadas",
                          np.where(lab.estado_lineas == 2, "separadas", "entre")),
        "cruce": lab.cruce,
        "en_zona_sep": lab.en_zona_sep.astype(int),
        "despegue": lab.despegue.astype(int),
    })
    csv_path = ROOT / "data" / "smc_borrowed" / "events_estocastico_zona.csv"
    out_df.to_csv(csv_path, index=False)

    # --- Tasas de la teoría ---
    n = len(kk)
    en_zona = lab.zona != 0
    en_zona_sep = lab.en_zona_sep
    cruces = lab.cruce != 0
    n_cruces = int(cruces.sum())
    # de los cruces que ocurren en zona separada, cuántos tienen despegue
    mask = en_zona_sep & cruces
    n_teoria = int(mask.sum())
    n_despegue = int(lab.despegue.sum())
    tasa = (n_despegue / n_teoria) if n_teoria else 0.0

    # desglose por tipo de zona
    def _stat(zona_code: int) -> tuple[int, int, float]:
        m = (lab.zona == zona_code) & cruces
        nt = int(m.sum())
        nd = int((lab.despegue & m).sum())
        return nt, nd, (nd / nt) if nt else 0.0

    os_t, os_d, os_rate = _stat(1)
    ob_t, ob_d, ob_rate = _stat(2)

    md = f"""# Estocástico en zona OS/OB — estudio empírico (EURUSD M15, 14 años)

Ventana: {n:,} velas M15 (datos SMC prestados, read-only).
Umbrales: OS<= {cfg.os:.0f} | OB>= {cfg.ob:.0f} | pegadas |K-D|<={cfg.peg_max:.0f}
          | separadas |K-D|>= {cfg.sep_min:.0f} | despegue a {cfg.fwd} velas >= {cfg.rebote_min_pips:.0f} pip

## Tu secuencia, con números

1. Velas en zona (OS o OB): **{int(en_zona.sum()):,}** de {n:,} ({100*en_zona.mean():.1f}%)
2. De esas, con líneas SEPARADAS de verdad: **{int(en_zona_sep.sum()):,}**
   ({100*en_zona_sep.mean():.1f}% del total)
3. Cruces totales de %K/%D: **{n_cruces:,}**
4. Cruces OCURRIENDO en zona + separadas (el setup de tu teoría): **{n_teoria:,}**
5. De esos setups, los que tuvieron DESPEGUE de precio real: **{n_despegue:,}**
   -> **tasa de despegue = {100*tasa:.1f}%**

## Desglose por zona

- Sobreventa (OS): {os_t:,} setups, {os_d:,} despegues -> {100*os_rate:.1f}%
- Sobrecompra (OB): {ob_t:,} setups, {ob_d:,} despegues -> {100*ob_rate:.1f}%

## Lectura

Si la tasa de despegue es claramente > 50% en una zona, tu teoría del
"despegue tras líneas separadas en zona" QUEDA REGISTRADA CON NÚMEROS.
Si está cerca de 50%, el despegue es azar (las líneas separadas no predicen
dirección). El CSV por vela permite auditar cada evento.
"""
    rep = ROOT / "docs" / "ESTOCASTICO_ZONA_reporte.md"
    rep.write_text(md, encoding="utf-8")

    print(f"[OK] velas={n:,} en_zona={int(en_zona.sum()):,} "
          f"en_zona_sep={int(en_zona_sep.sum()):,} cruces={n_cruces:,}")
    print(f"[OK] setups_teoria={n_teoria:,} despegues={n_despegue:,} "
          f"tasa_despegue={100*tasa:.1f}%")
    print(f"[OK] CSV -> {csv_path}")
    print(f"[OK] reporte -> {rep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
