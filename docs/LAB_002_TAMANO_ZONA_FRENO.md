# LAB-002 — Tamaño de la zona de freno (proxy del POI de reacción)

Fecha: 2026-07-27 · Laboratorio (docs/FILOSOFIA.md) · Estado: MEDIDO
(descriptivo validado; el gradiente tamaño→rebote es PISTA, pendiente tribunal)
Reproducir: `PYTHONPATH=src python scripts/lab_002_tamano_zona_freno.py`
Datos: mismos 117,169 episodios de LAB-001 + precios reales del parquet
EURUSD_M1 (SMC-SYSTEMS, solo lectura). 1 pip = 0.0001.

## Pregunta (de Ruben)
¿Cuánto mide la zona donde el precio frena y rebota? (tamaño promedio del
POI de reacción).

## Definición
Zona de freno = rango high-low del precio entre la entrada a BRAKE y la
RESOLUTION del episodio (transitions_v1). Es el proxy Fase-A del POI de
reacción; el objeto POI/AttentionZone formal llega en Fase B.

## Resultados (EURUSD, 14 años)
| Desenlace     | n      | media | mediana | p25-p75    | dur. mediana |
|---------------|--------|-------|---------|------------|--------------|
| REBOUND       | 35,288 | 6.3   | **5.1** | 3.2 - 7.8  | 7 min        |
| CONTINUATION  | 55,974 | 5.4   | 4.2     | 2.7 - 6.6  | 7 min        |
| CHAOS         | 24,902 | 4.8   | 3.9     | 2.5 - 6.1  | 7 min        |

**Respuesta directa: el POI de reacción típico del EURUSD M1 mide ~5-6 pips
(mediana 5.1, media 6.3) y el precio se revuelve en él ~7 minutos.**

## Pista secundaria (NO ley todavía)
El tamaño de la zona covaría con el desenlace — más ancha, más rebote:
- CHICA (<3.3 pips): REBOUND 23.5% (n=38,127)
- MEDIA (3.3-5.8): REBOUND 30.1% (n=39,082)
- GRANDE (>5.8): REBOUND 37.4% (n=38,955)

Lectura: la zona ancha = pelea real entre bandos (muro); la chica = peaje de
paso. OJO: correlación de una sola mirada, sin walk-forward ni placebo aún,
y confundida con volatilidad (zonas grandes abundan en sesiones volátiles).

## Pendiente (tribunal para ascender la pista a ley)
1. Walk-forward 2012-19 vs 2020-26 + placebo (estándar LAB-001).
2. Control por volatilidad (normalizar tamaño por ATR de la sesión).
3. APILADO con LAB-001: ¿muerte total del empuje + zona GRANDE > 70%?

## Límites honestos
- BRAKE→RESOLUTION es proxy: no es la POI dibujada a mano de un trader
  (order block / imbalance); Fase B definirá AttentionZone formal.
- EURUSD real ≠ OTC Quotex; pips de OTC pueden escalar distinto.
