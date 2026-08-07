# Informe de Agentes — Edificio ↔ Wyckoff Fase A (fase R0–R3)

> Convención: cada agente escribe su parte. El líder (Hermes) compila y cierra.
> Sesión 2026-08-07. Solo se usa evidencia anclada (datos en disco, reporte inmutable).
> Reglas de oro (ADR-039): (1) Edificio NO se modifica para encajar en Wyckoff;
> (2) volumen NUNCA requisito.

---

## 1. Trader-Humano

Rol: dueño del objetivo final y del marco de mercado.

- **Cambio de dirección**: el objetivo final es usar el Edificio como detector/timing
  de la **Fase A de Wyckoff para binarias**. No construir otro sistema alrededor del
  ratio `move/vol`.
- **Decisión de método**: radiografiar primero QUÉ estructura precede a los aciertos
  del Edificio (WIN) y a sus fallos (LOSS); después —y solo después— preguntar si eso
  es Fase A de Wyckoff. Eso evita imponer la teoría al algoritmo (curve fitting
  conceptual).
- **Reglas de oro dictadas y exigidas**:
  1. El Edificio **NO se modifica** para encajar en Wyckoff. Wyckoff se usa para
     explicar/clasificar la estructura que el Edificio YA explota.
  2. Volumen **NUNCA será requisito** fundamental. Si aporta, es evidencia adicional,
     no dependencia.
- **Aprobó el SDD** de la feature `edificio_wyckoff_phasea` (requirements/design/tasks).
- **Delegó los roles a la IA** y pidió aviso "cuando consigas la estructura adecuada".

---

## 2. Scientist

Rol: hipótesis, método, interpretación.

- **Hipótesis (R0–R3)**: ¿qué estructura de precio (OHLC+tiempo) precede a los WIN
  del Edificio, y cómo difiere de la que precede a los LOSS?
- **Diseño**:
  - Caja negra Edificio (no se toca `src/`).
  - Señales ya etiquetadas en `src/strategy_lab/results/edificio_events.parquet`
    (columna `win`, `split` train/test = OOS natural).
  - Contexto OHLC M15 previo (ventana N=20 velas) de
    `data/strategy_lab/cohorte_real_eurusd/EURUSD_M15.parquet` (543k velas, spot).
  - Features SOLO OHLC+tiempo: tendencia, impulso, compresión, lucha estructural.
- **Resultado (N = 946 señales con ventana válida)**. Separadores WIN/LOSS por
  |Cohen d| en TEST/OOS:
  1. `compression_ratio` — compresión de rango (ratio rango primeras 5 / últimas 5). **El más fuerte.**
  2. `break_fail_rate` — fallos de ruptura (tocar extremo y cerrar adentro).
  3. `impulse_mean_range` — rango medio de la ventana.
  4. `overlap_sum` — solapamiento entre velas.
  5. `body_range_ratio` — cuerpo/rango.
  - En TRAIN aparecen también `impulse_mean_range`, `overlap_sum`, `wick_ratio`,
    `body_range_ratio`. **Compresión y fallo de ruptura aparecen en ambos lados**
    → no es ruido de muestra.
- **Interpretación**: el Edificio ya explota **compresión + lucha de precios**; eso es
  la traducción OHLC de la Fase A de Wyckoff (agotamiento post-impulso, lucha en
  rango, fallos de ruptura). Todo **sin volumen** → regla de oro sostenida.
- **Retracción honesta (disciplina del proyecto)**: EW-1 (`move/vol` en 6E) no halló
  lo buscado — el −0.52 es reversión mecánica MA(1) del ratio, no memoria Wyckoff.
  EW-1 bajó a investigación auxiliar (`lab_ew_brake_link.py`, paralelo). NO se pagó
  Databento.

---

## 3. Engineer / Implementer

Rol: código y ejecución.

- Creó `scripts/lab_phaseA_radiografia.py` (standalone, **sin imports del Edificio**).
- Bugs corregidos en runtime:
  - variable `wick` era array → `float()` ilegal (eliminada; se usó `wick_ratio`).
  - división por `rng == 0` (velas sin rango) → `safe_rng` con máscara NaN.
  - `body_range` duplicado → dejado solo el cálculo seguro.
- **No tocó `src/`** (Edificio congelado, R1 cumplido).
- Usó **solo datasets en disco** (EURUSD_M15, edificio_events). Sin red, sin compras.
- Reporte inmutable en `data/strategy_lab/ew_reports/PHASEA-RADIO/`
  (`result.json` + `summary.md` + `protocol_frozen.json`).

---

## 4. Reviewer / QA

Rol: verificación y Charter.

- Verificación **ad-hoc** (no suite green; los scripts del lab están fuera de pytest
  por diseño del Lab Charter):
  - `py_compile` OK; import limpio sin side-effects.
  - Ejecución real: `rc 0`, **sin warnings**, 946 señales, reporte generado.
  - `src/` intacto confirmado; datos en disco; volumen no requisito.
- Protocolo inmutable: `protocol_frozen.json` con hashes de datasets + script + entorno.
- Declaración Charter: **Sí**.
- Temps de diagnóstico creados y borrados; repo limpio de temporales.

---

## 5. Líder (Hermes)

Rol: coordinación y cierre.

- SDD `edificio_wyckoff_phasea` cerrado y **APROBADO** por Trader-Humano.
- `ADR-039` escrito (reglas de oro). Feature `id 39` registrada en `feature_list.json`
  (`spec_ready`, `sdd: true`).
- **R0–R3 ejecutados y verificados** (commit `f7f13fe`, en `origin/main`, 0 ahead/0 behind).
- **La estructura adecuada YA se consiguió**: compresión de rango + fallos de ruptura
  son los separadores de WIN/LOSS del Edificio, coherentes con Fase A de Wyckoff, sin
  volumen. Se avisa al Trader-Humano según lo pedido.

---

## Próximos pasos (requieren OK del Trader-Humano)

- **R4** — Mapeo explícito de esas features a Fase A de Wyckoff.
- **R5** — Phase A Score (pesos por evidencia, no inventados).
- **R6** — Confirmación: Phase A context + señal Edificio.
- **R7** — Binarias: dirección + expiración (horizonte natural del Edificio).
- **R8–R10** — OOS/walk-forward, robustez (pares/sesiones), producción.
