# LAB-001 — La muerte del empuje predice el rebote

Fecha: 2026-07-27 · Laboratorio (docs/FILOSOFIA.md) · Estado: VALIDADO · **CONGELADO (referencia histórica, no editable)**
Fecha de congelación: 2026-07-27. La definición de "MUERTE TOTAL DEL EMPUJE"
de este LAB no se modificará. Toda mejora nace como nuevo experimento
(LAB-0XX "Muerte del impulso v2") para poder comparar generaciones.
Validación cruzada: ver docs/LAB_UNIVERSALIDAD.md (9 pares, misma señal 72-77%).
Reproducir: `PYTHONPATH=src python scripts/lab_001_muerte_empuje.py`
Datos: 14 años EURUSD M1 real (Dukascopy vía SMC-SYSTEMS), 117,169 episodios
grabados por el Observador Fase A (transitions_v1) en
`data/observador/episodes_eurusd_14y.db` (regenerable con `scripts/corrida_14y.py`).

## Pregunta
Ley 2 de la Constitución: "el freno del empuje anuncia el rebote". ¿Es medible?
¿Qué forma exacta del freno predice?

## Definición ganadora: MUERTE TOTAL DEL EMPUJE
Al final del episodio se cumplen las TRES a la vez:
1. Avance por vela chico (tercil inferior del avance normalizado, últimas 5 velas)
2. Queda <10% de la fuerza del pico del episodio
3. Continuidad baja (tercil inferior): velas alternadas, peleándose

## Resultados (n=116,164 episodios analizables)
| Condición final              | n      | % REBOUND |
|------------------------------|--------|-----------|
| MUERTE TOTAL del empuje      | 16,834 | **69.8%** |
| Resto                        | 99,330 | 23.7%     |
| Empuje VIVO (>60% del pico)  | 25,005 | 13.1%     |
| Tasa base global             |116,164 | 30.1%     |

## Falsación (estándar FILOSOFIA.md)
- Walk-forward: 2012-2019 → 69.3% (n=9,511) · 2020-2026 → 70.5% (n=7,323).
  Estable a través de QE, COVID y 14 años de regímenes distintos.
- Placebo: 1,000 barajadas de etiquetas; ninguna alcanzó la diferencia real
  (+46.1 pts). p < 0.001.
- Espejo: la señal invierte con empuje vivo (13.1%) — no es artefacto de la vara.
- Frecuencia: ~3.3 casos/día — fenómeno común, no curiosidad estadística.

## Hallazgo secundario (corrige la v1)
"Freno lento vs brusco" medido como pendiente (LAB-000, misma sesión) dio la
señal INVERTIDA (brusco 42.9% > lento 29.5%): la pendiente sola es mala vara.
Lo que predice no es la suavidad de la caída sino la MUERTE COMPLETA del
impulso. La Constitución se refina en ese sentido.

## Límites honestos
- Fenómeno ≠ trade: falta MFE/MAE y timing (Fase B) para saber si el rebote
  llega a tiempo/tamaño de una binaria de 15 min.
- EURUSD real ≠ OTC Quotex: validación final contra captura viva propia.
- REBOUND aquí = clasificación transitions_v1 (avance contrario ≥2× cuerpo
  mediano en 5 velas tras TRANSITION); umbrales versionados, recalibrables.
