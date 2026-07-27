"""Backfill Fase B: regenera la DB completa corriendo Fase A + Fase B unificadas
(el observer actual graba episodes Fase A Y evolution+summary Fase B en la misma
pasada, con IDs coherentes). Chunking por ano para evitar bugs de escala y con
progreso visible. Idempotente por (asset, ts_open, source).
DB fresca (nombre nuevo para esquivar locks de corridas previas)."""
import sys, time, sqlite3
sys.path.insert(0, 'src')
from marketfeed.sources import ParquetSource
from marketfeed.replay import ReplayFeed
from observador.observer import Observador
from observador.store import EpisodeStore

DB = 'data/observador/episodes_eurusd_full.db'   # nombre canonical nuevo
SRC = 'C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw/EURUSD_M1.parquet'
YEARS = list(range(2012, 2027))
SRC_LABEL = 'observador_unified'

store = EpisodeStore(DB)
total_closed = 0
t0 = time.time()
for y in YEARS:
    s = f'{y}-01-01'; e = f'{y+1}-01-01'
    src = ParquetSource(SRC, start=s, end=e)
    feed = ReplayFeed([src], speed='MAX')
    obs = Observador(feed=feed, store=store, source_label=SRC_LABEL)
    res = obs.run()
    total_closed += res['episodes_closed']
    print(f"[{y}] events={res['events_consumed']} closed={res['episodes_closed']} open={res['episodes_open']} | acum={total_closed} | {time.time()-t0:.1f}s", flush=True)
dt = time.time() - t0
print(f"BACKFILL_FASE_B DONE: total_closed={total_closed} time={dt:.1f}s")
c = sqlite3.connect(DB)
print(f"episodes={c.execute('SELECT COUNT(*) FROM episodes').fetchone()[0]} evolution_rows={c.execute('SELECT COUNT(*) FROM episode_evolution').fetchone()[0]} summaries={c.execute('SELECT COUNT(*) FROM episode_summary').fetchone()[0]}")
