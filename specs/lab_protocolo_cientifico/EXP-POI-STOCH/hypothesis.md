# EXP-POI-STOCH — Hipótesis

**Dominio:** REAL (precio + estocástico M15 de pares Quotex).  
**Tipo:** Descubrimiento (Art. 13). No promoción a Edificio sin validación OTC posterior.  
**Fecha diseño:** 2026-08-07  
**Estado:** LISTO PARA EJECUCIÓN HANDS-FREE

---

## Pregunta central

¿Existe un patrón reproducible de **retorno a POI geométrico + rango saludable de separación del estocástico + entrada en open M15** que tenga resolución superior al baseline, y la separación excesiva del estocástico predice retrace de la siguiente vela?

## Hipótesis formales

### H1 — Patrón completo tiene edge
Cuando se cumplen simultáneamente:
1. Precio retorna a una zona POI de calidad mínima (grosor/eficacia ≥ umbral),
2. Separación K-D del estocástico está en rango “saludable” (ni sticky ni excesiva),
3. Se entra en la apertura de la vela M15,

entonces la tasa de rebote limpio (movimiento alineado de N velas) es significativamente superior a la tasa base de cualquier retorno a zona sin filtro de estocástico.

### H2 — Separación excesiva predice retrace
Independientemente del POI: cuando |K − D| supera un umbral alto (separación excesiva), la siguiente vela M15 tiene probabilidad elevada de retroceder (cierre en dirección opuesta al impulso previo del estocástico), incluso si el precio está en zona de soporte/resistencia.

### H3 — Neural net puede refinar la secuencia
Un modelo (secuencia o clasificador) entrenado sobre muchas ocurrencias del patrón puede:
- Discriminar variantes fuertes vs débiles del POI,
- Aprender el rango óptimo de separación del estocástico,
- Reducir falsos positivos que el filtro manual no captura.

## Targets (resolución)

- **Clean bounce:** movimiento de precio en las siguientes 4–8 velas M15 en la dirección esperada (rebote desde POI) ≥ 1× mediana de rango reciente.
- **Retrace next candle:** cierre de la vela M15 siguiente en dirección opuesta al sesgo del estocástico (para H2).
- Baseline: tasa de clean bounce de todos los retornos a zona sin filtro de estocástico.

## Alcance de datos

- Pares disponibles en el pipeline SMC_ROOT / Quotex (prioridad EURUSD, EURCHF, y los que tengan historial M15 limpio).
- Timeframe: M15.
- Periodo: máximo disponible con split TRAIN / TEST OOS temporal (mínimo 60/40 o 2022-2024 / 2025-2026 si existe).
- Features: solo precio (OHLC) + estocástico (K, D, K-D, sticky flags). Sin volumen.

## Criterio de aceptación / rechazo

- H1: FDR-BH sobre descriptores del patrón + OR o diff de tasa limpia vs baseline. p_adj < 0.05 y effect size mínimo (diff ≥ 0.05 o OR ≥ 1.25) en TRAIN y replicado en OOS.
- H2: misma lógica sobre umbral de |K-D|.
- H3: métricas de clasificación (AUC / precision-recall en hold-out) superiores a baseline de reglas fijas; sin overfit evidente (gap TRAIN-TEST controlado).
- Si ninguna hipótesis sobrevive → archivar el patrón tal como está definido y documentar que la estrategia visual no generaliza en los datos disponibles.
