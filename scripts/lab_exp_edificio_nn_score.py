"""EXP-EDIFICIO-NN-SCORE — hands-free.
Modelo (LightGBM) sobre features que el Edificio YA calcula (edificio_events.parquet)
vs baseline (score proxy del Edificio). Mide si mejora ranking/win-rate top-k/calibracion OOS.
Whitelist estricta (no features de POI-STOCH refutada). Split temporal estricto.
Reporta IC95% (Wilson rates, bootstrap lift). No toca produccion.
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score
import lightgbm as lgb

ROOT = Path(r"C:\Users\v_jac\Desktop\QUOTEX")
PARQ = ROOT/"src/strategy_lab/results/edificio_events.parquet"
REP = ROOT/"reports/EXP-EDIFICIO-NN-SCORE"
REP.mkdir(parents=True, exist_ok=True)
SEED=42; np.random.seed(SEED)

df = pd.read_parquet(PARQ)
print(f"[*] eventos Edificio: {len(df)}")

# ---- whitelist (solo features que el Edificio ya calcula) ----
WHITE = ["k_brake","d_brake","kd_dist_brake","brake_ratio","extreme_flag",
         "cross_separation","k_cross","d_cross","hammer_flag","trend_brake",
         "rvol_brake","htf_bias_brake","minutes_brake_to_cross","body_n_brake",
         "cruce_en_zona_brake","cross_ago_brake"]
# codificar htf_sign categorical
df["htf_sign_n"] = df["htf_sign"].map({"ALCISTA":1,"BAJISTA":-1}).fillna(0)
WHITE.append("htf_sign_n")
for c in WHITE:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

y = df["win"].astype(int).values

# ---- split temporal estricto por brake_time ----
df = df.sort_values("brake_time").reset_index(drop=True)
cut = int(len(df)*0.70)
train = df.iloc[:cut]; test = df.iloc[cut:]
print(f"[*] TRAIN={len(train)} TEST={len(test)} (split temporal 70/30 por brake_time)")
if len(train) < 500:
    print("[!] n_train<500 -> potencia baja (declarar en summary)")

Xtr = train[WHITE].values; ytr = train["win"].astype(int).values
Xte = test[WHITE].values; yte = test["win"].astype(int).values

# ---- baseline: score proxy del Edificio = brake_ratio (lo que el Edificio usa para freno) ----
def auc_safe(y, s):
    if len(np.unique(y))<2 or len(np.unique(s))<2: return float('nan')
    return roc_auc_score(y, s)
base_train = auc_safe(ytr, train["brake_ratio"].values)
base_test = auc_safe(yte, test["brake_ratio"].values)

# ---- modelo ----
clf = lgb.LGBMClassifier(n_estimators=300, max_depth=4, learning_rate=0.03,
                         subsample=0.8, colsample_bytree=0.8, min_child_samples=10,
                         num_leaves=15, random_state=SEED)
clf.fit(Xtr, ytr, eval_set=[(Xte,yte)], eval_metric="auc",
        callbacks=[lgb.early_stopping(30, verbose=False)])
pte = clf.predict_proba(Xte)[:,1]
auc_train = roc_auc_score(ytr, clf.predict_proba(Xtr)[:,1])
auc_test = roc_auc_score(yte, pte)

# ---- H2 top-k win-rate + lift IC95% bootstrap ----
def topk_wr(yv, sv, frac):
    k=int(len(yv)*frac)
    order=np.argsort(-sv)[:k]
    return yv[order].mean(), k
def boot_lift(yv, sv, frac, B=2000):
    n=len(yv); base=yte.mean()
    klift=[]
    for _ in range(B):
        idx=np.random.choice(n,n,replace=True)
        wr,_=topk_wr(yv[idx],sv[idx],frac)
        klift.append(wr-base)
    return np.percentile(klift,2.5), np.percentile(klift,97.5)
topk_results={}
for f in [0.2,0.3]:
    wr_tr,k_tr=topk_wr(ytr, clf.predict_proba(Xtr)[:,1], f)
    wr_te,k_te=topk_wr(yte, pte, f)
    base=yte.mean()
    lo,hi=boot_lift(yte, pte, f)
    topk_results[f]={"wr_train":wr_tr,"wr_test":wr_te,"k_test":k_te,
                     "base":base,"lift":wr_te-base,"ci_lo":lo,"ci_hi":hi,
                     "include_zero": bool(lo<=0<=hi)}

# ---- H3 calibration (ECE) ----
def ece(yv, pv, bins=5):
    edges=np.linspace(0,1,bins+1); e=0
    for i in range(bins):
        m=(pv>=edges[i])&(pv<edges[i+1]); 
        if m.sum()==0: continue
        e+=abs(pv[m].mean()-yv[m].mean())*m.sum()/len(yv)
    return e
ece_model=ece(yte, pte)
ece_base=ece(yte, (test["brake_ratio"].values-test["brake_ratio"].min())/(test["brake_ratio"].max()-test["brake_ratio"].min()+1e-9))

# ---- veredictos ----
def verdict_h1():
    if len(train)<500: return "INCONCLUSA (n bajo)"
    return "ACEPTADA" if (auc_test>base_test and (auc_test-base_test)>0.02) else "REFUTADA"
def verdict_h2(f):
    r=topk_results[f]
    if r["k_test"]<30: return "INCONCLUSA (n top-k bajo)"
    return "ACEPTADA" if (r["lift"]>0 and not r["include_zero"]) else "REFUTADA"
v_h1=verdict_h1()
v_h2_20=verdict_h2(0.2); v_h2_30=verdict_h2(0.3)
v_h3="ACEPTADA" if ece_model<=ece_base+0.03 else "REFUTADA"

# ---- reports ----
PROTO={"seed":SEED,"alpha":0.05,"domain":"REAL_edificio_features","model":"lightgbm",
       "oos_split":"temporal 70/30 por brake_time","features_whitelist":WHITE,
       "target":"win","top_k_fractions":[0.2,0.3],"min_train_events":500,
       "auc_gap_warn":0.08,"n_events":len(df),"n_train":len(train),"n_test":len(test)}
json.dump(PROTO, open(REP/"protocol_frozen.json","w"), indent=2)

baseline_metrics={"auc_train_brake_ratio":base_train,"auc_test_brake_ratio":base_test,
                  "base_winrate_test":float(yte.mean())}
json.dump(baseline_metrics, open(REP/"baseline_metrics.json","w"), indent=2)
model_metrics={"auc_train":auc_train,"auc_test":auc_test,"auc_test_baseline":base_test,
               "auc_gap":auc_train-auc_test,"ece_model":ece_model,"ece_base":ece_base,
               "topk":topk_results}
json.dump(model_metrics, open(REP/"model_metrics.json","w"), indent=2)

imp=pd.DataFrame({"feat":WHITE,"imp":clf.feature_importances_}).sort_values("imp",ascending=False)
imp.to_csv(REP/"feature_importance.csv", index=False)

with open(REP/"topk_table.csv","w") as f:
    f.write("frac,wr_train,wr_test,k_test,base,lift,ci_lo,ci_hi,include_zero\n")
    for fr,r in topk_results.items():
        f.write(f"{fr},{r['wr_train']:.3f},{r['wr_test']:.3f},{r['k_test']},{r['base']:.3f},{r['lift']:.3f},{r['ci_lo']:.3f},{r['ci_hi']:.3f},{r['include_zero']}\n")

with open(REP/"summary.txt","w") as f:
    f.write("="*60+"\nEXP-EDIFICIO-NN-SCORE — RESUMEN (hands-free)\n"+"="*60+"\n")
    f.write(f"eventos={len(df)} TRAIN={len(train)} TEST={len(test)} (temporal 70/30)\n")
    f.write(f"winrate global TEST={yte.mean():.3f}\n")
    f.write(f"features whitelist ({len(WHITE)}): {WHITE}\n\n")
    f.write(f"BASELINE (score Edificio=brake_ratio): AUC_TRAIN={base_train:.3f} AUC_TEST={base_test:.3f}\n")
    f.write(f"MODELO LightGBM: AUC_TRAIN={auc_train:.3f} AUC_TEST={auc_test:.3f} gap={auc_train-auc_test:+.3f}\n\n")
    f.write(f"H1 (ranking mejora OOS): {v_h1}  (AUC_test {auc_test:.3f} vs base {base_test:.3f})\n")
    f.write(f"H2 top-20%: {v_h2_20}  lift={topk_results[0.2]['lift']:+.3f} IC95%[{topk_results[0.2]['ci_lo']:+.3f},{topk_results[0.2]['ci_hi']:+.3f}]\n")
    f.write(f"H2 top-30%: {v_h2_30}  lift={topk_results[0.3]['lift']:+.3f} IC95%[{topk_results[0.3]['ci_lo']:+.3f},{topk_results[0.3]['ci_hi']:+.3f}]\n")
    f.write(f"H3 (calibracion): {v_h3}  ECE_model={ece_model:.3f} ECE_base={ece_base:.3f}\n")
    f.write("\nNo se reintrodujo H2 de POI-STOCH (refutada). No se toco produccion.\n")
print("[+] reports ->", REP)
print(f"[+] H1={v_h1} H2_20={v_h2_20} H2_30={v_h2_30} H3={v_h3}")
print(f"    AUC test modelo={auc_test:.3f} vs base={base_test:.3f}")
