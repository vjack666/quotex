"""CLI para el Entry Intelligence Agent (Feature 18) auto-retrain.

Uso:
    python scripts/entry_intelligence_retrain.py            # decide segun umbral
    python scripts/entry_intelligence_retrain.py --force     # entrena aunque no haya 100 nuevos
    python scripts/entry_intelligence_retrain.py --status    # muestra estado sin entrenar

El modulo real esta en src/entry_intelligence.py (para que el bot pueda
importarlo y dispararlo en segundo plano desde black_box_recorder).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Asegurar import de src/ y scripts/
ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> int:
    ap = argparse.ArgumentParser(description="Entry Intelligence Agent retrain")
    ap.add_argument("--force", action="store_true", help="ignorar umbral de trades nuevos")
    ap.add_argument("--status", action="store_true", help="solo mostrar estado")
    ap.add_argument("--verbose", action="store_true", help="logs del entrenamiento")
    args = ap.parse_args()

    import entry_intelligence as ei  # noqa: E402

    if args.status:
        state = ei._load_state()
        dbs = ei.discover_databases()
        new = ei.count_new_resolved_trades(dbs, float(state.get("last_ts", 0.0)))
        print(json.dumps({
            "model_path": str(ei.MODEL_PATH),
            "model_exists": ei.MODEL_PATH.exists(),
            "last_retrain": state,
            "databases": dbs,
            "new_resolved_trades": new,
            "retrigger_threshold": ei.RETRAIN_MIN_NEW,
        }, indent=2, default=str))
        return 0

    quiet = not args.verbose
    out = ei.maybe_retrain(force=args.force, quiet=quiet)
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
