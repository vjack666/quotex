"""Check enfocado: para evento idx dado, direccion + resultado a H=1..5 velas M15.
Reusa la misma deteccion POI dinamico que lab_poi_dinamico.py.
"""
import sys, csv
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"C:\Users\v_jac\Desktop\QUOTEX")
CSV = ROOT/"tools/quotex-historical-data/EURUSD_otc_60s_365days.csv"
SWING_K=8; MIN_TOUCH=3; TOL_ATR_MULT=0.5; BOUNCE_MIN=0.5; HOLD=3; KILL_BODY_MULT=0.6; LOOK=2000

ts,o,h,l,c=[],[],[],[],[]
with open(CSV) as f:
    for r in csv.DictReader(f):
        ts.append(int(r["timestamp"]));o.append(float(r["open"]))
        h.append(float(r["high"]));l.append(float(r["low"]));c.append(float(r["close"]))
ts=np.array(ts);o=np.array(o);h=np.array(h);l=np.array(l);c=np.array(c)
step=15; n15=len(ts)//step
m_o=o[:n15*step].reshape(n15,step)[:,0]
m_c=c[:n15*step].reshape(n15,step)[:,-1]
m_h=h[:n15*step].reshape(n15,step).max(1)
m_l=l[:n15*step].reshape(n15,step).min(1)
tr=np.maximum.reduce([m_h-m_l, np.abs(m_h-np.roll(m_c,1)), np.abs(m_l-np.roll(m_c,1))])
atr=pd.Series(tr).rolling(14).mean().to_numpy()
atr_med=float(np.nanmedian(atr[14:])); TOL=TOL_ATR_MULT*atr_med

TARGET=int(sys.argv[1]) if len(sys.argv)>1 else 2609
zones=[]; events=[]  # events: (idx, dir, level)
for i in range(SWING_K, n15-SWING_K):
    is_sup = (m_l[i]==m_l[i-SWING_K:i+SWING_K+1].min())
    is_res = (m_h[i]==m_h[i-SWING_K:i+SWING_K+1].max())
    if is_sup or is_res:
        lvl = m_l[i] if is_sup else m_h[i]; direction = "CALL" if is_sup else "PUT"
        near=[z for z in zones if z["alive"] and abs(z["level"]-lvl)<=TOL]
        if not near:
            seg_lo=max(0,i-LOOK); cnt=0
            for j in range(seg_lo,i):
                if direction=="CALL" and abs(m_l[j]-lvl)<=TOL: cnt+=1
                if direction=="PUT" and abs(m_h[j]-lvl)<=TOL: cnt+=1
            if cnt>=MIN_TOUCH:
                zones.append({"level":lvl,"dir":direction,"birth":i,"toques":cnt,"bounces":cnt,"alive":True,"death":None})
    for z in zones:
        if not z["alive"]: continue
        lo=z["level"]-TOL; hi=z["level"]+TOL
        if (m_l[i]<=hi) and (m_h[i]>=lo):
            z["toques"]+=1
            seg_end=min(n15,i+1+HOLD); seg=m_c[i+1:seg_end]
            if len(seg)>0:
                broke = (z["dir"]=="CALL" and any(seg<(z["level"]-TOL))) or (z["dir"]=="PUT" and any(seg>(z["level"]+TOL)))
                if not broke: z["bounces"]+=1
            if i>z["birth"] and z["toques"]>0 and (z["bounces"]/z["toques"])>=BOUNCE_MIN:
                events.append((i,z["dir"],z["level"]))
        body=abs(m_c[i]-m_o[i])
        if z["dir"]=="CALL" and m_c[i]<(z["level"]-TOL) and body>=KILL_BODY_MULT*atr[i]: z["alive"]=False; z["death"]=i
        if z["dir"]=="PUT" and m_c[i]>(z["level"]+TOL) and body>=KILL_BODY_MULT*atr[i]: z["alive"]=False; z["death"]=i

ev=[e for e in events if e[0]==TARGET]
if not ev:
    print(f"[!] evento {TARGET} no encontrado entre {len(events)} eventos. Rango idx: {events[0][0]}..{events[-1][0]}")
    sys.exit()
idx,dirn,lvl=ev[0]
entry=m_o[idx]
print(f"=== EVENTO idx={idx} ===")
print(f"direccion={dirn}  zona_nivel={lvl:.5f}  banda=[{lvl-TOL:.5f},{lvl+TOL:.5f}]")
print(f"entrada (open M15 idx)={entry:.5f}  close prev={m_c[idx-1]:.5f}")
print(f"{'H':>3} {'close_H':>10} {'ret_pips':>10} {'WIN?':>6}")
for H in range(1,6):
    if idx+H>=n15: break
    cl=m_c[idx+H]; ret=(cl-entry)*1e4*(1 if dirn=="CALL" else -1)
    win = (cl>entry) if dirn=="CALL" else (cl<entry)
    print(f"{H:>3} {cl:.5f} {ret:+10.1f} {('GANA' if win else 'PIERDE'):>6}")
