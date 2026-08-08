"""Grafica POI como se calculo en EXP-POI-STOCH + marca todos los eventos + zoom a 1 secuencia.
Datos: EURUSD_otc M1->M15. Usa swing_levels_causal (mismos params del EXP) y detecta retornos.
"""
import sys, csv
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"C:\Users\v_jac\Desktop\QUOTEX")
CSV = ROOT / "tools/quotex-historical-data/EURUSD_otc_60s_365days.csv"
OUT1 = ROOT/"reports/EXP-POI-STOCH/poi_full_events.png"
OUT2 = ROOT/"reports/EXP-POI-STOCH/poi_sequence_example.png"

# ---- M1 -> M15 ----
ts,o,h,l,c=[],[],[],[],[]
with open(CSV) as f:
    for r in csv.DictReader(f):
        ts.append(int(r["timestamp"]));o.append(float(r["open"]))
        h.append(float(r["high"]));l.append(float(r["low"]));c.append(float(r["close"]))
ts=np.array(ts);o=np.array(o);h=np.array(h);l=np.array(l);c=np.array(c)
step=15; n15=len(ts)//step
m_ts=ts[:n15*step].reshape(n15,step)[:,0]
m_o=o[:n15*step].reshape(n15,step)[:,0]
m_c=c[:n15*step].reshape(n15,step)[:, -1]
m_h=h[:n15*step].reshape(n15,step).max(1)
m_l=l[:n15*step].reshape(n15,step).min(1)
t0=pd.Timestamp(m_ts[0], unit="s")
mt=[t0+pd.Timedelta(minutes=15*i) for i in range(n15)]

sys.path.insert(0,str(ROOT/"src"))
from strategy_lab.poi_behavior import swing_levels_causal
fl,ce,af,at=swing_levels_causal(m_h,m_l,min_touches=2,tol_pips=5.0,swing_k=2,lookback=200)
print(f"[*] POIs={fl.size}")

# estocastico
def stoch(hi,lo,cl,k=14,d=3,s=3):
    N=len(cl);raw=np.full(N,np.nan);kk=np.full(N,np.nan);dd=np.full(N,np.nan)
    for i in range(k-1,N):
        ll=lo[i-k+1:i+1].min();hh=hi[i-k+1:i+1].max()
        raw[i]=100*(cl[i]-ll)/(hh-ll) if hh>ll else 50.0
    for i in range(k-1,N): kk[i]=np.nanmean(raw[i-s+1:i+1])
    for i in range(k-1+d-1,N): dd[i]=np.nanmean(kk[i-d+1:i+1])
    return kk,dd
K,D=stoch(m_h,m_l,m_c); kd=np.abs(K-D)

# eventos de retorno (misma logica del EXP: toque banda + eficacia minima)
from zone_strength import compute_support_efficacy
class C:
    def __init__(s,o,h,l,c): s.open=o; s.high=h; s.low=l; s.close=c
candles=[C(m_o[i],m_h[i],m_l[i],m_c[i]) for i in range(n15)]
events=[]
for k_ in range(fl.size):
    a0,b0=int(af[k_]),int(at[k_])
    if a0>=b0: continue
    center=(fl[k_]+ce[k_])/2
    hit=np.flatnonzero((m_l[a0:b0]<=ce[k_])&(m_h[a0:b0]>=fl[k_]))
    for j in hit:
        i=a0+j
        if i<30 or i+9>=n15: continue
        pc=m_c[i-1]
        if not(pc>ce[k_] or pc<fl[k_]): continue
        direction="CALL" if pc>ce[k_] else "PUT"
        seg=candles[max(0,i-288):i]
        eff=compute_support_efficacy(center,seg,direction=direction,band_pct=0.0008,hold_candles=3)
        if eff.get("efficacy",0.0)<0.35: continue
        events.append(i)
print(f"[*] eventos retorno: {len(events)}")

# ---- FIG 1: vista completa ----
fig,ax=plt.subplots(figsize=(20,7))
ax.plot(mt,m_c,color="#4a90d9",lw=0.7,label="close M15")
for k_ in range(fl.size):
    a0,b0=int(af[k_]),int(at[k_])
    if a0>=b0: continue
    ax.hlines([fl[k_],ce[k_]],mt[a0],mt[b0],color="red",lw=0.6,alpha=0.5)
ax.scatter([mt[i] for i in events],[m_c[i] for i in events],color="orange",s=12,label=f"retornos ({len(events)})",zorder=5)
ax.set_title("POI (swing_levels_causal min_touches=2,tol=5,swing_k=2,lookback=200) + retornos — EURUSD_otc M15")
ax.legend(loc="upper left",fontsize=8)
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(OUT1,dpi=90); plt.close(fig)
print("[+] ",OUT1)

# ---- FIG 2: zoom a 1 secuencia (primer evento) ----
if events:
    ei=events[0]
    a=max(0,ei-20); b=min(n15,ei+15)
    fig,ax=plt.subplots(figsize=(14,7))
    ax.plot(mt[a:b],m_c[a:b],color="#4a90d9",lw=1.0)
    # zonas que cubren el evento
    for k_ in range(fl.size):
        a0,b0=int(af[k_]),int(at[k_])
        if a0>=b0: continue
        if a0<=ei<=b0:
            ax.hlines([fl[k_],ce[k_]],mt[max(a,a0)],mt[min(b,b0)],color="red",lw=1.0)
    ax.scatter([mt[ei]],[m_c[ei]],color="orange",s=80,marker="*",zorder=5,label=f"evento idx={ei}")
    ax.annotate("entrada open M15",(mt[ei],m_c[ei]),xytext=(8,-22),textcoords="offset points",fontsize=9,color="orange")
    # estocastico abajo
    ax2=ax.twinx(); ax2.plot(mt[a:b],K[a:b],color="teal",lw=0.8,label="K")
    ax2.plot(mt[a:b],D[a:b],color="purple",lw=0.8,label="D")
    ax2.set_ylabel("stochastic",color="gray"); ax2.tick_params(axis='y',colors="gray")
    ax.set_title(f"Secuencia de 1 evento (EURUSD_otc M15, ventana {a}..{b})")
    ax.legend(loc="upper left",fontsize=8); ax2.legend(loc="upper right",fontsize=8)
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(OUT2,dpi=100); plt.close(fig)
    print("[+] ",OUT2)
