"""POI humanizado v1: parametros de calidad (no los laxos del EXP).
swing_k=8, tol=0.5*ATR(14), min_touches=3, bounce_rate>=0.5, lookback=2000.
Redibuja poi_full_events + secuencia, y reporta niveles/eventos (debe bajar el ruido).
"""
import sys, csv
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"C:\Users\v_jac\Desktop\QUOTEX")
CSV = ROOT/"tools/quotex-historical-data/EURUSD_otc_60s_365days.csv"
OUT1 = ROOT/"reports/EXP-POI-STOCH/poi_humanizado_full.png"
OUT2 = ROOT/"reports/EXP-POI-STOCH/poi_humanizado_seq.png"

ts,o,h,l,c=[],[],[],[],[]
with open(CSV) as f:
    for r in csv.DictReader(f):
        ts.append(int(r["timestamp"]));o.append(float(r["open"]))
        h.append(float(r["high"]));l.append(float(r["low"]));c.append(float(r["close"]))
ts=np.array(ts);o=np.array(o);h=np.array(h);l=np.array(l);c=np.array(c)
step=15; n15=len(ts)//step
m_ts=ts[:n15*step].reshape(n15,step)[:,0]
m_o=o[:n15*step].reshape(n15,step)[:,0]
m_c=c[:n15*step].reshape(n15,step)[:,-1]
m_h=h[:n15*step].reshape(n15,step).max(1)
m_l=l[:n15*step].reshape(n15,step).min(1)
t0=pd.Timestamp(m_ts[0],unit="s"); mt=[t0+pd.Timedelta(minutes=15*i) for i in range(n15)]

# ATR(14) M15
tr=np.maximum.reduce([m_h-m_l, np.abs(m_h-np.roll(m_c,1)), np.abs(m_l-np.roll(m_c,1))])
atr=pd.Series(tr).rolling(14).mean().to_numpy()
atr_med=float(np.nanmedian(atr[14:]))

sys.path.insert(0,str(ROOT/"src"))
from strategy_lab.poi_behavior import swing_levels_causal
from zone_strength import compute_support_efficacy
class C:
    def __init__(s,o,h,l,c): s.open=o; s.high=h; s.low=l; s.close=c
candles=[C(m_o[i],m_h[i],m_l[i],m_c[i]) for i in range(n15)]

# --- POI humanizado v1 ---
SWING_K=8; TOL=0.5*atr_med; MIN_TOUCH=3; LOOK=2000; BOUNCE_MIN=0.5
fl,ce,af,at=swing_levels_causal(m_h,m_l,min_touches=MIN_TOUCH,tol_pips=TOL*1e4/ (m_c[0]) * (m_c[0]) ,swing_k=SWING_K,lookback=LOOK)
# nota: swing_levels_causal usa tol_pips en pips absolutos; convertimos TOL (precio) a pips
pip_TOL = TOL*1e4  # EURUSD: 1 pip = 1e-4
fl,ce,af,at=swing_levels_causal(m_h,m_l,min_touches=MIN_TOUCH,tol_pips=pip_TOL,swing_k=SWING_K,lookback=LOOK)
print(f"[*] POI humanizado: niveles={fl.size} (ATR_med={atr_med:.5f}, tol_pips={pip_TOL:.1f})")

# eventos con bounce_rate>=0.5
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
        seg=candles[max(0,i-LOOK):i]
        eff=compute_support_efficacy(center,seg,direction=direction,band_pct=0.0008,hold_candles=3)
        if eff.get("efficacy",0.0)<BOUNCE_MIN: continue
        events.append(i)
print(f"[*] eventos retorno (bounce>=0.5): {len(events)}")

fig,ax=plt.subplots(figsize=(20,7))
ax.plot(mt,m_c,color="#4a90d9",lw=0.7,label="close M15")
for k_ in range(fl.size):
    a0,b0=int(af[k_]),int(at[k_])
    if a0>=b0: continue
    ax.hlines([fl[k_],ce[k_]],mt[a0],mt[b0],color="red",lw=0.8,alpha=0.6)
ax.scatter([mt[i] for i in events],[m_c[i] for i in events],color="orange",s=14,label=f"retornos ({len(events)})",zorder=5)
ax.set_title(f"POI HUMANIZADO v1 (swing_k={SWING_K}, tol={pip_TOL:.0f}pip=0.5ATR, min_touch={MIN_TOUCH}, bounce>=0.5) — EURUSD_otc M15")
ax.legend(loc="upper left",fontsize=8); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(OUT1,dpi=90); plt.close(fig)
print("[+] ",OUT1)

if events:
    ei=events[0]; a=max(0,ei-20); b=min(n15,ei+15)
    fig,ax=plt.subplots(figsize=(14,7))
    ax.plot(mt[a:b],m_c[a:b],color="#4a90d9",lw=1.0)
    for k_ in range(fl.size):
        a0,b0=int(af[k_]),int(at[k_])
        if a0>=b0: continue
        if a0<=ei<=b0: ax.hlines([fl[k_],ce[k_]],mt[max(a,a0)],mt[min(b,b0)],color="red",lw=1.0)
    ax.scatter([mt[ei]],[m_c[ei]],color="orange",s=80,marker="*",zorder=5,label=f"evento idx={ei}")
    ax.set_title(f"Secuencia 1 evento (POI humanizado) ventana {a}..{b}")
    ax.legend(loc="upper left",fontsize=8); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(OUT2,dpi=100); plt.close(fig)
    print("[+] ",OUT2)
