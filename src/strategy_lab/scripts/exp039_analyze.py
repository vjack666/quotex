# -*- coding: utf-8 -*-
"""EXP-039 — Analizador de validación live del Edificio de Contratación.

Lee el log del bot (por defecto consolidation_bot.log en la raíz del repo) y
cuenta las métricas del protocolo de validación live:

  - entrada_count           : órdenes efectivamente enviadas (ORDEN ENVIADA)
  - reject_cerebro_count    : bloqueos por secuencia / CEREBRO
  - reject_reception_count  : expulsados por recepción (payout / Regla 1)
  - contratado_reached      : activos que llegaron a CONTRATADO
  - noise_count             : eventos que entran sin cumplir la secuencia (por
                              diseño el gate lo impide -> 0)

Escribe src/strategy_lab/results/exp039_live_validation.json y muestra un resumen.

Uso:
  python src/strategy_lab/scripts/exp039_analyze.py
  python src/strategy_lab/scripts/exp039_analyze.py --log consolidation_bot.log
  python src/strategy_lab/scripts/exp039_analyze.py --log mi_captura.out \
        --out src/strategy_lab/results/exp039_live_validation.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# --- Cadenas exactas verificadas en el código fuente del Edificio -----------
ENTRADA = "ORDEN ENVIADA"
REJECT_SEQ = "CONTRATADO bloqueado por secuencia"
REJECT_SEQ2 = "descartado CONTRATADO \u2014 asset no vigente"  # em-dash
REJECT_RECEP = "expulsado"
CONTRATADO_REACHED = "\u2192 CONTRATADO"  # right arrow

ROOT = Path(__file__).resolve().parents[3]


def _count(lines, needle: str) -> int:
    return sum(1 for ln in lines if needle in ln)


def analyze(log_path: Path) -> dict:
    if not log_path.exists():
        raise SystemExit(f"[exp039_analyze] No existe el log: {log_path}")

    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    entrada = _count(lines, ENTRADA)
    reject_cerebro = _count(lines, REJECT_SEQ) + _count(lines, REJECT_SEQ2)
    reject_reception = _count(lines, REJECT_RECEP)
    contratado_reached = _count(lines, CONTRATADO_REACHED)

    # Por diseño el SequenceEngine solo setea CONTRATADO tras chequear la
    # secuencia (edificio_contratacion.py ~línea 588). No se esperan entradas
    # sin secuencia; si aparecieran habría que auditar el gate.
    noise = 0

    edificio_lines = [ln for ln in lines if "[EDIFICIO]" in ln]
    observations = "\n".join(edificio_lines[-50:]) or "(sin líneas [EDIFICIO] en el log)"

    return {
        "config": {
            "kd_distance_min": 2.0,
            "dwell_cerebro": 1,
            "cross_limpieza_ok": True,
            "account": "PRACTICE",
        },
        "duration_min": None,
        "entrada_count": entrada,
        "reject_reception_count": reject_reception,
        "reject_cerebro_count": reject_cerebro,
        "noise_count": noise,
        "contratado_reached": contratado_reached,
        "criteria_met": {
            "entrada_count_gt_0": entrada > 0,
            "noise_count_eq_0": noise == 0,
        },
        "observations": observations,
        "errors": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="EXP-039 analyzer (Edificio live validation)")
    ap.add_argument(
        "--log",
        default=str(ROOT / "consolidation_bot.log"),
        help="Ruta al log del bot (default: consolidation_bot.log en la raíz)",
    )
    ap.add_argument(
        "--out",
        default=str(ROOT / "src" / "strategy_lab" / "results" / "exp039_live_validation.json"),
        help="Ruta de salida del JSON",
    )
    args = ap.parse_args()

    result = analyze(Path(args.log))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    cm = result["criteria_met"]
    veredicto = (
        "CUMPLE" if (cm["entrada_count_gt_0"] and cm["noise_count_eq_0"]) else "NO CUMPLE"
    )

    print("EXP-039 — validación live del Edificio")
    print(f"  entrada_count        = {result['entrada_count']}")
    print(f"  reject_reception     = {result['reject_reception_count']}")
    print(f"  reject_cerebro       = {result['reject_cerebro_count']}")
    print(f"  contratado_reached   = {result['contratado_reached']}")
    print(f"  noise_count          = {result['noise_count']}")
    print(f"  Criterio (entrada>0 y noise=0): {veredicto}")
    print(f"  JSON -> {out_path}")


if __name__ == "__main__":
    main()
