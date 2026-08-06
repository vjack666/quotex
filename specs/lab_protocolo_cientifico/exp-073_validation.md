# EXP-073 — Dinamica de la Fase A (energia, no eventos)

## Hipotesis (dictamen Trader-Humano 2026-08-06)

Tres experimentos (070/071/072) convergen en 'ningun confirmador tiene edge'.
No es falta de poder: es la pregunta equivocada. Wyckoff pregunta 'quien tiene el
control?', no 'que viene despues?'. El estocastico describe POSICION, no ENERGIA.
EXP-073 estudia la DINAMICA de la Fase A (como muere el impulso, compresion, entropia,
velocidad de oscilaciones) para responder: 'que cambia justo antes de que termine una
acumulacion/distribucion?' (que rompe el equilibrio).

## Metodologia

- Dominio: EURUSD REAL (Art. 13: solo descubrimiento).
- Fase A: inicio en extremo K<=20/>=80; cierre = nuevo extremo opuesto | cruce a banda | max 120 velas.
- Oscilaciones = segmentos entre cruces K-D. Variables continuas por fase:
  n_osc, amp_trend (compresion), amp_std (caos), dur_trend, entropy (Shannon de direcciones),
  mean_slope_K (equilibrio), max_kd_sep, time_to_break.
- Resolucion: movimiento de precio en 2h (H=8) vs direccion esperada -> clean/fizzle/fake.
- Descubrimiento: FDR (Art. 9) sobre 8 features dinamicas vs resolucion clean.
- Payout/seed no aplican (no es estrategia unitaria).

## Resultados

Fases A: 3308 | tasa base clean breakout: 0.405

Medias de variables dinamicas (medianas):
  n_osc=6.0  amp_trend=0.299  amp_std=4.375  dur_trend=0.035
  entropy=0.918  mean_slope_K=-0.016? NO: -0.016 es pendiente (equilibrio)  max_kd_sep=15.246  time_to_break=25.0

Dinamica vs RESOLUCION (FDR sobre features):
      feature  clean_rate_low  clean_rate_high   diff  p_value  p_adj_fdr
   max_kd_sep          0.3863           0.4247 0.0383 0.027090   0.216724
      amp_std          0.3900           0.4211 0.0311 0.074228   0.216724
 mean_slope_K          0.3930           0.4178 0.0248 0.156620   0.216724
      entropy          0.3981           0.4147 0.0166 0.351995   0.216724
    dur_trend          0.3996           0.4111 0.0115 0.523839   0.216724
        n_osc          0.4036           0.4081 0.0045 0.822984   0.216724
time_to_break          0.4033           0.4075 0.0042 0.834735   0.216724
    amp_trend          0.4051           0.4059 0.0009 0.988541   0.216724

Features con asociacion significativa (FDR): 0

## Veredicto del tribunal

- 3308 Fases A. Tasa base clean 0.405.
- NINGUNA variable dinamica de K-D separa breakout de fizzle (FDR 0/8).
- La mas cercana: max_kd_sep (diff +0.038, p_adj 0.217) y amp_std (+0.031, p_adj 0.217).
- Durante la Fase A el estocastico esta en equilibrio (slope -0.016) y es caotico
  (entropy 0.918): no hay 'quien tiene el control' detectable en K-D solo.

## Consecuencia cientifica

El estocastico describe POSICION, no ENERGIA/control. La dimension que falta (Wyckoff:
esfuerzo vs resultado) requiere VOLUMEN (tick_volume) y RANGO DE PRECIO (body/ATR), no
solo un oscilador. EXP-073 refuta usar K-D solo como medida de energia; NO refuta Wyckoff.

## Cumple Charter

- Art. 1 (descubrimiento): Si | Art. 9 (FDR): Si | Art. 13 (REAL=descubrimiento): Si