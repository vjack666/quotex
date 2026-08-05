"""Runner del laboratorio de secuencia libre.

Corre el motor de secuencia libre (sin orden impuesto) y produce:
  - data/strategy_lab/secuencia_libre_events.parquet  (expedientes)
  - data/strategy_lab/secuencia_libre_funnel.csv      (embudo por par)
  - stdout: embudo + WR por firma de secuencia (la gramática que pide Ruben)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # src/
from strategy_lab.secuencia_libre import run_secuencia_libre  # noqa: E402

OUT = Path(r"C:\Users\v_jac\Desktop\QUOTEX\data\strategy_lab")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    print("=== LAB-SEC: motor de secuencia libre (sin orden impuesto) ===")
    events, funnel = run_secuencia_libre(verbose=True)

    ev_path = OUT / "secuencia_libre_events.parquet"
    fn_path = OUT / "secuencia_libre_funnel.csv"
    events.to_parquet(ev_path)
    funnel.to_csv(fn_path, index=False)

    print("\n=== EMBUDO ===")
    print(funnel.to_string(index=False))

    comp = events[events["completa"] == 1].copy()
    print(f"\nTotal expedientes: {len(events)} | completas: {len(comp)}")
    if len(comp):
        print(f"WR global completas: {comp['win'].mean():.4f}")
        print("\n=== WR por FIRMA de secuencia (gramática descubierta) ===")
        g = comp.groupby("firma")["win"].agg(["size", "mean"]).sort_values(
            "size", ascending=False
        )
        print(g.round(4).head(25).to_string())

        print("\n=== WR por firma x asset (validación cruzada, no agregada) ===")
        for firma in g.head(8).index:
            sub = comp[comp["firma"] == firma]
            by_asset = sub.groupby("asset")["win"].agg(["size", "mean"]).round(4)
            print(f"\n[{firma}] n={len(sub)}")
            print(by_asset.to_string())

    print(f"\nGuardado: {ev_path}")
    print(f"Guardado: {fn_path}")


if __name__ == "__main__":
    main()
