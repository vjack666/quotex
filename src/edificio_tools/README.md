# Fabrica de Herramientas del Edificio (`src/edificio_tools/`)

Subpaquete del Edificio de Contratacion (feature 40, SDD `fabrica_herramientas_edificio`).
NO es un segundo edificio: es la fabrica de piezas que alimenta los pisos
P1->P2->P3 de `edificio_contratacion.py`.

## Orden de carpetas
```
src/edificio_tools/
  __init__.py     # exponte Evidence, Tool, load_catalog, get_tool, active_tools,
                   #          inspect, Decision, assemble, build_evidences,
                   #          assemble_from_tools
  evidence.py     # (R2) dataclass Evidence: direction/strength/confidence/stage — SIN orden
  registry.py     # (R1) dataclass Tool + loader del catalogo
  catalog.json    # herramientas ya medidas en el laboratorio (legible)
  inspector.py    # (R5) INSPECTOR: frena si direccion opuesta con confianza alta
  assembler.py    # (R4) ENSAMBLADOR: unico que produce BUY/SELL/NO_TRADE
  gate.py         # (R3/R4/R5/R8) punto de integracion con el Edificio en CONTRATADO
  README.md       # este archivo
  governor.py     # (R6) GOBERNADOR: tamaño Massaniello + veto DD  [Fase C, pendiente]
```

## Principio del contrato (R0-R16)
- Una HERRAMIENTA emite EVIDENCIA, nunca una orden (R2).
- El ENSAMBLADOR (R4) es el unico que produce BUY/SELL/NO_TRADE.
- El INSPECTOR (R5) frena si hay direccion opuesta con confianza alta.
- El GOBERNADOR (R6) calcula el tamaño (Massaniello) y veta por DD.
- Cada EXP del ciclo deja reporte en `reports/CICLO-XXX/EXP-NNN/` (R14/R15/R16).

## Herramientas registradas (ver `catalog.json`)
- `arcoiris_7ema` (EXP-EDF-04): gate P2, WR 70.6%, n=489.
- `valvula_kd` (EXP-EDF-FINAL): gate P3, WR 57.0%, n=5655.
- `cruce_limpio`: DESCARTADA (WR 48.4%).
- `composicion_arcoiris_valvula_kd` (EXP-077): WR ~60.5%, n combinado ~112k.

Ver `specs/fabrica_herramientas_edificio/` para el contrato completo.
