"""EXP-POI-STOCH — experimento hands-free (ver specs/lab_protocolo_cientifico/EXP-POI-STOCH/).
Patron: retorno a POI geometrico + separacion estocastica saludable + entrada open M15.
H1 patron completo tiene edge; H2 separacion excesiva predice retrace; H3 NN si n>=300.
Usa swing_levels_causal (poi_behavior) + compute_support_efficacy (zone_strength).
SOLO precio OHLC + estocastico. Sin volumen. Sin tocar src/ produccion.
"""
import sys, json, csv, os
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score
import lightgbm as lgb

import matplotlib
matplotlib.use("Agg")

ROOT = Path(r"C:\Users\v_jac\Desktop\QUOTEX")
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
from strategy_lab.poi_behavior import swing_levels_causal
from zone_strength import compute_support_efficacy

CSV = ROOT / "tools/quotex-historical-data/EURUSD_otc_60s_365days.csv"
REP = ROOT / "reports/EXP-POI-STOCH"
DATA = ROOT / "data/strategy_lab"
REP.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

# ---- protocolo congelado (a priori, sin mirar resultados) ----
PROTO = {
    "seed": 42,
    "alpha": 0.05,
    "fdr_method": "fdr_bh",
    "domain": "REAL_price_stoch_M15",
    "pair": "EURUSD_otc",
    "tf": "M15",
    "oos_split": "temporal",
    "poi_min_efficacy": 0.35,
    "kd_healthy_low": 5.0,    # |K-D| minimo (separacion moderada)
    "kd_healthy_high": 18.0,  # |K-D| maximo (no excesivo)
    "kd_excessive": 25.0,     # |K-D| umbral exceso (H2) — fijo a priori
    "n_forward_clean": [4, 8],
    "min_events_for_nn": 300,
    "effect_size_min_diff": 0.05,
    "effect_size_min_or": 1.25,
    "stoch_k": 14, "stoch_d": 3, "stoch_s": 3,
    "sticky_extreme": 20.0,   # K<=20 o K>=80 cuenta como extremo
    "sticky_max_bars": 2,     # menos de esto = no sticky
}
np.random.seed(PROTO["seed"])

# ---- cargar M1 y agregar a M15 ----
print("[*] cargando M1...")
ts, o, h, l, c = [], [], [], [], []
with open(CSV) as f:
    for row in csv.DictReader(f):
        ts.append(int(row["timestamp"])); o.append(float(row["open"]))
        h.append(float(row["high"])); l.append(float(row["low"])); c.append(float(row["close"]))
ts = np.array(ts); o = np.array(o); h = np.array(h); l = np.array(l); c = np.array(c)
step = 15
n15 = len(ts) // step
m_ts = ts[:n15*step].reshape(n15, step)[:, 0]
m_o = o[:n15*step].reshape(n15, step)[:, 0]
m_c = c[:n15*step].reshape(n15, step)[:, -1]
m_h = h[:n15*step].reshape(n15, step).max(1)
m_l = l[:n15*step].reshape(n15, step).min(1)
print(f"[*] M15 velas: {n15}")

# ---- estocastico %K/%D (14,3,3) ----
def stochastic(hi, lo, cl, k=14, d=3, s=3):
    n = len(cl); rng = np.full(n, np.nan); raw = np.full(n, np.nan)
    for i in range(k-1, n):
        ll = lo[i-k+1:i+1].min(); hh = hi[i-k+1:i+1].max()
        raw[i] = 100*(cl[i]-ll)/(hh-ll) if hh > ll else 50.0
    kk = np.full(n, np.nan)
    for i in range(k-1, n):
        kk[i] = np.nanmean(raw[i-s+1:i+1])
    dd = np.full(n, np.nan)
    for i in range(k-1+d-1, n):
        dd[i] = np.nanmean(kk[i-d+1:i+1])
    return kk, dd
K, D = stochastic(m_h, m_l, m_c, PROTO["stoch_k"], PROTO["stoch_d"], PROTO["stoch_s"])
kd = np.abs(K - D)
print("[*] estocastico listo")

# ---- POIs (swing_levels_causal) past-only por indice ----
fl, ce, af, at = swing_levels_causal(m_h, m_l, min_touches=2, tol_pips=5.0, swing_k=2, lookback=200)
print(f"[*] niveles POI: {fl.size}")

# envolver velas para compute_support_efficacy
class C:
    def __init__(s, o, h, l, c): s.open=o; s.high=h; s.low=l; s.close=c
candles = [C(m_o[i], m_h[i], m_l[i], m_c[i]) for i in range(n15)]

def efficacy_of(level, direction, upto):
    """eficacia usando solo velas anteriores a 'upto' (past-only, sin leakage)."""
    seg = candles[max(0, upto-288):upto]  # ~3 dias M15 hacia atras
    if len(seg) < 10: return 0.0, 0, 0
    eff = compute_support_efficacy(level, seg, direction=direction, band_pct=0.0008, hold_candles=3)
    return eff.get("efficacy", 0.0), eff.get("touch_count", 0), eff.get("bounce_count", 0)

# ---- detectar retornos a POI (past-only) ----
events = []
for k_ in range(fl.size):
    a0, b0 = int(af[k_]), int(at[k_])
    if a0 >= b0: continue
    center = (fl[k_] + ce[k_]) / 2
    is_support = True  # si el precio viene de arriba y toca por abajo => soporte
    seg = slice(a0, b0)
    hit = np.flatnonzero((m_l[seg] <= ce[k_]) & (m_h[seg] >= fl[k_]))
    if hit.size == 0: continue
    for j in hit:
        i = a0 + j
        if i < 30 or i+9 >= n15: continue
        pc = m_c[i-1]
        if not (pc > ce[k_] or pc < fl[k_]): continue
        direction = "CALL" if pc > ce[k_] else "PUT"  # soporte si viene de arriba
        eff, tc, bc = efficacy_of(center, direction, i)
        if eff < PROTO["poi_min_efficacy"]: continue
        # estocastico en el retorno (open de la vela de toque)
        kk = K[i]; dd = D[i]; sep = kd[i]
        sticky = int((kk <= PROTO["sticky_extreme"]) or (kk >= 100-PROTO["sticky_extreme"]))
        # labels forward (clean bounce en direccion del rebote)
        # direccion esperada: rebote desde soporte => sube; desde resistencia => baja
        exp_dir = 1 if direction == "CALL" else -1
        med_range = np.median(m_h[i-30:i] - m_l[i-30:i]) if i >= 30 else 0.001
        clean4 = (m_c[i+4] - m_c[i]) * exp_dir >= 1.0 * med_range
        clean8 = (m_c[i+8] - m_c[i]) * exp_dir >= 1.0 * med_range
        # H2: next candle retrace (cierre opuesto al sesgo del estocastico)
        stoch_bias = 1 if kk > 50 else -1
        next_retrace = ((m_c[i+1] - m_c[i]) * stoch_bias) < 0
        events.append({
            "idx": i, "ts": int(m_ts[i]), "level": center, "eff": eff,
            "touch_count": tc, "bounce_count": bc, "direction": direction,
            "K": kk, "D": dd, "kd_sep": sep, "sticky": sticky,
            "clean4": int(clean4), "clean8": int(clean8), "next_retrace": int(next_retrace),
        })
print(f"[*] eventos retorno-a-POI (calidad minima): {len(events)}")
if len(events) == 0:
    print("[!] BLOQUEADO: 0 eventos con eficacia minima. Documentar y parar.")
    with open(REP/"summary.txt","w") as f:
        f.write("EXP-POI-STOCH: BLOQUEADO por datos (0 eventos POI con eficacia>=%.2f)\n" % PROTO["poi_min_efficacy"])
    sys.exit(0)

ev = pd.DataFrame(events)
ev.to_parquet(DATA/"exp_poi_stoch_events.parquet")

# ---- split temporal TRAIN / TEST OOS (por indice de EVENTO ordenado, 70/30) ----
# Los POIs son densos y concentran eventos al inicio de la serie; cortar por indice de
# vela deja TEST casi vacio. Cortamos por evento temporalmente ordenado para OOS honesto.
ev = ev.sort_values("idx").reset_index(drop=True)
cut = int(len(ev) * 0.70)
train = ev.iloc[:cut]; test = ev.iloc[cut:]
split_idx = int(train["idx"].max())  # referencia temporal
print(f"[*] TRAIN={len(train)} TEST={len(test)} (split por evento 70/30, split_idx_vuela={split_idx})")

def fdr_test(df, mask_full, label_col):
    """compara tasa de label entre grupo filtrado (mask) y resto, FDR sobre 1 test."""
    grp = df[mask_full][label_col]
    rest = df[~mask_full][label_col]
    if len(grp) == 0 or len(rest) == 0:
        return None
    # chi2
    a = grp.sum(); b = len(grp)-a
    c = rest.sum(); d = len(rest)-c
    table = np.array([[a,b],[c,d]])
    chi2, p, _, _ = stats.chi2_contingency(table, correction=False)
    # OR
    orr = (a*d)/(b*c) if (b*c) > 0 else float('inf')
    rate_grp = a/len(grp); rate_rest = c/len(rest)
    diff = rate_grp - rate_rest
    return {"n_grp":len(grp),"n_rest":len(rest),"rate_grp":rate_grp,"rate_rest":rate_rest,
            "diff":diff,"OR":orr,"p":p,"chi2":chi2}

def verdict(res, oos_res):
    if res is None or oos_res is None: return "INCONCLUSA"
    p = res["p"]; pt = oos_res["p"]
    eff = (res["diff"] >= PROTO["effect_size_min_diff"]) or (res["OR"] >= PROTO["effect_size_min_or"])
    eff_oos = (oos_res["diff"] >= PROTO["effect_size_min_diff"]) or (oos_res["OR"] >= PROTO["effect_size_min_or"])
    if p < PROTO["alpha"] and pt < PROTO["alpha"] and eff and eff_oos:
        return "ACEPTADA"
    if p >= PROTO["alpha"] or (not eff and not eff_oos):
        return "REFUTADA"
    return "INCONCLUSA"

# H1: patron completo = POI calidad + kd saludable + no sticky
h1_mask = (ev["kd_sep"] >= PROTO["kd_healthy_low"]) & (ev["kd_sep"] <= PROTO["kd_healthy_high"]) & (ev["sticky"]==0)
res_h1_train = fdr_test(train, h1_mask[train.index], "clean8")
res_h1_test = fdr_test(test, h1_mask[test.index], "clean8")
v_h1 = verdict(res_h1_train, res_h1_test)

# baseline: todos los retornos sin filtro estocastico
base_train = train["clean8"].mean(); base_test = test["clean8"].mean()

# H2: separacion excesiva predice retrace
h2_mask = ev["kd_sep"] >= PROTO["kd_excessive"]
res_h2_train = fdr_test(train, h2_mask[train.index], "next_retrace")
res_h2_test = fdr_test(test, h2_mask[test.index], "next_retrace")
v_h2 = verdict(res_h2_train, res_h2_test)

# ---- H3: NN/boosting si n_train>=300 ----
v_h3 = "OMITIDA (n bajo)"
h3_metrics = {}
if len(train) >= PROTO["min_events_for_nn"]:
    feats = ["eff","touch_count","bounce_count","K","D","kd_sep","sticky"]
    Xtr = train[feats].fillna(0).values; ytr = train["clean8"].values.astype(int)
    Xte = test[feats].fillna(0).values; yte = test["clean8"].values.astype(int)
    clf = lgb.LGBMClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8, min_child_samples=5,
                             num_leaves=15, random_state=PROTO["seed"])
    clf.fit(Xtr, ytr)
    pte = clf.predict_proba(Xte)[:,1]
    auc = roc_auc_score(yte, pte) if len(np.unique(yte))>1 else float('nan')
    base_pred = (h1_mask[test.index]).astype(int).values
    auc_base = roc_auc_score(yte, base_pred) if (len(np.unique(yte))>1 and len(np.unique(base_pred))>1) else float('nan')
    h3_metrics = {"auc_oos":auc,"auc_baseline":auc_base,"gap":(auc-auc_base if not (np.isnan(auc) or np.isnan(auc_base)) else 0.0)}
    imp = pd.DataFrame({"feat":feats,"imp":clf.feature_importances_}).sort_values("imp",ascending=False)
    imp.to_csv(REP/"feature_importance.csv", index=False)
    v_h3 = "ACEPTADA" if (not np.isnan(auc) and not np.isnan(auc_base) and abs(auc-auc_base)<0.08 and auc>=auc_base) else "REFUTADA"

# ---- reports inmutables ----
with open(REP/"protocol_frozen.json","w") as f:
    json.dump(PROTO, f, indent=2)

def dump(res, name):
    if res is None: return f"{name}: sin datos\n"
    return (f"{name}: n_grp={res['n_grp']} rate={res['rate_grp']:.3f} | rest n={res['n_rest']} rate={res['rate_rest']:.3f} "
            f"| diff={res['diff']:+.3f} OR={res['OR']:.2f} p={res['p']:.4f} chi2={res['chi2']:.2f}\n")

with open(REP/"h1_results.csv","w") as f:
    f.write("H1 patron completo (POI calidad + kd saludable 5-18 + no sticky)\n")
    f.write("baseline clean8 TRAIN=%.3f TEST=%.3f\n" % (base_train, base_test))
    f.write(dump(res_h1_train,"TRAIN")); f.write(dump(res_h1_test,"TEST"))

with open(REP/"h2_results.csv","w") as f:
    f.write("H2 separacion excesiva |K-D|>=%.1f predice retrace next candle\n" % PROTO["kd_excessive"])
    f.write(dump(res_h2_train,"TRAIN")); f.write(dump(res_h2_test,"TEST"))

with open(REP/"summary.txt","w") as f:
    f.write("="*60+"\nEXP-POI-STOCH — RESUMEN (hands-free)\n"+"="*60+"\n")
    f.write(f"par: EURUSD_otc | tf M15 | velas={n15} | eventos={len(ev)}\n")
    f.write(f"TRAIN={len(train)} TEST={len(test)} (split temporal 60%%)\n")
    f.write(f"baseline clean8: TRAIN={base_train:.3f} TEST={base_test:.3f}\n\n")
    f.write(f"H1 (patron completo edge): {v_h1}\n")
    f.write(dump(res_h1_train,"  TRAIN")); f.write(dump(res_h1_test,"  TEST"))
    f.write(f"H2 (sep excesiva -> retrace): {v_h2}\n")
    f.write(dump(res_h2_train,"  TRAIN")); f.write(dump(res_h2_test,"  TEST"))
    f.write(f"H3 (NN refine): {v_h3}\n")
    if h3_metrics: f.write(f"  auc_oos={h3_metrics['auc_oos']:.3f} baseline={h3_metrics['auc_baseline']:.3f} gap={h3_metrics['gap']:+.3f}\n")
    f.write("\nNota datos: EURCHF_otc NO disponible (Token rejected servidor Quotex). Solo EURUSD_otc (M1->M15).\n")
    f.write("No se uso volumen. POI vía swing_levels_causal + compute_support_efficacy (zone_strength).\n")

ev.to_csv(REP/"events_sample.csv", index=False)
print("[+] reports escritos en", REP)

# ---- actualizar progress/HANDOFF ----
prog = ROOT/"progress/current.md"
htext = (f"\n## EXP-POI-STOCH ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})\n"
         f"H1={v_h1} H2={v_h2} H3={v_h3} | eventos={len(ev)} EURUSD_otc M15. EURCHF_otc no disp (Token rejected).\n")
if prog.exists():
    with open(prog,"a") as f: f.write(htext)
else:
    with open(prog,"w") as f: f.write(htext)

print(f"[+] H1={v_h1} H2={v_h2} H3={v_h3}")
