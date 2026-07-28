"""validar_walkforward — Bloque 3.5: los numeros del freno aguantan otra fecha?

Leave-one-date-out sobre las cajas negras disponibles:
  Para cada fecha T como TEST:
    - TRAIN = todas las demas fechas
    - mina sep_min y salida_zona en TRAIN (resumir)
    - aplica esos umbrales en TEST (wr_con_filtros) y mide WR real
  Reporta por fold y el promedio. Si test_WR ~ train_WR => los numeros
  del Bloque 3 aguantan out-of-sample (no son overfitting de un dia).

Uso:
  PYTHONPATH=src python -m strategy_lab.validar_walkforward
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from strategy_lab import minar_leyes_freno as miner

DB_DIR = Path("data/db")


def _cajas() -> list[Path]:
    out = []
    for p in sorted(DB_DIR.glob("black_box_strat_*.db")):
        out.append(p)
    return out


def main() -> dict:
    cajas = _cajas()
    if len(cajas) < 2:
        print("insuficientes cajas para walk-forward")
        return {}
    # Umbrales fijos adoptados por el cerebro (json descubierto, minado global).
    from strategy_lab.laws_freno import FrenoConfig
    cfg_fijo = FrenoConfig()
    sep_fijo, sal_fijo = cfg_fijo.sep_min, cfg_fijo.salida_zona
    print(f"umbrales FIJOS del cerebro (json): sep={sep_fijo} salida={sal_fijo}\n")

    folds = []
    for i, test_db in enumerate(cajas):
        train_dbs = [str(d) for j, d in enumerate(cajas) if j != i]
        train_ev = miner.extraer_eventos_de_dbs(train_dbs)
        train_summary = miner.resumir(train_ev)
        if "error" in train_summary:
            continue
        sep_t = train_summary["adoptados"]["sep_min"]
        sal_t = train_summary["adoptados"]["salida_zona"]
        test_ev = miner.extraer_eventos_de_dbs([str(test_db)])
        test_wr, test_n = miner.wr_con_filtros(test_ev, sep_t, sal_t)
        test_wr_fijo, test_n_fijo = miner.wr_con_filtros(test_ev, sep_fijo, sal_fijo)
        test_base = float(np.mean([e[3] for e in test_ev])) if test_ev else 0.0
        folds.append({
            "test": test_db.name,
            "train_n": train_summary["meta"]["eventos_total"],
            "sep_adopt": sep_t, "sal_adopt": sal_t,
            "test_n": test_n, "test_wr": round(test_wr, 4),
            "test_n_fijo": test_n_fijo, "test_wr_fijo": round(test_wr_fijo, 4),
            "test_wr_base": round(test_base, 4),
        })

    if folds:
        wr_f = [f["test_wr"] for f in folds if f["test_n"] > 0]
        wr_ff = [f["test_wr_fijo"] for f in folds if f["test_n_fijo"] > 0]
        prom_wr = float(np.mean(wr_f)) if wr_f else 0.0
        prom_wr_fijo = float(np.mean(wr_ff)) if wr_ff else 0.0
        print(f"folds: {len(folds)}")
        print(f"  WR promedio TEST (umbrales TRAIN del fold): "
              f"{prom_wr:.4f}")
        print(f"  WR promedio TEST (umbrales FIJOS json {sep_fijo}/{sal_fijo}): "
              f"{prom_wr_fijo:.4f}")
        for f in folds:
            flag = "OK" if (f["test_n_fijo"] > 0 and f["test_wr_fijo"] >= 0.80) else "BAJO"
            print(f"  {f['test']:42s} tr_n={f['train_n']:4d} "
                  f"sep={f['sep_adopt']} sal={f['sal_adopt']} | "
                  f"TEST fold WR={f['test_wr']:.3f}(n{f['test_n']}) "
                  f"FIJO WR={f['test_wr_fijo']:.3f}(n{f['test_n_fijo']}) "
                  f"base={f['test_wr_base']:.3f} [{flag}]")
    return {"folds": folds}


if __name__ == "__main__":
    main()
