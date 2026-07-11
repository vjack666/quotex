# SRS — Software Requirements Specification

> Proyecto QUOTEX · Estrategia STRAT-F (Wyckoff + Fractales, M15/M5/M1)
> Documento vivo de requisitos. Complementa `docs/ROADMAP.md` y los SDD en
> `specs/`. Los acrónimos usados aquí se definen en `docs/engineering/glosario.md`.

---

## 1. Propósito y alcance

Sistema de trading de opciones binarias que escanea múltiples pares en vivo,
evalúa setups con la estrategia STRAT-F y opera en cuenta de demostración
(Quotex practice / demo MetaQuotes) con gestión de riesgo.

**Objetivo de negocio (el "listo" del usuario):**
> Producir **5 entradas válidas dentro de una ventana de 2 horas** de
> operación, distribuidas en los distintos pares que entregue el escaneo,
> usando la estrategia STRAT-F (Wyckoff/Fractal, expiración 3 min).

Alcance:
- Solo lectura/operación en DEMO (no real).
- Marco temporal fijo: M15 (contexto), M5 (estructura/fractal), M1 (rechazo).
- Expiración fija de 3 minutos por operación.
- Principio rector: **nunca evaluar una señal en una sola vela**; el mercado
  deja rastro (formación de velas cerradas + ticks de Quotex).

Fuera de alcance (por ahora):
- Cuenta real / prop firm.
- Calibración automática con DSPy (futuro, ver ADR).
- Multi-agente (A2A) (futuro).

---

## 2. Actores

- **Trader (Ruben):** opera en demo, revisa panel y diario, acepta (UAT).
- **Bot (consolidation_bot + scanner):** escanea, evalúa, ejecuta, registra.
- **Agente IA (Hermes):** mantiene código, documentación y calibración.

---

## 3. Requisitos funcionales (FRS)

| ID | Requisito funcional | Origen |
|----|----------------------|--------|
| F1 | El sistema debe conectarse a la demo y obtener la lista de pares abiertos con payout >= 80%. | `config.MIN_PAYOUT` |
| F2 | El sistema debe bajar velas M15/M5/M1 de cada par evaluado. | `scanner._scan_phase_evaluate_assets` |
| F3 | El evaluador STRAT-F debe devolver señal solo si contexto M15, fractal M5 y rechazo M1 coinciden. | `strat_fractal.evaluate_strat_f` |
| F4 | El sistema debe rechazar si payout < 80% (R2). | `STRAT_F_MIN_PAYOUT` |
| F5 | El sistema debe rechazar si la zona del fractal tiene < 3 velas M5 de antigüedad (R3). | `STRAT_F_ZONE_MIN_AGE` |
| F6 | El sistema debe rechazar si el precio en M1 NO rechaza la banda (cierra fuera) (R4). | `evaluate_strat_f` |
| F7 | El sistema debe rechazar si la dirección es contra la tendencia M15 (R1). | `evaluate_strat_f` |
| F8 | El sistema debe rechazar si strength < 60 (R6). | `STRAT_F_MIN_SCORE` |
| F9 | Cada decisión (aceptada o rechazada) debe guardarse en el diario con su `skip_reason`, strength, payout, contexto M15 y velas M15/M5/M1. | `trade_journal.log_candidate` |
| F10 | El panel debe mostrar aceptadas (verde) y rechazadas (rojo) con su razón. | `hub/strat_f_state.py`, `hub/render.py` |
| F11 | Debe existir un reporte de calibración que agrupe rechazos por filtro y sugiera ajustes. | `calibration_report.py` |
| F12 | El backtester debe reconocer origen `STRAT-F` y reportar su win rate por separado. | `backtester._reevaluate_strat_f` |

---

## 4. Requisitos no funcionales (NFR)

| ID | Requisito no funcional | Valor / Criterio |
|----|------------------------|------------------|
| N1 | **Volumen objetivo** | El sistema debe ser capaz de producir **>= 5 entradas válidas en una ventana de 2h** (ver test ATDD `tests/test_window_2h.py`). |
| N2 | Tiempo de escaneo | Un ciclo de escaneo de ~14 pares debe completar en < 90s para dejar margen en la ventana. |
| N3 | Disponibilidad | Ventana de operación lun–vie 07:00–20:00 EC; el bot debe correr sin intervención manual durante esas horas. |
| N4 | Riesgo por ventana | No más de 5 entradas por ventana de 2h (límite de exposición Masaniello 5 ops / 60 min, ver `feature_list` Masaniello). |
| N5 | Calidad de decisión | Toda señal debe basarse en velas CERRADAS de 3 temporalidades; prohibido decidir en vela en formación. |
| N6 | Trazabilidad | Cada señal grabada debe ser reproducible (velas JSON en `candidates.candles_json` + `strategy_json`). |
| N7 | Verificabilidad | Todo cambio debe pasar `pytest` (actualmente 279 tests) antes de declararse "done". |
| N8 | Robustez | Ante caída de conexión, el bot debe reintentar; ante error de un par, continuar con los demás. |
| N9 | Sin secretos en repo | Credenciales solo en `.env` (gitignored). |

---

## 5. Métricas de aceptación (UAT)

- **A1 (el objetivo):** en una ventana de 2h de operación real en demo, el
  diario registra >= 5 entradas STRAT-F aceptadas. Medido por
  `python -m trade_journal --strat-f` y `python -m calibration_report`.
- **A2:** win rate de aceptadas resueltas >= 50% tras suficiente muestra
  (sugerido >= 30 trades para significancia).
- **A3:** el panel muestra en vivo aceptadas/rechazadas con razón.

---

## 6. Dependencias y supuestos

- Supuesto: Quotex envía campo `ticks` (no `volume`/`atime`); se usa para
  reforzar Fase A, no como order flow real.
- Supuesto: la demo tiene suficiente liquidez de pares OTC para alcanzar el
  volumen N1 en la ventana.
- Dependencia: `pyquotex` solo en venv (`.venv`) / Python313, no en global.
