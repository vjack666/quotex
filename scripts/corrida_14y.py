"""Corrida grande: 14 años de EURUSD M1 por el Observador, año por año.

Escribe data/observador/episodes_eurusd_14y.db (idempotente: re-correr no duplica).
Uso: PYTHONPATH=src python scripts/corrida_14y.py
"""
import sys
import time

from marketfeed.replay import ReplayFeed
from marketfeed.sources import ParquetSource
from observador.observer import Observador
from observador.store import EpisodeStore

PARQUET = r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\EURUSD_M1.parquet"
DB = "data/observador/episodes_eurusd_14y.db"

t0 = time.time()
store = EpisodeStore(DB)
total_ev = total_ep = 0
for year in range(2012, 2027):
    ty = time.time()
    src = ParquetSource(PARQUET, start=f"{year}-01-01", end=f"{year + 1}-01-01")
    feed = ReplayFeed([src], speed="MAX")
    res = Observador(feed, store).run()
    total_ev += res["events_consumed"]
    total_ep += res["episodes_closed"]
    print(f"{year}: {res['events_consumed']:>7} eventos, {res['episodes_closed']:>5} episodios, "
          f"{time.time() - ty:5.1f}s (acum: {total_ep} ep)", flush=True)

print(f"\nTOTAL: {total_ev} eventos, {total_ep} episodios en {(time.time() - t0) / 60:.1f} min")
print(f"DB: {DB}")
sys.exit(0)
