# Progress — 2026-08-06 (tarde) — CLAUSURA

## ⭐ Sesión actual: Paradigma Wyckoff en el Laboratorio + Freno Científico

**Estado: CERRADA (usuario dijo "listo por hoy"). Todo commiteado y pusheado.**

### Qué se hizo
- EXP-071 Zona de Descubrimiento: NINGÚN confirmador con edge (FDR 0.018, EV neg). → el contexto funciona, la entrada no. (efa212b)
- EXP-072 Mapa de Transiciones (Markov): mercado mean-reverting; impulso estocástico se revierte (0.28-0.30); 0 estados favorable>0.55. (76d467b)
- EXP-073 Dinámica Fase A (energía): FDR 0/8 — K-D describe posición, no predice resolución. (d696aba)
- EXP-074 Clustering no supervisado: K=2 (sil 0.2185), 24% explosivo / 76% lateral. Población mixta APOYADA. (ca8035f)
- EXP-074b Estabilidad (freno, 6 pruebas Grok/ChatGPT): RECHAZA GMM como robusta — no sobrevive a algoritmo (ARI~0), features (9.7%→48.1%), bootstrap (22%→95%). Lo real = duración de Fase A como variable continua. (c4ecb42)
- Art. 13 + ADR-005 (commit efa212b): EURUSD REAL = SOLO descubrimiento; validación OTC obligatoria antes de promover.

### Decisión
- Paradigma cambiado: el lab ya no busca "la estrategia"; modela el comportamiento del mercado (Wyckoff).
- Freno científico aplicado: NO procede EXP-075 sobre el cluster GMM (partición no estable). El lab evitó estrategia falsa.

### Próximo paso sugerido (al retomar con `start`)
- EXP-075 (re-enfocado): duración/tipo de Fase A como variable CONTINUA predictiva del breakout (cuartiles/regresión), no 2 cajas.
- Para PRUEBA 3 OOS faltante en 074b: necesitamos más historia EURUSD o datos OTC del propio lab.

### Archivos de la sesión (ya commiteados)
- scripts/lab_exp071_discovery.py, lab_exp072_state_graph.py, lab_exp073_phaseA_dynamics.py, lab_exp074_phaseA_clusters.py, lab_exp074b_cluster_stability.py
- reports/EXP-07{1,2,3,4}_*.csv, reports/EXP-074b_stability.txt
- specs/lab_protocolo_cientifico/exp-07{1,2,3,4}b_validation.md, exp07{1,2,3,4}b_index.md
- docs/LAB_CHARTER.md (Art.13), docs/decisions/ADR-005.md

### Notas
- Los scripts lab_exp0XX NO están en la suite pytest (se verifican por ejecución real, no pytest).
- Archivos sin commitear en el repo son de SESIONES PREVIAS (no tocados): ver `git status`.
- NO operar REAL sin OK. Bot corre PRACTICE por defecto.
