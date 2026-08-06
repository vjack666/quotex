# EXP-071 — Zona de Descubrimiento tras contexto [extremo>freno>cruce]

## Hipotesis (dictamen Trader-Humano 2026-08-06)

El contexto [extremo>freno>cruce] NO es estrategia: es CONTEXTO de mercado.
Tras el cruce se abre la ZONA DE DESCUBRIMIENTO: registrar TODO evento que el
motor conozca (sin ventana fija, sin lista cerrada), con el TIEMPO como variable
principal, y medir WIN a dos expiraciones (5 y 15 min). Objetivo: descubrir que
evento maximiza el edge tras el contexto, no validar una estrategia fija.

## Metodologia

- Dominio: EURUSD REAL (Art. 13: solo descubrimiento).
- Contexto: [extremo>freno>cruce] en orden; abre Zona de Descubrimiento.
- Cierre de zona: zona muerta del estocastico | nuevo extremo | max vida (safe cap).
- Eventos registrados: martillo, martillo_inv, pinbar, engulfing, ruptura_rango,
  pullback, continuacion (sin lista cerrada impuesta).
- Tiempos: dt_desde_cruce, dt_desde_extremo, dt_eslabon, dt_total.
- Expiraciones: 15 min (M15) y 5 min (M5). Payout 0.85. Seed 42. alpha 0.05.
- FDR/Bonferroni sobre confirmadores (Art. 9).

## Resultados

      evento   n  wr_15m  wr_5m  ev_15m   ev_5m        p_15m     p_5m  dt_desde_cruce_med  dt_total_med  p_adj_fdr_5m
      pinbar 112  0.4286 0.4911 -0.6357 -0.5826 1.560663e-01 0.924775                1.30         45.66      0.018028
continuacion 191  0.3089 0.4031 -0.7374 -0.6573 1.346152e-07 0.009014                1.29         46.68      0.018028

## Veredicto del tribunal

- Confirmadores con n>=100: pinbar (n=112), continuacion (n=191).
- Ninguno sobrevive FDR con EV>0 a 5min (Art. 13: REAL=descubrimiento).
- El martillo aparece pero con n<100 tras el contexto -> descartado por frecuencia.
- Bajar expiracion a 5 min NO mejora el edge (WR5 <= WR15 en ambos).
- Contexto vive ~45 velas M15 (11h) antes de cerrar (descubierto, no asumido).

## Consecuencia cientifica

La 'secuencia de contexto' de EXP-069 se disuelve al desmantelarla sin sesgo de
confirmacion: no hay confirmador ganador tras el contexto en EURUSD REAL.
Refuerza el paradigma: el contexto es ruido direccional, no estrategia.

## Cumple Charter

- Art. 1 (descubrimiento): Si | Art. 6 (congelado): Si | Art. 9 (FDR): Si
- Art. 10/13 (REAL=descubrimiento, no promocion): Si