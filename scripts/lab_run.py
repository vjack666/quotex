"""CLI único del laboratorio: `lab run EXP-XXX`.

Orquesta un experimento de forma reproducible (Art. 5 Charter) sin
intervención manual. Lee el manifest del dataset, congela el protocolo
(Art. 6) y delega en strategy_lab.experiment_runner.run_experiment.

Uso:
    python scripts/lab_run.py EXP-039 --dataset datasets/dataset_v001/manifest.json \
        --seed 42 --protocol '{"domain":"REAL","alpha":0.05}' --report-dir reports
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


def _load_protocol(args) -> dict:
    protocol: Dict[str, Any] = {"domain": "REAL"}
    if args.protocol:
        protocol.update(json.loads(args.protocol))
    protocol["alpha"] = protocol.get("alpha", 0.05)
    protocol["seed"] = args.seed
    return protocol


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="lab", description="Laboratorio científico reproducible")
    sub = ap.add_subparsers(dest="cmd", required=True)

    runp = sub.add_parser("run", help="Ejecuta un experimento")
    runp.add_argument("experiment_id", help="EXP-XXX")
    runp.add_argument("--dataset", required=True, help="ruta al manifest.json del dataset versionado")
    runp.add_argument("--seed", type=int, default=42, help="semilla fija para reproducibilidad")
    runp.add_argument("--protocol", default=None, help='JSON del protocolo congelado (Art. 6)')
    runp.add_argument("--report-dir", default="reports", help="directorio base de reportes inmutables")
    runp.add_argument("--hypothesis", default=None)

    args = ap.parse_args(argv)
    if args.cmd != "run":
        ap.error("solo se soporta 'lab run'")

    from strategy_lab.experiment_runner import run_experiment

    manifest = Path(args.dataset)
    if not manifest.exists():
        print(f"[lab] ERROR: manifest no encontrado: {manifest}", file=sys.stderr)
        return 2

    # Cargar eventos del dataset referenciado (SMC_ROOT) — sin copiar.
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    source_root = Path(manifest_data.get("source_root", ""))
    primary = next((f for f in manifest_data["files"] if f.get("role") == "primary"), None)
    if primary is None:
        print("[lab] ERROR: manifest sin archivo primary", file=sys.stderr)
        return 2

    import pandas as pd

    parquet = source_root / primary["name"]
    if not parquet.exists():
        print(f"[lab] ERROR: dataset primario no encontrado: {parquet}", file=sys.stderr)
        return 2
    events = pd.read_parquet(parquet)

    protocol = _load_protocol(args)
    artifacts = run_experiment(
        args.experiment_id,
        events,
        hypothesis=args.hypothesis,
        seed=args.seed,
        dataset_manifest=str(manifest),
        protocol=protocol,
        report_dir=Path(args.report_dir),
    )
    print(f"[lab] EXP={artifacts.experiment_id} verdict={artifacts.gate_decision.verdict if artifacts.gate_decision else 'n/a'}")
    print(f"[lab] report={artifacts.report_path}")
    print(f"[lab] seed={artifacts.seed} dataset_hash={artifacts.dataset_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
