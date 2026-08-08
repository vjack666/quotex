"""POI dinamico con VIDA (nace/muere segun reglas forex).
Barrido causal forward: zonas nacen en pivote estructural, se validan por toques+rebote,
y MUEREN cuando el precio cierra decisivamente contra ellas (breakout).
Solo se cuentan retornos a zonas VIVAS. Itera hasta quedar ordenado.
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
OUT1 = ROOT/"reports/EXP-POI-STOCH/poi_dinamico_full.png"
OUT2 = ROOT/"reports/EXP-POI-STOCH/poi_dinamico_seq.png"

# ---- params (ajustables, iterar hasta ordenado) ----
SWING_K=8
MIN_TOUCH=3
TOL_ATR_MULT=0.5
BOUNCE_MIN=0.5
HOLD=3
KILL_BODY_MULT=0.6   # cierre contra zona con cuerpo >= este * ATR => muerte
LOOK=2000

# ---- cargar M1->M15 ----
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
tr=np.maximum.reduce([m_h-m_l, np.abs(m_h-np.roll(m_c,1)), np.abs(m_l-np.roll(m_c,1))])
atr=pd.Series(tr).rolling(14).mean().to_numpy()
atr_med=float(np.nanmedian(atr[14:]))
TOL=TOL_ATR_MULT*atr_med
print(f"[*] ATR_med={atr_med:.5f} TOL={TOL:.5f} ({TOL*1e4:.0f} pip)")

# ---- barrido causal con zonas vivas ----
zones=[]   # dict: level, dir(CALL soporte/PUT resist), birth, toques, bounces, alive, death
events=[]
for i in range(SWING_K, n15-SWING_K):
    # pivote de soporte (low minimo local) o resistencia (high maximo local)
    is_sup = (m_l[i]==m_l[i-SWING_K:i+SWING_K+1].min())
    is_res = (m_h[i]==m_h[i-SWING_K:i+SWING_K+1].max())
    # nacer zona si hay pivote y no hay zona activa cercana
    if is_sup or is_res:
        lvl = m_l[i] if is_sup else m_h[i]
        direction = "CALL" if is_sup else "PUT"
        near=[z for z in zones if z["alive"] and abs(z["level"]-lvl)<=TOL]
        if not near:
            # validar min_touches en ventana pasada
            seg_lo=max(0,i-LOOK); cnt=0
            for j in range(seg_lo,i):
                if direction=="CALL" and abs(m_l[j]-lvl)<=TOL: cnt+=1
                if direction=="PUT" and abs(m_h[j]-lvl)<=TOL: cnt+=1
            if cnt>=MIN_TOUCH:
                zones.append({"level":lvl,"dir":direction,"birth":i,"toques":cnt,"bounces":cnt,
                              "alive":True,"death":None})
    # actualizar zonas vivas: toque / rebote / muerte
    for z in zones:
        if not z["alive"]: continue
        lo=z["level"]-TOL; hi=z["level"]+TOL
        touched = (m_l[i]<=hi) and (m_h[i]>=lo)
        if touched:
            z["toques"]+=1
            # rebote = las HOLD velas siguientes no cierran contra
            seg_end=min(n15,i+1+HOLD)
            seg=m_c[i+1:seg_end]
            if len(seg)>0:
                if z["dir"]=="CALL":
                    broke=any(seg < (z["level"]-TOL))
                else:
                    broke=any(seg > (z["level"]+TOL))
                if not broke: z["bounces"]+=1
            # evento de retorno (solo si bounce_rate>=BOUNCE_MIN y no es el nacimiento)
            if i>z["birth"] and z["toques"]>0 and (z["bounces"]/z["toques"])>=BOUNCE_MIN:
                events.append(i)
        # MUERTE: cierre decisivo contra la zona (breakout)
        body=abs(m_c[i]-m_o[i])
        if z["dir"]=="CALL" and m_c[i] < (z["level"]-TOL) and body>=KILL_BODY_MULT*atr[i]:
            z["alive"]=False; z["death"]=i
        if z["dir"]=="PUT" and m_c[i] > (z["level"]+TOL) and body>=KILL_BODY_MULT*atr[i]:
            z["alive"]=False; z["death"]=i

alive_final=[z for z in zones if z["alive"]]
print(f"[*] zonas totales={len(zones)} vivas_al_final={len(alive_final)} eventos_retorno={len(events)}")

# ---- FIG 1 ----
fig,ax=plt.subplots(figsize=(20,7))
ax.plot(mt,m_c,color="#4a90d9",lw=0.7,label="close M15")
for z in zones:
    if z["death"] is None:
        d0=mt[z["birth"]]; d1=mt[-1]
    else:
        d0=mt[z["birth"]]; d1=mt[z["death"]]
    col="red" if z["alive"] else "gray"
    ax.hlines([z["level"]-TOL,z["level"]+TOL],d0,d1,color=col,lw=0.8,alpha=(0.7 if z["alive"] else 0.25))
ax.scatter([mt[i] for i in events],[m_c[i] for i in events],color="orange",s=12,label=f"retornos vivos ({len(events)})",zorder=5)
ax.set_title(f"POI DINAMICO (swing_k={SWING_K}, tol={TOL*1e4:.0f}pip, min_touch={MIN_TOUCH}, muere si cierre breakout) — EURUSD_otc M15")
ax.legend(loc="upper left",fontsize=8); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(OUT1,dpi=90); plt.close(fig)
print("[+] ",OUT1)

# ---- FIG 2 secuencia ----
if events:
    ei=events[len(events)//2]; a=max(0,ei-25); b=min(n15,ei+20)
    fig,ax=plt.subplots(figsize=(14,7))
    ax.plot(mt[a:b],m_c[a:b],color="#4a90d9",lw=1.0)
    for z in zones:
        if z["death"] is None: d0,d1=z["birth"],n15-1
        else: d0,d1=z["birth"],z["death"]
        if d0<=ei<=d1 or (a<=d0<=b) or (a<=d1<=b):
            col="red" if z["alive"] else "gray"
            ax.hlines([z["level"]-TOL,z["level"]+TOL],mt[max(a,d0)],mt[min(b,d1)],color=col,lw=1.0,alpha=0.8)
    ax.scatter([mt[ei]],[m_c[ei]],color="orange",s=80,marker="*",zorder=5,label=f"evento idx={ei}")
    ax.set_title(f"Secuencia 1 evento (POI dinamico) ventana {a}..{b}")
    ax.legend(loc="upper left",fontsize=8); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(OUT2,dpi=100); plt.close(fig)
    print("[+] ",OUT2)
