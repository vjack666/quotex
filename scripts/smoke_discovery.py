"""Smoke E2E del Discovery Engine (T10): corre el motor sobre la DB poblada y
emite >=1 Ley #N con walk-forward y p<corte, guardada en tabla 'leyes'.

Uso (desde la raiz del repo):
  PYTHONPATH=src .venv/Scripts/python.exe scripts/smoke_discovery.py
"""

from __future__ import annotations

import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from discovery.config_loader import load_config  # noqa: E402
from discovery.reader import load_episodes, classify_source  # noqa: E402
from discovery.miner import discover  # noqa: E402
from discovery.law_store import SQLiteLawStore  # noqa: E402
from discovery.reporter import emit_lab_doc, record_law, slugify  # noqa: E402

DB = os.path.join(ROOT, "data", "observador", "episodes_eurusd_14y.db")
LAWS_DB = os.path.join(ROOT, "data", "observador", "discovery_laws.db")


def main() -> int:
    cfg = load_config()
    # Slice del Atlas. Cargamos desde el inicio (2012+) donde hay casos de
    # todas las curve_shape; luego fijamos split_year al ANO MEDIO del slice
    # para que walk-forward SIEMPRE cruce train/test (regla: jamas test vacio).
    offset = int(os.environ.get("DISCOVERY_OFFSET", "0"))
    limit = int(os.environ.get("DISCOVERY_LIMIT", "40000"))
    episodes = list(load_episodes(DB, asset="EURUSD", limit=limit, offset=offset))
    print(f"[smoke] episodios cargados: {len(episodes)}")

    # split_year dinámico = año medio del slice (garantiza train+test poblados).
    import datetime as _dt
    mid_ts = sum(e.ts_open for e in episodes) / max(len(episodes), 1)
    mid_year = _dt.datetime.fromtimestamp(mid_ts, _dt.timezone.utc).year
    cfg = dict(cfg, split_year=mid_year)
    print(f"[smoke] split_year dinamico = {mid_year}")

    assert episodes, "No se cargaron episodios del Atlas"

    conn = sqlite3.connect(LAWS_DB)
    conn.row_factory = sqlite3.Row
    store = SQLiteLawStore(conn)
    laws = discover(episodes, cfg, store)

    print(f"[smoke] Leyes #N descubiertas: {len(laws)}")
    docs_dir = os.path.join(ROOT, "docs")
    for law in laws:
        record_law(law, store)
        lab_path = os.path.join(docs_dir, f"LAB_{law.id.lstrip('#').zfill(3)}_{slugify(law.name)}.md")
        emit_lab_doc(law, lab_path)
        print(f"  {law.id} | {law.name} | prob={law.probability:.3f} | "
              f"state={law.state} | markets={law.markets} | sources={law.sources}")

    conn.commit()
    conn.close()

    if not laws:
        print("[smoke] FALLO: 0 leyes descubiertas")
        return 1
    print(f"[smoke] OK: {len(laws)} ley(es) en tabla 'leyes'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
