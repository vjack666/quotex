# ADR-039 — Reglas de oro de la ruta Edificio↔Wyckoff (Fase A)

Fecha: 2026-08-07
Estado: APROBADO (Trader-Humano + Hermes, con poder delegado)

## Contexto
El proyecto pivota: el objetivo final es usar el Edificio como detector/timing de
la Fase A de Wyckoff para binarias. Riesgo identificado: modificar el Edificio
para que "parezca Wyckoff" = curve fitting conceptual (circular). También riesgo
de convertir la investigación en búsqueda de correlaciones con volumen, cuando el
volumen real no existe en el feed del Edificio (spot tick volume).

## Decisión (reglas de oro, escritas por el Trader-Humano)

1. **El Edificio NO se modifica para encajar en Wyckoff.** Wyckoff se usa como
   marco para explicar y clasificar la estructura que el Edificio YA explota.
2. **Volumen NUNCA será requisito fundamental de la hipótesis estructural.** Si
   aparece valor en volumen, será evidencia adicional, no dependencia.

## Consecuencias
- EW-1 (`move/vol` en 6E) baja de categoría a investigación auxiliar.
  `lab_ew_brake_link.py` queda como experimento paralelo, no ruta principal.
- La ruta principal usa OHLC + tiempo (M15/M5 del Edificio, spot EURUSD).
- El Edificio es caja negra durante R0–R3 (no se toca `src/edificio_contratacion.py`
  ni `src/scanner.py`).
- Orden de trabajo: radiografiar WIN/LOSS del Edificio primero; mapear a Wyckoff
  después (R3 antes que R4).

## Referencias
- `specs/edificio_wyckoff_phasea/` (requirements R1, R6; design alternativas)
- `docs/specs.md` (SDD + roles Trader-Humano/Scientist)
