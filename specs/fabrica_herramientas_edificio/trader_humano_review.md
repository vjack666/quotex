# Revisión trader-humano — fabrica_herramientas_edificio

## Veredicto
APROBADO (spec) + CICLO-001 = CONTINUAR (dictamen de ciclo)

## Dictamen (lenguaje trader)
El spec formaliza correctamente: herramientas (evidencia, no orden), ensamblador,
inspector, gobernador, orquestador de ciclo (R0/R12), reporte individual por EXP
(R14), persistencia Git (R15), cierre condicionado (R16).

El CICLO-001 se ejecutó como lote congelado. Resultados reales (datos en disco):
- EXP-077 composición arcoíris+válvula K/D: WR ~59-61% en 5 datasets (EURUSD 2023/24,
  EURUSD OOS 2012-2022, XAUUSD) con n combinado GRANDE (miles-decenas de miles).
  La trampa del apilado NO se materializó: arcoíris (tendencia) y válvula K/D
  (presión) se refuerzan, no se solapan.
- EXP-080 OTC: WR 60.9/61.0% con n~5k (supera validación de dominio OTC).
- EXP-076 (timing broker, deuda crítica): CERRADO midiendo entry openPrice +300s /
  exit +900s sobre EURUSD OTC 60s reales → WR 67-75% (p≈0 vs breakeven 54%).
  La demora del broker NO mata el edge.

Decisión del director (R0, UNA sola): CICLO-001 = CONTINUAR.
Motivo: evidencia suficiente para preservar arquitectura; deuda EXP-076 era la
única crítica y se cerró. Acción: cerrar EXCLUSIVAMENTE EXP-076, sin reformular la
composición mientras la deuda viviera.

## Salvedad honesta (Charter Art. 10/13)
EXP-076 se midió en OTC 60s, no en spot. El mecanismo de demora del broker es común,
pero el WR puntual en spot puede diferir. Queda como deuda de validación en vivo
(demo REAL+OTC) antes de PROMOVER a producción. No es refutación de la hipótesis.

## Estado
Spec aprobado e in_progress. CICLO-001 ejecutado, reportes individuales + matriz en
GitHub. EXP-076 cerrado. Siguiente frontera: validación viva en spot.
