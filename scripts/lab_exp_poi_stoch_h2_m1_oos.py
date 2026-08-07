"""EXP-POI-STOCH H2 M1 OOS — tabla con IC.
H2: POI M1 + |K-D|>=25 -> retrace next M1 vela.
Split temporal 70/30 por evento. Reporta tasas, IC95% Wilson, baseline,
OR + IC95% bootstrap, p (chi2). Veredicto por protocolo. Sin tocar umbrales.
"""
import sys, csv, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(r"C:\Users\v_jac\Desktop\QUOTEX")
CSV = ROOT / "tools/quotex-historical-data/EURUSD_otc_60s_365days.csv"
OUT = ROOT / "reports/EXP-POI-STOCH/h2_m1_oos.txt"
KD_THR = 25.0
SEED = 42
np.random.seed(SEED)

# ---- cargar M1 ----
ts,o,h,l,c=[],[],[],[],[]
with open(CSV) as f:
    for r in csv.DictReader(f):
        ts.append(int(r["timestamp"]));o.append(float(r["open"]))
        h.append(float(r["high"]));l.append(float(r["low"]));c.append(float(r["close"]))
ts=np.array(ts);o=np.array(o);h=np.array(h);l=np.array(l);c=np.array(c);n=len(c)

def stoch(hi,lo,cl,k=14,d=3,s=3):
    N=len(cl);raw=np.full(N,np.nan);kk=np.full(N,np.nan);dd=np.full(N,np.nan)
    for i in range(k-1,N):
        ll=lo[i-k+1:i+1].min();hh=hi[i-k+1:i+1].max()
        raw[i]=100*(cl[i]-ll)/(hh-ll) if hh>ll else 50.0
    for i in range(k-1,N): kk[i]=np.nanmean(raw[i-s+1:i+1])
    for i in range(k-1+d-1,N): dd[i]=np.nanmean(kk[i-d+1:i+1])
    return kk,dd
K,D=stoch(h,l,c);kd=np.abs(K-D)

sys.path.insert(0,str(ROOT/"src"))
from strategy_lab.poi_behavior import swing_levels_causal
print("[*] swing M1...", flush=True)
fl,ce,af,at=swing_levels_causal(h,l,min_touches=2,tol_pips=2.0,swing_k=3,lookback=400)

ev=[]
for k_ in range(fl.size):
    a0,b0=int(af[k_]),int(at[k_])
    if a0>=b0: continue
    center=(fl[k_]+ce[k_])/2
    hit=np.flatnonzero((l[a0:b0]<=ce[k_])&(h[a0:b0]>=fl[k_]))
    for j in hit:
        i=a0+j
        if i<60 or i+2>=n: continue
        pc=c[i-1]
        if not(pc>ce[k_] or pc<fl[k_]): continue
        sepm=kd[i]
        bias=1 if K[i]>50 else -1
        nr=int(((c[i+1]-c[i])*bias)<0)
        ev.append({"idx":i,"level":center,"kd_m1":sepm,"next_retrace":nr})
ev=pd.DataFrame(ev).sort_values("idx").reset_index(drop=True)
ev["excess"]=(ev["kd_m1"]>=KD_THR).astype(int)

def wilson(k, nn, z=1.96):
    if nn==0: return (float('nan'),float('nan'))
    p=k/nn; den=1+z*z/nn
    ctr=(p+z*z/(2*nn))/den
    half=z*np.sqrt(p*(1-p)/nn+z*z/(4*nn*nn))/den
    return (ctr-half, ctr+half)

def boot_or(a,b,cc,d, B=2000):
    arr=np.concatenate([np.ones(a),np.zeros(b),np.ones(cc),np.zeros(d)]).astype(int)
    # a=exc_retrace, b=exc_noret; cc=rest_retrace, d=rest_noret
    grp=np.r_[np.zeros(a+b),np.ones(cc+d)]
    y=np.r_[np.ones(a),np.zeros(b),np.ones(cc),np.zeros(d)]
    ors=[]
    idx=np.arange(len(y))
    for _ in range(B):
        s=np.random.choice(idx,len(idx),replace=True)
        ya=y[s]; ga=grp[s]
        exc=ya[ga==0]; rest=ya[ga==1]
        ar=exc.sum(); br=len(exc)-ar; cr=rest.sum(); dr=len(rest)-cr
        if br*cr==0: continue
        ors.append((ar*dr)/(br*cr))
    ors=np.array(ors)
    return (np.percentile(ors,2.5), np.percentile(ors,97.5))

cut=int(len(ev)*0.70)
tr=ev.iloc[:cut]; te=ev.iloc[cut:]
lines=[]
lines.append("="*64+"\nEXP-POI-STOCH H2 M1 — OOS (POI + |K-D|>=25 -> retrace next M1)\n"+"="*64)
lines.append(f"M1 velas={n} | eventos POI M1={len(ev)} | KD_THR={KD_THR} | seed={SEED}\n")
lines.append(f"TRAIN={len(tr)} TEST={len(te)} (split temporal 70/30 por evento)\n")

def block(df,label):
    m=df["excess"]==1; nm=~m
    a=int(df[m]["next_retrace"].sum()); b=int(m.sum()-a)
    cc=int(df[nm]["next_retrace"].sum()); d=int(nm.sum()-cc)
    nn=a+b; nrest=cc+d
    rg=a/nn if nn else float('nan'); rr=cc/nrest if nrest else float('nan')
    diff=rg-rr
    lo_rg,hi_rg=wilson(a,nn); lo_rr,hi_rr=wilson(cc,nrest)
    tab=np.array([[a,b],[cc,d]])
    chi2,p,_,_=stats.chi2_contingency(tab,correction=False)
    orr=(a*d)/(b*cc) if b*cc>0 else float('inf')
    lo_or,hi_or=boot_or(a,b,cc,d)
    L=[]
    L.append(f"\n[{label}]")
    L.append(f"  |K-D|>=25 : n={nn} rate={rg:.3f} IC95%=[{lo_rg:.3f},{hi_rg:.3f}]")
    L.append(f"  rest      : n={nrest} rate={rr:.3f} IC95%=[{lo_rr:.3f},{hi_rr:.3f}]")
    L.append(f"  baseline(=rest) : {rr:.3f}")
    L.append(f"  diff={diff:+.3f}")
    L.append(f"  OR={orr:.2f} IC95%=[{lo_or:.2f},{hi_or:.2f}]  p={p:.2e}")
    return L,rg,rr,p,lo_or,hi_or

Ltr,rg_tr,rr_tr,p_tr,lo_or_tr,hi_or_tr=block(tr,"TRAIN")
Lte,rg_te,rr_te,p_te,lo_or_te,hi_or_te=block(te,"TEST OOS")
lines+=Ltr; lines+=Lte

# tabla compacta
lines.append("\n"+"-"*64)
lines.append("TABLA:")
lines.append(f"{'Grupo':<18}{'n':>7}{'rate':>8}{'IC95%':>16}{'base':>7}{'OR':>8}{'IC95%OR':>16}{'p':>10}")
def row(name,nn,rg,lo,hi,rr,orr,olo,ohi,p):
    lines.append(f"{name:<18}{nn:>7}{rg:>8.3f}{f'[{lo:.2f},{hi:.2f}]':>16}{rr:>7.3f}{orr:>8.2f}{f'[{olo:.2f},{ohi:.2f}]':>16}{p:>10.2e}")
a_tr=int(tr[tr.excess==1].next_retrace.sum()); b_tr=int((tr.excess==1).sum()-a_tr)
cc_tr=int(tr[tr.excess==0].next_retrace.sum()); d_tr=int((tr.excess==0).sum()-cc_tr)
a_te=int(te[te.excess==1].next_retrace.sum()); b_te=int((te.excess==1).sum()-a_te)
cc_te=int(te[te.excess==0].next_retrace.sum()); d_te=int((te.excess==0).sum()-cc_te)
orr_tr=(a_tr*d_tr)/(b_tr*cc_tr) if b_tr*cc_tr>0 else float('inf')
orr_te=(a_te*d_te)/(b_te*cc_te) if b_te*cc_te>0 else float('inf')
row("TRAIN |K-D|>=25", a_tr+b_tr, rg_tr, *wilson(a_tr,a_tr+b_tr), rr_tr, orr_tr, lo_or_tr, hi_or_tr, p_tr)
row("TEST  |K-D|>=25", a_te+b_te, rg_te, *wilson(a_te,a_te+b_te), rr_te, orr_te, lo_or_te, hi_or_te, p_te)

# veredicto: misma direccion + IC OR no incluye 1 + diff IC no incluye 0
def dir_ok(rg,rr): return rg>rr
ok_tr = dir_ok(rg_tr,rr_tr) and (lo_or_tr>1) and (p_tr<0.05)
ok_te = dir_ok(rg_te,rr_te) and (lo_or_te>1) and (p_te<0.05) if (a_te+b_te)>0 else False
if (a_te+b_te)==0:
    verd="INCONCLUSA (TEST sin instancias |K-D|>=25)"
elif ok_tr and ok_te:
    verd="ACEPTADA (efecto misma direccion TRAIN+TEST, IC OR>1, p<0.05 ambos)"
else:
    verd="REFUTADA (no replica OOS o IC incluye 1 / diff incluye 0)"
lines.append("\nVEREDICTO H2-M1: "+verd)
OUT.write_text("\n".join(lines))
print("\n".join(lines))
print("[+] ->",OUT)
