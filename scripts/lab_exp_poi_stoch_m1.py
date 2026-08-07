"""EXP-POI-STOCH M1 — busca los patrones sobre data M1 (no solo M15).
Usa el parquet de eventos M15 y expande a ventanas M1; ademas detecta
patron POI+estocastico directamente en M1.
"""
import sys, csv, json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"C:\Users\v_jac\Desktop\QUOTEX")
CSV = ROOT / "tools/quotex-historical-data/EURUSD_otc_60s_365days.csv"
PARQ = ROOT / "data/strategy_lab/exp_poi_stoch_events.parquet"
OUT = ROOT / "reports/EXP-POI-STOCH/m1_analysis.txt"

# ---- cargar M1 ----
ts, o, h, l, c = [], [], [], [], []
with open(CSV) as f:
    for r in csv.DictReader(f):
        ts.append(int(r["timestamp"])); o.append(float(r["open"]))
        h.append(float(r["high"])); l.append(float(r["low"])); c.append(float(r["close"]))
ts=np.array(ts); o=np.array(o); h=np.array(h); l=np.array(l); c=np.array(c)
n=len(c)
print(f"[*] M1 velas: {n}")

# estocastico M1 (14,3,3)
def stoch(hi,lo,cl,k=14,d=3,s=3):
    N=len(cl); raw=np.full(N,np.nan); kk=np.full(N,np.nan); dd=np.full(N,np.nan)
    for i in range(k-1,N):
        ll=lo[i-k+1:i+1].min(); hh=hi[i-k+1:i+1].max()
        raw[i]=100*(cl[i]-ll)/(hh-ll) if hh>ll else 50.0
    for i in range(k-1,N): kk[i]=np.nanmean(raw[i-s+1:i+1])
    for i in range(k-1+d-1,N): dd[i]=np.nanmean(kk[i-d+1:i+1])
    return kk,dd
K,D=stoch(h,l,c); kd=np.abs(K-D)

ev=pd.read_parquet(PARQ)
print(f"[*] eventos M15 cargados: {len(ev)}")

lines=[]
lines.append("="*60+"\nEXP-POI-STOCH M1 ANALYSIS\n"+"="*60)
lines.append(f"M1 velas={n} | eventos M15={len(ev)}\n")

# ---- (A) expandir cada evento M15 a 15 velas M1, mirar estocastico M1 en el open ----
# mapear idx M15 -> rango M1: idx*15 .. idx*15+14
rows_m1=[]
for _,e in ev.iterrows():
    i15=int(e["idx"])
    a=i15*15; b=a+15
    if b+2>=n: continue
    # estocastico M1 en el open de la ventana (equivale a open M15)
    km=K[a]; dm=D[a]; sepm=kd[a]
    # siguiente vela M1 despues del open: retrace?
    next_retrace_m1 = (c[a+1]-c[a]) * (1 if km>50 else -1) < 0
    rows_m1.append({"idx15":i15,"K_m1":km,"D_m1":dm,"kd_m1":sepm,
                    "next_retrace_m1":int(next_retrace_m1),"eff":e["eff"],
                    "clean8":e["clean8"]})
m1=pd.DataFrame(rows_m1)
lines.append(f"Ventanas M1 expandidas: {len(m1)}\n")

# estocastico M1 "muy separado" -> retrace next M1 vela?
for thr in [20,25,30]:
    m=(m1["kd_m1"]>=thr)
    if m.sum()==0:
        lines.append(f"[M1] |K-D|_m1>={thr}: SIN eventos\n"); continue
    rate=m1[m]["next_retrace_m1"].mean(); base=m1["next_retrace_m1"].mean()
    lines.append(f"[M1] |K-D|_m1>={thr}: n={m.sum()} retrace_next_m1={rate:.3f} vs base={base:.3f} diff={rate-base:+.3f}\n")

# ---- (B) deteccion directa POI en M1: swing levels M1 + retorno + estocastico M1 ----
# reusar swing_levels_causal sobre M1 (costoso pero n=76k; lo acotamos a ventanas)
sys.path.insert(0,str(ROOT/"src"))
from strategy_lab.poi_behavior import swing_levels_causal
fl,ce,af,at=swing_levels_causal(h,l,min_touches=2,tol_pips=2.0,swing_k=3,lookback=400)
print(f"[*] POIs M1: {fl.size}")
ev_m1=[]
for k_ in range(fl.size):
    a0,b0=int(af[k_]),int(at[k_])
    if a0>=b0: continue
    center=(fl[k_]+ce[k_])/2
    seg=slice(a0,b0)
    hit=np.flatnonzero((l[seg]<=ce[k_])&(h[seg]>=fl[k_]))
    if hit.size==0: continue
    for j in hit:
        i=a0+j
        if i<60 or i+5>=n: continue
        pc=c[i-1]
        if not(pc>ce[k_] or pc<fl[k_]): continue
        sepm=kd[i]
        # retrace next M1 vela en direccion opuesta al sesgo estocastico
        bias=1 if K[i]>50 else -1
        nr=((c[i+1]-c[i])*bias)<0
        ev_m1.append({"idx":i,"level":center,"kd_m1":sepm,"next_retrace":int(nr)})
em=pd.DataFrame(ev_m1)
lines.append(f"\nEventos POI M1 directos: {len(em)}\n")
if len(em)>0:
    for thr in [20,25,30]:
        m=(em["kd_m1"]>=thr)
        if m.sum()==0:
            lines.append(f"[M1-direct] |K-D|>={thr}: SIN eventos\n"); continue
        rate=em[m]["next_retrace"].mean(); base=em["next_retrace"].mean()
        lines.append(f"[M1-direct] |K-D|>={thr}: n={m.sum()} retrace={rate:.3f} vs base={base:.3f} diff={rate-base:+.3f}\n")

OUT.write_text("\n".join(lines))
print("[+] M1 analysis ->", OUT)
print("\n".join(lines))
