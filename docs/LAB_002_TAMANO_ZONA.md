# LAB-002 — El tamaño de la zona de freno (proxy POI)

Fecha: 2026-07-27 · Laboratorio · Estado: VALIDADO
Reproducir: `PYTHONPATH=src python scripts/lab_002_tamano_zona.py`
Datos: Atlas 14 años EURUSD M1 (117,169 episodios) + precios reales parquet.

## Pregunta
¿Qué tamaño tiene la zona donde el precio frena y rebota (el POI de reacción)?
¿El tamaño predice el desenlace?

## Definición
Zona de freno = rango high-low del precio entre la entrada a BRAKE y la
RESOLUTION del episodio (la caja donde los dos bandos pelean antes del
desenlace). Medida en pips sobre los precios reales del parquet.

## Resultados (n=116,164)
Tamaño de zona en episodios que REBOTAN:
- media 6.3 pips · mediana 5.1 · mitad central 3.2-7.8 pips
- duración típica de la pelea: ~7 minutos

El tamaño PREDICE el desenlace (terciles):
| Zona                | n      | % REBOUND | eras 12-19 / 20-26 |
|---------------------|--------|-----------|--------------------|
| CHICA  (<3.3 pips)  | 38,127 | 23.5%     | 24.1 / 22.8        |
| MEDIA  (3.3-5.8)    | 39,082 | 30.1%     | 30.0 / 30.3        |
| GRANDE (>5.8 pips)  | 38,955 | **37.4%** | 36.8 / 38.4        |

## Falsación
- Walk-forward: gradiente idéntico en ambas épocas.
- Placebo (1,000 barajadas): diff real +10.6 pts, p < 0.001.

## Lectura
La zona chica es peaje de paso; la zona ancha es muro: cuando la pelea se
ensancha, el giro es más probable. Variable INDEPENDIENTE de LAB-001
(muerte del empuje) — candidata a apilarse en LAB-005.

## Límites
- Proxy: la "zona" es el rango BRAKE→RESOLUTION del episodio, no una POI
  estructural pre-marcada (order block / imbalance llegan en Fase B).
- Solo EURUSD; universalidad pendiente (oro + 8 pares).
