# LAB-003/004/005 — Geografía del giro, tiempo en la pelea y EL MOTOR

Fecha: 2026-07-27 · Laboratorio · Estado: VALIDADO (walk-forward en cada fila)
Reproducir: `PYTHONPATH=src python scripts/lab_003_005_motor.py`
Datos: Atlas 14 años EURUSD M1 (116,164 episodios analizables) + precios parquet.

## LAB-003 — ¿Dónde dentro de la zona ocurre el giro?
Caja de referencia: rango high-low de las 5 velas previas al freno (lo que el
trader VE cuando el precio frena). Penetración = cuánto avanzó el precio MÁS
ALLÁ del borde de esa caja antes de resolverse (en % del tamaño de la caja).

| Penetración               | n      | % REBOUND | eras 12-19/20-26 |
|---------------------------|--------|-----------|------------------|
| POCA  (<-13%, no llegó al borde) | 38,292 | **38.2%** | 38.2/38.1 |
| MEDIA (-13% a +18%)       | 38,381 | 33.9%     | 34.2/33.6        |
| MUCHA (>+18% más allá)    | 39,491 | 19.4%     | 19.5/19.2        |

HALLAZGO (invierte la intuición "consumir la zona"): el rebote bueno NO
atraviesa la caja del freno — muere ANTES o EN el borde (mediana de rebotes:
-8%, es decir el extremo queda DENTRO). Si el precio penetra >18% más allá
del freno, el "freno" era falso y la probabilidad de rebote cae a 19%.
Regla cuantitativa: el giro ocurre en el borde de la caja, no tras consumirla.

Nota de método: medir "profundidad dentro del rango BRAKE→RESOLUTION" da 100%
por construcción (el extremo DEFINE el rango) — vara circular, descartada.
La caja pre-freno congelada es la vara honesta.

## LAB-004 — ¿El tiempo en la pelea importa?
Duración BRAKE→RESOLUTION: mediana 7 min, poca varianza (terciles 6/7 min:
la resolución v1 fija 5 velas tras TRANSITION y comprime la escala).
Solo (30.1% vs 31.2% corta vs larga): CASI NO discrimina.
PERO en el extremo del apilado sí aporta (ver combo E). Veredicto: variable
débil sola; útil solo como refinador final. Re-medir en Fase B con
resoluciones de duración libre.

## LAB-005 — EL MOTOR ESTADÍSTICO (apilado de condiciones)
| Combo | Condición                                  | n      | % REBOUND | eras | señales/día |
|-------|--------------------------------------------|--------|-----------|------|-------------|
| base  | todos los episodios                        |116,164 | 30.4%     | 30.6/30.1 | 33.2 |
| A     | muerte del empuje (LAB-001)                | 16,834 | 69.8%     | 69.3/70.5 | 4.8 |
| B     | A + zona grande (>5.8 pips)                |  6,359 | **81.9%** | 81.8/82.1 | 1.8 |
| C     | A + poca penetración                       |  9,628 | 68.1%     | 67.3/69.2 | 2.8 |
| D     | B + poca penetración                       |  3,812 | 79.9%     | 80.0/79.8 | 1.1 |
| E     | D + pelea larga                            |    236 | 90.3%     | 90.4/90.0 | 0.1 |

Lecturas:
- El MOTOR existe: la probabilidad escala de 30% → 70% → 82% → 90% apilando
  condiciones, con walk-forward prácticamente idéntico en CADA nivel.
- El combo B (muerte + zona grande) es el punto dulce operativo: 82% con
  ~2 señales/día — frecuencia tradeable.
- La penetración NO suma sobre B (D < B): su información ya está contenida
  en la muerte del empuje + zona. Apilar no siempre suma — el motor debe
  medir aporte MARGINAL, no acumular condiciones.
- El combo E (90.3%) es real pero raro (~2/mes): confirmación de techo, no
  base de negocio.

## Límites
- Fenómeno ≠ trade (MFE/MAE y timing = Fase B).
- Solo EURUSD real; universalidad y OTC pendientes.
- Umbrales por terciles in-sample; Fase B debe fijarlos en años de
  entrenamiento y validarlos en años vírgenes.
